"""XRPL transport — anchor round-proof hashes as memo transactions.

This module defines the **synchronous** ``XRPLTransport``. The async sibling
``AsyncXRPLTransport`` lives at ``sov_transport.xrpl_async``; both consume
shared deterministic helpers from ``sov_transport.xrpl_internals``.

This module replaces the v2.0.x ``sov_transport.xrpl_testnet`` surface. It
parameterizes the network (testnet, mainnet, devnet) on a single
``XRPLTransport`` class and adds multi-memo single-tx batching for game-end
flush via ``anchor_batch``. The legacy ``xrpl_testnet`` module is kept as a
thin compat shim and is removed in v2.2.

Architectural notes
-------------------

* **Transport surface stays pure-chain.** ``is_anchored_on_chain`` returns a
  plain ``bool``. The 3-state ``AnchorStatus`` (anchored / pending / missing)
  is composed in ``sov_engine.proof`` by consulting the local
  ``pending-anchors.json`` index and then deferring to the transport for the
  on-chain check. Keeping the transport pure-chain keeps it free of engine
  state coupling.
* **Multi-memo, not packed.** ``anchor_batch`` puts N memos on a single
  ``Payment.Memos`` list — one ``SOV|...`` line per memo. Each memo is
  individually capped at ``_MAX_MEMO_BYTES = 1024``; that cap is per-memo,
  not per-tx, so the 16-round game flush fits comfortably without packing
  logic. ``FINAL`` round_keys render as the literal string ``FINAL`` in
  the memo (no ``r`` prefix); numeric round_keys render as ``r<N>``.
* **Network parameterization.** ``XRPLNetwork`` selects the JSON-RPC URL +
  explorer prefix. ``url=`` overrides the table; ``allow_insecure`` still
  gates non-https.
* **Shared internals.** Pure helpers + retry-policy constants + the network
  table live in ``sov_transport.xrpl_internals`` so the async sibling shares
  one source of truth. The retry **loop** stays per-impl: sync uses
  ``time.sleep``, async uses ``await asyncio.sleep``.
"""

from __future__ import annotations

import contextlib
import time

from sov_transport import TransportError
from sov_transport.base import BatchEntry, LedgerTransport
from sov_transport.xrpl_internals import (
    _MAX_BATCH_MEMO_BYTES,
    _MAX_MEMO_BYTES,
    _NETWORK_TABLE,
    _SUBMIT_BACKOFF_SECONDS,
    _SUBMIT_DEADLINE_SECONDS,
    _SUBMIT_MAX_ATTEMPTS,
    ChainLookupResult,
    MainnetFaucetError,
    XRPLNetwork,
    _classify_submit_error,
    _extract_memos,
    _format_memo,
    _from_hex,
    _to_hex,
    logger,
)

# Re-export surface for back-compat. Test modules and the deprecated
# ``xrpl_testnet`` shim import a handful of private helpers (``_to_hex``,
# ``_from_hex``, ``_extract_memos``, ``_classify_submit_error``) from
# ``sov_transport.xrpl`` directly. Keep them in ``__all__`` so mypy's
# ``--strict`` ``attr-defined`` check sees them as explicitly re-exported and
# the legacy compat layer keeps working without churn at every test site.
__all__ = [
    "ChainLookupResult",
    "MainnetFaucetError",
    "XRPLNetwork",
    "XRPLTransport",
    "_MAX_BATCH_MEMO_BYTES",
    "_MAX_MEMO_BYTES",
    "_NETWORK_TABLE",
    "_SUBMIT_BACKOFF_SECONDS",
    "_SUBMIT_DEADLINE_SECONDS",
    "_SUBMIT_MAX_ATTEMPTS",
    "_classify_submit_error",
    "_extract_memos",
    "_format_memo",
    "_from_hex",
    "_to_hex",
    "fund_dev_wallet",
    "logger",
]


class XRPLTransport(LedgerTransport):
    """Anchor round proof hashes on XRPL via self-payment memos.

    Network is selected by ``XRPLNetwork`` (testnet, mainnet, devnet); the
    JSON-RPC endpoint and explorer URL prefix come from an internal table.
    Pass ``url=`` to override the endpoint without changing the explorer
    prefix (useful for proxies or local testbeds against testnet).
    """

    def __init__(
        self,
        network: XRPLNetwork = XRPLNetwork.TESTNET,
        *,
        url: str | None = None,
        allow_insecure: bool = False,
    ) -> None:
        """Construct a transport bound to a network (and its endpoint).

        Args:
            network: Which XRPL network to talk to. Defaults to TESTNET to
                match v2.0.x defaults.
            url: Optional JSON-RPC endpoint override. When None, uses the
                table entry for ``network``. MUST use ``https://`` unless
                ``allow_insecure=True``.
            allow_insecure: Escape hatch for local testbeds. When True, the
                scheme check is bypassed and a WARNING is logged.

        Raises:
            ValueError: If the resolved url does not start with ``https://``
                and ``allow_insecure`` is False.
        """
        rpc_url, explorer_prefix = _NETWORK_TABLE[network]
        resolved_url = url if url is not None else rpc_url

        if not resolved_url.startswith("https://"):
            if allow_insecure:
                logger.warning("XRPLTransport: allow_insecure=True; using non-https endpoint")
            else:
                raise ValueError("XRPL endpoint must use https:// scheme")

        self.network = network
        self.url = resolved_url
        self._explorer_prefix = explorer_prefix

    def _explorer_root(self) -> str:
        """Return the network's explorer root (no path), e.g.
        ``https://testnet.xrpl.org``. Used for non-tx surfaces (account
        lookups, validator status pages) that want network-correct host
        without the ``/transactions/`` segment.
        """
        return self._explorer_prefix.rsplit("/transactions/", 1)[0]

    def explorer_tx_url(self, txid: str) -> str:
        """Return the explorer URL for ``txid`` on the configured network.

        Surfacing this here keeps explorer URLs out of CLI hardcoding — the
        v2.0.x ``testnet.xrpl.org`` literals at ``sov_cli/main.py:1241,1317``
        were the most visible network leak that drove the v2.1 redesign.
        """
        return f"{self._explorer_prefix}{txid}"

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Anchor a single round-proof hash. (Legacy single-round path.)

        Kept for backward compatibility with the deprecated
        ``sov anchor <proof_file>`` CLI form. New CLI surfaces should prefer
        ``anchor_batch`` (one tx per game with N memos) for audit ergonomics.
        The ``round_hash`` parameter is unused inside the impl — the memo
        string already carries the hash — but is part of the legacy API
        surface; it is removed with the deprecated form in v2.2.

        Args:
            round_hash: The SHA-256 hash of the round proof. (Currently
                unused — kept for v2.0.x API compatibility.)
            memo: Formatted memo string (e.g.
                ``SOV|campfire_v1|...|sha256:...``). Capped at 1024 UTF-8
                bytes.
            signer: The wallet seed (SECRET). This value is sensitive —
                callers SHOULD source it from an environment variable or
                secret store and MUST NOT log it. The seed is scrubbed from
                local scope in a finally block, and any exception raised here
                is sanitized to avoid leaking the seed via traceback locals
                or chained causes.

        Returns:
            The XRPL transaction hash (a hex string suitable for explorer
            lookup).

        Raises:
            ValueError: If the memo exceeds 1024 UTF-8 bytes.
            TransportError: If the network call exhausts retries within the
                deadline, the response indicates failure, or the response
                shape is missing the expected ``hash`` field.
        """
        del round_hash  # unused — preserved for legacy API surface
        try:
            if len(memo.encode("utf-8")) > _MAX_MEMO_BYTES:
                raise ValueError(f"memo exceeds {_MAX_MEMO_BYTES} bytes")
            return self._submit([memo], signer)
        finally:
            # Caller-frame seed scrub (BRIDGE-001). The inner ``_submit``
            # already rebinds its own ``signer`` local, but a sanitized
            # exception unwinding through this frame still carries the
            # caller-supplied ``signer`` in this frame's locals dict —
            # observability layers (Sentry with-locals, ipdb post-mortem)
            # can walk ``tb.tb_frame.f_locals`` and read it. Rebinding
            # makes the underlying string GC-eligible (assuming no other
            # refs) before the frame's locals are captured by tooling.
            signer = ""  # noqa: F841 — intentional caller-frame scrub

    def anchor_batch(self, rounds: list[BatchEntry], signer: str) -> str:
        """Anchor N rounds in one Payment via N memos. Returns single txid.

        Each ``BatchEntry`` becomes one ``Memo`` field on the same Payment,
        carrying the SOV grammar string ``SOV|<ruleset>|<game-id>|r<N>|
        sha256:<envelope_hash>`` (or ``FINAL`` literal for the final round).
        Each memo is individually capped at ``_MAX_MEMO_BYTES``; XRPL itself
        accepts ~150 memo fields per tx, so a 16-round game (15 + FINAL) is
        well inside the per-tx ceiling. This is the audit-ergonomics primary:
        one verifiable chain pointer per game, not a 16-tx trail.

        Args:
            rounds: Non-empty list of ``BatchEntry`` dicts. Order is
                preserved on the wire (the round_key is in the memo, so
                consumers can reorder by round_key if needed).
            signer: The wallet seed (SECRET). Same sensitivity as ``anchor``.

        Returns:
            The XRPL transaction hash for the single Payment carrying all
            memos.

        Raises:
            ValueError: If ``rounds`` is empty, or any individual rendered
                memo exceeds 1024 UTF-8 bytes.
            TransportError: If submission fails after the bounded retry /
                deadline.
        """
        try:
            if not rounds:
                raise ValueError("anchor_batch requires at least one round entry")

            memos: list[str] = []
            total_bytes = 0
            for entry in rounds:
                rendered = _format_memo(entry)
                memo_bytes = len(rendered.encode("utf-8"))
                if memo_bytes > _MAX_MEMO_BYTES:
                    raise ValueError(
                        f"memo for round_key={entry['round_key']!r} exceeds "
                        f"{_MAX_MEMO_BYTES} bytes ({memo_bytes})"
                    )
                total_bytes += memo_bytes
                memos.append(rendered)

            # BRIDGE-002: pre-submit total-tx-size validation. The XRPL
            # Payment wire limit is ~10KB practical; we cap the memo total
            # at 8KB to leave headroom for the rest of the envelope. Without
            # this guard a 16-round batch with a long ruleset / game-id
            # would push past the wire ceiling, the bounded retry loop
            # would classify the rejection as ``unknown`` and burn 3
            # attempts on a deterministic failure before surfacing an
            # opaque TransportError.
            if total_bytes > _MAX_BATCH_MEMO_BYTES:
                raise ValueError(
                    f"Batch payload {total_bytes} bytes exceeds XRPL Payment "
                    f"ceiling {_MAX_BATCH_MEMO_BYTES} bytes; reduce round "
                    "count or shorten ruleset / game-id to fit. "
                    "(Per-memo cap is unchanged at "
                    f"{_MAX_MEMO_BYTES} bytes; this is the per-tx total.)"
                )

            return self._submit(memos, signer)
        finally:
            # Caller-frame seed scrub (BRIDGE-001). See anchor() finally
            # block for rationale; same gap, same fix.
            signer = ""  # noqa: F841 — intentional caller-frame scrub

    def _submit(self, memos: list[str], signer: str) -> str:
        """Submit a Payment carrying one or more memos. Internal helper.

        Centralizes the retry policy, secret scrub, and error classification
        so ``anchor`` and ``anchor_batch`` can't drift apart. The caller is
        responsible for size-validation of each memo string before this
        helper sees it.
        """
        try:
            from xrpl.clients import JsonRpcClient
            from xrpl.models import Memo, Payment
            from xrpl.transaction import submit_and_wait
            from xrpl.wallet import Wallet
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        wallet = None
        try:
            client = JsonRpcClient(self.url)
            wallet = Wallet.from_seed(signer)

            # Log address (PUBLIC) — never the seed.
            logger.info(
                "anchor.submit account=%s url=%s memos=%d",
                repr(wallet.classic_address),
                self.url,
                len(memos),
            )

            tx_memos = [
                Memo(
                    memo_data=_to_hex(m),
                    memo_type=_to_hex("text/plain"),
                    memo_format=_to_hex("text/plain"),
                )
                for m in memos
            ]

            payment = Payment(
                account=wallet.address,
                destination=wallet.address,
                amount="1",  # 1 drop
                memos=tx_memos,
            )

            # Bounded retry loop with overall deadline. Transient errors
            # (network blips, LedgerNotFound) are retried with exponential
            # backoff; the loop exits early if the overall deadline is hit.
            deadline = time.monotonic() + _SUBMIT_DEADLINE_SECONDS
            response = None
            last_exc: Exception | None = None
            attempts_made = 0
            for attempt in range(_SUBMIT_MAX_ATTEMPTS):
                if time.monotonic() >= deadline:
                    break
                attempts_made = attempt + 1
                try:
                    response = submit_and_wait(payment, client, wallet)
                    break
                except Exception as submit_exc:
                    last_exc = submit_exc
                    reason = _classify_submit_error(submit_exc)
                    if attempt + 1 >= _SUBMIT_MAX_ATTEMPTS:
                        break
                    backoff = _SUBMIT_BACKOFF_SECONDS[
                        min(attempt, len(_SUBMIT_BACKOFF_SECONDS) - 1)
                    ]
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    sleep_for = min(backoff, remaining)
                    # Stable structured WARNING — operators can grep
                    # `anchor.retry reason=ledger_not_found` to triage.
                    logger.warning(
                        "anchor.retry attempt=%d/%d reason=%s exc=%s "
                        "remaining_s=%.1f sleep_s=%.1f "
                        "(transient error; retrying after %.1fs)",
                        attempt + 1,
                        _SUBMIT_MAX_ATTEMPTS,
                        reason,
                        type(submit_exc).__name__,
                        remaining,
                        sleep_for,
                        sleep_for,
                    )
                    time.sleep(sleep_for)

            if response is None:
                last_reason = _classify_submit_error(last_exc) if last_exc else "deadline"
                last_exc_name = type(last_exc).__name__ if last_exc else "Deadline"
                logger.error(
                    "anchor.exhausted attempts=%d deadline_s=%.1f reason=%s exc=%s",
                    attempts_made,
                    _SUBMIT_DEADLINE_SECONDS,
                    last_reason,
                    last_exc_name,
                )
                raise TransportError(
                    f"Anchor failed after {attempts_made} attempts within "
                    f"{_SUBMIT_DEADLINE_SECONDS:.0f}s deadline "
                    f"(last reason: {last_reason}, last error: {last_exc_name}). "
                    f"Check XRPL {self.network.value} status at "
                    f"{self._explorer_root()}/network/validators "
                    "then re-run `sov anchor` to retry."
                ) from last_exc

            # Guarded extraction: check is_successful() before trusting the
            # result envelope, and use .get() instead of [] so a missing
            # 'hash' raises a typed TransportError rather than a bare KeyError.
            is_ok = True
            check = getattr(response, "is_successful", None)
            if callable(check):
                try:
                    is_ok = bool(check())
                except Exception:
                    is_ok = True
            if not is_ok:
                result_for_hint = getattr(response, "result", None)
                engine_hint = ""
                if isinstance(result_for_hint, dict):
                    er = result_for_hint.get("engine_result")
                    if isinstance(er, str) and er:
                        engine_hint = f" (engine_result: {er})"
                raise TransportError(
                    "XRPL reported the submission was not successful"
                    f"{engine_hint}. This usually means a transaction-level "
                    "rejection (insufficient balance, bad auth, or path issue). "
                    f"Check the wallet on {self._explorer_root()} and retry "
                    "after fixing the underlying cause."
                )

            result = getattr(response, "result", None)
            if not isinstance(result, dict):
                raise TransportError(
                    "XRPL submit_and_wait response was successful but missing "
                    f"the expected result dict (got {type(result).__name__}). "
                    "This is unexpected; please file an issue at "
                    "https://github.com/mcp-tool-shop-org/sovereignty/issues "
                    "with the xrpl-py version you have installed."
                )
            tx_hash = result.get("hash")
            if not isinstance(tx_hash, str) or not tx_hash:
                shape_keys = sorted(result.keys()) if result else []
                raise TransportError(
                    "XRPL response was successful but missing 'hash' field. "
                    f"Response shape (keys only): {shape_keys}. "
                    "This is unexpected; please file an issue at "
                    "https://github.com/mcp-tool-shop-org/sovereignty/issues "
                    "with this shape and your xrpl-py version."
                )

            logger.info(
                "anchor.success tx=%s attempts=%d memos=%d",
                tx_hash,
                attempts_made,
                len(memos),
            )
            return tx_hash
        except Exception as e:
            # Re-raise the same exception type with a sanitized message that
            # does NOT contain the seed value, and suppress the __cause__
            # chain (`from None`) so the original traceback's local-variable
            # frame (which holds `signer` and `wallet`) does not propagate
            # to logging.exception / Sentry / observability layers.
            sanitized = (
                f"{type(e).__name__} in XRPLTransport submission "
                "(details suppressed to protect signer secret)"
            )
            logger.error(
                "anchor.terminal exc=%s (details suppressed to protect signer secret)",
                type(e).__name__,
            )
            try:
                raise type(e)(sanitized) from None
            except Exception:
                raise TransportError(sanitized) from None
        finally:
            # Rebind the local names so the underlying secret string becomes
            # GC-eligible (assuming no other refs). Python strs are immutable
            # so we cannot zero them in place. Rebinding (vs del) tolerates
            # the case where wallet was never bound on an early raise.
            wallet = None
            signer = ""  # noqa: F841 — intentional scrub of caller's seed

    def is_anchored_on_chain(self, txid: str, expected_hash: str) -> ChainLookupResult:
        """3-state on-chain lookup: did ``txid`` carry ``expected_hash``?

        Returns one of three states (BRIDGE-004) so engine-side state
        composition can distinguish "definitively not anchored" from "could
        not reach chain to ask":

        * ``ChainLookupResult.FOUND`` — the lookup succeeded AND a memo on
          ``txid`` encodes ``sha256:<expected_hash>`` via the SOV grammar
          (split on ``|``, equality-check the suffix).
        * ``ChainLookupResult.NOT_FOUND`` — the lookup succeeded AND no
          matching memo was present. This includes "tx exists but encodes
          a different envelope_hash" (chain drift) and "tx does not exist
          on chain" (xrpl-py reports ``txnNotFound``).
        * ``ChainLookupResult.LOOKUP_FAILED`` — the lookup itself failed
          (RPC unreachable, 5xx response, malformed result envelope). The
          chain has not given a verdict; engine maps this to ``MISSING``
          with a different reason so callers can choose to retry rather
          than cache the result as a definitive answer.

        The 3-state ``AnchorStatus`` (anchored / pending / missing) is
        composed in ``sov_engine.proof.proof_anchor_status`` — this
        method's contract is the chain-pure 3-state lookup, not the
        engine's pending-vs-anchored composition.

        Args:
            txid: The XRPL transaction hash (as returned by ``anchor`` or
                ``anchor_batch``). Must be non-empty.
            expected_hash: The SHA-256 hash we expect to find inside one of
                the tx's memos. Must be non-empty.

        Returns:
            One of ``ChainLookupResult.FOUND`` / ``NOT_FOUND`` /
            ``LOOKUP_FAILED``.

        Raises:
            ValueError: If ``txid`` or ``expected_hash`` is empty.
            RuntimeError: If xrpl-py is not installed.
        """
        if not txid:
            raise ValueError("txid must be non-empty")
        if not expected_hash:
            raise ValueError("expected_hash must be non-empty")

        try:
            from xrpl.clients import JsonRpcClient
            from xrpl.models import Tx
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        client = JsonRpcClient(self.url)
        try:
            try:
                response = client.request(Tx(transaction=txid))
            except Exception as e:
                # Network failure / RPC unreachable / 5xx propagated as a
                # raised exception by xrpl-py. The chain has not given us
                # a verdict; surface LOOKUP_FAILED so engine-side composition
                # can render this differently from a real "not on chain".
                logger.warning(
                    "is_anchored_on_chain.lookup_failed txid=%s exc=%s",
                    txid,
                    type(e).__name__,
                )
                return ChainLookupResult.LOOKUP_FAILED

            # Some xrpl-py paths return a Response with is_successful() == False
            # rather than raising. ``txnNotFound`` is a "definitively not on
            # chain" verdict (NOT_FOUND); other unsuccessful responses signal
            # a lookup failure (LOOKUP_FAILED).
            check = getattr(response, "is_successful", None)
            if callable(check):
                try:
                    ok = bool(check())
                except Exception:
                    ok = True
                if not ok:
                    result_for_err = getattr(response, "result", None)
                    err_token = None
                    if isinstance(result_for_err, dict):
                        err_token = result_for_err.get("error")
                    if err_token == "txnNotFound":
                        return ChainLookupResult.NOT_FOUND
                    logger.warning(
                        "is_anchored_on_chain.lookup_failed txid=%s error=%s",
                        txid,
                        err_token,
                    )
                    return ChainLookupResult.LOOKUP_FAILED

            memos = _extract_memos(response.result)
            for m in memos:
                if not isinstance(m, dict):
                    continue
                memo_obj = m.get("Memo", {})
                if not isinstance(memo_obj, dict):
                    continue
                data = _from_hex(memo_obj.get("MemoData", ""))
                if not data:
                    continue
                for field in data.split("|"):
                    if field.startswith("sha256:") and field[len("sha256:") :] == expected_hash:
                        return ChainLookupResult.FOUND
            return ChainLookupResult.NOT_FOUND
        finally:
            # Defensive client lifecycle — sync httpx requests close on
            # exit by default, but if a future xrpl-py release adds an
            # explicit ``close()`` we want to invoke it. Also mirrors the
            # async sibling's BRIDGE-005 lifecycle pattern.
            close = getattr(client, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):  # pragma: no cover
                    close()

    def get_memo_text(self, txid: str) -> str | None:
        """Retrieve the first decodable memo text from a transaction.

        Returns None if no memos are present or none decode cleanly. Memos
        that fail to decode are skipped rather than raising, so an
        adversarial memo cannot DoS this call.
        """
        if not txid:
            raise ValueError("txid must be non-empty")
        try:
            from xrpl.clients import JsonRpcClient
            from xrpl.models import Tx
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        client = JsonRpcClient(self.url)
        try:
            response = client.request(Tx(transaction=txid))

            memos = _extract_memos(response.result)
            for m in memos:
                if not isinstance(m, dict):
                    continue
                memo_obj = m.get("Memo", {})
                if not isinstance(memo_obj, dict):
                    continue
                data = _from_hex(memo_obj.get("MemoData", ""))
                if data:
                    return data
            return None
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):  # pragma: no cover
                    close()


def fund_dev_wallet(network: XRPLNetwork = XRPLNetwork.TESTNET) -> tuple[str, str]:
    """Generate a faucet-funded wallet for testnet or devnet.

    When to use: call this once during first-time onboarding to mint a fresh
    wallet you control. For repeat play, DO NOT call this again — instead,
    store the seed via the OS keychain or set the ``XRPL_SEED`` env var, then
    reuse that seed. Funding the faucet repeatedly wastes capacity and
    creates orphan wallets.

    Args:
        network: Which network to mint against. ``TESTNET`` and ``DEVNET``
            have public faucets; ``MAINNET`` does not and raises
            ``MainnetFaucetError``.

    Returns:
        A ``(address, seed)`` tuple. The ``seed`` is a SECRET — see security
        note below.

    Raises:
        MainnetFaucetError: If ``network=XRPLNetwork.MAINNET``. Operator
            action: provide a funded mainnet seed via ``XRPL_SEED``, or run
            ``sov wallet --network testnet`` for a testnet wallet.
        RuntimeError: If xrpl-py is not installed.

    SECURITY: The returned seed is a SECRET. Do not log, print, or transmit.
    Store via the OS keychain or set ``XRPL_SEED``. Treat the seed with the
    same care as a private key — anyone holding it can sign transactions
    from the wallet.
    """
    if network is XRPLNetwork.MAINNET:
        raise MainnetFaucetError(
            "mainnet has no faucet — set XRPL_SEED to a funded mainnet wallet, "
            "or run sov wallet --network testnet."
        )

    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.wallet import generate_faucet_wallet
    except ImportError as e:
        raise RuntimeError(
            "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
        ) from e

    rpc_url, _ = _NETWORK_TABLE[network]
    client = JsonRpcClient(rpc_url)
    wallet = generate_faucet_wallet(client)
    if wallet.seed is None:
        raise RuntimeError("xrpl wallet has no seed")
    return wallet.address, wallet.seed

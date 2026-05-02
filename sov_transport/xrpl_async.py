"""Async XRPL transport sibling — ``AsyncXRPLTransport``.

Parallel to the synchronous ``sov_transport.xrpl.XRPLTransport``. Both impls
consume shared deterministic helpers from ``sov_transport.xrpl_internals``
(memo grammar, retry-policy constants, error classification, network table,
hex codecs) so they cannot drift on the wire format or the failure-mode
vocabulary.

Why a sibling instead of an ABC
-------------------------------

There is intentionally **no** ``AsyncLedgerTransport`` ABC. Same logic as the
v2.1 Wave 2 Signer-protocol skip: do not abstract without a second async impl
pulling on it. ``AsyncXRPLTransport`` stands alone until a second async impl
(EVM, Solana, etc.) materializes; introducing the ABC pre-emptively bakes the
shape of *one* transport's surface into "the contract" and constrains the
next async impl in the wrong direction.

Driver
------

The daemon (Wave 3 sibling work) cannot block its event loop on synchronous
xrpl-py calls — a 30-second submit deadline on the sync transport stalls SSE
streaming + chain polling for every connected client. ``AsyncXRPLTransport``
keeps the daemon's loop responsive: anchoring runs as an awaitable task, SSE
keeps flowing, multiple endpoints can share one client instance.

Wire-level parity with sync
---------------------------

* Same SOV memo grammar (``SOV|<ruleset>|<game-id>|r<round_key>|sha256:<hash>``).
* Same per-memo size cap (``_MAX_MEMO_BYTES = 1024``).
* Same retry-policy constants — ``_SUBMIT_MAX_ATTEMPTS = 3``,
  ``_SUBMIT_BACKOFF_SECONDS = (1.0, 2.0, 4.0)``,
  ``_SUBMIT_DEADLINE_SECONDS = 30.0``.
* Same error classification (``_classify_submit_error`` token set).
* Same secret-scrub ``try/finally`` discipline — ``signer`` is rebound to
  the empty string on every exit path, ``__cause__`` is suppressed via
  ``raise ... from None`` so traceback locals don't leak the seed.
* Same logger name (``sov_transport``) and same structured ``anchor.*`` log
  events so a single grep works across sync + async deployments.

The retry **loop** is the only thing that diverges: ``await asyncio.sleep(...)``
substitutes for ``time.sleep(...)``, and the loop body is otherwise a verbatim
port. The ``submit_and_wait`` call site uses the async variants from
``xrpl.asyncio.{clients, transaction}``.
"""

from __future__ import annotations

import asyncio
import time

from sov_transport import TransportError
from sov_transport.base import BatchEntry
from sov_transport.xrpl_internals import (
    _MAX_BATCH_MEMO_BYTES,
    _MAX_MEMO_BYTES,
    _NETWORK_TABLE,
    _SUBMIT_BACKOFF_SECONDS,
    _SUBMIT_DEADLINE_SECONDS,
    _SUBMIT_MAX_ATTEMPTS,
    ChainLookupResult,
    XRPLNetwork,
    _classify_submit_error,
    _extract_memos,
    _format_memo,
    _from_hex,
    _to_hex,
    logger,
)

__all__ = ["AsyncXRPLTransport"]


class AsyncXRPLTransport:
    """Async sibling of ``XRPLTransport``. Same wire format, asyncio-friendly.

    Stands alone — there is no ``AsyncLedgerTransport`` ABC. See module
    docstring for the rationale (mirrors Wave 2's no-Signer-protocol stance).

    Network is selected by ``XRPLNetwork`` (testnet, mainnet, devnet); the
    JSON-RPC endpoint and explorer URL prefix come from the same internal
    table the sync impl uses (``sov_transport.xrpl_internals._NETWORK_TABLE``).
    Pass ``url=`` to override the endpoint without changing the explorer
    prefix.
    """

    def __init__(
        self,
        network: XRPLNetwork = XRPLNetwork.TESTNET,
        *,
        url: str | None = None,
        allow_insecure: bool = False,
    ) -> None:
        """Construct an async transport bound to a network (and its endpoint).

        Args:
            network: Which XRPL network to talk to. Defaults to TESTNET.
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
                logger.warning("AsyncXRPLTransport: allow_insecure=True; using non-https endpoint")
            else:
                raise ValueError("XRPL endpoint must use https:// scheme")

        self.network = network
        self.url = resolved_url
        self._explorer_prefix = explorer_prefix

    def _explorer_root(self) -> str:
        """Return the network's explorer root (no path), e.g.
        ``https://testnet.xrpl.org``. Sync — no I/O. Used for non-tx surfaces
        (account lookups, validator status pages) that want network-correct
        host without the ``/transactions/`` segment.
        """
        return self._explorer_prefix.rsplit("/transactions/", 1)[0]

    def explorer_tx_url(self, txid: str) -> str:
        """Return the explorer URL for ``txid`` on the configured network.

        Sync — pure string formatting, no I/O. Kept sync intentionally so
        callers don't have to ``await`` for what is just a URL build.
        """
        return f"{self._explorer_prefix}{txid}"

    async def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Async anchor a single round-proof hash. (Legacy single-round path.)

        Mirrors the sync ``XRPLTransport.anchor`` API exactly. ``round_hash``
        is unused (the memo carries the hash); preserved for API parity with
        the sync impl. Prefer ``anchor_batch`` for new call sites.

        Args:
            round_hash: The SHA-256 hash of the round proof. (Currently
                unused — kept for API parity.)
            memo: Formatted memo string. Capped at 1024 UTF-8 bytes.
            signer: The wallet seed (SECRET). Same secret-scrub discipline
                as the sync impl: rebound to ``""`` on every exit path,
                ``__cause__`` suppressed, exception messages sanitized.

        Returns:
            The XRPL transaction hash.

        Raises:
            ValueError: If the memo exceeds 1024 UTF-8 bytes.
            TransportError: On retry exhaustion / network failure / unexpected
                response shape.
        """
        del round_hash  # unused — preserved for legacy API surface
        try:
            if len(memo.encode("utf-8")) > _MAX_MEMO_BYTES:
                raise ValueError(f"memo exceeds {_MAX_MEMO_BYTES} bytes")
            return await self._submit([memo], signer)
        finally:
            # Caller-frame seed scrub (BRIDGE-001) — see sync sibling for
            # rationale. Same gap (Sentry with-locals + ipdb post-mortem
            # walking ``tb.tb_frame.f_locals`` up to this frame), same fix.
            signer = ""  # noqa: F841 — intentional caller-frame scrub

    async def anchor_batch(self, rounds: list[BatchEntry], signer: str) -> str:
        """Async anchor N rounds in one Payment via N memos. Returns single txid.

        Same wire format as the sync impl — one verifiable chain pointer per
        game, not a 16-tx trail. The async path lets the daemon flush a batch
        without blocking its event loop on the 30s submit deadline.

        Args:
            rounds: Non-empty list of ``BatchEntry`` dicts.
            signer: The wallet seed (SECRET).

        Returns:
            The XRPL transaction hash for the single Payment.

        Raises:
            ValueError: If ``rounds`` is empty, or any rendered memo exceeds
                1024 UTF-8 bytes.
            TransportError: On retry exhaustion / network failure / unexpected
                response shape.
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

            # BRIDGE-002: pre-submit total-tx-size validation. See sync
            # sibling for the design rationale (8KB cap leaves headroom
            # under the ~10KB XRPL Payment wire limit).
            if total_bytes > _MAX_BATCH_MEMO_BYTES:
                raise ValueError(
                    f"Batch payload {total_bytes} bytes exceeds XRPL Payment "
                    f"ceiling {_MAX_BATCH_MEMO_BYTES} bytes; reduce round "
                    "count or shorten ruleset / game-id to fit. "
                    "(Per-memo cap is unchanged at "
                    f"{_MAX_MEMO_BYTES} bytes; this is the per-tx total.)"
                )

            return await self._submit(memos, signer)
        finally:
            # Caller-frame seed scrub (BRIDGE-001) — see anchor() finally
            # block for rationale; same gap, same fix.
            signer = ""  # noqa: F841 — intentional caller-frame scrub

    async def _submit(self, memos: list[str], signer: str) -> str:
        """Async submit a Payment carrying one or more memos. Internal helper.

        Verbatim port of the sync ``_submit`` retry loop with
        ``await asyncio.sleep(...)`` substituted for ``time.sleep(...)`` and
        the async variants of ``JsonRpcClient`` / ``submit_and_wait`` from
        ``xrpl.asyncio``. All retry-policy constants, the error
        classification, the secret scrub, and the structured log events are
        shared with the sync impl via ``sov_transport.xrpl_internals``.
        """
        try:
            from xrpl.asyncio.clients import AsyncJsonRpcClient
            from xrpl.asyncio.transaction import submit_and_wait
            from xrpl.models import AccountSet, Memo
            from xrpl.wallet import Wallet
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        wallet = None
        try:
            client = AsyncJsonRpcClient(self.url)
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

            # Wave 10 BRIDGE-A-bis-001 (mirror of sync xrpl.py): Payment →
            # AccountSet swap. xrpl-py 4.5.0 added a self-payment validator
            # rejecting account == destination. AccountSet is the canonical
            # XRPL no-op memo vehicle. Verify side is transaction-type
            # agnostic. See sov_transport/xrpl.py for full rationale.
            payment = AccountSet(
                account=wallet.address,
                memos=tx_memos,
            )

            # Bounded retry loop with overall deadline. Verbatim from sync
            # impl with ``await asyncio.sleep`` substituted for ``time.sleep``.
            # Deadline tracking still uses ``time.monotonic()`` — that's a
            # pure clock read, not a blocking call.
            deadline = time.monotonic() + _SUBMIT_DEADLINE_SECONDS
            response = None
            last_exc: Exception | None = None
            attempts_made = 0
            for attempt in range(_SUBMIT_MAX_ATTEMPTS):
                if time.monotonic() >= deadline:
                    break
                attempts_made = attempt + 1
                try:
                    response = await submit_and_wait(payment, client, wallet)
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
                    await asyncio.sleep(sleep_for)

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
                    "This is an unexpected response shape from xrpl-py. "
                    "File an issue at "
                    "https://github.com/mcp-tool-shop-org/sovereignty/issues "
                    "with your installed xrpl-py version."
                )
            tx_hash = result.get("hash")
            if not isinstance(tx_hash, str) or not tx_hash:
                shape_keys = sorted(result.keys()) if result else []
                raise TransportError(
                    "XRPL response was successful but missing the 'hash' field. "
                    f"Response shape (keys only): {shape_keys}. "
                    "This is an unexpected response shape from xrpl-py. "
                    "File an issue at "
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
                f"{type(e).__name__} in AsyncXRPLTransport submission "
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

    async def is_anchored_on_chain(self, txid: str, expected_hash: str) -> ChainLookupResult:
        """Async 3-state on-chain lookup. Mirrors the sync sibling exactly.

        Returns one of ``ChainLookupResult.FOUND`` / ``NOT_FOUND`` /
        ``LOOKUP_FAILED`` per BRIDGE-004. See ``XRPLTransport.is_anchored_on_chain``
        for the full state semantics.

        Args:
            txid: Non-empty XRPL transaction hash.
            expected_hash: Non-empty SHA-256 hex digest to match.

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
            from xrpl.asyncio.clients import AsyncJsonRpcClient
            from xrpl.models import Tx
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        client = AsyncJsonRpcClient(self.url)
        try:
            try:
                response = await client.request(Tx(transaction=txid))
            except Exception as e:
                # BRIDGE-C-005: mirror sync sibling — log the cause category
                # alongside the exception type so an operator triaging the
                # log sees why the lookup didn't reach a verdict.
                logger.warning(
                    "is_anchored_on_chain.lookup_failed txid=%s "
                    "category=network_unreachable exc=%s detail=%s",
                    txid,
                    type(e).__name__,
                    str(e) or "no detail",
                )
                return ChainLookupResult.LOOKUP_FAILED

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
                    # BRIDGE-C-005: distinguish a known RPC error token from a
                    # missing/malformed envelope so the operator can tell
                    # whether the chain refused the lookup or returned junk.
                    category = "rpc_error" if err_token else "malformed_response"
                    logger.warning(
                        "is_anchored_on_chain.lookup_failed txid=%s category=%s error=%s",
                        txid,
                        category,
                        err_token or "none",
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
            # BRIDGE-005: async client lifecycle. xrpl-py 2.x's
            # ``AsyncJsonRpcClient`` does not currently expose a close
            # method (each request internally builds its own httpx
            # AsyncClient via ``async with``), but if a future release
            # adds explicit lifecycle we want to honor it. Pattern A
            # (try/finally per call) chosen over Pattern B (cached
            # client) because the audit's daemon-coordination concern
            # (per-tab × per-round polling) is naturally bounded by the
            # daemon's single-flight + 5s cache (DAEMON-006).
            await _maybe_aclose(client)

    async def get_memo_text(self, txid: str) -> str | None:
        """Async retrieve the first decodable memo text from a transaction.

        Returns ``None`` if no memos are present or none decode cleanly. Memos
        that fail to decode are skipped rather than raising, so an adversarial
        memo cannot DoS this call.
        """
        if not txid:
            raise ValueError("txid must be non-empty")
        try:
            from xrpl.asyncio.clients import AsyncJsonRpcClient
            from xrpl.models import Tx
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        client = AsyncJsonRpcClient(self.url)
        try:
            response = await client.request(Tx(transaction=txid))

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
            # BRIDGE-005: see ``is_anchored_on_chain`` for rationale.
            await _maybe_aclose(client)


async def _maybe_aclose(client: object) -> None:
    """Best-effort async close of an xrpl-py client.

    xrpl-py 2.x's ``AsyncJsonRpcClient`` does not currently expose an async
    ``close()`` / ``aclose()`` method (each ``request`` call internally builds
    its own ``httpx.AsyncClient`` via ``async with``, which closes on exit).
    This helper still tries the documented async-client lifecycle methods so
    the lifecycle pattern is forward-compatible — when xrpl-py adds an
    explicit close API or we cache + reuse a client (BRIDGE-005 Pattern B),
    we will not have to re-walk every call site.

    Tries (in order): ``aclose()`` (httpx-style), ``close()`` (sync). Both
    are best-effort: any exception is swallowed because we are in a
    ``finally`` block and a cleanup error must not mask the real one.
    """
    aclose = getattr(client, "aclose", None)
    if callable(aclose):
        try:
            result = aclose()
            # ``aclose`` may be sync or awaitable depending on the impl.
            if hasattr(result, "__await__"):
                await result
            return
        except Exception:  # pragma: no cover — best-effort cleanup
            return
    close = getattr(client, "close", None)
    if callable(close):
        try:
            result = close()
            if hasattr(result, "__await__"):
                await result
        except Exception:  # pragma: no cover — best-effort cleanup
            return

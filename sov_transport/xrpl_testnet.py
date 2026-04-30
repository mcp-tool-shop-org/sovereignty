"""XRPL Testnet transport — anchor round proof hashes as memo transactions."""

from __future__ import annotations

import logging
import time
from typing import Any

from sov_transport import TransportError
from sov_transport.base import LedgerTransport

TESTNET_URL = "https://s.altnet.rippletest.net:51234/"

# Maximum memo length in bytes. XRPL allows ~1KB per memo field; we cap at 1024
# to give the user a clear, actionable error before submission rather than a
# silent network-side rejection or truncation.
_MAX_MEMO_BYTES = 1024

# submit_and_wait retry policy. Bounded retry with exponential backoff guards
# against transient testnet glitches (LedgerNotFound, brief network drops)
# without hanging the user's CLI turn indefinitely.
_SUBMIT_MAX_ATTEMPTS = 3
_SUBMIT_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
_SUBMIT_DEADLINE_SECONDS = 30.0

logger = logging.getLogger("sov_transport")


def _to_hex(text: str) -> str:
    return text.encode("utf-8").hex()


def _from_hex(hex_str: str) -> str:
    """Decode a hex-encoded UTF-8 memo field.

    Returns the empty string on malformed input (odd-length hex, non-hex
    characters, or invalid UTF-8 byte sequences). This guards verify() and
    get_memo_text() against DoS via adversarial memos attached to fetched
    transactions.
    """
    if not hex_str:
        return ""
    try:
        return bytes.fromhex(hex_str).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""


def _classify_submit_error(exc: BaseException) -> str:
    """Classify a submit_and_wait exception into a stable, grep-able reason token.

    Returns one of: ``"network"``, ``"ledger_not_found"``, ``"signing_failed"``,
    ``"timeout"``, ``"unknown"``. The token is stable across releases so
    operators can grep logs (``reason=ledger_not_found``) and dashboards can
    aggregate by failure mode.
    """
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "ledger" in name or "ledger_not_found" in msg or "ledgernotfound" in name:
        return "ledger_not_found"
    if "sign" in name or "wallet" in name or "signing" in msg:
        return "signing_failed"
    if "timeout" in name or "timeout" in msg or "timed out" in msg:
        return "timeout"
    if (
        "connection" in name
        or "network" in name
        or "http" in name
        or "connect" in msg
        or "refused" in msg
        or "unreachable" in msg
    ):
        return "network"
    return "unknown"


def _extract_memos(result: dict[str, Any]) -> list[Any]:
    """Extract the Memos list from an xrpl-py Tx response result.

    The xrpl-py Tx response shape varies across versions: memos may live at
    the top level of ``result``, nested under ``result['tx']`` (which may be a
    dict or, in some response variants, a list whose first element is the tx
    dict), or be entirely absent. We try the documented shapes and fall back
    to an empty list with a WARNING log on unexpected shapes so operators can
    see the drift instead of silently getting empty results.
    """
    if not isinstance(result, dict):
        logger.warning(
            "_extract_memos: unexpected result type %s; returning []",
            type(result).__name__,
        )
        return []

    memos = result.get("Memos")
    if isinstance(memos, list) and memos:
        return memos

    tx = result.get("tx")
    if isinstance(tx, dict):
        nested = tx.get("Memos")
        return nested if isinstance(nested, list) else []
    if isinstance(tx, list) and tx:
        first = tx[0]
        if isinstance(first, dict):
            nested = first.get("Memos")
            return nested if isinstance(nested, list) else []
        logger.warning(
            "_extract_memos: result['tx'] is a list but first element is %s; returning []",
            type(first).__name__,
        )
        return []

    return []


class XRPLTestnetTransport(LedgerTransport):
    """Anchor round proof hashes on XRPL Testnet via self-payment memos."""

    def __init__(
        self,
        url: str = TESTNET_URL,
        *,
        allow_insecure: bool = False,
    ) -> None:
        """Construct a transport bound to an XRPL JSON-RPC endpoint.

        Args:
            url: The JSON-RPC endpoint URL. MUST use the ``https://`` scheme
                unless ``allow_insecure=True`` is explicitly passed. Plain
                http:// is rejected by default to avoid accidental
                credential/MITM exposure on hostile networks.
            allow_insecure: Escape hatch for local testbeds. When True, the
                scheme check is bypassed and a WARNING is logged.

        Raises:
            ValueError: If ``url`` does not start with ``https://`` and
                ``allow_insecure`` is False.
        """
        if not url.startswith("https://"):
            if allow_insecure:
                logger.warning(
                    "XRPLTestnetTransport: allow_insecure=True; using non-https endpoint"
                )
            else:
                raise ValueError("XRPL endpoint must use https:// scheme")
        self.url = url

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Anchor a round proof hash on XRPL Testnet for public auditability.

        When to use: call this once per completed round to publish the round's
        SHA-256 proof onto XRPL Testnet. The returned testnet tx hash becomes
        part of the round's anchor record and lets anyone (including the
        operator, players, or auditors) cross-check the round on
        https://livenet.xrpl.org via the testnet explorer.

        Implementation: posts a 1-drop self-payment whose memo carries the
        SOV-grammar string. Bounded retry with exponential backoff handles
        transient testnet glitches; the call gives up after ~30s.

        Args:
            round_hash: The SHA-256 hash of the round proof.
            memo: Formatted memo string (e.g. SOV|campfire_v1|...|sha256:...).
                Capped at 1024 UTF-8 bytes.
            signer: The wallet seed (SECRET). This value is sensitive — callers
                SHOULD source it from an environment variable or secret store
                and MUST NOT log it. The seed is scrubbed from local scope in a
                finally block, and any exception raised here is sanitized to
                avoid leaking the seed via traceback locals or chained causes.

        Returns:
            The XRPL transaction hash (a hex string suitable for explorer
            lookup at https://livenet.xrpl.org).

        Raises:
            ValueError: If the memo exceeds 1024 UTF-8 bytes. Operator action:
                shorten the memo and retry.
            TransportError: If the network call exhausts retries within the
                deadline, the response indicates failure, or the response
                shape is missing the expected ``hash`` field. The message
                explains whether to retry, check XRPL testnet status, or
                file an issue.
        """
        # Validate memo size BEFORE the secret-scrub try/except so the caller
        # gets a clear, untransformed ValueError on this user-input mistake.
        if len(memo.encode("utf-8")) > _MAX_MEMO_BYTES:
            raise ValueError(f"memo exceeds {_MAX_MEMO_BYTES} bytes")

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
                "anchor.submit account=%s url=%s",
                repr(wallet.classic_address),
                self.url,
            )

            tx_memo = Memo(
                memo_data=_to_hex(memo),
                memo_type=_to_hex("text/plain"),
                memo_format=_to_hex("text/plain"),
            )

            payment = Payment(
                account=wallet.address,
                destination=wallet.address,
                amount="1",  # 1 drop
                memos=[tx_memo],
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
                # All attempts exhausted (or deadline) without a response.
                # Build a concrete operator-actionable message and re-raise
                # into the secret-scrub wrapper below.
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
                    "Check XRPL testnet status at "
                    "https://livenet.xrpl.org/network/validators "
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
                    # Don't let a misbehaving response object hide the real
                    # outcome — fall through to the result-shape check.
                    is_ok = True
            if not is_ok:
                # Try to surface the engine_result if present — it's the most
                # actionable hint for an operator (tecPATH_DRY, tefBAD_AUTH,
                # etc.) without leaking secrets.
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
                    "Check the wallet on https://livenet.xrpl.org and retry "
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
                # Sanitize the response shape (keys only, no values) so we can
                # share it in the error without leaking transaction internals.
                shape_keys = sorted(result.keys()) if result else []
                raise TransportError(
                    "XRPL response was successful but missing 'hash' field. "
                    f"Response shape (keys only): {shape_keys}. "
                    "This is unexpected; please file an issue at "
                    "https://github.com/mcp-tool-shop-org/sovereignty/issues "
                    "with this shape and your xrpl-py version."
                )

            logger.info("anchor.success tx=%s attempts=%d", tx_hash, attempts_made)
            return tx_hash
        except Exception as e:
            # Re-raise the same exception type with a sanitized message that
            # does NOT contain the seed value, and suppress the __cause__
            # chain (`from None`) so the original traceback's local-variable
            # frame (which holds `signer` and `wallet`) does not propagate
            # to logging.exception / Sentry / observability layers.
            sanitized = (
                f"{type(e).__name__} in XRPLTestnetTransport.anchor "
                "(details suppressed to protect signer secret)"
            )
            logger.error(
                "anchor.terminal exc=%s (details suppressed to protect signer secret)",
                type(e).__name__,
            )
            try:
                raise type(e)(sanitized) from None
            except Exception:
                # Some exception subclasses don't accept a single str arg
                # (e.g. OSError requires (errno, strerror); xrpl-py's
                # XRPLException variants may require keyword-only args).
                # Broaden to Exception so any reconstruction failure falls
                # back to TransportError without exposing the seed via the
                # propagated original frame.
                raise TransportError(sanitized) from None
        finally:
            # Rebind the local names so the underlying secret string becomes
            # GC-eligible (assuming no other refs). Python strs are immutable
            # so we cannot zero them in place. Rebinding (vs del) tolerates
            # the case where wallet was never bound on an early raise.
            wallet = None
            signer = ""  # noqa: F841 — intentional scrub of caller's seed

    def verify(self, txid: str, expected_hash: str) -> bool:
        """Check whether an XRPL tx contains a memo encoding the expected hash.

        When to use: call this to audit a previously-anchored round. Given the
        ``txid`` returned by ``anchor()`` and the SHA-256 hash you expect to
        find inside, this looks up the transaction on XRPL Testnet and returns
        True if a matching ``sha256:<expected_hash>`` field is present.
        Returns False if the tx exists but has no matching memo (e.g. it was
        anchored by a different round, or the proof was tampered with).

        Performs a STRUCTURED parse of the SOV memo grammar
        (e.g. ``SOV|campfire_v1|s42|r1|sha256:<hash>``): splits the memo on
        ``|``, locates the field starting with ``sha256:``, and equality-checks
        the suffix against ``expected_hash``. This avoids the substring-match
        false positives of the prior implementation (e.g. an empty
        expected_hash matching any memo, or a short prefix coincidentally
        appearing inside an unrelated memo).

        Args:
            txid: The XRPL transaction hash (as returned by ``anchor()``).
            expected_hash: The SHA-256 hash we expect in the memo. Must be
                non-empty.

        Returns:
            True if any memo on the transaction encodes the expected hash;
            False otherwise (including the case where the tx exists but has
            no matching memo).

        Raises:
            ValueError: If ``expected_hash`` is empty. Operator action: pass
                a non-empty hash.
            RuntimeError: If xrpl-py is not installed. Install with
                ``pip install 'sovereignty-game[xrpl]'``.
        """
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
        response = client.request(Tx(transaction=txid))

        # Memos may live at result['Memos'] (top-level) or result['tx']['Memos']
        # (nested) depending on xrpl-py response shape. _extract_memos tries both.
        memos = _extract_memos(response.result)
        for m in memos:
            if not isinstance(m, dict):
                # Skip non-dict memo entries gracefully — defends against
                # shape drift in xrpl-py response variants.
                continue
            memo_obj = m.get("Memo", {})
            if not isinstance(memo_obj, dict):
                continue
            data = _from_hex(memo_obj.get("MemoData", ""))
            if not data:
                # Skip memos that fail to decode rather than crashing verify().
                continue
            for field in data.split("|"):
                if field.startswith("sha256:") and field[len("sha256:") :] == expected_hash:
                    return True
        return False

    def get_memo_text(self, txid: str) -> str | None:
        """Retrieve the first decodable memo text from a transaction.

        Returns None if no memos are present or none decode cleanly. Memos
        that fail to decode are skipped rather than raising, so an adversarial
        memo cannot DoS this call.
        """
        try:
            from xrpl.clients import JsonRpcClient
            from xrpl.models import Tx
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        client = JsonRpcClient(self.url)
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


def fund_testnet_wallet() -> tuple[str, str]:
    """Generate a new testnet wallet funded by the public XRPL faucet.

    When to use: call this once during first-time testnet onboarding to mint
    a fresh wallet you control. For repeat play (every other round after
    onboarding), DO NOT call this again — instead, store the seed returned
    here via the OS keychain or set the ``XRPL_SEED`` env var, then reuse
    that seed across runs. Funding the faucet repeatedly wastes testnet
    capacity and creates orphan wallets.

    Returns:
        A ``(address, seed)`` tuple. The ``seed`` is a SECRET — see security
        note below.

    SECURITY: The returned seed is a SECRET. Do not log, print, or transmit.
    Store via the OS keychain or set the ``XRPL_SEED`` env var. Treat the
    seed with the same care as a private key — anyone holding it can sign
    transactions from the wallet.
    """
    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.wallet import generate_faucet_wallet
    except ImportError as e:
        raise RuntimeError(
            "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
        ) from e

    client = JsonRpcClient(TESTNET_URL)
    wallet = generate_faucet_wallet(client)
    if wallet.seed is None:
        raise RuntimeError("xrpl wallet has no seed")
    return wallet.address, wallet.seed

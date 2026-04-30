"""XRPL Testnet transport — anchor round proof hashes as memo transactions."""

from __future__ import annotations

from sov_transport.base import LedgerTransport

TESTNET_URL = "https://s.altnet.rippletest.net:51234/"

# Maximum memo length in bytes. XRPL allows ~1KB per memo field; we cap at 1024
# to give the user a clear, actionable error before submission rather than a
# silent network-side rejection or truncation.
_MAX_MEMO_BYTES = 1024


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


def _extract_memos(result: dict) -> list:
    """Extract the Memos list from an xrpl-py Tx response result.

    The xrpl-py Tx response shape varies across versions: memos may live at
    the top level of `result` or nested under `result['tx']`. We try the
    documented top-level path first, then fall back to the nested path.
    """
    memos = result.get("Memos")
    if memos:
        return memos
    tx = result.get("tx")
    if isinstance(tx, dict):
        return tx.get("Memos", []) or []
    return []


class XRPLTestnetTransport(LedgerTransport):
    """Anchor round proof hashes on XRPL Testnet via self-payment memos."""

    def __init__(self, url: str = TESTNET_URL) -> None:
        self.url = url

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Post a self-payment with the round hash as a memo.

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
            The transaction hash.
        """
        # Validate memo size BEFORE the secret-scrub try/except so the caller
        # gets a clear, untransformed ValueError on this user-input mistake.
        if len(memo.encode("utf-8")) > _MAX_MEMO_BYTES:
            raise ValueError(
                f"memo exceeds {_MAX_MEMO_BYTES} bytes"
            )

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

            response = submit_and_wait(payment, client, wallet)
            tx_hash: str = response.result["hash"]
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
            try:
                raise type(e)(sanitized) from None
            except TypeError:
                # Some exception subclasses don't accept a single str arg;
                # fall back to a plain RuntimeError to preserve the scrub.
                raise RuntimeError(sanitized) from None
        finally:
            # Rebind the local names so the underlying secret string becomes
            # GC-eligible (assuming no other refs). Python strs are immutable
            # so we cannot zero them in place.
            del wallet, signer

    def verify(self, txid: str, expected_hash: str) -> bool:
        """Look up a transaction and check that its memo encodes the expected hash.

        Performs a STRUCTURED parse of the SOV memo grammar
        (e.g. ``SOV|campfire_v1|s42|r1|sha256:<hash>``): splits the memo on
        ``|``, locates the field starting with ``sha256:``, and equality-checks
        the suffix against ``expected_hash``. This avoids the substring-match
        false positives of the prior implementation (e.g. an empty
        expected_hash matching any memo, or a short prefix coincidentally
        appearing inside an unrelated memo).

        Args:
            txid: The XRPL transaction hash.
            expected_hash: The SHA-256 hash we expect in the memo. Must be
                non-empty.

        Returns:
            True if any memo on the transaction encodes the expected hash.
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
            memo_obj = m.get("Memo", {})
            data = _from_hex(memo_obj.get("MemoData", ""))
            if not data:
                # Skip memos that fail to decode rather than crashing verify().
                continue
            for field in data.split("|"):
                if field.startswith("sha256:") and field[len("sha256:"):] == expected_hash:
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
            memo_obj = m.get("Memo", {})
            data = _from_hex(memo_obj.get("MemoData", ""))
            if data:
                return data
        return None


def fund_testnet_wallet() -> tuple[str, str]:
    """Create and fund a new XRPL Testnet wallet. Returns (address, seed)."""
    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.wallet import generate_faucet_wallet
    except ImportError as e:
        raise RuntimeError(
            "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
        ) from e

    client = JsonRpcClient(TESTNET_URL)
    wallet = generate_faucet_wallet(client)
    return wallet.address, wallet.seed  # type: ignore[return-value]

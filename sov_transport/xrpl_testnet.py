"""XRPL Testnet transport — anchor round proof hashes as memo transactions."""

from __future__ import annotations

from sov_transport.base import LedgerTransport

TESTNET_URL = "https://s.altnet.rippletest.net:51234/"


def _to_hex(text: str) -> str:
    return text.encode("utf-8").hex()


def _from_hex(hex_str: str) -> str:
    return bytes.fromhex(hex_str).decode("utf-8") if hex_str else ""


class XRPLTestnetTransport(LedgerTransport):
    """Anchor round proof hashes on XRPL Testnet via self-payment memos."""

    def __init__(self, url: str = TESTNET_URL) -> None:
        self.url = url

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Post a self-payment with the round hash as a memo.

        Args:
            round_hash: The SHA-256 hash of the round proof.
            memo: Formatted memo string (e.g. SOV|campfire_v1|...|sha256:...).
            signer: The wallet seed (secret).

        Returns:
            The transaction hash.
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

    def verify(self, txid: str, expected_hash: str) -> bool:
        """Look up a transaction and check that its memo contains the expected hash.

        Args:
            txid: The XRPL transaction hash.
            expected_hash: The SHA-256 hash we expect in the memo.

        Returns:
            True if the memo contains the expected hash.
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

        memos = response.result.get("Memos", [])
        for m in memos:
            memo_obj = m.get("Memo", {})
            data = _from_hex(memo_obj.get("MemoData", ""))
            if expected_hash in data:
                return True
        return False

    def get_memo_text(self, txid: str) -> str | None:
        """Retrieve the memo text from a transaction. Returns None if not found."""
        try:
            from xrpl.clients import JsonRpcClient
            from xrpl.models import Tx
        except ImportError as e:
            raise RuntimeError(
                "xrpl-py is not installed. Install with: pip install 'sovereignty-game[xrpl]'"
            ) from e

        client = JsonRpcClient(self.url)
        response = client.request(Tx(transaction=txid))

        memos = response.result.get("Memos", [])
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

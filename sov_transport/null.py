"""Null transport — offline mode, no ledger interaction."""

from __future__ import annotations

from sov_transport.base import LedgerTransport


class NullTransport(LedgerTransport):
    """Offline-mode transport — no ledger interaction.

    ``anchor`` returns ``offline:<round_hash[:16]>`` (a deterministic local
    txid, not a cryptographic anchor). ``verify`` returns True for any txid
    that begins with ``offline:`` — by design, since offline-mode trust comes
    from local proof files, not from on-ledger inspection.

    Strict-verify mode: pass ``strict_verify=True`` to the constructor and
    ``verify`` will raise ``NotImplementedError`` instead of returning True.
    Use this in test or audit contexts where a silent always-pass would mask
    a missing real transport — it forces the caller to wire up
    ``XRPLTestnetTransport`` (or another real ledger) for actual verification.
    """

    def __init__(self, *, strict_verify: bool = False) -> None:
        """Construct a NullTransport.

        Args:
            strict_verify: If True, ``verify`` raises NotImplementedError
                instead of returning True for ``offline:``-prefixed txids.
                Defaults to False to preserve existing offline-mode behavior.
        """
        self.strict_verify = strict_verify

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        return f"offline:{round_hash[:16]}"

    def verify(self, txid: str, expected_hash: str) -> bool:
        # In offline mode, verification is done via local proof files; this
        # returns True for any offline:-prefixed txid as a passthrough.
        if self.strict_verify:
            raise NotImplementedError(
                "NullTransport.verify cannot validate cryptographic anchors. "
                "Construct with strict_verify=False to allow always-True "
                "passthrough, or use XRPLTestnetTransport for real verification."
            )
        return txid.startswith("offline:")

    def get_memo_text(self, txid: str) -> str | None:
        """Offline mode has no on-ledger memos; return None as a no-op."""
        return None

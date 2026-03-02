"""Null transport — offline mode, no ledger interaction."""

from __future__ import annotations

from sov_transport.base import LedgerTransport


class NullTransport(LedgerTransport):
    """Offline transport that stores nothing. Used for local play."""

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        return f"offline:{round_hash[:16]}"

    def verify(self, txid: str, expected_hash: str) -> bool:
        # In offline mode, verification is done via local proof files
        return txid.startswith("offline:")

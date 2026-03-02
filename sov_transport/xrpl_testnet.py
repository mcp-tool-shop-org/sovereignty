"""XRPL Testnet transport — stub for Phase 1."""

from __future__ import annotations

from sov_transport.base import LedgerTransport


class XRPLTestnetTransport(LedgerTransport):
    """XRPL Testnet transport. Stub — not implemented in Phase 1."""

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        raise NotImplementedError(
            "XRPL transport is not enabled yet. Use offline mode (NullTransport) for Phase 1."
        )

    def verify(self, txid: str, expected_hash: str) -> bool:
        raise NotImplementedError(
            "XRPL transport is not enabled yet. Use offline mode (NullTransport) for Phase 1."
        )

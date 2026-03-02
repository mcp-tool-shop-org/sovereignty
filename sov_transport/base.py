"""Abstract base for ledger transports."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LedgerTransport(ABC):
    """Interface for anchoring round proofs to a ledger."""

    @abstractmethod
    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Anchor a round proof hash. Returns transaction ID or reference."""
        ...

    @abstractmethod
    def verify(self, txid: str, expected_hash: str) -> bool:
        """Verify that a transaction contains the expected hash."""
        ...

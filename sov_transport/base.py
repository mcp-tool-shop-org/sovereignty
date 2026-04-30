"""Abstract base for ledger transports."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LedgerTransport(ABC):
    """Abstract transport for anchoring round proofs.

    Implementations must support three operations:

    * ``anchor`` — submit a round proof and return a ledger-native txid.
    * ``verify`` — check that a txid contains the expected round-proof hash.
    * ``get_memo_text`` — retrieve the first decodable memo attached to a tx.

    Implementations MUST provide ``anchor`` and ``verify``. ``get_memo_text``
    is part of the contract so all transports (NullTransport, XRPLTestnetTransport,
    future EVMTransport, etc.) share a uniform polymorphic surface; the base
    class default raises ``NotImplementedError`` so a transport that genuinely
    cannot retrieve memos (e.g. an offline shim) can opt out explicitly.

    Txid prefix reservation: the ``offline:`` txid prefix is RESERVED for
    NullTransport. Real ledger transports MUST return their own native txid
    format (e.g. XRPL hex hash, EVM 0x-prefixed hash) and MUST NOT use the
    ``offline:`` prefix, which downstream code uses as a routing signal.
    """

    @abstractmethod
    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Anchor a round proof hash. Returns transaction ID or reference."""
        ...

    @abstractmethod
    def verify(self, txid: str, expected_hash: str) -> bool:
        """Verify that a transaction contains the expected hash."""
        ...

    def get_memo_text(self, txid: str) -> str | None:
        """Retrieve the first decodable memo text from a transaction.

        Default implementation raises ``NotImplementedError``. Concrete
        transports should override this to provide memo retrieval; offline
        transports may return ``None`` to signal absence rather than refusal.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement get_memo_text")

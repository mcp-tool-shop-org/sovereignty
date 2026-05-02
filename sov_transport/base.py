"""Abstract base for ledger transports."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import TypedDict


class BatchEntry(TypedDict):
    """One round's worth of anchor data for ``LedgerTransport.anchor_batch``.

    Fields mirror the SOV memo grammar
    ``SOV|<ruleset>|<game-id>|r<round_key>|sha256:<envelope_hash>``. The
    ``round_key`` is a stringified integer (``"1"``..``"15"``) or the literal
    ``"FINAL"`` — same convention as ``anchors.json`` and
    ``pending-anchors.json``. ``envelope_hash`` is the raw 64-char hex digest
    (no ``sha256:`` prefix; the prefix is added at the wire layer only).
    """

    round_key: str
    ruleset: str
    game_id: str
    envelope_hash: str


class LedgerTransport(ABC):
    """Abstract transport for anchoring round proofs.

    Implementations must support five operations:

    * ``anchor`` — submit a single round proof and return a ledger-native
      txid. Kept for backward compat with the deprecated single-round CLI
      form; new callers should prefer ``anchor_batch``.
    * ``anchor_batch`` — submit N rounds in one tx (multi-memo on XRPL).
      One verifiable chain pointer per game, not a scattered N-tx trail.
    * ``is_anchored_on_chain`` — pure on-chain lookup. Returns ``bool``; the
      3-state ``AnchorStatus`` composition lives in the engine layer
      (``sov_engine.proof.proof_anchor_status``) so the transport does not
      couple to local pending-state.
    * ``explorer_tx_url`` — explorer URL for the configured network. Lets
      CLI surfaces stop hardcoding network-specific URLs.
    * ``get_memo_text`` — retrieve the first decodable memo on a tx.

    ``verify`` is kept as a deprecated alias for ``is_anchored_on_chain``
    until v2.2; it emits ``DeprecationWarning`` on call.

    Txid prefix reservation: the ``offline:`` txid prefix is RESERVED for
    NullTransport. Real ledger transports MUST return their own native txid
    format (e.g. XRPL hex hash, EVM 0x-prefixed hash) and MUST NOT use the
    ``offline:`` prefix, which downstream code uses as a routing signal.
    """

    @abstractmethod
    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        """Anchor a single round-proof hash. Returns transaction id/reference.

        Legacy single-round path. ``round_hash`` may be unused inside the
        implementation (the memo carries the hash); preserved for backward
        compat with the deprecated ``sov anchor <proof_file>`` CLI form.
        """
        ...

    @abstractmethod
    def anchor_batch(self, rounds: list[BatchEntry], signer: str) -> str:
        """Anchor N rounds in a single transaction. Returns one txid.

        On XRPL, this packs N memos onto one ``Payment.Memos``. ``rounds``
        must be non-empty; empty input raises ``ValueError`` at the
        implementation layer.
        """
        ...

    @abstractmethod
    def is_anchored_on_chain(self, txid: str, expected_hash: str) -> bool:
        """Pure on-chain lookup: does ``txid`` carry ``expected_hash``?

        Returns ``True`` if any memo on the transaction encodes the expected
        hash via the SOV grammar; ``False`` otherwise. The 3-state
        ``AnchorStatus`` composition is the engine's responsibility — this
        method intentionally returns a plain ``bool``.
        """
        ...

    @abstractmethod
    def explorer_tx_url(self, txid: str) -> str:
        """Return the explorer URL for ``txid`` on this transport's network.

        Real ledger transports return a publicly browsable URL; offline
        transports return a synthetic placeholder.
        """
        ...

    def verify(self, txid: str, expected_hash: str) -> bool:
        """Deprecated alias for ``is_anchored_on_chain``.

        Removed in v2.2. New callers should use ``is_anchored_on_chain``
        directly; the engine's ``proof_anchor_status`` already does.
        """
        warnings.warn(
            "LedgerTransport.verify() is deprecated; use is_anchored_on_chain()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.is_anchored_on_chain(txid, expected_hash)

    def get_memo_text(self, txid: str) -> str | None:
        """Retrieve the first decodable memo text from a transaction.

        Default implementation raises ``NotImplementedError``. Concrete
        transports should override this to provide memo retrieval; offline
        transports may return ``None`` to signal absence rather than refusal.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement get_memo_text")

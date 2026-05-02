"""Abstract base for ledger transports."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TypedDict


class ChainLookupResult(StrEnum):
    """3-state result from ``is_anchored_on_chain`` (BRIDGE-004).

    Lives on the abstract base so every concrete transport (XRPL sync,
    XRPL async, NullTransport, future EVM/Solana) returns the same shape.
    Re-exported by ``sov_transport.xrpl_internals`` and the package root
    (``sov_transport.ChainLookupResult``) for ergonomic call sites.

    ``FOUND`` — the lookup succeeded AND a memo carrying
        ``sha256:<expected>`` was present on the transaction. Engine maps
        this to ``AnchorStatus.ANCHORED``.

    ``NOT_FOUND`` — the lookup succeeded AND no matching memo was present.
        Includes "tx exists but encodes a different envelope_hash" (chain
        drift) and "tx does not exist on chain" (txnNotFound). Engine
        maps this to ``AnchorStatus.MISSING`` — a definitive verdict.

    ``LOOKUP_FAILED`` — the lookup itself failed (RPC unreachable, 5xx,
        malformed response). The chain has not given a verdict on whether
        the proof is anchored. Engine maps this to ``AnchorStatus.MISSING``
        with a different reason ("could not reach chain") so callers can
        choose to retry instead of caching the result.

    ``StrEnum`` so values round-trip through JSON / SSE events without
    bespoke (de)serialization. Stable string values (``"found"`` /
    ``"not_found"`` / ``"lookup_failed"``) are part of the audit surface
    — operators may grep for them in logs and dashboards.
    """

    FOUND = "found"
    NOT_FOUND = "not_found"
    LOOKUP_FAILED = "lookup_failed"


# intentional non-mirror: BatchEntry is bridge-internal, no frontend consumer.
# A repo-wide grep for ``BatchEntry`` in app/ returns zero hits — the daemon
# composes batches via its anchor-flush path and never exposes the shape over
# HTTP. If a future Tauri command exposes batch composition to the shell,
# mirror to ``app/src/types/daemon.ts`` and pin via
# ``tests/test_daemon_types_ts_in_sync.py``. Tracked: BRIDGE-B-006.
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
    * ``is_anchored_on_chain`` — pure on-chain lookup. Returns a
      ``ChainLookupResult`` (FOUND / NOT_FOUND / LOOKUP_FAILED) so the
      engine layer can distinguish "definitively not on chain" from
      "could not reach the chain to ask" when composing the 3-state
      ``AnchorStatus`` (``sov_engine.proof.proof_anchor_status``).
    * ``explorer_tx_url`` — explorer URL for the configured network. Lets
      CLI surfaces stop hardcoding network-specific URLs.
    * ``get_memo_text`` — retrieve the first decodable memo on a tx.

    ``verify`` is kept as a deprecated alias for ``is_anchored_on_chain``
    until v2.2; it emits ``DeprecationWarning`` on call and converts the
    ``ChainLookupResult`` back to a plain ``bool`` (FOUND → True, all
    other states → False) for ABI parity with v2.0.x callers.

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
    def anchor_batch(self, rounds: list[BatchEntry], signer: str) -> list[str]:
        """Anchor N rounds across one or more transactions. Returns txid trail.

        On XRPL, each transaction (an AccountSet carrying memos) is bounded
        by rippled's aggregate Memos-field cap (~1 KB on the wire, ≤8
        memos for the SOV grammar). When ``rounds`` exceeds the per-tx cap,
        the implementation splits the batch into N sequential txs of ≤cap
        memos each and returns one txid per tx in submission order.

        ``rounds`` must be non-empty; empty input raises ``ValueError`` at
        the implementation layer. A 1-element ``rounds`` list returns a
        1-element txid list. Order is preserved across chunk boundaries
        (the first chunk carries the lowest round_keys).
        """
        ...

    @abstractmethod
    def is_anchored_on_chain(self, txid: str, expected_hash: str) -> ChainLookupResult:
        """Pure on-chain lookup with 3-state result.

        Returns:
            ``ChainLookupResult.FOUND`` — lookup succeeded AND a memo on
                ``txid`` encodes ``sha256:<expected_hash>``.
            ``ChainLookupResult.NOT_FOUND`` — lookup succeeded AND no
                matching memo was present (tx absent, or tx present but
                encodes a different envelope_hash).
            ``ChainLookupResult.LOOKUP_FAILED`` — the lookup itself failed
                (RPC unreachable, 5xx, malformed response). The chain has
                not given a verdict; callers should retry rather than
                cache the result as a definitive answer.

        The 3-state ``AnchorStatus`` composition is the engine's
        responsibility (``sov_engine.proof.proof_anchor_status``) — this
        method's contract is the chain-pure 3-state lookup, not the
        engine's pending-vs-anchored composition.
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

        Returns ``True`` only when the chain lookup confirms a matching
        memo (``ChainLookupResult.FOUND``). Both ``NOT_FOUND`` and
        ``LOOKUP_FAILED`` collapse to ``False`` for ABI parity with the
        v2.0.x ``bool``-returning surface; new callers wanting to
        distinguish "definitively not anchored" from "could not reach
        chain" should call ``is_anchored_on_chain`` directly.
        """
        warnings.warn(
            "LedgerTransport.verify() is deprecated; use is_anchored_on_chain(). "
            "This method will be removed in v2.2.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.is_anchored_on_chain(txid, expected_hash) is ChainLookupResult.FOUND

    def get_memo_text(self, txid: str) -> str | None:
        """Retrieve the first decodable memo text from a transaction.

        Default implementation raises ``NotImplementedError``. Concrete
        transports should override this to provide memo retrieval; offline
        transports may return ``None`` to signal absence rather than refusal.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement get_memo_text")

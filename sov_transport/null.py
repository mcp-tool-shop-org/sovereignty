"""Null transport — offline mode, no ledger interaction."""

from __future__ import annotations

from sov_transport.base import BatchEntry, LedgerTransport


class NullTransport(LedgerTransport):
    """Offline-mode transport — no ledger interaction.

    ``anchor`` returns ``offline:<round_hash[:16]>`` (a deterministic local
    txid, not a cryptographic anchor). ``anchor_batch`` returns
    ``offline:batch:<envelope_hash[:16]>`` keyed off the first entry's hash —
    distinct prefix so downstream code can recognize batched offline txids
    if the routing distinction ever matters. ``is_anchored_on_chain`` returns
    True for any txid that begins with ``offline:`` — by design, since
    offline-mode trust comes from local proof files, not on-ledger inspection.

    Strict-verify mode: pass ``strict_verify=True`` to the constructor and
    ``is_anchored_on_chain`` will raise ``NotImplementedError`` instead of
    returning True. Use this in test or audit contexts where a silent
    always-pass would mask a missing real transport — it forces the caller
    to wire up ``XRPLTransport`` (or another real ledger) for actual
    verification.
    """

    def __init__(self, *, strict_verify: bool = False) -> None:
        """Construct a NullTransport.

        Args:
            strict_verify: If True, ``is_anchored_on_chain`` raises
                NotImplementedError instead of returning True for
                ``offline:``-prefixed txids. Defaults to False to preserve
                existing offline-mode behavior.
        """
        self.strict_verify = strict_verify

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        return f"offline:{round_hash[:16]}"

    def anchor_batch(self, rounds: list[BatchEntry], signer: str) -> str:
        """Return a deterministic local marker for an offline batch.

        Keyed off the first entry's envelope_hash so the marker is stable
        for a given batch contents. Empty input is rejected to mirror the
        XRPL transport's contract (which would otherwise produce an empty
        Payment.Memos).
        """
        if not rounds:
            raise ValueError("anchor_batch requires at least one round entry")
        return f"offline:batch:{rounds[0]['envelope_hash'][:16]}"

    def is_anchored_on_chain(self, txid: str, expected_hash: str) -> bool:
        # In offline mode, verification is done via local proof files; this
        # returns True for any offline:-prefixed txid as a passthrough.
        if self.strict_verify:
            raise NotImplementedError(
                "NullTransport.is_anchored_on_chain cannot validate "
                "cryptographic anchors. Construct with strict_verify=False "
                "to allow always-True passthrough, or use XRPLTransport for "
                "real verification."
            )
        return txid.startswith("offline:")

    def explorer_tx_url(self, txid: str) -> str:
        """No real chain — return a synthetic offline:// URL placeholder."""
        return f"offline://tx/{txid}"

    def get_memo_text(self, txid: str) -> str | None:
        """Offline mode has no on-ledger memos; return None as a no-op."""
        return None

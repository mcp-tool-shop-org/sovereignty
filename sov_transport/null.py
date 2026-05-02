"""Null transport — offline mode, no ledger interaction."""

from __future__ import annotations

from sov_transport.base import BatchEntry, LedgerTransport
from sov_transport.xrpl_internals import ChainLookupResult


class NullTransport(LedgerTransport):
    """Offline-mode transport — no ledger interaction.

    ``anchor`` returns ``offline:<round_hash[:16]>`` (a deterministic local
    txid, not a cryptographic anchor). ``anchor_batch`` returns
    ``offline:batch:<envelope_hash[:16]>`` keyed off the first entry's hash —
    distinct prefix so downstream code can recognize batched offline txids
    if the routing distinction ever matters. ``is_anchored_on_chain`` returns
    ``ChainLookupResult.FOUND`` for any txid that begins with ``offline:`` —
    by design, since offline-mode trust comes from local proof files, not
    on-ledger inspection.

    Strict-verify mode: pass ``strict_verify=True`` to the constructor and
    ``is_anchored_on_chain`` will raise ``NotImplementedError`` instead of
    returning ``FOUND``. Use this in test or audit contexts where a silent
    always-pass would mask a missing real transport — it forces the caller
    to wire up ``XRPLTransport`` (or another real ledger) for actual
    verification.
    """

    def __init__(self, *, strict_verify: bool = False) -> None:
        """Construct a NullTransport.

        Args:
            strict_verify: If True, ``is_anchored_on_chain`` raises
                NotImplementedError instead of returning ``FOUND`` for
                ``offline:``-prefixed txids. Defaults to False to preserve
                existing offline-mode behavior.
        """
        self.strict_verify = strict_verify

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        return f"offline:{round_hash[:16]}"

    def anchor_batch(self, rounds: list[BatchEntry], signer: str) -> list[str]:
        """Return a deterministic local-marker trail for an offline batch.

        Wave 10 BRIDGE-A-bis-003: matches the XRPL transports' txid-trail
        return shape (``list[str]``). Offline mode is a single conceptual
        anchor regardless of round count, but mirrors the chunked shape so
        callers don't branch on transport identity. The marker is keyed off
        the first entry's envelope_hash for stability.

        Empty input is rejected to mirror the XRPL transport's contract.
        """
        if not rounds:
            raise ValueError("anchor_batch requires at least one round entry")
        return [f"offline:batch:{rounds[0]['envelope_hash'][:16]}"]

    def is_anchored_on_chain(self, txid: str, expected_hash: str) -> ChainLookupResult:
        # In offline mode, verification is done via local proof files; this
        # returns FOUND for any offline:-prefixed txid as a passthrough.
        if self.strict_verify:
            raise NotImplementedError(
                "NullTransport.is_anchored_on_chain cannot validate "
                "cryptographic anchors. Construct with strict_verify=False "
                "to allow always-FOUND passthrough, or use XRPLTransport for "
                "real verification."
            )
        if txid.startswith("offline:"):
            return ChainLookupResult.FOUND
        return ChainLookupResult.NOT_FOUND

    def explorer_tx_url(self, txid: str) -> str:
        """No real chain — return a synthetic offline:// URL placeholder."""
        return f"offline://tx/{txid}"

    def get_memo_text(self, txid: str) -> str | None:
        """Offline mode has no on-ledger memos; return None as a no-op."""
        return None

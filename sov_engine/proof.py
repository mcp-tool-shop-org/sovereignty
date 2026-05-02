"""Engine-side proof verification — local recompute and 3-state anchor status.

The verify contract splits two questions that v2.0.x conflated:

1. *Does this proof file's ``envelope_hash`` match its contents?* This is a
   pure-local recompute, no chain hit. ``verify_proof_local`` answers it.
2. *Is this proof anchored on chain?* In v2.1 there are three answers, not
   two: ``ANCHORED`` (txid present, memo matches), ``PENDING`` (in
   ``pending-anchors.json``, no txid yet), or ``MISSING`` (not pending,
   no txid). ``proof_anchor_status`` composes the three by consulting the
   pending-anchor index and the chain-pure ``transport.is_anchored_on_chain``.

This module is pure engine — no CLI imports — so the verify contract can
be reused by ``sov status``, ``sov doctor``, future GUI surfaces, and the
``sov anchor`` flush path without each one re-implementing the 3-state
composition.

Reference: ``docs/v2.1-bridge-changes.md`` §3.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from sov_cli.errors import ProofFormatError
from sov_engine.io_utils import anchors_file, read_pending_anchors
from sov_engine.serialize import canonical_json
from sov_transport.base import LedgerTransport

PROOF_VERSION = 2


class AnchorStatus(StrEnum):
    """Per-round chain-anchor state. Used by ``proof_anchor_status``.

    ``ANCHORED`` — a txid is recorded in ``anchors.json`` for this round,
    and ``transport.is_anchored_on_chain`` confirms the on-chain memo
    matches the proof's ``envelope_hash``.

    ``PENDING`` — the proof's hash is sitting in ``pending-anchors.json``
    waiting for the next ``sov anchor`` flush, but no txid has been
    recorded yet. Distinct from ``MISSING`` because the local index says
    "we will anchor this" rather than "we never tried".

    ``MISSING`` — neither pending nor recorded. Either the operator never
    ran ``sov anchor``, or the txid was lost, or the chain memo doesn't
    match the local proof (anchor drifted).
    """

    ANCHORED = "anchored"
    PENDING = "pending"
    MISSING = "missing"


def _compute_envelope_hash(envelope: dict[str, Any]) -> str:
    """Recompute the v2 envelope hash, mirroring ``sov_engine.hashing``.

    Excludes the ``envelope_hash`` field itself so the digest covers only
    the canonical envelope payload. The implementation here is duplicated
    intentionally: ``sov_engine.hashing`` imports state-domain types
    (``GameState``, etc.); this module operates on already-loaded JSON
    dicts and stays free of those imports so verify-only callers don't
    drag in the full engine model graph.
    """
    import hashlib

    payload = {k: v for k, v in envelope.items() if k != "envelope_hash"}
    payload_json = canonical_json(payload)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _load_proof(proof_path: Path) -> dict[str, Any]:
    """Load and validate the structural shape of a v2 proof file.

    Returns the parsed dict. Raises ``ProofFormatError`` for v1 / unknown
    proof_version, missing required fields, or unparseable JSON.
    """
    try:
        text = proof_path.read_text(encoding="utf-8")
        proof = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofFormatError(
            f"Could not read proof file {proof_path}: {type(exc).__name__}: {exc}"
        ) from exc

    if not isinstance(proof, dict):
        raise ProofFormatError(f"Proof file {proof_path} is not a JSON object.")

    version = proof.get("proof_version")
    if version is None or version == 1:
        raise ProofFormatError(
            "Proof format v1 is no longer supported as of sovereignty v2.0.0. "
            "Re-run the original game with current sovereignty to generate a "
            "v2 proof, or use sovereignty <2.0.0 to verify legacy proofs."
        )
    if version != PROOF_VERSION:
        raise ProofFormatError(
            f"Unknown proof_version: {version} (this binary supports v{PROOF_VERSION})."
        )

    for required in ("envelope_hash", "round", "game_id"):
        if required not in proof:
            raise ProofFormatError(f"Proof file {proof_path} missing required field '{required}'.")
    if not isinstance(proof["envelope_hash"], str):
        raise ProofFormatError(f"Proof file {proof_path} 'envelope_hash' must be a string.")

    return proof


def verify_proof_local(proof_path: Path) -> bool:
    """Recompute the envelope hash and compare to the stored field.

    Pure-local check: no chain hit. Returns ``True`` when the recomputed
    hash matches the proof's ``envelope_hash`` field, ``False`` otherwise.

    Raises ``ProofFormatError`` for unparseable JSON, ``proof_version != 2``,
    or missing required fields. Mirrors the recompute pattern from the
    v2.0.x ``sov verify`` CLI command (``sov_engine/hashing.py::verify_proof``)
    in pure-engine form so non-CLI surfaces (status / doctor / GUI) can
    use the same contract.
    """
    proof = _load_proof(proof_path)
    expected = str(proof["envelope_hash"])
    computed = _compute_envelope_hash(proof)
    return expected == computed


def _round_key_from_proof(proof: dict[str, Any]) -> str:
    """Map a proof envelope's ``round`` field to its anchors-key form.

    Final proofs (set by ``sov game-end`` via ``proof['final'] = True``)
    use the literal string ``"FINAL"`` in both ``anchors.json`` and
    ``pending-anchors.json``. All other rounds use the stringified
    integer round number (``"1"``…``"15"``).
    """
    if proof.get("final") is True:
        return "FINAL"
    round_field = proof.get("round")
    if round_field is None:
        return "FINAL"
    return str(round_field)


def _read_anchors(game_id: str) -> dict[str, str]:
    """Read ``anchors.json`` as ``{round_key: txid}``.

    Returns an empty dict when the file is absent or unreadable.
    Mirrors the defensive read pattern used by the CLI's ``_record_anchor``
    so a corrupted anchors file degrades to MISSING rather than crashing
    the status / verify path.
    """
    path = anchors_file(game_id)
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str):
            cleaned[key] = value
    return cleaned


def proof_anchor_status(
    proof_path: Path,
    transport: LedgerTransport,
) -> AnchorStatus:
    """Return the 3-state chain-anchor status for ``proof_path``.

    Algorithm (per spec §3):

    1. Load the proof, derive its ``round_key`` (``"FINAL"`` for final
       proofs, else stringified round number) and ``game_id``.
    2. Consult ``pending-anchors.json``. If ``round_key`` is pending,
       short-circuit return ``PENDING``.
    3. Consult ``anchors.json`` for a recorded txid. If found, defer to
       ``transport.is_anchored_on_chain(txid, envelope_hash)``:
       - True → ``ANCHORED``
       - False → ``MISSING`` (recorded txid no longer matches; chain drift)
    4. Otherwise → ``MISSING`` (never attempted).

    Raises ``ProofFormatError`` for malformed proofs, propagating from
    ``_load_proof``. Network errors from the transport propagate as-is —
    the caller decides whether to render them as MISSING or surface the
    underlying error to the operator.
    """
    proof = _load_proof(proof_path)
    game_id = str(proof["game_id"])
    envelope_hash = str(proof["envelope_hash"])
    round_key = _round_key_from_proof(proof)

    pending = read_pending_anchors(game_id)
    if round_key in pending:
        return AnchorStatus.PENDING

    anchors = _read_anchors(game_id)
    txid = anchors.get(round_key)
    if txid is None:
        return AnchorStatus.MISSING

    # Wave 6 BRIDGE-004: is_anchored_on_chain returns ChainLookupResult
    # (FOUND / NOT_FOUND / LOOKUP_FAILED), not bool. Explicit identity check
    # against FOUND — every other result (NOT_FOUND, LOOKUP_FAILED) maps to
    # MISSING. Truthy comparison would silently treat NOT_FOUND as ANCHORED
    # because the StrEnum value "not_found" is non-empty.
    from sov_transport.xrpl_internals import ChainLookupResult

    if transport.is_anchored_on_chain(txid, envelope_hash) is ChainLookupResult.FOUND:
        return AnchorStatus.ANCHORED
    return AnchorStatus.MISSING

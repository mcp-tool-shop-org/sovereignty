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
import logging
from enum import StrEnum
from pathlib import Path
from typing import Any

from sov_cli.errors import ProofFormatError
from sov_engine.io_utils import anchors_file, atomic_write_text, read_pending_anchors
from sov_engine.serialize import canonical_json
from sov_transport.base import LedgerTransport

logger = logging.getLogger("sov_engine")

PROOF_VERSION = 2

#: Current ``anchors.json`` schema version. Stage 7-B amend (BACKEND-B-002)
#: introduces the ``{"schema_version": 1, "anchors": {...}}`` wrapper.
#: Bare-dict files written by pre-Stage-7-B binaries are migrated on first
#: read by ``_read_anchors``.
_ANCHORS_SCHEMA_VERSION = 1


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


def _render_proof_path(proof_path: Path) -> str:
    """Render ``proof_path`` for display in error messages.

    BACKEND-C-004: when the path lives under a ``.sov/`` ancestor, render
    it relative to that ancestor's parent so the message shows the
    canonical short form (``.sov/games/sNNN/proofs/round_001.proof.json``)
    instead of an absolute path that may leak the operator's home dir to
    support bundles. Otherwise fall back to the absolute path supplied by
    the caller. Platform separators are honored — ``Path`` renders with
    the platform-correct separator on both POSIX and Windows.
    """
    try:
        absolute = proof_path.resolve()
    except OSError:
        return str(proof_path)
    for ancestor in absolute.parents:
        if ancestor.name == ".sov":
            try:
                return str(absolute.relative_to(ancestor.parent))
            except ValueError:
                break
    return str(proof_path)


def _load_proof(proof_path: Path) -> dict[str, Any]:
    """Load and validate the structural shape of a v2 proof file.

    Returns the parsed dict. Raises ``ProofFormatError`` for v1 / unknown
    proof_version, missing required fields, or unparseable JSON. Each
    structural-error message names a recovery action so the user surface
    (uncaught traceback or wrapped SovError fallback) carries an
    actionable hint.
    """
    rendered_path = _render_proof_path(proof_path)
    try:
        text = proof_path.read_text(encoding="utf-8")
        proof = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofFormatError(
            f"Could not read proof file {rendered_path}: {type(exc).__name__}: {exc}. "
            f"Regenerate with `sov end-round` from the original save, "
            f"or report a bug if the file should be intact."
        ) from exc

    if not isinstance(proof, dict):
        raise ProofFormatError(
            f"Proof file {rendered_path} is not a JSON object — file may "
            f"be truncated or corrupted. Regenerate with `sov end-round` "
            f"from the original save."
        )

    version = proof.get("proof_version")
    if version is None or version == 1:
        raise ProofFormatError(
            "Proof format v1 is no longer supported as of sovereignty v2.0.0. "
            "Re-run the original game with current sovereignty to generate a "
            "v2 proof, or use sovereignty <2.0.0 to verify legacy proofs."
        )
    if version != PROOF_VERSION:
        raise ProofFormatError(
            f"Unknown proof_version: {version} (this binary supports "
            f"v{PROOF_VERSION}). Upgrade sovereignty if {version} is from a "
            f"newer release, or regenerate with `sov end-round`."
        )

    for required in ("envelope_hash", "round", "game_id"):
        if required not in proof:
            raise ProofFormatError(
                f"Proof file {rendered_path} missing required field "
                f"{required!r}. Regenerate with `sov end-round` from the "
                f"original save."
            )
    if not isinstance(proof["envelope_hash"], str):
        raise ProofFormatError(
            f"Proof file {rendered_path} 'envelope_hash' must be a string. "
            f"Regenerate with `sov end-round` from the original save."
        )

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

    Stage 7-B amend (BACKEND-B-002) introduces the
    ``{"schema_version": 1, "anchors": {...}}`` wrapper. Backward-compat:
    bare-dict files written by pre-amend binaries are detected and migrated
    on read — the wrapped form is written back atomically so subsequent
    reads find the canonical shape.

    Returns an empty dict when the file is absent, unreadable, or has an
    unrecognised schema version. Malformed reads are logged at WARNING
    (BACKEND-B-005) so operators have a signal beyond a silent
    ``AnchorStatus.MISSING`` degradation. Mirrors the defensive read pattern
    used by the CLI's ``_record_anchor``.
    """
    path = anchors_file(game_id)
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "anchors.read.malformed path=%s exc=%s detail=%s "
            "(treating as empty; proof_anchor_status will degrade to MISSING)",
            path,
            type(exc).__name__,
            exc,
        )
        return {}
    if not isinstance(data, dict):
        logger.warning(
            "anchors.read.malformed path=%s reason=not-an-object "
            "(treating as empty; proof_anchor_status will degrade to MISSING)",
            path,
        )
        return {}

    schema_version = data.get("schema_version")
    if schema_version is None:
        # Bare-dict shape from pre-Stage-7-B binaries. Treat the whole document
        # as the entries map and rewrite in wrapped form on the way out.
        cleaned = _coerce_anchor_entries(data)
        _migrate_anchors_to_wrapped(path, cleaned)
        return cleaned
    if schema_version != _ANCHORS_SCHEMA_VERSION:
        logger.warning(
            "anchors.read.schema_mismatch path=%s expected=%d found=%r "
            "(treating as empty; proof_anchor_status will degrade to MISSING)",
            path,
            _ANCHORS_SCHEMA_VERSION,
            schema_version,
        )
        return {}

    inner = data.get("anchors", {})
    if not isinstance(inner, dict):
        logger.warning(
            "anchors.read.malformed path=%s reason=anchors-not-an-object "
            "(treating as empty; proof_anchor_status will degrade to MISSING)",
            path,
        )
        return {}
    return _coerce_anchor_entries(inner)


def _coerce_anchor_entries(raw: dict[Any, Any]) -> dict[str, str]:
    """Filter a raw anchors mapping down to ``{str: str}`` entries.

    Rejects non-string keys/values silently — the same defensive posture as
    the previous bare-dict reader (proof.py pre-Stage-7-B).
    """
    cleaned: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            cleaned[key] = value
    return cleaned


def _migrate_anchors_to_wrapped(path: Path, entries: dict[str, str]) -> None:
    """Rewrite a bare-dict ``anchors.json`` in wrapped form.

    Best-effort: a write failure (read-only filesystem, permission error)
    must not poison the read — the entries we already coerced still flow
    back to the caller. Logs at INFO so operators following an upgrade can
    see the migration once.
    """
    document: dict[str, Any] = {
        "schema_version": _ANCHORS_SCHEMA_VERSION,
        "anchors": dict(sorted(entries.items())),
    }
    try:
        atomic_write_text(
            path,
            json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        )
    except OSError as exc:
        logger.warning(
            "anchors.migrate.failed path=%s exc=%s detail=%s "
            "(read returned coerced entries; on-disk bytes still bare-dict)",
            path,
            type(exc).__name__,
            exc,
        )
        return
    logger.info(
        "anchors.migrated path=%s shape=wrapped schema_version=%d entries=%d",
        path,
        _ANCHORS_SCHEMA_VERSION,
        len(entries),
    )


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
        logger.info(
            "proof_anchor.missing reason=no_txid_recorded game_id=%s round=%s",
            game_id,
            round_key,
        )
        return AnchorStatus.MISSING

    # Wave 6 BRIDGE-004: is_anchored_on_chain returns ChainLookupResult
    # (FOUND / NOT_FOUND / LOOKUP_FAILED), not bool. Explicit identity check
    # against FOUND — every other result (NOT_FOUND, LOOKUP_FAILED) maps to
    # MISSING. Truthy comparison would silently treat NOT_FOUND as ANCHORED
    # because the StrEnum value "not_found" is non-empty.
    from sov_transport.xrpl_internals import ChainLookupResult

    if transport.is_anchored_on_chain(txid, envelope_hash) is ChainLookupResult.FOUND:
        return AnchorStatus.ANCHORED
    logger.info(
        "proof_anchor.missing reason=chain_drift game_id=%s round=%s txid=%s",
        game_id,
        round_key,
        txid,
    )
    return AnchorStatus.MISSING

"""Round proof generation and verification.

Proof format v2 (sovereignty >= 2.0.0)
--------------------------------------
The hash field is named ``envelope_hash`` and covers the FULL canonical
envelope (game_id, round, ruleset, rng_seed, timestamp_utc, players, state,
proof_version) excluding the ``envelope_hash`` field itself. This closes the
v1 gap where only the embedded ``state`` was hashed, leaving envelope metadata
(round, ruleset, rng_seed, player order, timestamp) unsigned and tamperable.

v1 proofs (single ``state_hash`` over only ``state``) are no longer supported.
Use sovereignty <2.0.0 to verify legacy proofs, or re-run the original game
under current sovereignty to regenerate a v2 proof.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sov_cli.errors import ProofFormatError
from sov_engine.io_utils import atomic_write_text
from sov_engine.models import GameState
from sov_engine.serialize import canonical_json, game_state_snapshot

logger = logging.getLogger("sov_engine")

PROOF_VERSION = 2


def _compute_envelope_hash(envelope: dict[str, Any]) -> str:
    """Compute sha256 over the canonical envelope, excluding ``envelope_hash``.

    Returns the raw 64-char lowercase hex digest. The ``sha256:`` algorithm tag
    is added at the wire/memo layer (see ``sov_cli/main.py`` anchor memo
    construction); storing it in the field value would cause double-prefix
    drift with the on-chain memo.
    """
    payload = {k: v for k, v in envelope.items() if k != "envelope_hash"}
    payload_json = canonical_json(payload)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def make_round_proof(state: GameState) -> dict[str, Any]:
    """Create a v2 round proof envelope from the current game state."""
    snapshot = game_state_snapshot(state)

    envelope: dict[str, Any] = {
        "game_id": f"s{state.config.seed}",
        "players": [p.name for p in state.players],
        "proof_version": PROOF_VERSION,
        "rng_seed": state.config.seed,
        "round": state.current_round,
        "ruleset": state.config.ruleset,
        "state": snapshot,
        "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    envelope["envelope_hash"] = _compute_envelope_hash(envelope)
    return envelope


def save_proof(proof: dict[str, Any], directory: Path | None = None) -> Path:
    """Write proof to a JSON file atomically. Returns the path."""
    directory = directory or Path(".")
    directory.mkdir(parents=True, exist_ok=True)
    round_num = proof["round"]
    filename = f"round_{round_num:03d}.proof.json"
    path = directory / filename
    content = canonical_json(proof)
    atomic_write_text(path, content)
    logger.info("save_proof round=%s path=%s", round_num, path)
    return path


def verify_proof(proof_path: Path) -> tuple[bool, str]:
    """Verify a proof file's integrity. Returns (valid, message).

    Raises:
        ProofFormatError: if the proof is missing ``proof_version`` or is v1.
    """
    try:
        text = proof_path.read_text(encoding="utf-8")
        proof = json.loads(text)
    except (OSError, json.JSONDecodeError) as e:
        return False, f"Failed to read proof: {e}"

    version = proof.get("proof_version")
    if version is None or version == 1:
        raise ProofFormatError(
            "Proof format v1 is no longer supported as of sovereignty v2.0.0. "
            "Re-run the original game with current sovereignty to generate a "
            "v2 proof, or use sovereignty <2.0.0 to verify legacy proofs."
        )

    if version != PROOF_VERSION:
        return False, f"Unknown proof_version: {version} (this binary supports v{PROOF_VERSION})."

    if "envelope_hash" not in proof:
        return False, "Proof missing 'envelope_hash' field."

    expected = proof["envelope_hash"]
    computed = _compute_envelope_hash(proof)

    if expected != computed:
        return False, f"Hash mismatch: expected {expected}, computed {computed}"

    return True, f"Proof valid. Round {proof.get('round', '?')}, envelope hash matches."

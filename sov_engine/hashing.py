"""Round proof generation and verification."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sov_engine.models import GameState
from sov_engine.serialize import canonical_json, game_state_snapshot


def make_round_proof(state: GameState) -> dict[str, Any]:
    """Create a round proof document from the current game state."""
    snapshot = game_state_snapshot(state)
    snapshot_json = canonical_json(snapshot)
    state_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

    return {
        "game_id": f"sov_{state.config.seed}",
        "round": state.current_round,
        "ruleset": state.config.ruleset,
        "rng_seed": state.config.seed,
        "state_hash": f"sha256:{state_hash}",
        "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "players": [p.name for p in state.players],
        "state": snapshot,
    }


def save_proof(proof: dict[str, Any], directory: Path | None = None) -> Path:
    """Write proof to a JSON file. Returns the path."""
    directory = directory or Path(".")
    directory.mkdir(parents=True, exist_ok=True)
    round_num = proof["round"]
    filename = f"round_{round_num:03d}.proof.json"
    path = directory / filename
    content = canonical_json(proof)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def verify_proof(proof_path: Path) -> tuple[bool, str]:
    """Verify a proof file's integrity. Returns (valid, message)."""
    try:
        text = proof_path.read_text(encoding="utf-8")
        proof = json.loads(text)
    except (OSError, json.JSONDecodeError) as e:
        return False, f"Failed to read proof: {e}"

    if "state" not in proof or "state_hash" not in proof:
        return False, "Proof missing 'state' or 'state_hash' field."

    # Recompute hash from the embedded state
    state_json = canonical_json(proof["state"])
    computed = hashlib.sha256(state_json.encode("utf-8")).hexdigest()
    expected_hash = proof["state_hash"]

    if expected_hash != f"sha256:{computed}":
        return False, f"Hash mismatch: expected {expected_hash}, computed sha256:{computed}"

    return True, f"Proof valid. Round {proof.get('round', '?')}, hash matches."

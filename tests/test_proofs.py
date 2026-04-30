"""Tests for round proof generation and verification.

Includes legacy hash-determinism tests plus the v2 envelope tamper suite
(F-V2CUT-001) which exercises one mutated envelope field per test and
asserts ``verify_proof`` rejects it.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from sov_cli.errors import ProofFormatError
from sov_engine.hashing import make_round_proof, save_proof, verify_proof
from sov_engine.rules.campfire import new_game
from sov_engine.serialize import canonical_json, game_state_snapshot

# ---------------------------------------------------------------------------
# Determinism / canonical JSON
# ---------------------------------------------------------------------------


def test_deterministic_hash():
    """Same seed + same state -> same canonical JSON."""
    state1, _ = new_game(42, ["Alice", "Bob"])
    state2, _ = new_game(42, ["Alice", "Bob"])

    snap1 = game_state_snapshot(state1)
    snap2 = game_state_snapshot(state2)

    json1 = canonical_json(snap1)
    json2 = canonical_json(snap2)

    assert json1 == json2, "Canonical JSON should be identical for same seed"


def test_canonical_json_sorted_keys():
    """Keys should be sorted for determinism."""
    data = {"z": 1, "a": 2, "m": 3}
    result = canonical_json(data)
    parsed = json.loads(result)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_canonical_json_no_floats_in_state():
    """Game state should contain no floats (all ints)."""
    state, _ = new_game(42, ["Alice", "Bob"])
    snap = game_state_snapshot(state)
    json_str = canonical_json(snap)

    def check_no_floats(obj, path=""):
        if isinstance(obj, float):
            raise AssertionError(f"Float found at {path}: {obj}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                check_no_floats(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_no_floats(v, f"{path}[{i}]")

    parsed = json.loads(json_str)
    check_no_floats(parsed)


# ---------------------------------------------------------------------------
# v2 envelope shape
# ---------------------------------------------------------------------------


def test_proof_has_required_v2_fields():
    """A freshly minted proof has the v2 envelope fields."""
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    assert proof["proof_version"] == 2
    assert "game_id" in proof
    assert "round" in proof
    assert "ruleset" in proof
    assert "rng_seed" in proof
    assert "envelope_hash" in proof
    assert "timestamp_utc" in proof
    assert "players" in proof
    assert "state" in proof
    assert proof["envelope_hash"].startswith("sha256:")


def test_proof_round_trip():
    """Generate proof -> save -> load -> verify."""
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_proof(proof, Path(tmpdir))
        assert path.exists()

        valid, msg = verify_proof(path)
        assert valid, f"Proof should be valid: {msg}"


def test_proof_detects_tampering():
    """Mutating the embedded state should invalidate the envelope hash.

    Reused as the helper pattern for all v2 envelope-field tamper tests below.
    """
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    proof["state"]["players"][0]["coins"] = 999

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "tampered.proof.json"
        content = canonical_json(proof)
        path.write_text(content, encoding="utf-8", newline="\n")

        valid, msg = verify_proof(path)
        assert not valid, "Tampered proof should fail verification"
        assert "mismatch" in msg.lower()


# ---------------------------------------------------------------------------
# F-V2CUT-001 — envelope-field tamper suite
# ---------------------------------------------------------------------------


def _write_proof(proof: dict[str, Any], tmpdir: Path) -> Path:
    """Serialize a (possibly tampered) proof envelope to disk for verify_proof."""
    path = tmpdir / "proof.json"
    path.write_text(canonical_json(proof), encoding="utf-8", newline="\n")
    return path


def _make_proof_for_tamper() -> dict[str, Any]:
    """Build a fresh v2 proof with at least 3 players so name reorder is testable."""
    state, _rng = new_game(42, ["Alice", "Bob", "Carol"])
    return make_round_proof(state)


def test_v2_clean_proof_verifies_true():
    """Positive control: an unmodified v2 proof verifies True."""
    proof = _make_proof_for_tamper()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_proof(proof, Path(tmp))
        valid, msg = verify_proof(path)
        assert valid, f"Clean v2 proof must verify: {msg}"


def _round_flip(p: dict[str, Any]) -> None:
    p["round"] = p["round"] + 1


def _ruleset_flip(p: dict[str, Any]) -> None:
    # Flip from "campfire_v1" to a different ruleset string.
    p["ruleset"] = "treaty_table_v1" if p["ruleset"] != "treaty_table_v1" else "campfire_v1"


def _player_swap(p: dict[str, Any]) -> None:
    """Swap the order of the top-level players list (Alice/Bob)."""
    players = list(p["players"])
    assert len(players) >= 2, "test fixture must have >= 2 players"
    players[0], players[1] = players[1], players[0]
    p["players"] = players


def _player_rename(p: dict[str, Any]) -> None:
    """Rename one player in the top-level envelope list."""
    players = list(p["players"])
    players[0] = players[0] + "_renamed"
    p["players"] = players


def _rng_seed_change(p: dict[str, Any]) -> None:
    p["rng_seed"] = p["rng_seed"] + 1


def _timestamp_tweak(p: dict[str, Any]) -> None:
    """Bump the timestamp by one second."""
    ts = p["timestamp_utc"]
    # Format: YYYY-MM-DDTHH:MM:SSZ — flip a digit deterministically.
    body = ts[:-1] if ts.endswith("Z") else ts
    # Replace the last second-digit by adding 1 mod 10 to make it different.
    last = body[-1]
    new_last = str((int(last) + 1) % 10) if last.isdigit() else "0"
    p["timestamp_utc"] = body[:-1] + new_last + "Z"


def _game_id_change(p: dict[str, Any]) -> None:
    p["game_id"] = p["game_id"] + "_tampered"


@pytest.mark.parametrize(
    "tamper_name,tamper_fn",
    [
        ("round_flip", _round_flip),
        ("ruleset_flip", _ruleset_flip),
        ("player_swap", _player_swap),
        ("player_rename", _player_rename),
        ("rng_seed_change", _rng_seed_change),
        ("timestamp_tweak", _timestamp_tweak),
        ("game_id_change", _game_id_change),
    ],
)
def test_v2_envelope_field_tampering_invalidates_proof(tamper_name, tamper_fn):
    """One test per tamper vector. Each mutates a single envelope field and
    asserts ``verify_proof`` returns (False, ...). This is the F-V2CUT-001
    coverage that proves ``envelope_hash`` actually covers each named field.
    """
    proof = _make_proof_for_tamper()
    tamper_fn(proof)

    with tempfile.TemporaryDirectory() as tmp:
        path = _write_proof(proof, Path(tmp))
        valid, msg = verify_proof(path)
        assert not valid, f"tamper '{tamper_name}' should invalidate envelope_hash"
        assert "mismatch" in msg.lower(), (
            f"tamper '{tamper_name}' produced unexpected message: {msg}"
        )


# ---------------------------------------------------------------------------
# v1-format rejection
# ---------------------------------------------------------------------------


def test_v1_proof_format_is_rejected():
    """A synthetic v1-format proof (no proof_version, with state_hash) must
    raise ``ProofFormatError`` with the locked-spec message."""
    # Build a v1-shaped envelope manually.
    state, _ = new_game(42, ["Alice", "Bob"])
    snapshot = game_state_snapshot(state)

    v1_proof = {
        "game_id": "sov_42",
        "round": 1,
        "ruleset": "campfire_v1",
        "rng_seed": 42,
        "state_hash": "sha256:00",  # legacy field name
        "timestamp_utc": "2024-01-01T00:00:00Z",
        "players": ["Alice", "Bob"],
        "state": snapshot,
        # Notably: NO `proof_version` key.
    }

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "v1.proof.json"
        path.write_text(canonical_json(v1_proof), encoding="utf-8", newline="\n")

        with pytest.raises(ProofFormatError) as exc_info:
            verify_proof(path)

    msg = str(exc_info.value)
    assert "v1" in msg.lower()
    assert "no longer supported" in msg
    assert "v2.0.0" in msg


def test_explicit_v1_proof_version_is_rejected():
    """Even an explicit `proof_version: 1` is rejected with ProofFormatError."""
    state, _ = new_game(42, ["Alice", "Bob"])
    snapshot = game_state_snapshot(state)

    v1_proof = {
        "game_id": "sov_42",
        "proof_version": 1,
        "round": 1,
        "ruleset": "campfire_v1",
        "rng_seed": 42,
        "state_hash": "sha256:00",
        "timestamp_utc": "2024-01-01T00:00:00Z",
        "players": ["Alice", "Bob"],
        "state": snapshot,
    }

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "v1.proof.json"
        path.write_text(canonical_json(v1_proof), encoding="utf-8", newline="\n")

        with pytest.raises(ProofFormatError):
            verify_proof(path)

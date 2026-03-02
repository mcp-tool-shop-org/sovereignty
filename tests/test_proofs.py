"""Tests for round proof generation and verification."""

import json
import tempfile
from pathlib import Path

from sov_engine.hashing import make_round_proof, save_proof, verify_proof
from sov_engine.rules.campfire import new_game
from sov_engine.serialize import canonical_json, game_state_snapshot


def test_deterministic_hash():
    """Same seed + same state → same proof hash."""
    state1, _ = new_game(42, ["Alice", "Bob"])
    state2, _ = new_game(42, ["Alice", "Bob"])

    snap1 = game_state_snapshot(state1)
    snap2 = game_state_snapshot(state2)

    json1 = canonical_json(snap1)
    json2 = canonical_json(snap2)

    assert json1 == json2, "Canonical JSON should be identical for same seed"


def test_proof_round_trip():
    """Generate proof → save → load → verify."""
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_proof(proof, Path(tmpdir))
        assert path.exists()

        valid, msg = verify_proof(path)
        assert valid, f"Proof should be valid: {msg}"


def test_proof_detects_tampering():
    """Modifying the state should invalidate the hash."""
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    # Tamper with the state
    proof["state"]["players"][0]["coins"] = 999

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "tampered.proof.json"
        content = canonical_json(proof)
        path.write_text(content, encoding="utf-8", newline="\n")

        valid, msg = verify_proof(path)
        assert not valid, "Tampered proof should fail verification"
        assert "mismatch" in msg.lower()


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

    # Parse and check all numeric values are ints
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


def test_proof_has_required_fields():
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    assert "game_id" in proof
    assert "round" in proof
    assert "ruleset" in proof
    assert "rng_seed" in proof
    assert "state_hash" in proof
    assert "timestamp_utc" in proof
    assert "players" in proof
    assert "state" in proof
    assert proof["state_hash"].startswith("sha256:")

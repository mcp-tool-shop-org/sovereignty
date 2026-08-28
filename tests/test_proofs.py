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
from typer.testing import CliRunner

from sov_cli.errors import ProofFormatError
from sov_cli.main import app
from sov_engine.hashing import make_round_proof, save_proof, verify_proof
from sov_engine.rules.campfire import new_game
from sov_engine.serialize import canonical_json, game_state_snapshot

runner = CliRunner()

# Invalid recovery form F-d26e6014 removed from the README: Typer requires
# positional proof_file, so `sov verify --tx <hash>` is rejected.
_ORPHAN_VERIFY_TX = "sov verify --tx"
# proof_invalid_error(kind="MODIFIED") hint. Hash-mismatch is the only path
# that may emit this; IO / unknown-version / missing envelope_hash must not.
_MODIFIED_HINT = "bytes don't match"

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
    # envelope_hash is the raw 64-char hex digest. The sha256: algorithm tag
    # is added at the wire/memo layer, not stored in the field value (would
    # cause double-prefix drift with the on-chain memo).
    assert len(proof["envelope_hash"]) == 64
    assert all(c in "0123456789abcdef" for c in proof["envelope_hash"])


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


def test_envelope_hash_includes_proof_version() -> None:
    """Direct empirical proof that ``proof_version`` is in the hashed payload.

    Build a real proof, recompute the envelope hash WITHOUT ``proof_version``
    in the dict, and assert the result differs from ``proof['envelope_hash']``.
    This is the "is-the-field-actually-covered" assertion that the parametrized
    tamper suite cannot make for ``proof_version`` (because the version-check
    short-circuit at hashing.py:94 fires before the hash compare).
    """
    from sov_engine.hashing import _compute_envelope_hash

    proof = _make_proof_for_tamper()
    original_hash = proof["envelope_hash"]

    # Strip proof_version from a copy and recompute. Different payload =>
    # different hash. If a future refactor accidentally drops proof_version
    # from the canonical envelope, original_hash and stripped_hash will
    # collide and this test will fail.
    stripped = {k: v for k, v in proof.items() if k != "proof_version"}
    stripped_hash = _compute_envelope_hash(stripped)

    assert original_hash != stripped_hash, (
        "envelope_hash must depend on proof_version; removing it from the "
        "canonical payload should change the digest. If this test fails, "
        "proof_version is not being hashed and is silently tamperable."
    )


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
    """One test per tamper vector. Each mutates a single hashed envelope field
    and asserts ``verify_proof`` returns (False, hash-mismatch).

    Unknown ``proof_version`` is not a tamper vector: it raises
    ``ProofFormatError`` (same as ``_load_proof``). Field coverage for
    ``proof_version`` is ``test_envelope_hash_includes_proof_version``.
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


# ---------------------------------------------------------------------------
# verify_proof negative branches (F-b0e0c574 / F-516d1a7f / F-1f2828ea)
# IO, unknown proof_version, and missing envelope_hash raise
# ProofFormatError, same as _load_proof. Hash mismatch remains the
# (False, ...) / CLI kind=MODIFIED path.
# ---------------------------------------------------------------------------


def _assert_format_error_not_orphan_tx(exc: BaseException) -> str:
    """ProofFormatError must not recommend the no-file ``sov verify --tx`` form."""
    msg = str(exc)
    assert msg, "ProofFormatError must carry a non-empty message"
    assert _ORPHAN_VERIFY_TX not in msg, (
        f"recovery must not be `{_ORPHAN_VERIFY_TX} <hash>` (no proof_file); got: {msg!r}"
    )
    return msg


def test_verify_proof_raises_when_file_missing(tmp_path):
    """A path that doesn't exist raises ProofFormatError, not (False, ...).

    Returning False here made ``sov verify`` wrap the miss as
    ``kind=MODIFIED`` ("bytes don't match"). Same contract as ``_load_proof``.
    """
    missing = tmp_path / "does_not_exist.proof.json"
    assert not missing.exists()

    with pytest.raises(ProofFormatError) as exc_info:
        verify_proof(missing)
    msg = _assert_format_error_not_orphan_tx(exc_info.value)
    assert "read" in msg.lower() or "no such" in msg.lower() or missing.name in msg


def test_verify_proof_raises_on_invalid_json(tmp_path):
    """Garbage JSON raises ProofFormatError, not json.JSONDecodeError or False."""
    bad = tmp_path / "bad.proof.json"
    bad.write_text("not json{", encoding="utf-8")

    with pytest.raises(ProofFormatError) as exc_info:
        verify_proof(bad)
    msg = _assert_format_error_not_orphan_tx(exc_info.value)
    assert "read" in msg.lower() or "json" in msg.lower() or "parse" in msg.lower()


def test_verify_proof_raises_on_missing_envelope_hash_field(tmp_path):
    """A v2-shaped proof missing ``envelope_hash`` raises ProofFormatError.

    Returning False here made ``sov verify`` wrap the miss as
    ``kind=MODIFIED`` ("bytes don't match"). Same contract as ``_load_proof``.
    """
    path = _write_v2_proof_missing_envelope_hash(tmp_path)

    with pytest.raises(ProofFormatError) as exc_info:
        verify_proof(path)
    msg = _assert_format_error_not_orphan_tx(exc_info.value)
    assert "envelope_hash" in msg, f"missing-field error must name the missing field; got: {msg!r}"


def test_verify_proof_raises_on_unknown_proof_version(tmp_path):
    """Unknown ``proof_version`` (e.g. 3 or 99) raises ProofFormatError.

    Returning False made the CLI report tampering (kind=MODIFIED). v1 is
    already ProofFormatError; unknown future versions must match _load_proof.
    """
    state, _ = new_game(42, ["Alice", "Bob"])
    snapshot = game_state_snapshot(state)

    proof_unknown_version: dict[str, Any] = {
        "game_id": "sov_42",
        "proof_version": 99,
        "round": 1,
        "ruleset": "campfire_v1",
        "rng_seed": 42,
        "timestamp_utc": "2024-01-01T00:00:00Z",
        "players": ["Alice", "Bob"],
        "state": snapshot,
        "envelope_hash": "0" * 64,
    }

    path = tmp_path / "unknown_version.proof.json"
    path.write_text(
        canonical_json(proof_unknown_version),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ProofFormatError) as exc_info:
        verify_proof(path)
    msg = _assert_format_error_not_orphan_tx(exc_info.value)
    assert "99" in msg or "version" in msg.lower(), (
        f"unknown proof_version must name the version; got: {msg!r}"
    )


def _write_v2_proof_missing_envelope_hash(tmp_path: Path) -> Path:
    state, _ = new_game(42, ["Alice", "Bob"])
    snapshot = game_state_snapshot(state)
    path = tmp_path / "no_hash.proof.json"
    path.write_text(
        canonical_json(
            {
                "game_id": "sov_42",
                "proof_version": 2,
                "round": 1,
                "ruleset": "campfire_v1",
                "rng_seed": 42,
                "timestamp_utc": "2024-01-01T00:00:00Z",
                "players": ["Alice", "Bob"],
                "state": snapshot,
                # Notably: NO envelope_hash key.
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_v3_proof(tmp_path: Path) -> Path:
    state, _ = new_game(42, ["Alice", "Bob"])
    snapshot = game_state_snapshot(state)
    path = tmp_path / "v3.proof.json"
    path.write_text(
        canonical_json(
            {
                "game_id": "sov_42",
                "proof_version": 3,
                "round": 1,
                "ruleset": "campfire_v1",
                "rng_seed": 42,
                "timestamp_utc": "2024-01-01T00:00:00Z",
                "players": ["Alice", "Bob"],
                "state": snapshot,
                "envelope_hash": "0" * 64,
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _assert_cli_verify_not_modified(result: Any, *, label: str) -> None:
    """sov verify on IO / unknown-version / missing envelope_hash is not tampering."""
    output = result.output
    assert result.exit_code != 0, f"{label}: sov verify must fail; output={output!r}"
    lower = output.lower()
    assert _MODIFIED_HINT not in lower, (
        f"{label}: must not emit STATE_PROOF_INVALID kind=MODIFIED "
        f"({_MODIFIED_HINT!r}); got: {output!r}"
    )
    assert _ORPHAN_VERIFY_TX not in output, (
        f"{label}: must not recommend `{_ORPHAN_VERIFY_TX} <hash>` (no proof_file); got: {output!r}"
    )


def test_cli_verify_missing_file_is_not_modified(tmp_path: Path) -> None:
    """CliRunner: missing proof is UNSUPPORTED_VERSION or IO, not MODIFIED."""
    missing = tmp_path / "does_not_exist.proof.json"
    result = runner.invoke(app, ["verify", str(missing)])
    _assert_cli_verify_not_modified(result, label="missing")


def test_cli_verify_truncated_json_is_not_modified(tmp_path: Path) -> None:
    """CliRunner: truncated JSON is a format/IO failure, not hash tampering."""
    bad = tmp_path / "truncated.proof.json"
    bad.write_text("not json{", encoding="utf-8")
    result = runner.invoke(app, ["verify", str(bad)])
    _assert_cli_verify_not_modified(result, label="truncated")


def test_cli_verify_proof_version_3_is_not_modified(tmp_path: Path) -> None:
    """CliRunner: proof_version 3 is UNSUPPORTED_VERSION, not MODIFIED."""
    path = _write_v3_proof(tmp_path)
    result = runner.invoke(app, ["verify", str(path)])
    _assert_cli_verify_not_modified(result, label="proof_version 3")
    lower = result.output.lower()
    assert "3" in result.output or "version" in lower, (
        f"proof_version 3 must name the version; got: {result.output!r}"
    )


def test_cli_verify_missing_envelope_hash_is_not_modified(tmp_path: Path) -> None:
    """CliRunner: v2 proof missing envelope_hash is format error, not MODIFIED."""
    path = _write_v2_proof_missing_envelope_hash(tmp_path)
    result = runner.invoke(app, ["verify", str(path)])
    _assert_cli_verify_not_modified(result, label="missing envelope_hash")


def test_cli_verify_hash_mismatch_is_the_only_modified_path(tmp_path: Path) -> None:
    """Hash mismatch is the only sov verify path that emits kind=MODIFIED."""
    proof = _make_proof_for_tamper()
    proof["state"]["players"][0]["coins"] = 999
    path = _write_proof(proof, tmp_path)
    result = runner.invoke(app, ["verify", str(path)])
    assert result.exit_code != 0, f"tampered proof must fail; output={result.output!r}"
    assert _MODIFIED_HINT in result.output.lower(), (
        f"hash mismatch is the MODIFIED path ({_MODIFIED_HINT!r}); got: {result.output!r}"
    )
    assert _ORPHAN_VERIFY_TX not in result.output


# ---------------------------------------------------------------------------
# JOB-010 — FINAL proof must rehash after final:true
# ---------------------------------------------------------------------------


def test_stamping_final_without_rehash_mismatches() -> None:
    """Reproduce: setting final=True after make_round_proof breaks verify."""
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)
    proof["final"] = True
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_proof(proof, Path(tmp))
        valid, msg = verify_proof(path)
        assert not valid, "stale envelope_hash after final:true must mismatch"
        assert "mismatch" in msg.lower()


def test_mark_final_proof_recomputes_envelope_hash() -> None:
    """game-end helper: final:true plus rehash verifies."""
    from sov_engine.hashing import mark_final_proof

    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)
    before = proof["envelope_hash"]
    mark_final_proof(proof)
    assert proof["final"] is True
    assert proof["envelope_hash"] != before
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_proof(proof, Path(tmp))
        valid, msg = verify_proof(path)
        assert valid, f"FINAL proof must verify after rehash: {msg}"

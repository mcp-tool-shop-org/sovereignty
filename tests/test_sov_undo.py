"""Tests for last-turn ``sov undo`` (JOB-024).

Undo restores the pre-turn checkpoint written by ``sov turn``. It is not a
full history journal: ``sov end-round`` clears the checkpoint so sealed
proofs (with envelope_hash) stay consistent, and intervening saves clear it
too.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sov_cli.main import app
from sov_engine.hashing import verify_proof
from sov_engine.io_utils import proofs_dir, undo_state_file

runner = CliRunner()


def _active_game_id(cwd: Path) -> str:
    pointer = cwd / ".sov" / "active-game"
    assert pointer.exists()
    return pointer.read_text(encoding="utf-8").strip()


def _read_state(cwd: Path) -> dict:
    game_id = _active_game_id(cwd)
    state_path = cwd / ".sov" / "games" / game_id / "state.json"
    return json.loads(state_path.read_text(encoding="utf-8"))


def test_undo_restores_last_turn(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["play", "campfire_v1", "--seed", "7"]).exit_code == 0
    before = _read_state(tmp_path)
    assert runner.invoke(app, ["turn"]).exit_code == 0
    after = _read_state(tmp_path)
    assert after != before
    result = runner.invoke(app, ["undo"])
    assert result.exit_code == 0, result.output
    assert "Last-turn undo only" in result.output
    restored = _read_state(tmp_path)
    assert restored == before
    # One-shot: second undo has nothing to restore.
    result2 = runner.invoke(app, ["undo"])
    assert result2.exit_code == 1
    assert "Nothing to undo" in result2.output


def test_undo_nothing_without_turn(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["play", "campfire_v1", "--seed", "11"]).exit_code == 0
    result = runner.invoke(app, ["undo"])
    assert result.exit_code == 1
    assert "Nothing to undo" in result.output


def test_end_round_clears_undo_keeps_proof(monkeypatch, tmp_path: Path) -> None:
    """end-round seals a proof with envelope_hash and clears the undo buffer."""
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["play", "campfire_v1", "--seed", "13"]).exit_code == 0
    assert runner.invoke(app, ["turn"]).exit_code == 0
    game_id = _active_game_id(tmp_path)
    assert undo_state_file(game_id).exists()
    assert runner.invoke(app, ["end-round"]).exit_code == 0
    assert not undo_state_file(game_id).exists()
    # Proof on disk still verifies (envelope_hash not skipped).
    proof_files = list(proofs_dir(game_id).glob("round_*.proof.json"))
    assert proof_files, "expected a round proof after end-round"
    proof_path = proof_files[0]
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    assert "envelope_hash" in proof
    ok, msg = verify_proof(proof_path)
    assert ok is True, msg
    result = runner.invoke(app, ["undo"])
    assert result.exit_code == 1
    assert "Nothing to undo" in result.output

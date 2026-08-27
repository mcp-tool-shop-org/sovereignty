"""JOB-010: sov game-end FINAL proof must verify after final:true."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sov_cli.main import app
from sov_engine.hashing import verify_proof
from sov_engine.io_utils import proofs_dir

runner = CliRunner()


def test_game_end_final_proof_verifies(monkeypatch, tmp_path: Path) -> None:
    """sov game-end then sov verify on final.proof.json must match."""
    from tests.test_anchor_cli import _seed_game

    monkeypatch.chdir(tmp_path)
    game_id = _seed_game(tmp_path, game_over=True)
    ended = runner.invoke(app, ["game-end"])
    assert ended.exit_code == 0, ended.output
    proof_path = proofs_dir(game_id) / "final.proof.json"
    assert proof_path.is_file(), f"missing {proof_path}"
    valid, msg = verify_proof(proof_path)
    assert valid, msg
    checked = runner.invoke(app, ["verify", str(proof_path)])
    assert checked.exit_code == 0, checked.output

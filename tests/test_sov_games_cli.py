"""Tests for ``sov games`` — the saved-games listing CLI command.

Exercises the contract via Typer's ``CliRunner``:

- Empty layout → friendly "No saved games" message, exit 0 (not an error).
- ``--json`` mode → list of ``GameSummary`` dicts shaped per the spec.
- Multiple games → both surfaced, sorted by last-played descending.

Until the backend agent wires the ``games`` command, ``CliRunner`` will
return a UsageError exit code (typically 2). The tests skip in that
window so the wave's full pytest pass isn't blocked by inter-agent
sequencing — but they activate the moment the command lands.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from sov_cli.main import app
from sov_engine.io_utils import (
    game_dir,
    games_dir,
    rng_seed_file,
    save_root,
    state_file,
)

runner = CliRunner()


def _seed_v2_game(
    seed: int,
    *,
    players: list[str] | None = None,
    current_round: int = 1,
    ruleset: str = "campfire_v1",
) -> str:
    """Plant a minimal v2 game in ``.sov/games/<id>/``. Returns the game-id."""
    players = players or ["Alice", "Bob"]
    game_id = f"s{seed}"
    save_root().mkdir(parents=True, exist_ok=True)
    games_dir().mkdir(parents=True, exist_ok=True)
    game_dir(game_id).mkdir(parents=True, exist_ok=True)
    state_file(game_id).write_text(
        json.dumps(
            {
                "config": {"seed": seed, "ruleset": ruleset, "max_rounds": 15},
                "current_round": current_round,
                "players": [{"name": n} for n in players],
                "schema_version": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rng_seed_file(game_id).write_text(str(seed), encoding="utf-8")
    return game_id


def _skip_if_command_unwired(result: Result) -> None:
    """Skip the test if `sov games` isn't wired yet (parallel-agent guard)."""
    if result.exit_code == 2 and "No such command" in (result.output or ""):
        pytest.skip(
            "`sov games` command not yet wired by backend agent in this wave; "
            "tests will activate once the command lands."
        )


# ---------------------------------------------------------------------------
# Empty / no-saves path
# ---------------------------------------------------------------------------


def test_sov_games_no_saves_prints_friendly_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Empty workspace → "No saved games" + exit 0 (not an error)."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["games"])
    _skip_if_command_unwired(result)

    assert result.exit_code == 0, (
        f"sov games on empty workspace must exit 0; output={result.output!r}"
    )
    out = result.output.lower()
    assert "no saved games" in out, (
        f"expected friendly 'No saved games' message; got: {result.output!r}"
    )


def test_sov_games_json_no_saves_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``sov games --json`` with no saves → ``[]`` (and exit 0)."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["games", "--json"])
    _skip_if_command_unwired(result)

    assert result.exit_code == 0, (
        f"sov games --json on empty workspace must exit 0; output={result.output!r}"
    )

    # Locate the first JSON token in stdout.
    output = result.output
    start = output.find("[")
    end = output.rfind("]")
    assert start != -1 and end != -1 and end >= start, (
        f"sov games --json must emit a JSON array; got: {output!r}"
    )
    payload = json.loads(output[start : end + 1])
    assert payload == [], f"empty workspace must yield []; got: {payload!r}"


# ---------------------------------------------------------------------------
# Populated path
# ---------------------------------------------------------------------------


def test_sov_games_lists_two_games_sorted_most_recent_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two saved games → both surface, most-recent-first."""
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(17, players=["Dora", "Eve"], current_round=8)
    older_mtime = time.time() - 5.0
    os.utime(state_file("s17"), (older_mtime, older_mtime))

    _seed_v2_game(42, players=["Alice", "Bob"], current_round=3)

    result = runner.invoke(app, ["games"])
    _skip_if_command_unwired(result)

    assert result.exit_code == 0, f"sov games must exit 0; output={result.output!r}"
    # Both game ids surface (table layout — exact spacing not pinned).
    assert "s42" in result.output, f"s42 missing from listing; got: {result.output!r}"
    assert "s17" in result.output, f"s17 missing from listing; got: {result.output!r}"
    # Most-recent-first ordering: s42 (just-written) appears before s17.
    pos_42 = result.output.index("s42")
    pos_17 = result.output.index("s17")
    assert pos_42 < pos_17, (
        f"sov games must list most-recent first; s42 at {pos_42}, s17 at {pos_17}; "
        f"output={result.output!r}"
    )


def test_sov_games_json_returns_summary_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``sov games --json`` returns a list of GameSummary dicts.

    Schema (per Wave 1 SPEC):
        {
          "game_id": str,
          "ruleset": str,
          "current_round": int,
          "max_rounds": int,
          "players": [str, ...],
          "last_modified_iso": str,
        }
    """
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42, players=["Alice", "Bob", "Charlie"], current_round=3)

    result = runner.invoke(app, ["games", "--json"])
    _skip_if_command_unwired(result)

    assert result.exit_code == 0, f"sov games --json must exit 0; output={result.output!r}"

    output = result.output
    start = output.find("[")
    end = output.rfind("]")
    assert start != -1 and end > start, f"sov games --json must emit a JSON array; got: {output!r}"
    payload = json.loads(output[start : end + 1])
    assert isinstance(payload, list)
    assert len(payload) == 1, f"expected one summary; got {len(payload)}: {payload!r}"
    summary = payload[0]
    for required in (
        "game_id",
        "ruleset",
        "current_round",
        "max_rounds",
        "players",
        "last_modified_iso",
    ):
        assert required in summary, f"GameSummary JSON missing key {required!r}; got: {summary!r}"
    assert summary["game_id"] == "s42"
    assert summary["ruleset"] == "campfire_v1"
    assert summary["current_round"] == 3
    assert summary["max_rounds"] == 15
    assert list(summary["players"]) == ["Alice", "Bob", "Charlie"]
    assert isinstance(summary["last_modified_iso"], str)
    assert summary["last_modified_iso"], "last_modified_iso must not be empty"

"""Smoke test for the ``sov play <ruleset>`` quickstart alias.

Wave 11 added ``sov play <ruleset>`` as a thin Typer alias to ``sov new``
so a cold-start operator can be playing in one command without spelling
out ``-p Alice -p Bob`` first. The alias defaults to a solo-vs-AI roster
(1 human "You" + 1 AI "Rival") and maps the engine ruleset slug
(``campfire_v1``) to the corresponding ``--tier`` value.

These tests pin:
  * ``sov play campfire_v1`` exits 0 on a fresh directory.
  * The resulting save has 2 players (You + Rival).
  * ``sov play campfire_v1`` produces the same player roster + tier as
    ``sov new -p You -p Rival`` (parity claim — that's what "thin alias"
    means).
  * Ruleset → tier mapping covers every shipped tier (campfire,
    market-day, town-hall, treaty-table) so README / empty-state
    references like ``sov play town_hall_v1`` resolve.

Local fast-check: ``uv run pytest tests/test_sov_play_alias.py -v``.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sov_cli.main import app

runner = CliRunner()


def _read_active_state(cwd: Path) -> dict:
    """Read the active game's state.json from a fresh-cwd test root."""
    pointer = cwd / ".sov" / "active-game"
    assert pointer.exists(), f"active-game pointer missing under {cwd}"
    game_id = pointer.read_text(encoding="utf-8").strip()
    state_path = cwd / ".sov" / "games" / game_id / "state.json"
    assert state_path.exists(), f"state.json missing for active game {game_id}"
    return json.loads(state_path.read_text(encoding="utf-8"))


def test_sov_play_campfire_v1_exits_zero(monkeypatch, tmp_path: Path) -> None:
    """``sov play campfire_v1`` runs cleanly on a fresh directory."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["play", "campfire_v1"])
    assert result.exit_code == 0, (
        f"sov play campfire_v1 must exit 0 on a fresh directory; output={result.output!r}"
    )


def test_sov_play_default_roster_is_solo_vs_ai(monkeypatch, tmp_path: Path) -> None:
    """Default ``sov play`` roster is 1 human + 1 AI opponent."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["play", "campfire_v1"])
    assert result.exit_code == 0

    state = _read_active_state(tmp_path)
    player_names = [p["name"] for p in state["players"]]
    assert player_names == ["You", "Rival"], (
        f"sov play default roster must be ['You', 'Rival']; got {player_names!r}"
    )


def test_sov_play_parity_with_sov_new_defaults(monkeypatch, tmp_path: Path) -> None:
    """``sov play campfire_v1`` produces the same roster + ruleset as
    ``sov new -p You -p Rival`` (the thin-alias parity claim).
    """
    # Run sov play in one tmp_path
    play_dir = tmp_path / "play"
    play_dir.mkdir()
    monkeypatch.chdir(play_dir)
    result = runner.invoke(app, ["play", "campfire_v1"])
    assert result.exit_code == 0
    play_state = _read_active_state(play_dir)

    # Run sov new in a second isolated tmp_path with the same defaults
    new_dir = tmp_path / "new"
    new_dir.mkdir()
    monkeypatch.chdir(new_dir)
    result = runner.invoke(
        app,
        ["new", "--seed", "42", "-p", "You", "-p", "Rival", "--tier", "campfire"],
    )
    assert result.exit_code == 0, f"sov new failed: {result.output!r}"
    new_state = _read_active_state(new_dir)

    # Parity claim: same players, same ruleset, same seed
    assert [p["name"] for p in play_state["players"]] == [p["name"] for p in new_state["players"]]
    assert play_state["config"]["ruleset"] == new_state["config"]["ruleset"]
    assert play_state["config"]["seed"] == new_state["config"]["seed"]


def test_sov_play_ruleset_to_tier_mapping(monkeypatch, tmp_path: Path) -> None:
    """Every shipped ruleset slug maps to the matching tier."""
    cases = [
        ("campfire_v1", "campfire_v1"),
        ("market_day_v1", "market_day_v1"),
        ("town_hall_v1", "town_hall_v1"),
        ("treaty_table_v1", "treaty_table_v1"),
    ]
    for i, (ruleset, expected_engine_ruleset) in enumerate(cases):
        case_dir = tmp_path / f"case-{i}"
        case_dir.mkdir()
        monkeypatch.chdir(case_dir)
        result = runner.invoke(app, ["play", ruleset, "--seed", str(100 + i)])
        assert result.exit_code == 0, f"sov play {ruleset} must exit 0; output={result.output!r}"
        state = _read_active_state(case_dir)
        assert state["config"]["ruleset"] == expected_engine_ruleset, (
            f"sov play {ruleset} must produce ruleset={expected_engine_ruleset!r}; "
            f"got {state['config']['ruleset']!r}"
        )


def test_sov_play_help_lists_ruleset_argument() -> None:
    """``sov play --help`` documents the ruleset argument."""
    result = runner.invoke(app, ["play", "--help"])
    assert result.exit_code == 0
    # Ruleset argument is documented; default is campfire_v1.
    assert "ruleset" in result.output.lower() or "RULESET" in result.output
    assert "campfire_v1" in result.output

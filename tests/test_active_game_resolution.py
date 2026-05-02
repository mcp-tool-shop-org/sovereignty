"""Active-game resolution rules — pins ``_resolve_active_game_id`` behavior.

Resolution order (per Wave 1 SPEC):

1. v1 layout present → migrate (which sets the pointer) → return migrated id.
2. ``.sov/active-game`` set + valid → return its value.
3. Pointer absent + exactly one saved game in ``.sov/games/`` → auto-pick it
   AND write the pointer as a side effect.
4. Pointer absent + zero or multiple saved games → raise
   ``SovError(STATE_NO_ACTIVE_GAME)`` via ``_fail``.

These tests target the helper directly (not through a Typer CliRunner) so
each branch is exercised in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from sov_cli.errors import SovError
from sov_cli.main import _resolve_active_game_id
from sov_engine.io_utils import (
    active_game_pointer_path,
    game_dir,
    games_dir,
    save_root,
    set_active_game_id,
    state_file,
)


def _seed_v2_game(seed: int, *, players: list[str] | None = None) -> str:
    """Plant a minimal v2 game directory rooted at cwd. Returns the game-id."""
    players = players or ["Alice", "Bob"]
    game_id = f"s{seed}"
    save_root().mkdir(parents=True, exist_ok=True)
    games_dir().mkdir(parents=True, exist_ok=True)
    game_dir(game_id).mkdir(parents=True, exist_ok=True)
    state_file(game_id).write_text(
        json.dumps(
            {
                "config": {"seed": seed, "ruleset": "campfire_v1", "max_rounds": 15},
                "current_round": 1,
                "players": [{"name": n} for n in players],
                "schema_version": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return game_id


# ---------------------------------------------------------------------------
# Branch 2: pointer present + valid
# ---------------------------------------------------------------------------


def test_resolves_to_pointer_value_when_pointer_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With ``.sov/active-game`` set to a valid game id, that id is returned."""
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    _seed_v2_game(17)
    set_active_game_id("s42")

    assert _resolve_active_game_id() == "s42"


def test_pointer_value_wins_over_lone_saved_game(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Even with only one saved game on disk, an explicit pointer is honored.

    This guards against regression where the auto-resolution branch
    overwrites an explicit choice.
    """
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    set_active_game_id("s42")
    # No second game seeded — branch 3 would also pick s42, but we want to
    # prove the pointer was honored, not the fallback.
    assert _resolve_active_game_id() == "s42"


# ---------------------------------------------------------------------------
# Branch 3: no pointer, exactly one saved game → auto-resolve
# ---------------------------------------------------------------------------


def test_auto_resolves_when_pointer_absent_and_single_game(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Pointer absent + exactly one saved game → auto-pick that game."""
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)

    assert not active_game_pointer_path().exists(), "test setup: pointer should start absent"

    resolved = _resolve_active_game_id()
    assert resolved == "s42"


def test_auto_resolution_writes_pointer_as_side_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Auto-resolution must persist the choice to ``.sov/active-game``.

    A subsequent call to ``_resolve_active_game_id`` will hit branch 2
    (pointer set), not re-derive — keeps the operator's implicit choice
    durable across invocations.
    """
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    assert not active_game_pointer_path().exists()

    _resolve_active_game_id()

    pointer = active_game_pointer_path()
    assert pointer.exists(), "auto-resolution must write the active-game pointer as a side effect"
    assert pointer.read_text(encoding="utf-8").strip() == "s42"


# ---------------------------------------------------------------------------
# Branch 4: no pointer + zero or multiple games → fail
# ---------------------------------------------------------------------------


def test_raises_when_no_pointer_and_zero_games(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Empty ``.sov/games/`` (or missing) + no pointer → STATE_NO_ACTIVE_GAME.

    ``_resolve_active_game_id`` calls ``_fail`` which prints and raises
    ``typer.Exit(1)``. We assert on the exit, then re-build the SovError
    via the public factory to pin the error code/message contract.
    """
    monkeypatch.chdir(tmp_path)
    save_root().mkdir(parents=True, exist_ok=True)
    games_dir().mkdir(parents=True, exist_ok=True)  # empty
    assert not active_game_pointer_path().exists()

    with pytest.raises(typer.Exit) as exc_info:
        _resolve_active_game_id()
    assert exc_info.value.exit_code == 1

    # Pin the error code via the factory (not the rendered output) so
    # message wording can drift without breaking this contract test.
    from sov_cli.errors import no_active_game_error

    err = no_active_game_error()
    assert isinstance(err, SovError)
    assert err.code == "STATE_NO_ACTIVE_GAME"
    assert "sov games" in err.hint and "sov resume" in err.hint


def test_raises_when_no_pointer_and_multiple_games(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Pointer absent + multiple saved games → STATE_NO_ACTIVE_GAME.

    Two saves with no pointer is the canonical "user picked nothing yet"
    state on a freshly migrated tree. The CLI must refuse to guess.
    """
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    _seed_v2_game(17)
    assert not active_game_pointer_path().exists()

    with pytest.raises(typer.Exit) as exc_info:
        _resolve_active_game_id()
    assert exc_info.value.exit_code == 1


def test_pointer_absent_but_files_exist_outside_games_dir_still_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Junk files in ``.sov/`` (wallet, season) without any saved game → fail.

    The presence of cross-game state at the root must not trick the
    resolver into auto-picking a non-existent save.
    """
    monkeypatch.chdir(tmp_path)
    save_root().mkdir(parents=True, exist_ok=True)
    (save_root() / "wallet_seed.txt").write_text("sEdSENTINEL", encoding="utf-8")
    (save_root() / "season.json").write_text("{}\n", encoding="utf-8")
    # No games_dir at all.

    with pytest.raises(typer.Exit) as exc_info:
        _resolve_active_game_id()
    assert exc_info.value.exit_code == 1

"""Tests for ``sov resume <game-id>`` — switch the active save.

Contract (per Wave 1 SPEC):

- ``sov resume <missing-id>`` exits 1 with a helpful error pointing at
  ``sov games``.
- ``sov resume <valid-id>`` writes ``.sov/active-game = <id>`` and prints a
  one-line confirmation.

Skips when the command isn't wired yet so this test file doesn't block the
wave's pytest run during parallel-agent execution.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from sov_cli.main import app
from sov_engine.io_utils import (
    active_game_pointer_path,
    game_dir,
    games_dir,
    rng_seed_file,
    save_root,
    set_active_game_id,
    state_file,
)

runner = CliRunner()


def _seed_v2_game(seed: int, *, players: list[str] | None = None) -> str:
    """Plant a minimal v2 game in ``.sov/games/<id>/``. Returns the game-id."""
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
    rng_seed_file(game_id).write_text(str(seed), encoding="utf-8")
    return game_id


def _skip_if_command_unwired(result: Result) -> None:
    """Skip the test if `sov resume` isn't wired yet (parallel-agent guard)."""
    if result.exit_code == 2 and "No such command" in (result.output or ""):
        pytest.skip(
            "`sov resume` command not yet wired by backend agent in this wave; "
            "tests will activate once the command lands."
        )


# ---------------------------------------------------------------------------
# Missing-id failure path
# ---------------------------------------------------------------------------


def test_sov_resume_missing_game_exits_with_helpful_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``sov resume <unknown-id>`` exits 1 and points at `sov games`."""
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)

    result = runner.invoke(app, ["resume", "s999"])
    _skip_if_command_unwired(result)

    assert result.exit_code == 1, (
        f"sov resume on missing game must exit 1; output={result.output!r}"
    )
    out_lower = result.output.lower()
    # Some signal that the game doesn't exist + a pointer at the listing
    # command. Wording is allowed to humanize; the load-bearing pieces are
    # the missing-id signal and the `sov games` breadcrumb.
    assert "s999" in result.output, (
        f"error must mention the requested game-id; got: {result.output!r}"
    )
    assert "sov games" in out_lower, (
        f"error must point at `sov games` for discovery; got: {result.output!r}"
    )


def test_sov_resume_missing_game_does_not_change_pointer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed resume must leave the existing active-game pointer alone."""
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    set_active_game_id("s42")
    before = active_game_pointer_path().read_text(encoding="utf-8")

    result = runner.invoke(app, ["resume", "s999"])
    _skip_if_command_unwired(result)

    assert result.exit_code == 1
    assert active_game_pointer_path().read_text(encoding="utf-8") == before, (
        "failed sov resume must not mutate the active-game pointer"
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_sov_resume_valid_game_updates_pointer_and_confirms(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``sov resume <valid-id>`` writes the pointer and prints a confirmation."""
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    _seed_v2_game(17)
    set_active_game_id("s42")  # Start out on s42.

    result = runner.invoke(app, ["resume", "s17"])
    _skip_if_command_unwired(result)

    assert result.exit_code == 0, f"sov resume on valid game must exit 0; output={result.output!r}"

    # Pointer flipped.
    assert active_game_pointer_path().read_text(encoding="utf-8").strip() == "s17"

    # Confirmation surfaces the new active id (wording flexible).
    assert "s17" in result.output, (
        f"resume confirmation must name the new active game; got: {result.output!r}"
    )


def test_sov_resume_can_switch_back_and_forth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Resume is reversible: switching A → B → A leaves A active again."""
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    _seed_v2_game(17)
    set_active_game_id("s42")

    result_b = runner.invoke(app, ["resume", "s17"])
    _skip_if_command_unwired(result_b)
    assert result_b.exit_code == 0
    assert active_game_pointer_path().read_text(encoding="utf-8").strip() == "s17"

    result_a = runner.invoke(app, ["resume", "s42"])
    _skip_if_command_unwired(result_a)
    assert result_a.exit_code == 0
    assert active_game_pointer_path().read_text(encoding="utf-8").strip() == "s42"


# ---------------------------------------------------------------------------
# Wave-7 CLI-001: path-traversal validation
# ---------------------------------------------------------------------------
#
# ``sov resume`` must reject any value that doesn't match the engine-layer
# allowlist (``^s\d{1,19}$``) BEFORE touching the filesystem. Without the
# guard, ``sov resume "s17/../s42"`` resolves to a sibling save's
# ``state.json`` AND poisons ``.sov/active-game`` with the literal
# traversal payload — every subsequent CLI invocation that consults the
# pointer then constructs malformed paths via ``state_file`` /
# ``proofs_dir`` / ``anchors_file`` / etc.


@pytest.mark.parametrize(
    "bad_id",
    [
        "s17/../s42",
        "../etc/passwd",
        "..",
        "s42\n",  # newline injection
        "s42\x00",  # NUL byte
        "",  # empty
        "/absolute/path",
        "s42/extra",
        "garbage",  # not s-prefixed
        "s",  # missing digits
        "s-1",  # negative
    ],
)
def test_sov_resume_rejects_invalid_game_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad_id: str
) -> None:
    """`sov resume <bad-id>` exits non-zero with a structured error.

    Each parametrized value covers a distinct attack / typo class:
    path traversal, control character injection, empty input,
    missing-prefix / missing-digits / negative.
    """
    monkeypatch.chdir(tmp_path)
    # Plant a real save so a successful traversal would resolve to a
    # valid state.json — proves the validator fires BEFORE filesystem.
    _seed_v2_game(42)

    result = runner.invoke(app, ["resume", bad_id])
    _skip_if_command_unwired(result)

    assert result.exit_code != 0, (
        f"sov resume must reject invalid game-id {bad_id!r}; output={result.output!r}"
    )
    # Surface the structured error code so audit-tier tooling can grep.
    assert "INPUT_GAME_ID" in result.output or "Invalid game-id" in result.output, (
        f"expected structured INPUT_GAME_ID error; got: {result.output!r}"
    )


def test_sov_resume_invalid_game_id_does_not_poison_pointer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A rejected resume must not write the malformed value to the pointer.

    Pointer-poisoning is the load-bearing harm — every subsequent helper
    that consults ``.sov/active-game`` would construct paths that resolve
    outside the per-game directory. The validator MUST run before
    ``set_active_game_id`` to keep the pointer clean.
    """
    monkeypatch.chdir(tmp_path)
    _seed_v2_game(42)
    set_active_game_id("s42")
    before = active_game_pointer_path().read_text(encoding="utf-8")

    result = runner.invoke(app, ["resume", "s17/../s42"])
    _skip_if_command_unwired(result)

    assert result.exit_code != 0
    assert active_game_pointer_path().read_text(encoding="utf-8") == before, (
        "rejected sov resume must not mutate the active-game pointer"
    )

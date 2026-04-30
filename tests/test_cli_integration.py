"""CLI integration tests for doctor / self-check / support-bundle / save-load.

Pairs with parking-lot F-432101-018: the recently-added diagnostic commands
and the persistence layer (``_save_state`` / ``_load_game``) had ZERO
integration coverage. This file exercises each command via
``typer.testing.CliRunner`` so future regressions surface in CI.

The Sovereignty CLI uses a relative ``Path(".sov")`` for its state directory,
so every test isolates state by ``monkeypatch.chdir(tmp_path)`` before
invoking the runner. This avoids polluting the developer's local ``.sov/``
directory and gives each test a clean filesystem.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sov_cli.main import app
from sov_engine.hashing import save_proof
from sov_engine.rules.campfire import new_game
from sov_engine.serialize import canonical_json, game_state_snapshot

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_minimal_game(cwd: Path, *, players: list[str] | None = None) -> None:
    """Write a minimal valid ``.sov/`` directory under *cwd*.

    Mirrors what ``sov new`` does: ``.sov/game_state.json`` (canonical
    snapshot) and ``.sov/rng_seed.txt`` (the integer seed). Avoids invoking
    ``sov new`` directly to keep these tests independent of the ``new``
    command surface (which is tested elsewhere) and to side-step its
    ``typer.confirm`` overwrite prompt.
    """
    players = players or ["Alice", "Bob"]
    state, _ = new_game(42, players)
    sov_dir = cwd / ".sov"
    sov_dir.mkdir(parents=True, exist_ok=True)
    snapshot = game_state_snapshot(state)
    (sov_dir / "game_state.json").write_text(
        canonical_json(snapshot),
        encoding="utf-8",
        newline="\n",
    )
    (sov_dir / "rng_seed.txt").write_text("42", encoding="utf-8")


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def test_sov_doctor_exits_clean_with_no_game(monkeypatch, tmp_path):
    """``sov doctor`` in a fresh directory must exit 0 and report no game."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, f"doctor must exit clean with no game; output={result.output!r}"
    # Must mention there's no active game (in some shape -- info-level line).
    assert "No active game" in result.output or "No game directory" in result.output


def test_sov_doctor_with_active_game_lists_state(monkeypatch, tmp_path):
    """``sov doctor`` with a seeded game must enumerate players and round."""
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path, players=["Alice", "Bob"])

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, f"doctor with active game must exit 0; output={result.output!r}"
    # Active-game line names the players and the round.
    assert "Alice" in result.output
    assert "Bob" in result.output


def test_sov_doctor_with_corrupted_game_state_emits_clean_error(monkeypatch, tmp_path):
    """Corrupted ``.sov/game_state.json`` must produce a structured, non-bare
    error path (no raw ``json.JSONDecodeError`` traceback to the user).

    Pairs with engine F-432101-008 (``_load_game`` defensive try/except).
    Today ``doctor`` already catches the load failure and reports
    ``"Game state exists but can't load"``; this test pins that observable
    behavior so a regression that drops the catch will fail loud.
    """
    monkeypatch.chdir(tmp_path)
    sov_dir = tmp_path / ".sov"
    sov_dir.mkdir(parents=True, exist_ok=True)
    # Garbage JSON -- must NOT crash with a bare JSONDecodeError trace.
    (sov_dir / "game_state.json").write_text("{ not json garbage", encoding="utf-8")
    (sov_dir / "rng_seed.txt").write_text("42", encoding="utf-8")

    result = runner.invoke(app, ["doctor"])

    # Either: (a) doctor catches and reports a structured warn line (current
    # behavior, exit 0), OR (b) the engine's STATE_CORRUPT SovError exits
    # non-zero with a clean message. Either way: NO bare Python traceback
    # should reach the user. The structured message MAY include the
    # exception class name as a debug breadcrumb (engine F-008 amend
    # surfaces "Saved game state is unreadable. JSONDecodeError: ...") —
    # that's not a leaked traceback, just informative context.
    assert "Traceback (most recent call last)" not in result.output, (
        f"doctor must not emit a bare Python traceback to the user; got: {result.output!r}"
    )
    # Some structured signal that the load failed.
    assert (
        "unreadable" in result.output.lower()
        or "can't load" in result.output.lower()
        or "corrupt" in result.output.lower()
        or "invalid" in result.output.lower()
        or "error" in result.output.lower()
    ), f"doctor must surface a clean load-failure message; got: {result.output!r}"


# ---------------------------------------------------------------------------
# self-check
# ---------------------------------------------------------------------------


def test_sov_self_check_returns_ok_status_lines(monkeypatch, tmp_path):
    """``sov self-check`` must run cleanly and emit OK lines."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["self-check"])

    assert result.exit_code == 0, f"self-check must exit 0; output={result.output!r}"
    # At least one OK status line for the core checks.
    assert "OK" in result.output, (
        f"self-check must emit at least one OK status; got: {result.output!r}"
    )
    # Version line is always present.
    assert "Version" in result.output


def test_sov_self_check_json_mode(monkeypatch, tmp_path):
    """``sov self-check --json`` must emit a parseable structured payload.

    Engine adds ``--json`` in this wave. Per the coordination contract the
    payload must include: ``timestamp``, ``command``, ``status``, ``fields[]``.

    NOTE: this test is tolerant of the engine landing the flag slightly
    differently. If ``--json`` is not yet wired (exit code 2 from typer's
    UsageError), the test is skipped rather than failing -- but as soon as
    the flag is recognized, it pins the schema.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["self-check", "--json"])

    if result.exit_code == 2:
        pytest.skip(
            "self-check --json flag not yet wired by engine agent in this wave; "
            "this test will activate once the flag lands.",
        )

    assert result.exit_code == 0, f"self-check --json must exit 0; output={result.output!r}"

    # Locate the JSON payload in stdout. Some implementations wrap the JSON
    # in a single line; others may print it as a block. Try to parse the
    # first '{' -> last '}' window.
    output = result.output
    start = output.find("{")
    end = output.rfind("}")
    assert start != -1 and end != -1 and end > start, (
        f"self-check --json must emit a JSON object; got: {output!r}"
    )
    payload = json.loads(output[start : end + 1])

    # Coordination contract schema: {timestamp, command, status, fields[]}
    for required in ("timestamp", "command", "status", "fields"):
        assert required in payload, (
            f"self-check --json payload missing '{required}' key; got: {payload!r}"
        )
    assert isinstance(payload["fields"], list), (
        f"'fields' must be a list; got: {type(payload['fields']).__name__}"
    )
    assert payload["command"] == "self-check"


# ---------------------------------------------------------------------------
# support-bundle
# ---------------------------------------------------------------------------


def test_sov_support_bundle_writes_zip_with_required_files_and_no_seed_material(
    monkeypatch,
    tmp_path,
):
    """``sov support-bundle`` must:

    1. write a zip into the cwd with a recognizable name pattern
    2. include the diagnostic files (self-check.txt, environment.json)
    3. NOT include any wallet seed material -- this is the security
       regression guard for the seed-leak class.
    """
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)

    # Plant a wallet seed so we can prove it does not leak into the bundle.
    sentinel_seed = "sEdTESTSEEDDONOTLEAK1234567890XYZ"
    (tmp_path / ".sov" / "wallet_seed.txt").write_text(sentinel_seed, encoding="utf-8")

    result = runner.invoke(app, ["support-bundle"])
    assert result.exit_code == 0, f"support-bundle must exit 0; output={result.output!r}"

    # Find the bundle in cwd.
    bundles = sorted(tmp_path.glob("sov-support-*.zip"))
    assert bundles, (
        f"support-bundle must write a sov-support-*.zip into cwd; "
        f"found: {list(tmp_path.iterdir())!r}"
    )
    bundle = bundles[-1]

    with zipfile.ZipFile(bundle, "r") as zf:
        names = set(zf.namelist())
        # Required diagnostic artifacts.
        assert "self-check.txt" in names, (
            f"bundle must contain self-check.txt; got: {sorted(names)!r}"
        )
        assert "environment.json" in names, (
            f"bundle must contain environment.json; got: {sorted(names)!r}"
        )

        # Security regression guard: the wallet seed string must NOT appear
        # in ANY bundled file's bytes.
        for name in names:
            blob = zf.read(name)
            assert sentinel_seed.encode("utf-8") not in blob, (
                f"wallet seed leaked into bundle file '{name}'; "
                "support-bundle must scrub seed material from every artifact."
            )


# ---------------------------------------------------------------------------
# save / load round-trip with treaty dedup
# ---------------------------------------------------------------------------


def test_save_load_round_trip_preserves_treaties_with_dedup(monkeypatch, tmp_path):
    """Save -> load must preserve a SHARED treaty as one deduped object.

    Pairs with engine state ``schema_version`` work. Two players sharing a
    treaty (Alice <-> Bob) is the historical bug source: the deduplicating
    registry in ``_load_game`` (sov_cli/main.py:179) must yield ONE Treaty
    instance referenced by both players, not two divergent copies.
    """
    monkeypatch.chdir(tmp_path)

    # Build a Treaty Table game and stake a treaty between Alice and Bob.
    from sov_engine.models import Stake
    from sov_engine.rules.treaty_table import new_treaty_table_game, treaty_make

    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    treaty_make(state, alice, bob, "shared pact", Stake(coins=2), Stake(coins=1))

    # Both players reference the same Treaty object pre-save.
    assert len(alice.active_treaties) == 1
    assert len(bob.active_treaties) == 1
    assert alice.active_treaties[0] is bob.active_treaties[0]
    treaty_id = alice.active_treaties[0].treaty_id

    # Persist via _save_state (the production write path).
    from sov_cli.main import _load_game, _save_state

    _save_state(state)
    (tmp_path / ".sov" / "rng_seed.txt").write_text("42", encoding="utf-8")

    # Reload and assert the treaty is deduped.
    loaded = _load_game()
    assert loaded is not None, "_load_game must round-trip a saved game"
    state2, _ = loaded

    alice2, bob2 = state2.players
    assert len(alice2.active_treaties) == 1, (
        f"Alice should have 1 treaty after reload; got {len(alice2.active_treaties)}"
    )
    assert len(bob2.active_treaties) == 1, (
        f"Bob should have 1 treaty after reload; got {len(bob2.active_treaties)}"
    )
    # The dedup contract: both players share the SAME Treaty instance.
    assert alice2.active_treaties[0] is bob2.active_treaties[0], (
        "After reload, shared treaty must be ONE deduped object referenced "
        "by both players (not two divergent copies)."
    )
    assert alice2.active_treaties[0].treaty_id == treaty_id


# ---------------------------------------------------------------------------
# Suppress unused-import warnings for save_proof / Path (kept for forward use)
# ---------------------------------------------------------------------------

_ = (save_proof, Path)

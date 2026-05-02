"""v1 → v2 multi-save migration tests.

Pins ``sov_engine.io_utils.migrate_v1_layout``: the one-shot, idempotent
migration that moves a single-game v1 ``.sov/`` tree into the v2 multi-save
layout under ``.sov/games/<game-id>/``.

Migration contract (per Wave 1 SPEC):

- Detect: ``.sov/game_state.json`` exists AND ``.sov/games/`` does not.
- Move ``game_state.json`` → ``.sov/games/<id>/state.json``.
- Move ``rng_seed.txt`` → ``.sov/games/<id>/rng_seed.txt`` (if present).
- Move ``proofs/`` → ``.sov/games/<id>/proofs/`` (if present).
- Set ``.sov/active-game`` = ``<id>``.
- Cross-game state (``wallet_seed.txt``, ``season.json``) stays at root.
- Re-run on v2 tree → no-op, returns ``None``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sov_engine.io_utils import (
    active_game_pointer_path,
    game_dir,
    games_dir,
    migrate_v1_layout,
    save_root,
    state_file,
)


def _write_v1_layout(
    cwd: Path,
    *,
    seed: int = 42,
    with_proofs: bool = True,
    with_wallet: bool = True,
    with_season: bool = True,
) -> None:
    """Plant a v1-shaped ``.sov/`` tree rooted at *cwd*.

    Mirrors what an existing v2.0.x install left on disk: a single
    ``game_state.json`` at the root, an ``rng_seed.txt`` next to it, a
    ``proofs/`` directory with at least one round proof + an anchors.json,
    plus the cross-game ``wallet_seed.txt`` and ``season.json``.
    """
    sov = cwd / ".sov"
    sov.mkdir(parents=True, exist_ok=True)

    # Minimal v1 game_state.json. Migration only reads ``config.seed`` to
    # derive the game-id; the rest is opaque payload that gets moved as-is.
    payload = {
        "config": {"seed": seed, "ruleset": "campfire_v1", "max_rounds": 15},
        "current_round": 1,
        "players": [{"name": "Alice"}, {"name": "Bob"}],
        "schema_version": 1,
    }
    (sov / "game_state.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (sov / "rng_seed.txt").write_text(str(seed), encoding="utf-8")

    if with_proofs:
        proofs = sov / "proofs"
        proofs.mkdir(parents=True, exist_ok=True)
        (proofs / "round_1.proof.json").write_text(
            json.dumps({"round": 1, "envelope_hash": "deadbeef"}) + "\n",
            encoding="utf-8",
        )
        (proofs / "anchors.json").write_text("{}\n", encoding="utf-8")

    if with_wallet:
        (sov / "wallet_seed.txt").write_text("sEdSENTINEL_WALLET_SEED", encoding="utf-8")
    if with_season:
        (sov / "season.json").write_text(
            json.dumps({"games": [], "standings": {}}) + "\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Happy path: v1 → v2
# ---------------------------------------------------------------------------


def test_migrate_v1_returns_derived_game_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Migration returns ``f"s{seed}"`` from the v1 state's config.seed."""
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)

    result = migrate_v1_layout()
    assert result == "s42", f"migration must return the derived game-id 's{42}'; got: {result!r}"


def test_migrate_v1_moves_state_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``.sov/game_state.json`` moves to ``.sov/games/s42/state.json``."""
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)

    assert (tmp_path / ".sov" / "game_state.json").exists()
    migrate_v1_layout()

    # Old path gone.
    assert not (tmp_path / ".sov" / "game_state.json").exists(), (
        "v1 game_state.json must be removed (moved) by migration"
    )
    # New path present.
    new_state = state_file("s42")
    assert new_state.exists(), f"migrated state file must exist at {new_state}"
    # Contents preserved (round-trip identity check via config.seed).
    data = json.loads(new_state.read_text(encoding="utf-8"))
    assert data["config"]["seed"] == 42


def test_migrate_v1_moves_rng_seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``.sov/rng_seed.txt`` moves to ``.sov/games/s42/rng_seed.txt``."""
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)
    migrate_v1_layout()

    assert not (tmp_path / ".sov" / "rng_seed.txt").exists()
    moved = game_dir("s42") / "rng_seed.txt"
    assert moved.exists()
    assert moved.read_text(encoding="utf-8").strip() == "42"


def test_migrate_v1_moves_proofs_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``.sov/proofs/`` (entire dir incl. anchors.json) moves into the per-game subtree."""
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)
    assert (tmp_path / ".sov" / "proofs" / "round_1.proof.json").exists()

    migrate_v1_layout()

    assert not (tmp_path / ".sov" / "proofs").exists(), (
        "v1 .sov/proofs/ must be moved (not copied) — old dir should be gone"
    )
    new_proofs = game_dir("s42") / "proofs"
    assert new_proofs.is_dir()
    assert (new_proofs / "round_1.proof.json").exists()
    assert (new_proofs / "anchors.json").exists()


def test_migrate_v1_sets_active_game_pointer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """After migration, ``.sov/active-game`` contains the migrated game-id."""
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)
    migrate_v1_layout()

    pointer = active_game_pointer_path()
    assert pointer.exists(), "active-game pointer must be written by migration"
    assert pointer.read_text(encoding="utf-8").strip() == "s42"


def test_migrate_v1_does_not_move_wallet_seed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cross-game ``wallet_seed.txt`` stays at ``.sov/wallet_seed.txt``."""
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)
    wallet = tmp_path / ".sov" / "wallet_seed.txt"
    sentinel = wallet.read_text(encoding="utf-8")

    migrate_v1_layout()

    assert wallet.exists(), "wallet_seed.txt must remain at .sov/ root after migration"
    assert wallet.read_text(encoding="utf-8") == sentinel, (
        "wallet_seed.txt contents must be untouched"
    )
    # And it must NOT have been duplicated into the per-game dir.
    assert not (game_dir("s42") / "wallet_seed.txt").exists(), (
        "wallet_seed.txt must not be copied into the per-game dir"
    )


def test_migrate_v1_does_not_move_season_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cross-game ``season.json`` stays at ``.sov/season.json``."""
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)
    season = tmp_path / ".sov" / "season.json"
    sentinel = season.read_text(encoding="utf-8")

    migrate_v1_layout()

    assert season.exists(), "season.json must remain at .sov/ root"
    assert season.read_text(encoding="utf-8") == sentinel
    assert not (game_dir("s42") / "season.json").exists()


# ---------------------------------------------------------------------------
# Idempotency / no-op cases
# ---------------------------------------------------------------------------


def test_migrate_v1_is_noop_on_already_v2_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Running migration on a v2 tree returns ``None`` and changes nothing.

    Idempotency contract: the CLI calls migrate on every invocation; a v2
    tree with multiple games must not be reshaped or have its active-game
    pointer overwritten.
    """
    monkeypatch.chdir(tmp_path)

    # Build a v2 tree by hand (no v1 game_state.json present).
    save_root().mkdir(parents=True, exist_ok=True)
    games_dir().mkdir(parents=True, exist_ok=True)
    game_dir("s42").mkdir(parents=True, exist_ok=True)
    state_file("s42").write_text(
        json.dumps(
            {
                "config": {"seed": 42, "ruleset": "campfire_v1", "max_rounds": 15},
                "current_round": 1,
                "players": [{"name": "Alice"}],
                "schema_version": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pointer = active_game_pointer_path()
    pointer.write_text("s42\n", encoding="utf-8")

    before_state_bytes = state_file("s42").read_bytes()
    before_pointer = pointer.read_text(encoding="utf-8")

    result = migrate_v1_layout()
    assert result is None, f"v2 tree must produce no migration; got: {result!r}"

    # Layout untouched.
    assert state_file("s42").read_bytes() == before_state_bytes
    assert pointer.read_text(encoding="utf-8") == before_pointer
    # No phantom v1 paths should have appeared.
    assert not (tmp_path / ".sov" / "game_state.json").exists()
    assert not (tmp_path / ".sov" / "rng_seed.txt").exists()


def test_migrate_v1_returns_none_when_sov_dir_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Empty workspace (no ``.sov/`` at all) → migration is a no-op."""
    monkeypatch.chdir(tmp_path)
    assert migrate_v1_layout() is None
    # And nothing should have been created.
    assert not save_root().exists()


def test_migrate_v1_returns_none_when_no_v1_game_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``.sov/`` exists but no ``game_state.json`` → no-op."""
    monkeypatch.chdir(tmp_path)
    save_root().mkdir(parents=True, exist_ok=True)
    # Plant cross-game state only — common shape just after `sov wallet`.
    (save_root() / "wallet_seed.txt").write_text("sEdEMPTY", encoding="utf-8")

    assert migrate_v1_layout() is None
    # Wallet untouched.
    assert (save_root() / "wallet_seed.txt").read_text(encoding="utf-8") == "sEdEMPTY"


def test_migrate_v1_running_twice_is_safe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Running migration a second time after success returns ``None``.

    First run does the move. Second run sees a v2 layout (state.json under
    ``.sov/games/s42/``) plus no remaining ``.sov/game_state.json``, so it
    must short-circuit cleanly without raising or duplicating.
    """
    monkeypatch.chdir(tmp_path)
    _write_v1_layout(tmp_path, seed=42)

    first = migrate_v1_layout()
    assert first == "s42"

    second = migrate_v1_layout()
    assert second is None, f"second migration must be a no-op; got: {second!r}"
    # Pointer + state still present.
    assert state_file("s42").exists()
    assert active_game_pointer_path().read_text(encoding="utf-8").strip() == "s42"

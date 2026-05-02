"""Shared I/O utilities for sovereignty.

Atomic write helper used by both the engine (proof persistence) and the
CLI (game state, season, rng_seed, anchors). Lives in the engine layer
because the engine cannot import from the CLI; CLI imports from engine.

Multi-save layout (v2.1)
------------------------
``.sov/`` is the persistence root. Cross-game state (``wallet_seed.txt``,
``season.json``) lives at the root. Per-game state lives under
``.sov/games/<game-id>/`` where ``game-id`` is ``f"s{seed}"`` to match the
existing convention used in proof envelopes / anchors.

A single-line pointer file ``.sov/active-game`` names the currently active
game. The CLI's ``_resolve_active_game_id`` helper reads it and falls back
to migration / single-game inference.

The v1 → v2 migration runs once on first invocation against a v1 layout.
It is idempotent: running on a v2 layout is a no-op.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("sov_engine")


def atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically.

    Crash / disk-full mid-write leaves a ``.tmp`` sibling, NOT a half-written
    target file. Single-process write atomicity only — concurrent-writer
    locking is the caller's responsibility.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Multi-save layout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GameSummary:
    """Summary of a saved game, surfaced by ``sov games`` and viewers.

    ``last_modified_iso`` is the state.json mtime rendered as ISO-8601 UTC
    (``YYYY-MM-DDTHH:MM:SSZ``). It's used both for the human-readable
    "LAST PLAYED" column and for sorting most-recent-first in the listing.
    """

    game_id: str
    ruleset: str
    current_round: int
    max_rounds: int
    players: tuple[str, ...]
    last_modified_iso: str


def save_root() -> Path:
    """Return ``Path('.sov')`` — the root of all sovereignty persistence."""
    return Path(".sov")


def games_dir() -> Path:
    """Return ``.sov/games/`` — the directory holding per-game subtrees."""
    return save_root() / "games"


def active_game_pointer_path() -> Path:
    """Return ``.sov/active-game`` — the pointer file naming the active game."""
    return save_root() / "active-game"


def game_dir(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/``."""
    return games_dir() / game_id


def state_file(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/state.json``."""
    return game_dir(game_id) / "state.json"


def rng_seed_file(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/rng_seed.txt``."""
    return game_dir(game_id) / "rng_seed.txt"


def proofs_dir(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/proofs/``."""
    return game_dir(game_id) / "proofs"


def anchors_file(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/proofs/anchors.json``."""
    return proofs_dir(game_id) / "anchors.json"


def get_active_game_id() -> str | None:
    """Read ``.sov/active-game`` and return its game-id.

    Returns ``None`` when the pointer file is absent, empty, or unreadable.
    Whitespace is stripped — the file is a one-liner by contract.
    """
    pointer = active_game_pointer_path()
    if not pointer.exists():
        return None
    try:
        contents = pointer.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning(
            "active_game.read.failed path=%s exc=%s detail=%s",
            pointer,
            type(exc).__name__,
            exc,
        )
        return None
    return contents or None


def set_active_game_id(game_id: str) -> None:
    """Atomically write ``.sov/active-game = <game-id>``.

    Creates ``.sov/`` if it does not yet exist. The write goes through
    ``atomic_write_text`` so crash-mid-write leaves a ``.tmp`` sibling,
    not a half-written pointer.
    """
    save_root().mkdir(parents=True, exist_ok=True)
    atomic_write_text(active_game_pointer_path(), game_id + "\n")


def _summarize_game(game_id: str, sf: Path) -> GameSummary | None:
    """Build a ``GameSummary`` for ``sf`` (an existing state.json path).

    Returns ``None`` and logs at WARNING when the file is unreadable or
    malformed — listings should skip such directories silently rather
    than crash the whole `sov games` command.
    """
    try:
        raw = sf.read_text(encoding="utf-8")
        data = json.loads(raw)
        ruleset = str(data.get("config", {}).get("ruleset", "unknown"))
        max_rounds = int(data.get("config", {}).get("max_rounds", 0))
        current_round = int(data.get("current_round", 0))
        players_raw = data.get("players", [])
        players = tuple(str(p.get("name", "?")) for p in players_raw)
        mtime = sf.stat().st_mtime
        last_modified = datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.warning(
            "list_saved_games.skip path=%s exc=%s detail=%s",
            sf,
            type(exc).__name__,
            exc,
        )
        return None
    return GameSummary(
        game_id=game_id,
        ruleset=ruleset,
        current_round=current_round,
        max_rounds=max_rounds,
        players=players,
        last_modified_iso=last_modified,
    )


def list_saved_games() -> list[GameSummary]:
    """Scan ``.sov/games/`` and return one ``GameSummary`` per valid game.

    Directories without a readable ``state.json`` are skipped silently
    (logged at WARNING). Result is sorted by ``last_modified_iso``
    descending — most recently played first.
    """
    root = games_dir()
    if not root.exists():
        return []
    summaries: list[GameSummary] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        sf = entry / "state.json"
        if not sf.exists():
            continue
        summary = _summarize_game(entry.name, sf)
        if summary is not None:
            summaries.append(summary)
    summaries.sort(key=lambda s: s.last_modified_iso, reverse=True)
    return summaries


def migrate_v1_layout() -> str | None:
    """Detect + migrate a v1 ``.sov/`` layout to v2.

    v1 layout: ``.sov/game_state.json`` exists.
    v2 layout: ``.sov/games/<game-id>/state.json`` (one or more).

    On a v1 tree, this:
      1. Reads ``.sov/game_state.json`` to derive ``game_id = f"s{seed}"``.
      2. Creates ``.sov/games/<game-id>/``.
      3. Moves the v1 files into the per-game subtree.
      4. Writes ``.sov/active-game`` pointing at ``<game-id>``.
      5. Returns the migrated game-id.

    On a v2 tree (or an empty ``.sov/``), returns ``None`` and writes
    nothing. Idempotent.

    The migration uses ``os.replace`` for the directory move — atomic on
    the same filesystem, which ``.sov/`` always is by construction
    (everything lives under one parent dir).
    """
    root = save_root()
    legacy_state = root / "game_state.json"
    legacy_seed = root / "rng_seed.txt"
    legacy_proofs = root / "proofs"
    new_games = games_dir()

    # v2 already in place — no-op.
    if new_games.exists() and any(new_games.iterdir()):
        return None
    # Nothing to migrate from.
    if not legacy_state.exists():
        return None

    # Derive game_id from the v1 state.
    try:
        data = json.loads(legacy_state.read_text(encoding="utf-8"))
        seed = data["config"]["seed"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning(
            "migrate_v1_layout.skip path=%s exc=%s detail=%s "
            "(unreadable v1 state.json — leaving layout alone)",
            legacy_state,
            type(exc).__name__,
            exc,
        )
        return None

    game_id = f"s{seed}"
    new_games.mkdir(parents=True, exist_ok=True)
    target = game_dir(game_id)
    target.mkdir(parents=True, exist_ok=True)

    # Move state.json + rng_seed.txt + the proofs/ directory.
    os.replace(legacy_state, target / "state.json")
    if legacy_seed.exists():
        os.replace(legacy_seed, target / "rng_seed.txt")
    if legacy_proofs.exists() and legacy_proofs.is_dir():
        os.replace(legacy_proofs, target / "proofs")

    set_active_game_id(game_id)

    # One-line stderr breadcrumb so operators know what happened.
    import sys

    print(
        f"[multi-save] migrated v1 layout → .sov/games/{game_id}/",
        file=sys.stderr,
    )
    return game_id

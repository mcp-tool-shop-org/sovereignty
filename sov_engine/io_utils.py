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

Game-id validation (v2.1, BACKEND-001)
--------------------------------------
``game_id`` is the only user-controlled component of every per-game path.
``VALID_GAME_ID_PATTERN`` is the canonical regex (``^s\\d{1,19}$`` — matches
``f"s{seed}"`` where ``seed`` is a non-negative int64). ``_validate_game_id``
is called at the top of every helper that accepts ``game_id`` so that path
traversal (``..``, ``/``, ``\\``, NUL, ASCII control, anything not matching
the pattern) is rejected at the engine layer. Daemon and CLI re-import
``VALID_GAME_ID_PATTERN`` for their boundary checks (defense in depth).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger("sov_engine")


# ---------------------------------------------------------------------------
# Game-id validation (BACKEND-001)
# ---------------------------------------------------------------------------

#: Canonical game-id pattern. Matches ``f"s{seed}"`` where seed is a non-negative
#: integer up to 19 digits (int64 ceiling). Producers: ``sov_engine.hashing``
#: (line 53) and ``sov_cli.main`` (the resume / new-game paths). Re-exported so
#: ``sov_daemon.server`` and ``sov_cli.main`` can validate at their boundaries.
VALID_GAME_ID_PATTERN = re.compile(r"^s\d{1,19}$")


def _validate_game_id(game_id: str) -> None:
    """Raise ``ValueError`` if ``game_id`` is not a legitimate ``s<int>`` id.

    Rejects path-traversal payloads (``..``, ``/``, ``\\``), NUL / control
    characters, empty string, non-string input, and anything that isn't the
    ``f"s{seed}"`` shape produced by the engine. This is the engine-layer
    last line of defense — daemon and CLI should also validate at their
    boundaries (defense in depth).
    """
    if not isinstance(game_id, str) or not VALID_GAME_ID_PATTERN.fullmatch(game_id):
        raise ValueError(f"invalid game_id (must match s<integer>, got): {game_id!r}")


def atomic_write_text(path: Path, content: str, *, mode: int | None = None) -> None:
    """Write ``content`` to ``path`` atomically.

    Crash / disk-full mid-write leaves a ``.tmp`` sibling, NOT a half-written
    target file. Single-process write atomicity only — concurrent-writer
    locking is the caller's responsibility.

    When ``mode`` is given (e.g. ``0o600``), the resulting file's permission
    bits are set via ``os.chmod`` after the rename. On Windows ``os.chmod``
    only honors the read-only bit and is treated as best-effort. When
    ``mode`` is ``None`` the umask-default (typically ``0o644``) applies.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    if mode is not None:
        try:
            os.chmod(path, mode)
        except OSError as exc:
            # Windows + best-effort: chmod may only honor the read-only bit.
            # Not a fatal error — log and continue.
            logger.warning(
                "atomic_write_text.chmod.failed path=%s mode=%o exc=%s detail=%s",
                path,
                mode,
                type(exc).__name__,
                exc,
            )


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
    """Return ``.sov/games/<game-id>/``. Validates ``game_id``."""
    _validate_game_id(game_id)
    return games_dir() / game_id


def state_file(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/state.json``. Validates ``game_id``."""
    _validate_game_id(game_id)
    return games_dir() / game_id / "state.json"


def rng_seed_file(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/rng_seed.txt``. Validates ``game_id``."""
    _validate_game_id(game_id)
    return games_dir() / game_id / "rng_seed.txt"


def proofs_dir(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/proofs/``. Validates ``game_id``."""
    _validate_game_id(game_id)
    return games_dir() / game_id / "proofs"


def anchors_file(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/proofs/anchors.json``. Validates ``game_id``."""
    _validate_game_id(game_id)
    return games_dir() / game_id / "proofs" / "anchors.json"


def get_active_game_id() -> str | None:
    """Read ``.sov/active-game`` and return its game-id.

    Returns ``None`` when the pointer file is absent, empty, or unreadable.
    Whitespace is stripped — the file is a one-liner by contract.

    A poisoned pointer (one that fails ``_validate_game_id``) surfaces as
    ``None`` plus a WARNING log, NOT propagated to callers — defense in depth
    against an attacker who managed to write the pointer once.
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
    if not contents:
        return None
    try:
        _validate_game_id(contents)
    except ValueError as exc:
        logger.warning(
            "active_game.read.poisoned path=%s detail=%s "
            "(rejecting malformed pointer; treating as no active game)",
            pointer,
            exc,
        )
        return None
    return contents


def set_active_game_id(game_id: str) -> None:
    """Atomically write ``.sov/active-game = <game-id>``.

    Validates ``game_id`` before writing — refuses to persist a malformed
    pointer that subsequent invocations would have to defensively reject.
    Creates ``.sov/`` if it does not yet exist. The write goes through
    ``atomic_write_text`` so crash-mid-write leaves a ``.tmp`` sibling,
    not a half-written pointer.
    """
    _validate_game_id(game_id)
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
        # Skip subdirs whose names aren't valid game-ids — don't surface
        # accidentally-created junk in `sov games` output.
        try:
            _validate_game_id(entry.name)
        except ValueError:
            continue
        sf = entry / "state.json"
        if not sf.exists():
            continue
        summary = _summarize_game(entry.name, sf)
        if summary is not None:
            summaries.append(summary)
    summaries.sort(key=lambda s: s.last_modified_iso, reverse=True)
    return summaries


# ---------------------------------------------------------------------------
# Migration breadcrumb (BACKEND-002)
# ---------------------------------------------------------------------------
#
# ``migrate_v1_layout`` performs three sequential ``os.replace`` calls.
# When the second or third fails (cross-device mount, permission
# revocation, disk full), the tree is left half-migrated. Without a
# breadcrumb the next invocation short-circuits past the orphan files
# silently. We stamp ``.sov/migration-state.json`` before each move and
# clear it after the last move succeeds so a crash leaves a record of
# what was supposed to happen, plus an operator-actionable hint.


_MIGRATION_BREADCRUMB_NAME = "migration-state.json"


def _migration_breadcrumb_path() -> Path:
    """Return ``.sov/migration-state.json``."""
    return save_root() / _MIGRATION_BREADCRUMB_NAME


def _write_migration_breadcrumb(
    *,
    target_game_id: str,
    step: str,
    legacy_paths: list[str],
) -> None:
    """Stamp the in-flight migration step. Tolerates write failures.

    The breadcrumb is best-effort — if the disk is so far gone that we
    can't even stamp it, we still want the original ``os.replace`` failure
    to propagate as the primary error.
    """
    payload = {
        "schema_version": 1,
        "target_game_id": target_game_id,
        "step": step,
        "legacy_paths": legacy_paths,
        "stamped_iso": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        atomic_write_text(
            _migration_breadcrumb_path(),
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
    except OSError as exc:
        logger.warning(
            "migrate_v1_layout.breadcrumb.write_failed step=%s exc=%s detail=%s",
            step,
            type(exc).__name__,
            exc,
        )


def _clear_migration_breadcrumb() -> None:
    """Remove the breadcrumb. Tolerates missing-file."""
    path = _migration_breadcrumb_path()
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


def _read_migration_breadcrumb() -> dict[str, object] | None:
    """Read the breadcrumb if present + parsable; else ``None``."""
    path = _migration_breadcrumb_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "migrate_v1_layout.breadcrumb.read_failed path=%s exc=%s detail=%s",
            path,
            type(exc).__name__,
            exc,
        )
        return None
    if not isinstance(data, dict):
        return None
    return data


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

    Partial-failure recovery (BACKEND-002): a breadcrumb at
    ``.sov/migration-state.json`` is stamped before each move and cleared
    on success. On entry, we check for a stale breadcrumb and complete
    the in-flight migration before deciding the tree is "v2 already".
    """
    root = save_root()
    legacy_state = root / "game_state.json"
    legacy_seed = root / "rng_seed.txt"
    legacy_proofs = root / "proofs"
    new_games = games_dir()

    # If a previous invocation crashed mid-migration, the breadcrumb is
    # still on disk. Recover before deciding shape.
    crumb = _read_migration_breadcrumb()
    if crumb is not None:
        recovered = _recover_partial_migration(crumb)
        if recovered is not None:
            return recovered

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
    try:
        _validate_game_id(game_id)
    except ValueError as exc:
        logger.warning(
            "migrate_v1_layout.skip reason=invalid_seed_in_v1_state seed=%r detail=%s",
            seed,
            exc,
        )
        return None
    new_games.mkdir(parents=True, exist_ok=True)
    target = game_dir(game_id)
    target.mkdir(parents=True, exist_ok=True)

    legacy_paths = [str(p) for p in (legacy_state, legacy_seed, legacy_proofs) if p.exists()]

    try:
        _write_migration_breadcrumb(target_game_id=game_id, step="state", legacy_paths=legacy_paths)
        os.replace(legacy_state, target / "state.json")

        if legacy_seed.exists():
            _write_migration_breadcrumb(
                target_game_id=game_id, step="rng_seed", legacy_paths=legacy_paths
            )
            os.replace(legacy_seed, target / "rng_seed.txt")

        if legacy_proofs.exists() and legacy_proofs.is_dir():
            _write_migration_breadcrumb(
                target_game_id=game_id, step="proofs", legacy_paths=legacy_paths
            )
            os.replace(legacy_proofs, target / "proofs")
    except OSError as exc:
        logger.error(
            "migrate_v1_layout.partial_failure target=%s exc=%s detail=%s "
            "— breadcrumb at %s names the in-flight step. The next invocation "
            "will retry the remaining moves.",
            target,
            type(exc).__name__,
            exc,
            _migration_breadcrumb_path(),
        )
        raise

    _clear_migration_breadcrumb()
    set_active_game_id(game_id)

    # One-line stderr breadcrumb so operators know what happened.
    print(
        f"[multi-save] migrated v1 layout → .sov/games/{game_id}/",
        file=sys.stderr,
    )
    return game_id


def _recover_partial_migration(crumb: dict[str, object]) -> str | None:
    """Finish a previously-interrupted migration based on the breadcrumb.

    Returns the recovered game-id when the partial state was successfully
    completed, or ``None`` when there's nothing to do (breadcrumb names a
    game that no longer has any orphan v1 files).
    """
    target_game_id = crumb.get("target_game_id")
    if not isinstance(target_game_id, str):
        logger.warning("migrate_v1_layout.breadcrumb.malformed reason=missing_target_game_id")
        _clear_migration_breadcrumb()
        return None
    try:
        _validate_game_id(target_game_id)
    except ValueError:
        logger.warning(
            "migrate_v1_layout.breadcrumb.malformed reason=invalid_target_game_id value=%r",
            target_game_id,
        )
        _clear_migration_breadcrumb()
        return None

    root = save_root()
    legacy_state = root / "game_state.json"
    legacy_seed = root / "rng_seed.txt"
    legacy_proofs = root / "proofs"

    target = game_dir(target_game_id)
    target.mkdir(parents=True, exist_ok=True)

    try:
        if legacy_state.exists():
            os.replace(legacy_state, target / "state.json")
        if legacy_seed.exists():
            os.replace(legacy_seed, target / "rng_seed.txt")
        if legacy_proofs.exists() and legacy_proofs.is_dir():
            os.replace(legacy_proofs, target / "proofs")
    except OSError as exc:
        logger.error(
            "migrate_v1_layout.recover.partial_failure target=%s exc=%s detail=%s "
            "— breadcrumb retained; next invocation will retry.",
            target,
            type(exc).__name__,
            exc,
        )
        raise

    _clear_migration_breadcrumb()
    set_active_game_id(target_game_id)
    print(
        f"[multi-save] completed interrupted migration → .sov/games/{target_game_id}/",
        file=sys.stderr,
    )
    return target_game_id


# ---------------------------------------------------------------------------
# Pending-anchor index (v2.1 multi-tx batching)
# ---------------------------------------------------------------------------
#
# The pending-anchor index tracks per-game proofs that have been generated
# locally but not yet flushed to the chain. It is consulted by the
# 3-state ``proof_anchor_status`` (in ``sov_engine/proof.py``) and by the
# ``sov anchor`` flush path in the CLI.
#
# File layout (per spec ``docs/v2.1-bridge-changes.md`` §4):
#
#     .sov/games/<game-id>/pending-anchors.json
#
#     {
#       "schema_version": 1,
#       "entries": {
#         "1":     { "envelope_hash": "<64-hex>", "added_iso": "<ISO8601-utc>" },
#         "2":     { "envelope_hash": "<64-hex>", "added_iso": "<ISO8601-utc>" },
#         "FINAL": { "envelope_hash": "<64-hex>", "added_iso": "<ISO8601-utc>" }
#       }
#     }
#
# Round keys match the existing ``anchors.json`` convention: stringified round
# number ``"1"``…``"15"`` for in-game rounds, or the literal ``"FINAL"`` for
# the end-of-game proof. Helpers are atomic — crash mid-write leaves a ``.tmp``
# sibling rather than a corrupted index.
#
# Concurrency (BACKEND-004): the read-modify-write pair in
# ``add_pending_anchor`` / ``clear_pending_anchors`` is wrapped in a POSIX
# advisory lock (``fcntl.flock``) on a sibling lockfile. Windows falls back
# to no-lock today (best-effort; sovereignty is single-process per project
# root in practice). A second writer on POSIX blocks at the lock and
# observes the first writer's commit before proceeding — last-writer-wins
# is replaced with serialized append.
#
# Malformed-file quarantine (BACKEND-003): when the read sees an existing
# but unparseable file, the bytes are renamed to
# ``pending-anchors.json.malformed.<unix-ts>`` BEFORE the new write
# clobbers them, preserving evidence for operator review.
#
# File mode (BACKEND-005): writes use ``mode=0o600`` so the index is
# owner-only on POSIX. Pending-anchor entries leak game progress + per-
# round timestamps to other local users when world-readable.


_PENDING_ANCHORS_SCHEMA_VERSION = 1


class PendingEntry(TypedDict):
    """One row in ``pending-anchors.json``'s ``entries`` map.

    ``envelope_hash`` is the raw 64-char lowercase hex digest (no
    ``sha256:`` prefix — the prefix is added at the wire/memo layer only,
    same convention as the proof envelope's ``envelope_hash`` field).

    ``added_iso`` is ISO-8601 UTC with second precision and the literal
    ``Z`` suffix, matching the proof envelope's ``timestamp_utc`` shape
    (e.g. ``"2026-05-01T18:30:00Z"``).
    """

    envelope_hash: str
    added_iso: str


def pending_anchors_path(game_id: str) -> Path:
    """Return ``.sov/games/<game-id>/pending-anchors.json``.

    Sibling helper to ``state_file``, ``rng_seed_file``, ``proofs_dir``,
    ``anchors_file`` — same multi-save layout convention. Validates
    ``game_id``.
    """
    _validate_game_id(game_id)
    return games_dir() / game_id / "pending-anchors.json"


def _pending_anchors_lock_path(game_id: str) -> Path:
    """Return the sibling lockfile path for the pending-anchor index."""
    return games_dir() / game_id / "pending-anchors.json.lock"


def _quarantine_malformed(path: Path) -> Path | None:
    """Move a malformed pending file aside, returning the new path.

    Names the quarantine sibling ``<original>.malformed.<unix-ts>`` so
    repeated quarantines don't collide. Returns ``None`` when the file
    no longer exists or quarantine itself fails — in either case the
    caller proceeds with the fresh write rather than crashing.
    """
    if not path.exists():
        return None
    quarantine = path.with_suffix(path.suffix + f".malformed.{int(time.time())}")
    try:
        os.replace(path, quarantine)
    except OSError as exc:
        logger.error(
            "pending_anchors.quarantine.failed path=%s exc=%s detail=%s "
            "(proceeding with overwrite — malformed bytes lost)",
            path,
            type(exc).__name__,
            exc,
        )
        return None
    logger.error(
        "pending_anchors.quarantined original=%s preserved_at=%s "
        "(malformed pending-anchor file moved aside before fresh write)",
        path,
        quarantine,
    )
    return quarantine


def _read_pending_anchors_tagged(
    game_id: str,
) -> tuple[str, dict[str, PendingEntry]]:
    """Like ``read_pending_anchors`` but distinguishes missing vs malformed.

    Returns ``("ok", entries)``, ``("missing", {})``, or
    ``("malformed", {})``. The ``"malformed"`` tag tells the caller to
    quarantine the existing file before issuing the fresh write.

    Schema-version validation is delegated to
    ``sov_engine.schemas.read_versioned`` (Stage 7-B amend, BACKEND-B-001 +
    BACKEND-B-003). A forward-bumped or absent ``schema_version`` is treated
    as ``malformed`` so the existing quarantine-and-fresh-write recovery
    posture preserves the original bytes for inspection.
    """
    from sov_engine.schemas import (
        SchemaVersionUnsupportedError,
        read_versioned,
    )

    path = pending_anchors_path(game_id)
    if not path.exists():
        return "missing", {}
    try:
        data = read_versioned(
            path,
            expected_schema=_PENDING_ANCHORS_SCHEMA_VERSION,
            file_class="pending-anchors",
        )
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "pending_anchors.read.failed path=%s exc=%s detail=%s "
            "(treating as malformed; will quarantine on next write)",
            path,
            type(exc).__name__,
            exc,
        )
        return "malformed", {}
    except SchemaVersionUnsupportedError as exc:
        logger.warning(
            "pending_anchors.read.schema_mismatch path=%s expected=%d found=%d "
            "(treating as malformed; will quarantine on next write)",
            path,
            exc.expected,
            exc.found,
        )
        return "malformed", {}
    entries = data.get("entries", {})
    if not isinstance(entries, dict):
        logger.warning(
            "pending_anchors.read.malformed path=%s reason=entries-not-an-object "
            "(treating as malformed; will quarantine on next write)",
            path,
        )
        return "malformed", {}
    cleaned: dict[str, PendingEntry] = {}
    for round_key, row in entries.items():
        if not isinstance(round_key, str) or not isinstance(row, dict):
            continue
        envelope_hash = row.get("envelope_hash")
        added_iso = row.get("added_iso")
        if not isinstance(envelope_hash, str) or not isinstance(added_iso, str):
            continue
        cleaned[round_key] = PendingEntry(
            envelope_hash=envelope_hash,
            added_iso=added_iso,
        )
    return "ok", cleaned


def read_pending_anchors(game_id: str) -> dict[str, PendingEntry]:
    """Read the pending-anchor index. Returns the ``entries`` sub-dict.

    Returns an empty dict if the file does not exist, is unreadable, or
    has a malformed shape — pending-anchor reads should never crash a
    status / verify path. Malformed reads are logged at WARNING.

    Note: callers receive only the inner ``entries`` map, not the
    wrapper containing ``schema_version``. The wrapper is an implementation
    detail of the on-disk format. Validates ``game_id``.
    """
    _validate_game_id(game_id)
    _, entries = _read_pending_anchors_tagged(game_id)
    return entries


def _write_pending_anchors(game_id: str, entries: dict[str, PendingEntry]) -> None:
    """Atomically persist the wrapped pending-anchor document with mode 0600."""
    path = pending_anchors_path(game_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, object] = {
        "schema_version": _PENDING_ANCHORS_SCHEMA_VERSION,
        "entries": dict(sorted(entries.items())),
    }
    atomic_write_text(
        path,
        json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        mode=0o600,
    )


@contextmanager
def _locked_pending_index(game_id: str) -> Iterator[None]:
    """Hold a POSIX advisory lock on the pending-anchor sibling lockfile.

    Serializes the read-modify-write pair in ``add_pending_anchor`` /
    ``clear_pending_anchors`` so two concurrent writers don't drop a
    mutation. POSIX uses ``fcntl.flock(LOCK_EX)``; Windows falls back to
    no-lock (sovereignty is single-process per project root in practice;
    a Windows-specific lock via ``msvcrt.locking`` is on the v2.2 backlog).
    """
    lock_path = _pending_anchors_lock_path(game_id)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        # Best-effort no-lock on Windows. Documented limitation.
        yield
        return

    import fcntl  # POSIX-only; deferred import keeps Windows imports clean.

    # Open in append mode so we never truncate the lockfile across concurrent
    # holders; the file's contents are irrelevant — we hold the kernel lock.
    fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def add_pending_anchor(game_id: str, round_key: str, envelope_hash: str) -> None:
    """Record a pending anchor for ``round_key``.

    Idempotent: re-adding the same ``round_key`` overwrites the row,
    refreshing ``added_iso`` to "now" but keeping (or updating) the
    ``envelope_hash``. The file is created if it does not exist;
    parent directories are created as needed.

    ``round_key`` follows the existing anchors.json convention:
    stringified round number (``"1"``…``"15"``) or the literal ``"FINAL"``.

    Concurrency: protected by a POSIX flock on a sibling lockfile so
    concurrent writers serialize. A malformed existing file is quarantined
    to a ``.malformed.<ts>`` sibling before the fresh write — operator
    evidence is preserved instead of silently overwritten.
    """
    _validate_game_id(game_id)
    with _locked_pending_index(game_id):
        tag, entries = _read_pending_anchors_tagged(game_id)
        if tag == "malformed":
            _quarantine_malformed(pending_anchors_path(game_id))
        now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        entries[round_key] = PendingEntry(
            envelope_hash=envelope_hash,
            added_iso=now_iso,
        )
        _write_pending_anchors(game_id, entries)


def clear_pending_anchors(game_id: str, round_keys: list[str]) -> None:
    """Remove the named rows from the pending-anchor index.

    Idempotent partial clear: round keys not present are silently skipped.
    An empty ``round_keys`` is a no-op (no read, no write). When the
    pending-anchor file does not exist, this is a no-op even if
    ``round_keys`` is non-empty — there is nothing to clear.

    Concurrency + quarantine: same protection as ``add_pending_anchor`` —
    POSIX advisory lock plus malformed-file quarantine before any rewrite.
    """
    _validate_game_id(game_id)
    if not round_keys:
        return
    if not pending_anchors_path(game_id).exists():
        return
    with _locked_pending_index(game_id):
        tag, entries = _read_pending_anchors_tagged(game_id)
        if tag == "malformed":
            _quarantine_malformed(pending_anchors_path(game_id))
            # File is gone; nothing to clear.
            _write_pending_anchors(game_id, {})
            return
        if not entries:
            # File existed but read returned empty — rewrite a clean wrapper.
            _write_pending_anchors(game_id, entries)
            return
        for key in round_keys:
            entries.pop(key, None)
        _write_pending_anchors(game_id, entries)

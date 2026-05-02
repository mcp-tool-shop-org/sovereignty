"""Multi-save model tests (v2.1).

Pins the ``sov_engine.io_utils`` public API for the multi-save layout:

- ``list_saved_games()`` discovery + sort-order + malformed-skip
- ``get_active_game_id`` / ``set_active_game_id`` round-trip + atomicity
- ``state_file`` / ``rng_seed_file`` / ``proofs_dir`` / ``anchors_file``
  path-builder shape

All tests use ``monkeypatch.chdir(tmp_path)`` so ``Path('.sov')`` resolves
inside the temp dir, never the developer's real workspace.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from sov_engine.io_utils import (
    GameSummary,
    active_game_pointer_path,
    anchors_file,
    game_dir,
    games_dir,
    get_active_game_id,
    list_saved_games,
    proofs_dir,
    rng_seed_file,
    save_root,
    set_active_game_id,
    state_file,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_state_json(seed: int, players: list[str], current_round: int = 1) -> str:
    """Render the smallest snapshot ``_summarize_game`` will accept.

    The summarizer only reads ``config.ruleset``, ``config.max_rounds``,
    ``current_round``, and ``players[*].name``. Everything else is ignored,
    so we don't need a fully canonical snapshot here.
    """
    payload = {
        "config": {
            "ruleset": "campfire_v1",
            "max_rounds": 15,
            "seed": seed,
        },
        "current_round": current_round,
        "players": [{"name": n} for n in players],
        "schema_version": 1,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _seed_game(game_id: str, *, players: list[str], seed: int, current_round: int = 1) -> None:
    """Write a minimal ``.sov/games/<game_id>/state.json`` rooted at cwd."""
    save_root().mkdir(parents=True, exist_ok=True)
    games_dir().mkdir(parents=True, exist_ok=True)
    game_dir(game_id).mkdir(parents=True, exist_ok=True)
    state_file(game_id).write_text(
        _minimal_state_json(seed, players, current_round),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# list_saved_games
# ---------------------------------------------------------------------------


def test_list_saved_games_empty_when_games_dir_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing ``.sov/games/`` returns an empty list, not an error."""
    monkeypatch.chdir(tmp_path)
    assert list_saved_games() == []


def test_list_saved_games_empty_when_games_dir_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An empty ``.sov/games/`` directory returns an empty list."""
    monkeypatch.chdir(tmp_path)
    games_dir().mkdir(parents=True, exist_ok=True)
    assert list_saved_games() == []


def test_list_saved_games_returns_one_summary_per_game(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Each ``.sov/games/<id>/state.json`` produces one ``GameSummary``."""
    monkeypatch.chdir(tmp_path)
    _seed_game("s42", players=["Alice", "Bob"], seed=42, current_round=3)
    _seed_game("s17", players=["Dora", "Eve"], seed=17, current_round=8)

    summaries = list_saved_games()
    ids = {s.game_id for s in summaries}
    assert ids == {"s42", "s17"}, f"expected both games to surface; got: {ids!r}"

    by_id = {s.game_id: s for s in summaries}
    assert by_id["s42"].players == ("Alice", "Bob")
    assert by_id["s42"].current_round == 3
    assert by_id["s42"].max_rounds == 15
    assert by_id["s42"].ruleset == "campfire_v1"
    assert by_id["s17"].players == ("Dora", "Eve")
    assert by_id["s17"].current_round == 8


def test_list_saved_games_sorted_by_mtime_desc(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Result is sorted by ``last_modified_iso`` descending (most recent first)."""
    monkeypatch.chdir(tmp_path)
    _seed_game("s1", players=["A", "B"], seed=1)
    # Pre-date the older save by 2 seconds — mtime resolution is per-second
    # on most filesystems and we want unambiguous ordering.
    older_mtime = time.time() - 2.0
    os.utime(state_file("s1"), (older_mtime, older_mtime))

    _seed_game("s2", players=["C", "D"], seed=2)

    summaries = list_saved_games()
    assert [s.game_id for s in summaries] == ["s2", "s1"], (
        "list_saved_games() must return most-recently-modified first; "
        f"got: {[s.game_id for s in summaries]!r}"
    )


def test_list_saved_games_skips_malformed_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A directory with garbage state.json is skipped (logged WARNING, no raise).

    Attaches a direct handler to the ``sov_engine`` logger rather than using
    ``caplog`` or ``capfd``. The project convention (CLAUDE.md "Logger names")
    is that ``sov_engine`` has its own stderr handler bound at module-load
    time with ``propagate=False``; both caplog (root-logger capture) and
    capfd (post-import fd capture) miss it. A locally-attached handler is the
    robust capture pattern for non-propagating loggers.
    """
    import logging

    monkeypatch.chdir(tmp_path)
    _seed_game("s42", players=["Alice", "Bob"], seed=42)

    # Plant a malformed game next to the valid one. Using a valid-shaped
    # game-id (``s99``) — the malformed bytes live in state.json itself.
    # ``game_dir`` validates the id at construction time as of v2.1
    # BACKEND-001 hardening; an invalid-name skip is exercised separately.
    games_dir().mkdir(parents=True, exist_ok=True)
    bad_dir = game_dir("s99")
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "state.json").write_text("{ not json garbage", encoding="utf-8")

    captured_records: list[logging.LogRecord] = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured_records.append(record)

    handler = _CaptureHandler(level=logging.WARNING)
    sov_logger = logging.getLogger("sov_engine")
    sov_logger.addHandler(handler)
    try:
        summaries = list_saved_games()
    finally:
        sov_logger.removeHandler(handler)

    ids = {s.game_id for s in summaries}
    assert ids == {"s42"}, (
        f"malformed game must be skipped silently; got ids={ids!r} (expected just s42)"
    )
    # The skip path must log a WARNING — quiet failure is not OK.
    assert any("list_saved_games.skip" in rec.getMessage() for rec in captured_records), (
        f"malformed-state skip must log a WARNING; got records: "
        f"{[rec.getMessage() for rec in captured_records]!r}"
    )


def test_list_saved_games_skips_directories_without_state_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A game directory missing ``state.json`` is silently skipped."""
    monkeypatch.chdir(tmp_path)
    _seed_game("s42", players=["Alice", "Bob"], seed=42)

    # Directory present but no state.json (could happen mid-creation).
    # Use ``s7`` — a valid-shaped game-id under v2.1 BACKEND-001 hardening.
    game_dir("s7").mkdir(parents=True, exist_ok=True)

    summaries = list_saved_games()
    assert {s.game_id for s in summaries} == {"s42"}


def test_list_saved_games_returns_typed_summaries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Result entries are ``GameSummary`` instances (frozen dataclass)."""
    monkeypatch.chdir(tmp_path)
    _seed_game("s42", players=["Alice", "Bob"], seed=42)
    summaries = list_saved_games()
    assert len(summaries) == 1
    s = summaries[0]
    assert isinstance(s, GameSummary)
    # Frozen dataclass: re-assignment must raise.
    with pytest.raises((AttributeError, TypeError)):
        s.game_id = "smutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_active_game_id / set_active_game_id round-trip
# ---------------------------------------------------------------------------


def test_get_active_game_id_returns_none_when_pointer_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No ``.sov/active-game`` pointer file → returns ``None``."""
    monkeypatch.chdir(tmp_path)
    assert get_active_game_id() is None


def test_get_active_game_id_returns_none_when_pointer_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An empty pointer file → returns ``None`` (not the empty string)."""
    monkeypatch.chdir(tmp_path)
    save_root().mkdir(parents=True, exist_ok=True)
    active_game_pointer_path().write_text("", encoding="utf-8")
    assert get_active_game_id() is None


def test_set_then_get_active_game_id_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``set_active_game_id`` writes a pointer ``get_active_game_id`` reads back."""
    monkeypatch.chdir(tmp_path)
    set_active_game_id("s42")
    assert get_active_game_id() == "s42"
    # Whitespace trimming: pointer file is a one-liner by contract.
    raw = active_game_pointer_path().read_text(encoding="utf-8")
    assert raw.strip() == "s42"


def test_set_active_game_id_creates_save_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``set_active_game_id`` creates ``.sov/`` if it does not yet exist."""
    monkeypatch.chdir(tmp_path)
    assert not save_root().exists()
    set_active_game_id("s42")
    assert save_root().is_dir()
    assert active_game_pointer_path().exists()


def test_set_active_game_id_overwrites_existing_pointer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Calling ``set_active_game_id`` again replaces the pointer value."""
    monkeypatch.chdir(tmp_path)
    set_active_game_id("s42")
    set_active_game_id("s17")
    assert get_active_game_id() == "s17"


def test_set_active_game_id_is_atomic_no_partial_pointer_visible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Atomicity: the pointer must never be observable in a half-written state.

    ``atomic_write_text`` writes to ``<path>.tmp`` then ``os.replace`` swaps
    it in. After the call, only the final pointer must exist — no leftover
    ``.tmp`` file, and the contents must match exactly the requested
    ``game_id`` (no truncation, no doubled write).
    """
    monkeypatch.chdir(tmp_path)
    set_active_game_id("s42")
    pointer = active_game_pointer_path()
    assert pointer.exists(), "pointer must exist after set_active_game_id"

    # No leftover .tmp sibling — replace cleared it.
    tmp_sibling = pointer.with_suffix(pointer.suffix + ".tmp")
    assert not tmp_sibling.exists(), (
        f"atomic write must not leave behind {tmp_sibling}; pointer dir contents: "
        f"{list(pointer.parent.iterdir())!r}"
    )

    # Contents are the requested id (newline-terminated by impl, stripped on read).
    contents = pointer.read_text(encoding="utf-8")
    assert contents.strip() == "s42"
    # The implementation appends "\n" so the on-disk byte-length is len+1; the
    # test pins that the written byte count is deterministic, not partial.
    assert len(contents) == len("s42") + 1, (
        f"pointer must be exactly the id + trailing newline; got {contents!r}"
    )


# ---------------------------------------------------------------------------
# Path-builder helpers
# ---------------------------------------------------------------------------


def test_save_root_returns_dot_sov() -> None:
    assert save_root() == Path(".sov")


def test_games_dir_under_save_root() -> None:
    assert games_dir() == Path(".sov") / "games"


def test_active_game_pointer_path_under_save_root() -> None:
    assert active_game_pointer_path() == Path(".sov") / "active-game"


def test_game_dir_under_games_dir() -> None:
    assert game_dir("s42") == Path(".sov") / "games" / "s42"


def test_state_file_path() -> None:
    assert state_file("s42") == Path(".sov") / "games" / "s42" / "state.json"


def test_rng_seed_file_path() -> None:
    assert rng_seed_file("s42") == Path(".sov") / "games" / "s42" / "rng_seed.txt"


def test_proofs_dir_path() -> None:
    assert proofs_dir("s42") == Path(".sov") / "games" / "s42" / "proofs"


def test_anchors_file_path() -> None:
    assert anchors_file("s42") == Path(".sov") / "games" / "s42" / "proofs" / "anchors.json"


def test_path_helpers_are_pure_no_side_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Path-returning helpers must not create directories or files."""
    monkeypatch.chdir(tmp_path)
    # Call every path builder; none should mkdir.
    save_root()
    games_dir()
    active_game_pointer_path()
    game_dir("s42")
    state_file("s42")
    rng_seed_file("s42")
    proofs_dir("s42")
    anchors_file("s42")
    # Nothing should have been created in the temp dir.
    assert list(tmp_path.iterdir()) == [], (
        f"path-builder helpers must be pure; tmp_path leaked: {list(tmp_path.iterdir())!r}"
    )

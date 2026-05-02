"""Wave-6 backend amend regression tests (sovereignty v2.1).

One-stop test file pinning the BACKEND-001 through BACKEND-005 fixes
applied in Stage 6-A. Each fix has a ``test_<finding_id>_*`` block —
audit-bound traceability so the regression that's being defended against
is named in the test, not just in commit history.

Fix-to-test map:

* BACKEND-001 → ``test_BACKEND_001_*`` — game-id validator rejects
  path-traversal payloads at every helper that accepts ``game_id``.
* BACKEND-002 → ``test_BACKEND_002_*`` — partial v1→v2 migration
  recovery via ``.sov/migration-state.json`` breadcrumb.
* BACKEND-003 → ``test_BACKEND_003_*`` — malformed pending-anchor file
  is quarantined to ``*.malformed.<unix-ts>`` instead of silently
  overwritten.
* BACKEND-004 → ``test_BACKEND_004_*`` — concurrent
  ``add_pending_anchor`` writers serialize via POSIX flock; no mutation
  is dropped.
* BACKEND-005 → ``test_BACKEND_005_*`` — ``atomic_write_text(..,
  mode=0o600)`` honors the requested mode on POSIX, and the pending-
  anchor write applies it by default.

All tests use ``monkeypatch.chdir(tmp_path)`` so ``Path('.sov')``
resolves inside the temp dir, never the developer's real workspace.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from sov_engine.io_utils import (
    VALID_GAME_ID_PATTERN,
    add_pending_anchor,
    anchors_file,
    atomic_write_text,
    clear_pending_anchors,
    game_dir,
    get_active_game_id,
    migrate_v1_layout,
    pending_anchors_path,
    proofs_dir,
    read_pending_anchors,
    rng_seed_file,
    set_active_game_id,
    state_file,
)

# ---------------------------------------------------------------------------
# BACKEND-001 — path traversal validator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "good_id",
    [
        "s0",
        "s1",
        "s42",
        "s9999999999999999999",  # 19 digits, int64 ceiling
    ],
)
def test_BACKEND_001_validator_accepts_well_formed_ids(good_id: str) -> None:
    """The canonical ``s<int>`` shape passes — producers from hashing.py +
    main.py must keep working."""
    assert VALID_GAME_ID_PATTERN.fullmatch(good_id) is not None


@pytest.mark.parametrize(
    "bad_id",
    [
        "../etc/passwd",
        "..",
        "../",
        "/etc/passwd",
        "s42/..",
        "s42\\..",
        "sNotANumber",
        "s",
        "",
        "s\x00",
        "s/",
        "s\\",
        "s\n",
        "s 42",
        "s42 ",
        " s42",
        "S42",  # uppercase S not accepted
        "s99999999999999999999",  # 20 digits, beyond int64
        "s-1",
        "s+1",
        "s0x42",
    ],
)
def test_BACKEND_001_state_file_rejects_traversal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad_id: str
) -> None:
    """``state_file`` raises ``ValueError`` on path-traversal / malformed
    ids — not a silent path resolve outside ``.sov/``."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="invalid game_id"):
        state_file(bad_id)


@pytest.mark.parametrize(
    "helper",
    [game_dir, state_file, rng_seed_file, proofs_dir, anchors_file, pending_anchors_path],
)
def test_BACKEND_001_every_path_helper_validates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, helper: object
) -> None:
    """Every public ``game_id``-taking helper validates — defense in
    depth across the full path-construction surface."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="invalid game_id"):
        helper("../escape")  # type: ignore[operator]


def test_BACKEND_001_set_active_game_id_rejects_traversal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``set_active_game_id`` refuses to persist a malformed pointer."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="invalid game_id"):
        set_active_game_id("../etc/passwd")


def test_BACKEND_001_get_active_game_id_treats_poisoned_pointer_as_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A pre-existing poisoned ``.sov/active-game`` surfaces as ``None``,
    not propagated to callers (defense in depth)."""
    monkeypatch.chdir(tmp_path)
    sov = tmp_path / ".sov"
    sov.mkdir(parents=True)
    # Write a malicious pointer directly, bypassing set_active_game_id.
    (sov / "active-game").write_text("../etc/passwd\n", encoding="utf-8")

    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Capture(level=logging.WARNING)
    logger = logging.getLogger("sov_engine")
    logger.addHandler(handler)
    try:
        result = get_active_game_id()
    finally:
        logger.removeHandler(handler)

    assert result is None, "poisoned pointer must surface as None"
    assert any("active_game.read.poisoned" in rec.getMessage() for rec in captured), (
        f"poisoned pointer must log a WARNING; got: {[rec.getMessage() for rec in captured]!r}"
    )


def test_BACKEND_001_validator_path_remains_inside_sov(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Even a well-formed id resolves strictly inside ``.sov/games/``."""
    monkeypatch.chdir(tmp_path)
    p = state_file("s42")
    resolved = p.resolve()
    assert (tmp_path / ".sov" / "games").resolve() in resolved.parents


# ---------------------------------------------------------------------------
# BACKEND-002 — migration partial-failure breadcrumb
# ---------------------------------------------------------------------------


def _plant_v1_layout(tmp_path: Path, *, seed: int = 42) -> None:
    """Plant a minimal v1 ``.sov/`` tree."""
    sov = tmp_path / ".sov"
    sov.mkdir(parents=True)
    (sov / "game_state.json").write_text(
        json.dumps({"config": {"seed": seed, "ruleset": "campfire_v1", "max_rounds": 15}}),
        encoding="utf-8",
    )
    (sov / "rng_seed.txt").write_text(str(seed), encoding="utf-8")
    (sov / "proofs").mkdir()
    (sov / "proofs" / "round_1.json").write_text("{}", encoding="utf-8")


def test_BACKEND_002_migration_partial_failure_leaves_breadcrumb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When the second move fails, the breadcrumb names the in-flight
    step and the OSError propagates to the caller."""
    monkeypatch.chdir(tmp_path)
    _plant_v1_layout(tmp_path, seed=42)

    real_replace = os.replace
    call_count = {"n": 0}

    def flaky_replace(src: object, dst: object) -> None:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError(28, "No space left on device")
        real_replace(src, dst)

    with (
        patch("sov_engine.io_utils.os.replace", side_effect=flaky_replace),
        pytest.raises(OSError, match="No space left on device"),
    ):
        migrate_v1_layout()

    breadcrumb = tmp_path / ".sov" / "migration-state.json"
    assert breadcrumb.exists(), "breadcrumb must be left on partial failure"
    crumb = json.loads(breadcrumb.read_text(encoding="utf-8"))
    assert crumb["target_game_id"] == "s42"
    assert crumb["step"] in {"state", "rng_seed", "proofs"}, (
        f"breadcrumb must name the in-flight step; got step={crumb['step']!r}"
    )
    # Whichever step failed, legacy v1 paths NOT yet moved must still
    # exist; the recovery path will pick them up on the next invocation.
    legacy_paths_remaining = sum(
        1
        for p in (
            tmp_path / ".sov" / "game_state.json",
            tmp_path / ".sov" / "rng_seed.txt",
            tmp_path / ".sov" / "proofs",
        )
        if p.exists()
    )
    assert legacy_paths_remaining >= 1, (
        "at least one v1 path must still be at .sov/ root for recovery to fix"
    )


def test_BACKEND_002_recovery_completes_partial_migration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A second invocation against a partially-migrated tree completes
    the migration and clears the breadcrumb."""
    monkeypatch.chdir(tmp_path)
    _plant_v1_layout(tmp_path, seed=42)

    real_replace = os.replace
    call_count = {"n": 0}

    def flaky_replace(src: object, dst: object) -> None:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError(28, "No space left on device")
        real_replace(src, dst)

    with (
        patch("sov_engine.io_utils.os.replace", side_effect=flaky_replace),
        pytest.raises(OSError),
    ):
        migrate_v1_layout()

    # Disk pressure cleared — second invocation completes the migration.
    recovered = migrate_v1_layout()
    assert recovered == "s42", f"recovery must return migrated id; got {recovered!r}"

    target = tmp_path / ".sov" / "games" / "s42"
    assert (target / "state.json").exists(), "state.json must be moved"
    assert (target / "rng_seed.txt").exists(), "rng_seed.txt must be moved"
    assert (target / "proofs").is_dir(), "proofs/ must be moved"

    breadcrumb = tmp_path / ".sov" / "migration-state.json"
    assert not breadcrumb.exists(), "breadcrumb must be cleared on success"

    # Active-game pointer must point at the recovered id.
    assert get_active_game_id() == "s42"


def test_BACKEND_002_clean_migration_leaves_no_breadcrumb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A migration that runs cleanly clears the breadcrumb at the end."""
    monkeypatch.chdir(tmp_path)
    _plant_v1_layout(tmp_path, seed=7)

    result = migrate_v1_layout()
    assert result == "s7"
    assert not (tmp_path / ".sov" / "migration-state.json").exists(), (
        "breadcrumb must not survive a clean migration"
    )


# ---------------------------------------------------------------------------
# BACKEND-003 — malformed pending-anchor file quarantine
# ---------------------------------------------------------------------------


def test_BACKEND_003_add_quarantines_malformed_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``add_pending_anchor`` against a malformed existing file moves
    the bytes to a ``*.malformed.<ts>`` sibling instead of silently
    clobbering them."""
    monkeypatch.chdir(tmp_path)
    path = pending_anchors_path("s42")
    path.parent.mkdir(parents=True)
    malformed_bytes = "{ not json garbage"
    path.write_text(malformed_bytes, encoding="utf-8")

    add_pending_anchor("s42", "1", "a" * 64)

    # New file is well-formed.
    new_data = json.loads(path.read_text(encoding="utf-8"))
    assert new_data["entries"]["1"]["envelope_hash"] == "a" * 64

    # Quarantine sibling preserves the original malformed bytes.
    siblings = list(path.parent.glob("pending-anchors.json.malformed.*"))
    assert len(siblings) == 1, f"expected exactly one quarantine sibling; got: {siblings!r}"
    quarantined = siblings[0]
    assert quarantined.read_text(encoding="utf-8") == malformed_bytes


def test_BACKEND_003_clear_quarantines_malformed_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``clear_pending_anchors`` quarantines instead of silently
    overwriting (the docstring's old "rewrite clean empty index"
    branch was a data-loss footgun)."""
    monkeypatch.chdir(tmp_path)
    path = pending_anchors_path("s42")
    path.parent.mkdir(parents=True)
    path.write_text('{"entries": "this should be a dict"}', encoding="utf-8")

    clear_pending_anchors("s42", ["1"])

    siblings = list(path.parent.glob("pending-anchors.json.malformed.*"))
    assert len(siblings) == 1, f"clear must quarantine malformed bytes; got: {siblings!r}"


def test_BACKEND_003_quarantine_logs_at_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Quarantine fires an ERROR-level record — silent quarantine is not
    operator-actionable."""
    monkeypatch.chdir(tmp_path)
    path = pending_anchors_path("s42")
    path.parent.mkdir(parents=True)
    path.write_text("{ malformed", encoding="utf-8")

    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Capture(level=logging.ERROR)
    logger = logging.getLogger("sov_engine")
    logger.addHandler(handler)
    try:
        add_pending_anchor("s42", "1", "a" * 64)
    finally:
        logger.removeHandler(handler)

    error_records = [r for r in captured if r.levelno >= logging.ERROR]
    assert any("pending_anchors.quarantined" in r.getMessage() for r in error_records), (
        f"quarantine must log at ERROR level; got: "
        f"{[(r.levelname, r.getMessage()) for r in captured]!r}"
    )


# ---------------------------------------------------------------------------
# BACKEND-004 — read-modify-write race lock
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX flock-only; Windows lock fallback is v2.2 backlog",
)
def test_BACKEND_004_concurrent_adds_no_drop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """N threads concurrently calling ``add_pending_anchor`` must end
    with N entries in the index — no last-writer-wins drop."""
    monkeypatch.chdir(tmp_path)

    n_writers = 20

    def writer(round_key: str) -> None:
        # Distinct envelope_hash per round so a drop is detectable.
        add_pending_anchor("s42", round_key, round_key.zfill(64).replace(" ", "0"))

    threads = [threading.Thread(target=writer, args=(str(i + 1),)) for i in range(n_writers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    entries = read_pending_anchors("s42")
    assert len(entries) == n_writers, (
        f"all {n_writers} writers must commit under flock; got {len(entries)} entries: "
        f"{sorted(entries.keys())!r}"
    )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX flock-only; Windows lock fallback is v2.2 backlog",
)
def test_BACKEND_004_concurrent_add_and_clear_no_corruption(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Concurrent ``add`` + ``clear`` against the same file produce a
    well-formed result — no half-written / corrupt JSON."""
    monkeypatch.chdir(tmp_path)
    # Seed with one entry so clear has work to do.
    add_pending_anchor("s42", "1", "a" * 64)

    def adder() -> None:
        for i in range(2, 12):
            add_pending_anchor("s42", str(i), str(i).zfill(64).replace(" ", "0"))

    def clearer() -> None:
        for i in range(2, 12):
            clear_pending_anchors("s42", [str(i)])

    t_add = threading.Thread(target=adder)
    t_clear = threading.Thread(target=clearer)
    t_add.start()
    t_clear.start()
    t_add.join()
    t_clear.join()

    # Whatever survives, the file must be readable JSON with the right shape.
    path = pending_anchors_path("s42")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert isinstance(data["entries"], dict)


# ---------------------------------------------------------------------------
# BACKEND-005 — atomic_write_text mode= kwarg + pending-anchor 0600
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX permission bits — Windows ACL semantics out of scope for v2.1",
)
def test_BACKEND_005_atomic_write_text_honors_mode(tmp_path: Path) -> None:
    """``atomic_write_text(.., mode=0o600)`` produces a file with mode 0600."""
    target = tmp_path / "secret.txt"
    atomic_write_text(target, "hush\n", mode=0o600)
    actual_mode = stat.S_IMODE(target.stat().st_mode)
    assert actual_mode == 0o600, f"expected mode 0o600 (owner-only); got 0o{actual_mode:o}"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX permission bits — Windows ACL semantics out of scope for v2.1",
)
def test_BACKEND_005_atomic_write_text_default_mode_unchanged(tmp_path: Path) -> None:
    """Without ``mode=``, ``atomic_write_text`` keeps umask-default behavior
    (no ``os.chmod`` call), preserving existing callers' contracts."""
    target = tmp_path / "ordinary.txt"
    atomic_write_text(target, "ordinary\n")
    actual_mode = stat.S_IMODE(target.stat().st_mode)
    # umask 0o022 → 0o644; some CI / dev envs run with 0o002 → 0o664.
    # Both are "non-secret" — assert the world-read bit (0o004) is set,
    # which is the regression marker (0o600 would clear it).
    assert actual_mode & 0o004, (
        f"default mode must be umask-driven, not forced 0600; got 0o{actual_mode:o}"
    )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX permission bits — Windows ACL semantics out of scope for v2.1",
)
def test_BACKEND_005_pending_anchors_written_owner_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The pending-anchor file lands with mode 0600 by default."""
    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", "a" * 64)
    actual_mode = stat.S_IMODE(pending_anchors_path("s42").stat().st_mode)
    assert actual_mode == 0o600, f"pending-anchors.json must be owner-only; got 0o{actual_mode:o}"


def test_BACKEND_005_pending_anchors_mode_persists_across_writes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Re-write via the public API keeps mode 0600 — atomic_write_text
    re-applies the chmod after each os.replace (replace can reset
    permissions to the umask default of the temp file)."""
    if sys.platform == "win32":
        pytest.skip("POSIX permission bits — Windows ACL semantics out of scope")

    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", "a" * 64)
    # Wait a moment so a second add isn't optimized into a no-op anywhere.
    time.sleep(0.01)
    add_pending_anchor("s42", "2", "b" * 64)
    actual_mode = stat.S_IMODE(pending_anchors_path("s42").stat().st_mode)
    assert actual_mode == 0o600

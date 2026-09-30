"""Phase 5 coverage: persistence, proof reads, error factories, wallet seed.

Targets the failure and recovery branches that the happy-path suites never
reach: ``atomic_write_text`` cleanup, the v1 → v2 migration breadcrumb and its
recovery, pending-anchor quarantine, legacy ``anchors.json`` shapes,
``verify_proof_local`` mismatch, the CLI error factories, and the keychain
seed helpers (in-memory backend only, never ``keyrings.alt``).

Every test asserts an outcome: a return value, state on disk, an error code,
or a log record. Nothing here touches the network or a real OS keychain.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import types
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import keyring
import pytest
from keyring.backend import KeyringBackend

from sov_cli import errors as sov_errors
from sov_engine import io_utils, schemas
from sov_engine import proof as proof_mod
from sov_engine.io_utils import (
    add_pending_anchor,
    anchors_file,
    atomic_write_text,
    clear_pending_anchors,
    get_active_game_id,
    list_saved_games,
    migrate_v1_layout,
    pending_anchors_path,
    read_pending_anchors,
)
from sov_engine.serialize import canonical_json
from sov_engine.wallet_seed import (
    KEYRING_MAINNET_USER,
    KEYRING_SERVICE,
    KeyringUnavailableError,
    clear_mainnet_seed,
    get_mainnet_seed,
    resolve_wallet_seed,
    set_mainnet_seed,
)

_GAME = "s7"
_HASH = "a" * 64
_SECRET = "sEdVPersistenceCoverageSeedXXXX"
_REAL_REPLACE = os.replace


class _SovLog(logging.Handler):
    """Collects ``sov_engine`` records regardless of logger propagation.

    Importing ``sov_cli.main`` sets ``propagate = False`` on the ``sov_engine``
    logger, which blinds pytest's root-attached ``caplog`` once any test has
    imported the CLI. This handler attaches to the logger itself.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())

    @property
    def text(self) -> str:
        return "\n".join(self.messages)

    @contextmanager
    def at_level(self, level: int, logger: str | None = None) -> Iterator[None]:
        yield


@pytest.fixture()
def caplog() -> Iterator[_SovLog]:
    """Override of pytest's ``caplog`` (see ``_SovLog``); same ``.text`` surface."""
    lg = logging.getLogger("sov_engine")
    handler = _SovLog()
    old_level = lg.level
    lg.addHandler(handler)
    lg.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)


@pytest.fixture()
def in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run with a scratch cwd so the relative ``.sov`` root is isolated."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _tmp_leftovers(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p.name.endswith(".tmp"))


def _fail_replace_for(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    """Make ``os.replace`` raise only when the source file is one of *names*."""

    def _replace(src: Any, dst: Any) -> None:
        if Path(src).name in names:
            raise OSError("simulated replace failure")
        _REAL_REPLACE(src, dst)

    monkeypatch.setattr(io_utils.os, "replace", _replace)


# ---------------------------------------------------------------------------
# atomic_write_text
# ---------------------------------------------------------------------------


def test_atomic_write_cleans_tmp_when_fsync_fails(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = in_tmp / "state.json"
    target.write_text("old", encoding="utf-8")

    def _boom(fd: int) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(io_utils.os, "fsync", _boom)
    with pytest.raises(OSError, match="disk full"):
        atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "old"
    assert _tmp_leftovers(in_tmp) == []


def test_atomic_write_replace_failure_keeps_target_and_next_write_recovers(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = in_tmp / "state.json"
    target.write_text("old", encoding="utf-8")
    _fail_replace_for(monkeypatch, "state.json.tmp")

    with pytest.raises(OSError, match="simulated replace failure"):
        atomic_write_text(target, "new")
    # The documented crash window: target untouched, .tmp sibling remains.
    assert target.read_text(encoding="utf-8") == "old"
    assert _tmp_leftovers(in_tmp) == ["state.json.tmp"]

    monkeypatch.setattr(io_utils.os, "replace", _REAL_REPLACE)
    atomic_write_text(target, "newer")
    assert target.read_text(encoding="utf-8") == "newer"
    assert _tmp_leftovers(in_tmp) == []


def test_atomic_write_chmod_failure_is_best_effort(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch, caplog: _SovLog
) -> None:
    def _no_chmod(path: Any, mode: int) -> None:
        raise OSError("chmod unsupported")

    monkeypatch.setattr(io_utils.os, "chmod", _no_chmod)
    target = in_tmp / "secret.txt"
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        atomic_write_text(target, "payload", mode=0o600)

    assert target.read_text(encoding="utf-8") == "payload"
    assert "atomic_write_text.chmod.failed" in caplog.text
    assert _tmp_leftovers(in_tmp) == []


# ---------------------------------------------------------------------------
# active-game pointer + game listing
# ---------------------------------------------------------------------------


def test_get_active_game_id_unreadable_pointer_is_none(in_tmp: Path, caplog: _SovLog) -> None:
    # A directory where the pointer file should be: exists() is True but
    # read_text raises an OSError subclass on every platform.
    (in_tmp / ".sov" / "active-game").mkdir(parents=True)
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert get_active_game_id() is None
    assert "active_game.read.failed" in caplog.text


def test_get_active_game_id_poisoned_pointer_is_none(in_tmp: Path, caplog: _SovLog) -> None:
    (in_tmp / ".sov").mkdir()
    (in_tmp / ".sov" / "active-game").write_text("../../etc\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert get_active_game_id() is None
    assert "active_game.read.poisoned" in caplog.text


def test_list_saved_games_skips_stray_files_junk_dirs_and_bad_state(in_tmp: Path) -> None:
    games = in_tmp / ".sov" / "games"
    good = games / "s1"
    good.mkdir(parents=True)
    (good / "state.json").write_text(
        json.dumps(
            {
                "config": {"ruleset": "campfire_v1", "max_rounds": 5},
                "current_round": 2,
                "players": [{"name": "Ada"}, {"name": "Bo"}],
            }
        ),
        encoding="utf-8",
    )
    (games / "notes.txt").write_text("stray file", encoding="utf-8")
    (games / "not-a-game").mkdir()
    (games / "not-a-game" / "state.json").write_text("{}", encoding="utf-8")
    (games / "s2").mkdir()  # valid id, no state.json
    (games / "s3").mkdir()
    (games / "s3" / "state.json").write_text("{not json", encoding="utf-8")

    summaries = list_saved_games()

    assert [s.game_id for s in summaries] == ["s1"]
    assert summaries[0].ruleset == "campfire_v1"
    assert summaries[0].current_round == 2
    assert summaries[0].players == ("Ada", "Bo")


def test_list_saved_games_no_games_dir_is_empty(in_tmp: Path) -> None:
    assert list_saved_games() == []


# ---------------------------------------------------------------------------
# migration breadcrumb + v1 -> v2 recovery
# ---------------------------------------------------------------------------


def _plant_v1(root: Path, *, seed: object = 7) -> None:
    sov = root / ".sov"
    (sov / "proofs").mkdir(parents=True)
    (sov / "game_state.json").write_text(json.dumps({"config": {"seed": seed}}), encoding="utf-8")
    (sov / "rng_seed.txt").write_text(f"{seed}\n", encoding="utf-8")
    (sov / "proofs" / "round_01.proof.json").write_text("{}", encoding="utf-8")


def test_breadcrumb_write_failure_is_swallowed(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch, caplog: _SovLog
) -> None:
    def _boom(path: Path, content: str, *, mode: int | None = None) -> None:
        raise OSError("read-only fs")

    monkeypatch.setattr(io_utils, "atomic_write_text", _boom)
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        io_utils._write_migration_breadcrumb(target_game_id=_GAME, step="state", legacy_paths=[])
    assert "breadcrumb.write_failed" in caplog.text
    assert not io_utils._migration_breadcrumb_path().exists()


def test_breadcrumb_roundtrip_and_clear(in_tmp: Path) -> None:
    (in_tmp / ".sov").mkdir()
    io_utils._write_migration_breadcrumb(
        target_game_id=_GAME, step="rng_seed", legacy_paths=["a", "b"]
    )
    crumb = io_utils._read_migration_breadcrumb()
    assert crumb is not None
    assert crumb["target_game_id"] == _GAME
    assert crumb["step"] == "rng_seed"
    assert crumb["legacy_paths"] == ["a", "b"]

    io_utils._clear_migration_breadcrumb()
    assert io_utils._read_migration_breadcrumb() is None
    io_utils._clear_migration_breadcrumb()  # tolerates a missing file


@pytest.mark.parametrize(
    ("text", "expect_warning"),
    [("{not json", True), ("[1, 2, 3]", False)],
    ids=["unparseable", "not-an-object"],
)
def test_breadcrumb_read_rejects_bad_content(
    in_tmp: Path, caplog: _SovLog, text: str, expect_warning: bool
) -> None:
    (in_tmp / ".sov").mkdir()
    io_utils._migration_breadcrumb_path().write_text(text, encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert io_utils._read_migration_breadcrumb() is None
    assert ("breadcrumb.read_failed" in caplog.text) is expect_warning


@pytest.mark.parametrize(
    ("state_text", "log_marker"),
    [
        ("{not json", "migrate_v1_layout.skip"),
        (json.dumps({"config": {}}), "migrate_v1_layout.skip"),
        (json.dumps({"config": {"seed": "../evil"}}), "invalid_seed_in_v1_state"),
        (json.dumps({"config": {"seed": -5}}), "invalid_seed_in_v1_state"),
    ],
    ids=["garbage-json", "missing-seed", "traversal-seed", "negative-seed"],
)
def test_migrate_leaves_unusable_v1_state_alone(
    in_tmp: Path, caplog: _SovLog, state_text: str, log_marker: str
) -> None:
    sov = in_tmp / ".sov"
    sov.mkdir()
    (sov / "game_state.json").write_text(state_text, encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert migrate_v1_layout() is None
    assert log_marker in caplog.text
    assert (sov / "game_state.json").read_text(encoding="utf-8") == state_text
    assert not (sov / "games").exists()


def test_migrate_partial_failure_then_recovery_completes(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _plant_v1(in_tmp)
    sov = in_tmp / ".sov"
    _fail_replace_for(monkeypatch, "rng_seed.txt")

    with pytest.raises(OSError, match="simulated replace failure"):
        migrate_v1_layout()

    # Half-migrated: state moved, seed + proofs orphaned, breadcrumb names the step.
    assert (sov / "games" / _GAME / "state.json").exists()
    assert (sov / "rng_seed.txt").exists()
    crumb = json.loads((sov / "migration-state.json").read_text(encoding="utf-8"))
    assert crumb["target_game_id"] == _GAME
    assert crumb["step"] == "rng_seed"

    monkeypatch.setattr(io_utils.os, "replace", _REAL_REPLACE)
    capsys.readouterr()
    assert migrate_v1_layout() == _GAME

    assert "completed interrupted migration" in capsys.readouterr().err
    assert (sov / "games" / _GAME / "rng_seed.txt").exists()
    assert (sov / "games" / _GAME / "proofs" / "round_01.proof.json").exists()
    assert not (sov / "rng_seed.txt").exists()
    assert not (sov / "proofs").exists()
    assert not (sov / "migration-state.json").exists()
    assert get_active_game_id() == _GAME


def test_recover_partial_migration_failure_retains_breadcrumb(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch, caplog: _SovLog
) -> None:
    _plant_v1(in_tmp)
    sov = in_tmp / ".sov"
    io_utils._write_migration_breadcrumb(target_game_id=_GAME, step="state", legacy_paths=[])
    _fail_replace_for(monkeypatch, "rng_seed.txt")

    with pytest.raises(OSError, match="simulated replace failure"):
        migrate_v1_layout()

    assert "recover.partial_failure" in caplog.text
    assert (sov / "migration-state.json").exists()  # kept so the next run retries
    assert (sov / "games" / _GAME / "state.json").exists()


@pytest.mark.parametrize(
    ("crumb", "reason"),
    [
        ({"step": "state"}, "missing_target_game_id"),
        ({"target_game_id": 7}, "missing_target_game_id"),
        ({"target_game_id": "../escape"}, "invalid_target_game_id"),
    ],
    ids=["absent", "wrong-type", "traversal"],
)
def test_recover_rejects_malformed_breadcrumb_and_clears_it(
    in_tmp: Path, caplog: _SovLog, crumb: dict[str, object], reason: str
) -> None:
    (in_tmp / ".sov").mkdir()
    io_utils._migration_breadcrumb_path().write_text(json.dumps(crumb), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert migrate_v1_layout() is None
    assert reason in caplog.text
    assert not io_utils._migration_breadcrumb_path().exists()
    assert not (in_tmp / ".sov" / "games").exists()


# ---------------------------------------------------------------------------
# pending-anchor index
# ---------------------------------------------------------------------------


def _write_pending_raw(text: str) -> Path:
    path = pending_anchors_path(_GAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _quarantined(directory: Path) -> list[Path]:
    return sorted(directory.glob("pending-anchors.json.malformed.*"))


@pytest.mark.parametrize(
    "text",
    [
        json.dumps({"schema_version": 99, "entries": {}}),
        json.dumps({"entries": {}}),
        json.dumps([1, 2]),
        json.dumps({"schema_version": 1, "entries": ["nope"]}),
        "{not json",
    ],
    ids=["future-schema", "no-schema", "top-level-list", "entries-not-object", "garbage"],
)
def test_pending_read_treats_bad_documents_as_empty(in_tmp: Path, text: str) -> None:
    _write_pending_raw(text)
    assert read_pending_anchors(_GAME) == {}
    tag, entries = io_utils._read_pending_anchors_tagged(_GAME)
    assert (tag, entries) == ("malformed", {})


def test_pending_read_missing_file_is_tagged_missing(in_tmp: Path) -> None:
    assert io_utils._read_pending_anchors_tagged(_GAME) == ("missing", {})


def test_pending_read_filters_ill_typed_rows(in_tmp: Path) -> None:
    _write_pending_raw(
        json.dumps(
            {
                "schema_version": 1,
                "entries": {
                    "1": {"envelope_hash": _HASH, "added_iso": "2026-01-01T00:00:00Z"},
                    "2": "not-a-dict",
                    "3": {"envelope_hash": 5, "added_iso": "2026-01-01T00:00:00Z"},
                    "4": {"envelope_hash": _HASH, "added_iso": None},
                },
            }
        )
    )
    assert read_pending_anchors(_GAME) == {
        "1": {"envelope_hash": _HASH, "added_iso": "2026-01-01T00:00:00Z"}
    }


def test_add_pending_quarantines_malformed_file_preserving_bytes(in_tmp: Path) -> None:
    bad = "{ this was corrupted"
    path = _write_pending_raw(bad)

    add_pending_anchor(_GAME, "1", _HASH)

    assert list(read_pending_anchors(_GAME)) == ["1"]
    saved = _quarantined(path.parent)
    assert len(saved) == 1
    assert saved[0].read_text(encoding="utf-8") == bad


def test_clear_pending_on_malformed_file_quarantines_and_resets(in_tmp: Path) -> None:
    path = _write_pending_raw(json.dumps({"schema_version": 42, "entries": {}}))

    clear_pending_anchors(_GAME, ["1"])

    assert len(_quarantined(path.parent)) == 1
    assert json.loads(path.read_text(encoding="utf-8")) == {"schema_version": 1, "entries": {}}


def test_clear_pending_on_empty_wrapper_rewrites_clean_wrapper(in_tmp: Path) -> None:
    path = _write_pending_raw(json.dumps({"schema_version": 1, "entries": {}}))
    clear_pending_anchors(_GAME, ["1"])
    assert json.loads(path.read_text(encoding="utf-8")) == {"schema_version": 1, "entries": {}}
    assert _quarantined(path.parent) == []


def test_clear_pending_drops_only_named_rows_and_ignores_unknown(in_tmp: Path) -> None:
    add_pending_anchor(_GAME, "1", _HASH)
    add_pending_anchor(_GAME, "2", _HASH)
    clear_pending_anchors(_GAME, ["1", "99"])
    assert list(read_pending_anchors(_GAME)) == ["2"]
    clear_pending_anchors(_GAME, [])  # empty list: no-op
    assert list(read_pending_anchors(_GAME)) == ["2"]


def test_quarantine_missing_file_returns_none(in_tmp: Path) -> None:
    assert io_utils._quarantine_malformed(in_tmp / "absent.json") is None


def test_quarantine_rename_failure_returns_none(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch, caplog: _SovLog
) -> None:
    target = in_tmp / "pending-anchors.json"
    target.write_text("{bad", encoding="utf-8")
    _fail_replace_for(monkeypatch, "pending-anchors.json")
    with caplog.at_level(logging.ERROR, logger="sov_engine"):
        assert io_utils._quarantine_malformed(target) is None
    assert "pending_anchors.quarantine.failed" in caplog.text
    assert target.read_text(encoding="utf-8") == "{bad"


def test_quarantine_success_names_sibling_with_timestamp(in_tmp: Path) -> None:
    target = in_tmp / "pending-anchors.json"
    target.write_text("{bad", encoding="utf-8")
    moved = io_utils._quarantine_malformed(target)
    assert moved is not None
    assert moved.name.startswith("pending-anchors.json.malformed.")
    assert moved.read_text(encoding="utf-8") == "{bad"
    assert not target.exists()


class _FakeFcntl(types.ModuleType):
    """Records ``flock`` calls so the POSIX lock branch runs on any platform."""

    LOCK_EX = 2
    LOCK_UN = 8

    def __init__(self) -> None:
        super().__init__("fcntl")
        self.calls: list[int] = []

    def flock(self, fd: int, op: int) -> None:
        self.calls.append(op)


def test_locked_pending_index_posix_takes_and_releases_flock(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeFcntl()
    monkeypatch.setitem(sys.modules, "fcntl", fake)
    monkeypatch.setattr(io_utils.sys, "platform", "linux")

    with io_utils._locked_pending_index(_GAME):
        assert fake.calls == [fake.LOCK_EX]
    assert fake.calls == [fake.LOCK_EX, fake.LOCK_UN]
    assert io_utils._pending_anchors_lock_path(_GAME).exists()


def test_locked_pending_index_releases_lock_when_body_raises(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeFcntl()
    monkeypatch.setitem(sys.modules, "fcntl", fake)
    monkeypatch.setattr(io_utils.sys, "platform", "linux")

    with (
        pytest.raises(RuntimeError, match="inside lock"),
        io_utils._locked_pending_index(_GAME),
    ):
        raise RuntimeError("inside lock")
    assert fake.calls == [fake.LOCK_EX, fake.LOCK_UN]


def test_locked_pending_index_windows_is_a_lockless_passthrough(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(io_utils.sys, "platform", "win32")
    with io_utils._locked_pending_index(_GAME):
        pass
    assert io_utils._pending_anchors_lock_path(_GAME).parent.is_dir()
    assert not io_utils._pending_anchors_lock_path(_GAME).exists()


# ---------------------------------------------------------------------------
# schemas.read_versioned in-process migration
# ---------------------------------------------------------------------------


def test_read_versioned_runs_registered_migration_and_warns(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch, caplog: _SovLog
) -> None:
    path = in_tmp / "old.json"
    path.write_text(json.dumps({"schema_version": 0, "value": 1}), encoding="utf-8")

    def _upgrade(data: dict[str, Any]) -> dict[str, Any]:
        return {**data, "schema_version": 1, "upgraded": True}

    monkeypatch.setitem(schemas._MIGRATIONS, (0, 1), _upgrade)
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        result = schemas.read_versioned(path, 1, file_class="test-file")

    assert result == {"schema_version": 1, "value": 1, "upgraded": True}
    assert "schema.deprecated" in caplog.text
    assert "file_class=test-file" in caplog.text


# ---------------------------------------------------------------------------
# proof.py
# ---------------------------------------------------------------------------


def _make_proof(**overrides: Any) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "proof_version": 2,
        "game_id": _GAME,
        "round": 1,
        "ruleset": "campfire_v1",
        "rng_seed": 7,
        "timestamp_utc": "2026-05-01T00:00:00Z",
        "players": [],
        "state": {},
    }
    envelope.update(overrides)
    envelope["envelope_hash"] = overrides.get(
        "envelope_hash", proof_mod._compute_envelope_hash(envelope)
    )
    return envelope


def _write_proof(directory: Path, proof: dict[str, Any], name: str = "round_01.proof.json") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(proof), encoding="utf-8")
    return path


def test_compute_envelope_hash_excludes_the_hash_field_itself() -> None:
    base = _make_proof()
    other = {**base, "envelope_hash": "f" * 64}
    assert proof_mod._compute_envelope_hash(base) == proof_mod._compute_envelope_hash(other)
    assert proof_mod._compute_envelope_hash(base) != proof_mod._compute_envelope_hash(
        {**base, "round": 2}
    )
    assert len(proof_mod._compute_envelope_hash(base)) == 64


def test_verify_proof_local_true_for_intact_and_false_for_tampered(in_tmp: Path) -> None:
    proofs = in_tmp / ".sov" / "games" / _GAME / "proofs"
    good = _write_proof(proofs, _make_proof())
    assert proof_mod.verify_proof_local(good) is True

    tampered = _make_proof()
    tampered["state"] = {"coins": 999}  # bytes changed after the hash was stamped
    bad = _write_proof(proofs, tampered, "round_02.proof.json")
    assert proof_mod.verify_proof_local(bad) is False


@pytest.mark.parametrize("version", [None, 1])
def test_load_proof_rejects_v1_and_missing_version(in_tmp: Path, version: int | None) -> None:
    body: dict[str, Any] = {"game_id": _GAME, "round": 1, "envelope_hash": _HASH}
    if version is not None:
        body["proof_version"] = version
    path = _write_proof(in_tmp, body)
    with pytest.raises(sov_errors.ProofFormatError, match="v1 is no longer supported"):
        proof_mod.verify_proof_local(path)


def test_render_proof_path_uses_short_form_under_dot_sov(in_tmp: Path) -> None:
    path = in_tmp / ".sov" / "games" / _GAME / "proofs" / "round_01.proof.json"
    rendered = proof_mod._render_proof_path(path)
    assert rendered == str(Path(".sov") / "games" / _GAME / "proofs" / "round_01.proof.json")
    assert str(in_tmp) not in rendered


def test_render_proof_path_falls_back_when_resolve_fails(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(self: Path, strict: bool = False) -> Path:
        raise OSError("cannot resolve")

    monkeypatch.setattr(Path, "resolve", _boom)
    given = Path("some") / "proof.json"
    assert proof_mod._render_proof_path(given) == str(given)


def test_render_proof_path_falls_back_when_relative_to_fails(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(self: Path, *other: Any) -> Path:
        raise ValueError("not relative")

    monkeypatch.setattr(Path, "relative_to", _boom)
    given = in_tmp / ".sov" / "games" / _GAME / "proofs" / "round_01.proof.json"
    assert proof_mod._render_proof_path(given) == str(given)


@pytest.mark.parametrize(
    ("proof", "expected"),
    [
        ({"final": True, "round": 15}, "FINAL"),
        ({"round": None}, "FINAL"),
        ({}, "FINAL"),
        ({"round": 3}, "3"),
        ({"final": False, "round": 4}, "4"),
    ],
)
def test_round_key_from_proof(proof: dict[str, Any], expected: str) -> None:
    assert proof_mod._round_key_from_proof(proof) == expected


def _anchors_path() -> Path:
    path = anchors_file(_GAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_bare_dict_anchors_migrate_to_wrapped_on_read(in_tmp: Path, caplog: _SovLog) -> None:
    path = _anchors_path()
    path.write_text(json.dumps({"1": "TX1", "2": "TX2", "bad": 5, "9": None}), encoding="utf-8")

    with caplog.at_level(logging.INFO, logger="sov_engine"):
        entries = proof_mod._read_anchors(_GAME)

    assert entries == {"1": "TX1", "2": "TX2"}
    assert "anchors.migrated" in caplog.text
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == {"schema_version": 1, "entries": {"1": "TX1", "2": "TX2"}}
    assert proof_mod._read_anchors(_GAME) == entries  # second read is stable


def test_bare_dict_migration_write_failure_still_returns_entries(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch, caplog: _SovLog
) -> None:
    path = _anchors_path()
    original = json.dumps({"1": "TX1"})
    path.write_text(original, encoding="utf-8")

    def _boom(path: Path, content: str, *, mode: int | None = None) -> None:
        raise OSError("read-only fs")

    monkeypatch.setattr(proof_mod, "atomic_write_text", _boom)
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert proof_mod._read_anchors(_GAME) == {"1": "TX1"}
    assert "anchors.migrate.failed" in caplog.text
    assert path.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    ("document", "expected", "marker"),
    [
        ({"schema_version": 1, "entries": {"1": "TX"}}, {"1": "TX"}, ""),
        ({"schema_version": 1, "anchors": {"2": "TY"}}, {"2": "TY"}, ""),
        ({"schema_version": 1, "entries": "nope", "anchors": {"3": "TZ"}}, {"3": "TZ"}, ""),
        ({"schema_version": 1, "entries": 5, "anchors": 6}, {}, "reason=entries-not-an-object"),
        ({"schema_version": 9, "entries": {"1": "TX"}}, {}, "anchors.read.schema_mismatch"),
        ([1, 2], {}, "reason=not-an-object"),
    ],
    ids=["entries", "legacy-anchors", "entries-fallback", "both-bad", "future", "list"],
)
def test_read_anchors_shapes(
    in_tmp: Path,
    caplog: _SovLog,
    document: Any,
    expected: dict[str, str],
    marker: str,
) -> None:
    _anchors_path().write_text(json.dumps(document), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert proof_mod._read_anchors(_GAME) == expected
    if marker:
        assert marker in caplog.text


def test_read_anchors_absent_and_unparseable(in_tmp: Path, caplog: _SovLog) -> None:
    assert proof_mod._read_anchors(_GAME) == {}
    _anchors_path().write_text("{oops", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_engine"):
        assert proof_mod._read_anchors(_GAME) == {}
    assert "anchors.read.malformed" in caplog.text


def test_record_anchors_merges_and_keeps_earlier_rows(in_tmp: Path) -> None:
    proof_mod.record_anchors(_GAME, {"1": "TX1"})
    proof_mod.record_anchors(_GAME, {"2": "TX2", "1": "TX1b"})
    on_disk = json.loads(anchors_file(_GAME).read_text(encoding="utf-8"))
    assert on_disk == {"schema_version": 1, "entries": {"1": "TX1b", "2": "TX2"}}


def test_record_anchors_and_clear_pending(in_tmp: Path) -> None:
    add_pending_anchor(_GAME, "1", _HASH)
    add_pending_anchor(_GAME, "2", _HASH)

    proof_mod.record_anchors_and_clear_pending(_GAME, {})  # empty: no-op
    assert set(read_pending_anchors(_GAME)) == {"1", "2"}
    assert not anchors_file(_GAME).exists()

    proof_mod.record_anchors_and_clear_pending(_GAME, {"1": "TX1"})
    assert proof_mod._read_anchors(_GAME) == {"1": "TX1"}
    assert set(read_pending_anchors(_GAME)) == {"2"}


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ({"1": "TX1", "x": 2}, {"1": "TX1"}),
        ({"schema_version": 1, "entries": {"1": "TX1"}}, {"1": "TX1"}),
        ({"schema_version": 1, "anchors": {"2": "TY"}}, {"2": "TY"}),
        ({"schema_version": 1, "entries": 1, "anchors": 2}, {}),
        ([1], {}),
    ],
    ids=["bare", "entries", "legacy-anchors", "both-bad", "list"],
)
def test_read_anchors_file_shapes_without_migrating(
    in_tmp: Path, document: Any, expected: dict[str, str]
) -> None:
    path = in_tmp / "anchors.json"
    text = json.dumps(document)
    path.write_text(text, encoding="utf-8")
    assert proof_mod.read_anchors_file(path) == expected
    assert path.read_text(encoding="utf-8") == text  # never rewritten


def test_read_anchors_file_missing_and_garbage(in_tmp: Path) -> None:
    assert proof_mod.read_anchors_file(in_tmp / "absent.json") == {}
    bad = in_tmp / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    assert proof_mod.read_anchors_file(bad) == {}


class _Transport:
    """Minimal ledger stub: ``is_anchored_on_chain`` returns a fixed result."""

    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def is_anchored_on_chain(self, txid: str, envelope_hash: str) -> Any:
        self.calls.append((txid, envelope_hash))
        return self.result


def _proof_on_disk(**overrides: Any) -> tuple[Path, dict[str, Any]]:
    proof = _make_proof(**overrides)
    path = _write_proof(proofs_path(), proof)
    return path, proof


def proofs_path() -> Path:
    return io_utils.proofs_dir(_GAME)


def test_proof_anchor_status_three_states(in_tmp: Path) -> None:
    from sov_transport.xrpl_internals import ChainLookupResult

    path, proof = _proof_on_disk()
    transport = _Transport(ChainLookupResult.FOUND)

    # never attempted -> MISSING, chain never consulted
    assert proof_mod.proof_anchor_status(path, transport) is proof_mod.AnchorStatus.MISSING
    assert transport.calls == []

    # queued locally -> PENDING
    add_pending_anchor(_GAME, "1", proof["envelope_hash"])
    assert proof_mod.proof_anchor_status(path, transport) is proof_mod.AnchorStatus.PENDING

    # recorded txid heals stale pending, then defers to the chain
    proof_mod.record_anchors(_GAME, {"1": "TX1"})
    assert proof_mod.proof_anchor_status(path, transport) is proof_mod.AnchorStatus.ANCHORED
    assert transport.calls == [("TX1", proof["envelope_hash"])]
    assert read_pending_anchors(_GAME) == {}

    # recorded txid the chain no longer matches -> MISSING (drift)
    for result in (ChainLookupResult.NOT_FOUND, ChainLookupResult.LOOKUP_FAILED):
        drift = _Transport(result)
        assert proof_mod.proof_anchor_status(path, drift) is proof_mod.AnchorStatus.MISSING


def test_proof_anchor_status_final_proof_uses_final_key(in_tmp: Path) -> None:
    from sov_transport.xrpl_internals import ChainLookupResult

    path, _ = _proof_on_disk(final=True, round=15)
    proof_mod.record_anchors(_GAME, {"FINAL": "TXF"})
    transport = _Transport(ChainLookupResult.FOUND)
    assert proof_mod.proof_anchor_status(path, transport) is proof_mod.AnchorStatus.ANCHORED
    assert transport.calls[0][0] == "TXF"


@pytest.mark.parametrize(
    ("mutate", "needle"),
    [
        (lambda p: p.pop("game_id"), "missing required field 'game_id'"),
        (lambda p: p.pop("round"), "missing required field 'round'"),
        (lambda p: p.pop("envelope_hash"), "missing required field 'envelope_hash'"),
        (lambda p: p.update(envelope_hash=12345), "'envelope_hash' must be a string"),
        (lambda p: p.update(proof_version=99), "Unknown proof_version: 99"),
    ],
    ids=["no-game-id", "no-round", "no-hash", "hash-not-str", "future-version"],
)
def test_load_proof_structural_errors(in_tmp: Path, mutate: Any, needle: str) -> None:
    proof = _make_proof()
    mutate(proof)
    path = _write_proof(in_tmp, proof)
    with pytest.raises(sov_errors.ProofFormatError, match=needle):
        proof_mod.verify_proof_local(path)


def test_load_proof_unreadable_and_non_object(in_tmp: Path) -> None:
    with pytest.raises(sov_errors.ProofFormatError, match="Could not read proof file"):
        proof_mod.verify_proof_local(in_tmp / "absent.proof.json")
    listy = in_tmp / "list.proof.json"
    listy.write_text(json.dumps([1, 2]), encoding="utf-8")
    with pytest.raises(sov_errors.ProofFormatError, match="is not a JSON object"):
        proof_mod.verify_proof_local(listy)


def test_canonical_json_is_key_order_independent() -> None:
    # The hash contract verify_proof_local depends on.
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})


# ---------------------------------------------------------------------------
# sov_cli.errors factories
# ---------------------------------------------------------------------------


def _backticks(text: str) -> int:
    return text.count("`")


def test_state_corrupt_error_plain(in_tmp: Path) -> None:
    err = sov_errors.state_corrupt_error("JSONDecodeError: bad")
    assert err.code == "STATE_CORRUPT"
    assert "JSONDecodeError: bad" in err.message
    assert "leftover v1" not in err.message
    assert _backticks(err.hint) >= 2 and "`sov games --json`" in err.hint


def test_state_corrupt_error_mentions_leftover_v1_layout(in_tmp: Path) -> None:
    (in_tmp / ".sov").mkdir()
    (in_tmp / ".sov" / "game_state.json").write_text("{}", encoding="utf-8")
    err = sov_errors.state_corrupt_error("boom")
    assert err.code == "STATE_CORRUPT"
    assert "leftover v1 `.sov/game_state.json`" in err.message


def test_v1_layout_note_swallows_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> Path:
        raise OSError("no cwd")

    monkeypatch.setattr(io_utils, "save_root", _boom)
    assert sov_errors._v1_layout_note() == ""


def test_state_version_mismatch_error_names_supported_version(in_tmp: Path) -> None:
    err = sov_errors.state_version_mismatch_error(7)
    assert err.code == "STATE_VERSION_MISMATCH"
    assert "schema_version=7" in err.message
    assert "supports v1" in err.message
    assert "`pipx install 'sovereignty-game<2.0.0'`" in err.hint


def test_state_version_mismatch_error_survives_missing_main(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A broken circular import must degrade to "?", not raise from an error path.
    monkeypatch.setitem(sys.modules, "sov_cli.main", None)
    err = sov_errors.state_version_mismatch_error("x")
    assert err.code == "STATE_VERSION_MISMATCH"
    assert "supports v?" in err.message


def test_chain_lookup_failed_error_retryable_with_and_without_detail() -> None:
    bare = sov_errors.chain_lookup_failed_error()
    assert bare.code == "NET_ANCHOR"
    assert bare.retryable is True
    assert bare.message.endswith("verify this anchor.")
    detailed = sov_errors.chain_lookup_failed_error("HTTP 503")
    assert detailed.message.endswith("verify this anchor. HTTP 503")
    assert "`sov doctor --json`" in detailed.hint


def test_insufficient_resources_error_formats_needs_and_haves() -> None:
    err = sov_errors.insufficient_resources_error(
        "workshop", {"coins": 2, "wood": 1}, {"coins": 1, "wood": 0}, "Run `sov market sell`."
    )
    assert err.code == "INPUT_UPGRADE"
    assert err.message == "Cannot upgrade workshop: need 2 coins + 1 wood, have 1 coin + 0 wood."
    assert err.hint == "Run `sov market sell`."


def test_insufficient_resources_error_empty_maps_say_nothing() -> None:
    err = sov_errors.insufficient_resources_error("builder", {}, {}, "hint")
    assert err.message == "Cannot upgrade builder: need nothing, have nothing."


def test_upgrade_rep_error() -> None:
    err = sov_errors.upgrade_rep_error("builder", 3, 1, "Earn rep with `sov vote`.")
    assert err.code == "INPUT_UPGRADE"
    assert err.message == "Cannot upgrade builder: need Rep >= 3, have 1."
    assert "`sov vote`" in err.hint


def test_mainnet_faucet_rejected_error() -> None:
    err = sov_errors.mainnet_faucet_rejected_error()
    assert err.code == "MAINNET_FAUCET_REJECTED"
    assert "no faucet" in err.message
    assert "`XRPL_SEED=<seed> sov wallet --network mainnet`" in err.hint
    assert "`sov wallet --network testnet`" in err.hint


def test_keyring_unavailable_error_carries_detail_and_never_a_seed() -> None:
    err = sov_errors.keyring_unavailable_error("no backend")
    assert err.code == "KEYRING_UNAVAILABLE"
    assert err.message == "OS keychain unavailable: no backend."
    assert "`.sov/wallet_seed.txt`" in err.hint
    assert "`XRPL_SEED=<seed> sov wallet --network mainnet`" in err.hint


def test_user_message_renders_code_message_and_hint() -> None:
    err = sov_errors.keyring_unavailable_error("no backend")
    rendered = err.user_message()
    assert rendered.startswith("[KEYRING_UNAVAILABLE] OS keychain unavailable")
    assert "\n  Hint: " in rendered


# ---------------------------------------------------------------------------
# wallet_seed (in-memory keyring only)
# ---------------------------------------------------------------------------


class _MemoryKeyring(KeyringBackend):
    priority = 1.0

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.store.pop((service, username))  # KeyError when absent, like real backends raise


class _BrokenKeyring(KeyringBackend):
    """Every operation raises, like a host with no usable OS store."""

    priority = 1.0

    def get_password(self, service: str, username: str) -> str | None:
        raise RuntimeError("no keyring backend")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise RuntimeError("no keyring backend")

    def delete_password(self, service: str, username: str) -> None:
        raise RuntimeError("no keyring backend")


@pytest.fixture()
def memory_keyring() -> Any:
    previous = keyring.get_keyring()
    backend = _MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    backend.store.clear()
    keyring.set_keyring(previous)


@pytest.fixture()
def broken_keyring() -> Any:
    previous = keyring.get_keyring()
    keyring.set_keyring(_BrokenKeyring())
    yield
    keyring.set_keyring(previous)


def test_seed_set_get_clear_roundtrip(memory_keyring: _MemoryKeyring) -> None:
    assert get_mainnet_seed() is None
    set_mainnet_seed(f"  {_SECRET}\n")
    assert memory_keyring.store[(KEYRING_SERVICE, KEYRING_MAINNET_USER)] == _SECRET
    assert get_mainnet_seed() == _SECRET
    clear_mainnet_seed()
    assert get_mainnet_seed() is None


def test_clear_when_nothing_stored_is_a_quiet_noop(
    memory_keyring: _MemoryKeyring, caplog: _SovLog
) -> None:
    with caplog.at_level(logging.INFO, logger="sov_engine"):
        clear_mainnet_seed()  # backend raises KeyError; must be swallowed
    assert "wallet_seed.keyring.clear_skipped" in caplog.text
    assert _SECRET not in caplog.text


@pytest.mark.parametrize("blank", ["", "   ", "\n\t"])
def test_set_rejects_empty_seed(memory_keyring: _MemoryKeyring, blank: str) -> None:
    with pytest.raises(ValueError, match="empty seed"):
        set_mainnet_seed(blank)
    assert memory_keyring.store == {}


@pytest.mark.parametrize("stored", ["", "   \n"])
def test_get_treats_blank_entry_as_missing(memory_keyring: _MemoryKeyring, stored: str) -> None:
    memory_keyring.store[(KEYRING_SERVICE, KEYRING_MAINNET_USER)] = stored
    assert get_mainnet_seed() is None


def test_keyring_unavailable_paths(broken_keyring: None, caplog: _SovLog) -> None:
    with caplog.at_level(logging.INFO, logger="sov_engine"):
        assert get_mainnet_seed() is None
        clear_mainnet_seed()
        with pytest.raises(
            KeyringUnavailableError, match=r"OS keychain unavailable \(RuntimeError\)"
        ):
            set_mainnet_seed(_SECRET)
    assert "wallet_seed.keyring.get_failed exc=RuntimeError" in caplog.text
    assert "wallet_seed.keyring.clear_skipped" in caplog.text
    assert _SECRET not in caplog.text


def test_keyring_package_missing_paths(monkeypatch: pytest.MonkeyPatch, caplog: _SovLog) -> None:
    # ``import keyring`` inside the helpers raises ImportError when the entry is None.
    monkeypatch.setitem(sys.modules, "keyring", None)
    with caplog.at_level(logging.INFO, logger="sov_engine"):
        assert get_mainnet_seed() is None
        clear_mainnet_seed()
        with pytest.raises(KeyringUnavailableError, match="keyring package is not installed"):
            set_mainnet_seed(_SECRET)
    assert "wallet_seed.keyring.unavailable reason=import" in caplog.text


def test_resolve_seed_skips_unreadable_and_blank_files(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XRPL_SEED", "sEdVEnvSeedXXXXXXXXXXXXXXXXXX")
    missing = in_tmp / "absent.txt"
    blank = in_tmp / "blank.txt"
    blank.write_text("  \n", encoding="utf-8")

    # signer file missing / blank -> falls through to the plaintext wallet file (blank) -> env
    got = resolve_wallet_seed(network="testnet", signer_file=missing, wallet_file=blank)
    assert got == "sEdVEnvSeedXXXXXXXXXXXXXXXXXX"


def test_resolve_seed_none_when_every_source_is_empty(
    in_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XRPL_SEED", raising=False)
    assert resolve_wallet_seed(network="testnet") is None
    assert resolve_wallet_seed(network="testnet", seed_env=None) is None
    monkeypatch.setenv("XRPL_SEED", "   ")
    assert resolve_wallet_seed(network="testnet") is None


def test_resolve_mainnet_falls_back_to_file_when_keyring_empty(
    in_tmp: Path, memory_keyring: _MemoryKeyring, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XRPL_SEED", raising=False)
    wallet_file = in_tmp / "wallet_seed.txt"
    wallet_file.write_text("sEdVFileSeedXXXXXXXXXXXXXXXXXXX\n", encoding="utf-8")
    assert (
        resolve_wallet_seed(network="mainnet", wallet_file=wallet_file)
        == "sEdVFileSeedXXXXXXXXXXXXXXXXXXX"
    )

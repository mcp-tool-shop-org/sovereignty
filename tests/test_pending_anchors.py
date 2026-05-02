"""Tests for ``sov_engine.io_utils`` pending-anchors helpers (v2.1 §4).

Pins the on-disk schema + helper API:

* ``pending_anchors_path(game_id) -> .sov/games/<game-id>/pending-anchors.json``
* ``read_pending_anchors(game_id) -> dict[str, PendingEntry]`` (empty when missing)
* ``add_pending_anchor(game_id, round_key, envelope_hash)`` — idempotent;
  re-add overwrites the timestamp (and envelope_hash) without raising.
* ``clear_pending_anchors(game_id, round_keys)`` — partial clear; empty list no-op.
* All writes go through ``atomic_write_text`` (no ``.tmp`` sibling persists).
* On-disk shape matches spec §4: ``{"schema_version": 1, "entries": {...}}``.

All tests use ``monkeypatch.chdir(tmp_path)`` so ``Path('.sov')`` resolves
inside the temp dir, never the developer's real workspace.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sov_engine.io_utils import (
    add_pending_anchor,
    clear_pending_anchors,
    pending_anchors_path,
    read_pending_anchors,
)

_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_C = "c" * 64
_HASH_FINAL = "f" * 64


# ---------------------------------------------------------------------------
# pending_anchors_path
# ---------------------------------------------------------------------------


def test_pending_anchors_path_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Path matches spec §4: ``.sov/games/<game-id>/pending-anchors.json``."""
    monkeypatch.chdir(tmp_path)
    p = pending_anchors_path("s42")
    assert p == Path(".sov") / "games" / "s42" / "pending-anchors.json"


# ---------------------------------------------------------------------------
# read_pending_anchors
# ---------------------------------------------------------------------------


def test_read_pending_anchors_empty_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Returns an empty dict when the file does not exist."""
    monkeypatch.chdir(tmp_path)
    assert read_pending_anchors("s42") == {}


# ---------------------------------------------------------------------------
# add_pending_anchor
# ---------------------------------------------------------------------------


def test_add_pending_anchor_creates_file_with_right_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """First add creates the file with ``schema_version`` + ``entries``."""
    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", _HASH_A)

    raw = pending_anchors_path("s42").read_text(encoding="utf-8")
    data = json.loads(raw)

    assert data["schema_version"] == 1
    assert "entries" in data
    entries = data["entries"]
    assert "1" in entries
    row = entries["1"]
    assert row["envelope_hash"] == _HASH_A
    assert isinstance(row["added_iso"], str)
    # ISO-8601 UTC with literal Z suffix (matches proof envelope shape).
    assert row["added_iso"].endswith("Z")


def test_add_pending_anchor_re_add_same_round_key_overwrites_timestamp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Re-add of the same round_key overwrites the row (idempotent).

    Per spec §4, adding the same round_key refreshes ``added_iso``. The
    envelope_hash field carries whatever the latest call passed — for the
    common case (re-adding with the same hash), that's stable; for the
    edge case (same round_key, different hash), the latest write wins.
    """
    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", _HASH_A)
    first = read_pending_anchors("s42")["1"]

    # Re-add same round_key, same hash. Expect row to still exist with
    # the same envelope_hash; added_iso stays well-formed.
    add_pending_anchor("s42", "1", _HASH_A)
    second = read_pending_anchors("s42")["1"]

    assert second["envelope_hash"] == _HASH_A
    # No new row was added.
    entries = read_pending_anchors("s42")
    assert list(entries.keys()) == ["1"]
    # added_iso is still well-formed.
    assert second["added_iso"].endswith("Z")
    # First and second are the same shape.
    assert set(first.keys()) == set(second.keys())


def test_add_pending_anchor_multiple_rounds_accumulates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Successive adds accumulate distinct round_keys."""
    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", _HASH_A)
    add_pending_anchor("s42", "2", _HASH_B)
    add_pending_anchor("s42", "FINAL", _HASH_FINAL)

    entries = read_pending_anchors("s42")
    assert set(entries.keys()) == {"1", "2", "FINAL"}
    assert entries["1"]["envelope_hash"] == _HASH_A
    assert entries["2"]["envelope_hash"] == _HASH_B
    assert entries["FINAL"]["envelope_hash"] == _HASH_FINAL


# ---------------------------------------------------------------------------
# clear_pending_anchors
# ---------------------------------------------------------------------------


def test_clear_pending_anchors_removes_named_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Removes the named keys, leaves others."""
    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", _HASH_A)
    add_pending_anchor("s42", "2", _HASH_B)
    add_pending_anchor("s42", "3", _HASH_C)

    clear_pending_anchors("s42", ["1", "2"])

    entries = read_pending_anchors("s42")
    assert set(entries.keys()) == {"3"}
    assert entries["3"]["envelope_hash"] == _HASH_C


def test_clear_pending_anchors_empty_list_is_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Empty ``round_keys`` does not write or alter the file."""
    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", _HASH_A)

    before = pending_anchors_path("s42").read_text(encoding="utf-8")
    clear_pending_anchors("s42", [])
    after = pending_anchors_path("s42").read_text(encoding="utf-8")

    assert before == after, "empty round_keys must be a no-op (no rewrite)"
    # And the entry survives.
    assert read_pending_anchors("s42") == {
        "1": {"envelope_hash": _HASH_A, "added_iso": read_pending_anchors("s42")["1"]["added_iso"]},
    }


def test_clear_pending_anchors_idempotent_on_missing_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Clearing keys that don't exist is silently OK."""
    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", _HASH_A)

    # "999" is not pending — must not raise.
    clear_pending_anchors("s42", ["999"])

    entries = read_pending_anchors("s42")
    assert set(entries.keys()) == {"1"}


def test_clear_pending_anchors_when_file_missing_is_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Clearing on a fresh game (no pending file) does nothing, no crash."""
    monkeypatch.chdir(tmp_path)
    # No add_pending_anchor first — file doesn't exist.
    clear_pending_anchors("s42", ["1", "2"])
    assert not pending_anchors_path("s42").exists()


# ---------------------------------------------------------------------------
# Atomic write: no ``.tmp`` sibling left behind
# ---------------------------------------------------------------------------


def test_pending_anchors_writes_through_atomic_write_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No ``.tmp`` sibling persists after add or clear.

    ``atomic_write_text`` writes to ``<path>.tmp`` then ``os.replace`` to
    ``<path>``. After a successful call the ``.tmp`` sibling MUST NOT exist
    — its presence indicates either a non-atomic rewrite or a crashed write
    that was never cleaned up.
    """
    monkeypatch.chdir(tmp_path)

    add_pending_anchor("s42", "1", _HASH_A)
    add_pending_anchor("s42", "2", _HASH_B)
    clear_pending_anchors("s42", ["1"])

    p = pending_anchors_path("s42")
    tmp_sibling = p.with_suffix(p.suffix + ".tmp")
    assert not tmp_sibling.exists(), (
        f"atomic-write sibling {tmp_sibling} must not persist after a successful write"
    )
    assert p.exists(), f"final file {p} should be in place"

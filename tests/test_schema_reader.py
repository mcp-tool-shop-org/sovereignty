"""Forward-bump safety + empty-migration-registry pin for sov_engine.schemas.

Stage 7-B amend (BACKEND-B-003) introduced the centralised versioned-JSON
read seam. These tests pin two invariants:

1. Unknown ``schema_version`` raises ``SchemaVersionUnsupportedError`` rather
   than silently round-tripping (the failure mode that motivated BACKEND-B-001
   on ``pending-anchors.json``).
2. ``_MIGRATIONS`` is empty in v2.1 — locks the pattern so v2.2's first
   migrator is a single-line registry addition rather than a "design the
   framework" project.

When v2.2 lands its first migrator, the empty-registry assertion below should
flip to a positive check that the migrator round-trips correctly — not be
deleted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sov_engine.schemas import (
    _MIGRATIONS,
    SchemaVersionUnsupportedError,
    read_versioned,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_migrations_registry_is_empty_in_v2_1() -> None:
    """Locks the v2.1 contract: no migrators land at the v2.1 cut.

    v2.2's first migrator must come with a corresponding test that asserts
    its round-trip behaviour; this assertion forces that future change to
    update both halves rather than silently growing the registry.
    """
    assert _MIGRATIONS == {}, (
        f"Stage 7-B locked _MIGRATIONS empty in v2.1; got {sorted(_MIGRATIONS.keys())!r}"
    )


def test_read_versioned_round_trips_current_schema(tmp_path: Path) -> None:
    """Current-version files parse and return the full payload (including
    ``schema_version``)."""
    path = tmp_path / "doc.json"
    _write_json(path, {"schema_version": 1, "entries": {"1": "abc"}})
    data = read_versioned(path, expected_schema=1, file_class="test-doc")
    assert data == {"schema_version": 1, "entries": {"1": "abc"}}


def test_read_versioned_forward_bump_raises(tmp_path: Path) -> None:
    """A file declaring a schema_version this binary doesn't recognise raises
    ``SchemaVersionUnsupportedError``. This is the forward-bump safety
    contract from AMEND.md §A."""
    path = tmp_path / "future.json"
    _write_json(path, {"schema_version": 999, "entries": {}})
    with pytest.raises(SchemaVersionUnsupportedError) as exc_info:
        read_versioned(path, expected_schema=1, file_class="pending-anchors")
    err = exc_info.value
    assert err.found == 999
    assert err.expected == 1
    assert err.file_class == "pending-anchors"
    assert err.path == path


def test_read_versioned_missing_schema_version_raises(tmp_path: Path) -> None:
    """Bare-dict files without ``schema_version`` raise — callers that want
    bare-dict backward-compat (e.g. anchors.json migrate-on-read) must do so
    explicitly outside ``read_versioned``."""
    path = tmp_path / "bare.json"
    _write_json(path, {"entries": {}})
    with pytest.raises(SchemaVersionUnsupportedError) as exc_info:
        read_versioned(path, expected_schema=1, file_class="test-doc")
    assert exc_info.value.found == -1


def test_read_versioned_non_object_raises(tmp_path: Path) -> None:
    """Top-level non-objects (lists, scalars) raise immediately."""
    path = tmp_path / "list.json"
    path.write_text(json.dumps([{"schema_version": 1}]), encoding="utf-8")
    with pytest.raises(SchemaVersionUnsupportedError):
        read_versioned(path, expected_schema=1, file_class="test-doc")


def test_read_versioned_no_migration_path_raises(tmp_path: Path) -> None:
    """With the empty registry, a recognisably-numeric older version still
    raises because no migrator is registered to bring it to current.

    This pins the v2.1 contract; v2.2's first migrator changes this case
    from "raises" to "warns + migrates"."""
    path = tmp_path / "old.json"
    _write_json(path, {"schema_version": 1, "entries": {}})
    with pytest.raises(SchemaVersionUnsupportedError) as exc_info:
        read_versioned(path, expected_schema=2, file_class="test-doc")
    assert exc_info.value.found == 1
    assert exc_info.value.expected == 2

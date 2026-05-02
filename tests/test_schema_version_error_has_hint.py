"""Regression test for BACKEND-C-001 — SchemaVersionUnsupportedError carries a hint.

Stage 8-C amend (Wave 11) attached a recovery hint to
``SchemaVersionUnsupportedError`` so any uncaught surface (third-party
tooling, debug stderr, support-bundle tracebacks) renders the operator
action plus a doc reference instead of a bare structured field.

DISPATCH target A row for SCHEMA_VERSION_UNSUPPORTED requires the
supported version range and the upgrade-doc reference in the hint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sov_engine.schemas import SchemaVersionUnsupportedError, read_versioned


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_schema_version_error_exposes_hint_attribute(tmp_path: Path) -> None:
    """The exception carries a ``hint`` attribute for structured consumers."""
    path = tmp_path / "future.json"
    _write_json(path, {"schema_version": 999, "entries": {}})

    with pytest.raises(SchemaVersionUnsupportedError) as exc_info:
        read_versioned(path, expected_schema=1, file_class="pending-anchors")

    err = exc_info.value
    assert isinstance(err.hint, str)
    assert err.hint, "hint must be a non-empty string"


def test_schema_version_error_hint_names_supported_version(tmp_path: Path) -> None:
    """The hint mentions the supported version range — operator must know
    what THIS binary expects, not just what was found."""
    path = tmp_path / "future.json"
    _write_json(path, {"schema_version": 999, "entries": {}})

    with pytest.raises(SchemaVersionUnsupportedError) as exc_info:
        read_versioned(path, expected_schema=1, file_class="pending-anchors")

    assert "schema_version=1" in exc_info.value.hint, (
        f"hint must name the supported version; got: {exc_info.value.hint!r}"
    )


def test_schema_version_error_hint_references_doc(tmp_path: Path) -> None:
    """The hint carries an upgrade-doc reference (DISPATCH target A row)."""
    path = tmp_path / "future.json"
    _write_json(path, {"schema_version": 999, "entries": {}})

    with pytest.raises(SchemaVersionUnsupportedError) as exc_info:
        read_versioned(path, expected_schema=1, file_class="pending-anchors")

    assert "docs/v2.1-bridge-changes.md" in exc_info.value.hint, (
        f"hint must reference the upgrade doc; got: {exc_info.value.hint!r}"
    )


def test_schema_version_error_str_includes_hint(tmp_path: Path) -> None:
    """``str(err)`` carries the hint so uncaught surfaces (third-party
    tooling, debug stderr) render the recovery sentence rather than a
    bare structured field."""
    path = tmp_path / "future.json"
    _write_json(path, {"schema_version": 999, "entries": {}})

    with pytest.raises(SchemaVersionUnsupportedError) as exc_info:
        read_versioned(path, expected_schema=1, file_class="pending-anchors")

    rendered = str(exc_info.value)
    assert "Re-export" in rendered or "upgrade sovereignty" in rendered, (
        f"str(err) must surface the hint; got: {rendered!r}"
    )

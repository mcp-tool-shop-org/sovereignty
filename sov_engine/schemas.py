"""Centralised versioned-JSON read seam for sov_engine.

Every persisted-JSON consumer that carries ``schema_version`` goes through
``read_versioned``. Forward-bump safety: unknown versions raise
``SchemaVersionUnsupportedError`` rather than silently round-tripping. Migration
registry: ``_MIGRATIONS`` maps ``(from_version, to_version) -> Callable`` so
v2.2 can register a v1→v2 migrator without re-plumbing the readers.

The pattern is locked in v2.1 with an empty migration registry — the v2.2
first migrator is a single-line ``_MIGRATIONS[...]`` addition, not a "design
the framework" project.

Reference: ``docs/v2.1-bridge-changes.md`` §B (audit trail), AMEND.md §A.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("sov_engine")


class SchemaVersionUnsupportedError(Exception):
    """Raised when a versioned JSON file declares ``schema_version`` this
    binary doesn't recognize.

    Operator action: upgrade sovereignty or downgrade the file via export-
    and-reimport. The exception carries ``path``, ``found``, ``expected``,
    and ``file_class`` attributes so structured-error consumers (CLI
    ``SovError``, daemon error envelopes) can surface a precise hint.
    """

    def __init__(self, path: Path, found: int, expected: int, file_class: str):
        super().__init__(
            f"{file_class} at {path} has schema_version={found!r} "
            f"but this binary expects schema_version={expected}"
        )
        self.path = path
        self.found = found
        self.expected = expected
        self.file_class = file_class


_MIGRATIONS: dict[tuple[int, int], Callable[[dict[str, Any]], dict[str, Any]]] = {
    # No entries in v2.1; pattern locked for v2.2's first migrator.
    # Key: (from_version, to_version). Value: pure function migrating one to the other.
}


def read_versioned(
    path: Path,
    expected_schema: int,
    *,
    file_class: str,
) -> dict[str, Any]:
    """Read versioned JSON. Validates ``schema_version`` recognized.

    Returns the parsed dict (with the ``schema_version`` field intact —
    callers are free to pop or ignore it). Raises
    ``SchemaVersionUnsupportedError`` on unrecognized version (forward-bump
    safety). Logs at WARNING with ``schema.deprecated`` event when a
    supported-but-older version is read and a registered migration runs in
    process — operator should re-export to land the wrapped form on disk.

    The migration registry is empty in v2.1; the WARNING path will only
    trigger when v2.2 (or later) lands its first migrator.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SchemaVersionUnsupportedError(path, -1, expected_schema, file_class)
    data: dict[str, Any] = {str(k): v for k, v in raw.items()}
    version = data.get("schema_version")
    if version != expected_schema:
        if isinstance(version, int) and (version, expected_schema) in _MIGRATIONS:
            logger.warning(
                "schema.deprecated path=%s found=%d expected=%d file_class=%s "
                "(migrating in-process; consider exporting + re-importing to "
                "avoid the deprecation warning on next read)",
                path,
                version,
                expected_schema,
                file_class,
            )
            data = _MIGRATIONS[(version, expected_schema)](data)
        else:
            raise SchemaVersionUnsupportedError(
                path,
                version if isinstance(version, int) else -1,
                expected_schema,
                file_class,
            )
    return data

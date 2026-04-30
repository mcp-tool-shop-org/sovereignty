"""Shared I/O utilities for sovereignty.

Atomic write helper used by both the engine (proof persistence) and the
CLI (game state, season, rng_seed, anchors). Lives in the engine layer
because the engine cannot import from the CLI; CLI imports from engine.
"""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically.

    Crash / disk-full mid-write leaves a ``.tmp`` sibling, NOT a half-written
    target file. Single-process write atomicity only — concurrent-writer
    locking is the caller's responsibility.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    os.replace(tmp, path)

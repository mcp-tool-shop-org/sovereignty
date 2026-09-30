"""The npx launcher downloads the release binary for its own version.

If ``npm/package.json`` lags ``pyproject.toml``, `npx @mcptoolshop/sovereignty`
keeps serving the old binaries. That happened for all of 2.3.x (the launcher
stayed at 2.2.1 while it was published by hand), so the versions are pinned
together here.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_npm_launcher_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))

    assert package["version"] == pyproject["project"]["version"]

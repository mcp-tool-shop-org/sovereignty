"""Version consistency tests for sovereignty."""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _get_version() -> str:
    """Read version from pyproject.toml."""
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert match, "Could not find version in pyproject.toml"
    return match.group(1)


def test_version_is_semver():
    ver = _get_version()
    parts = ver.split(".")
    assert len(parts) >= 3, f"Expected semver, got {ver}"
    assert all(p.isdigit() for p in parts[:3])


def test_version_at_least_1_0_0():
    ver = _get_version()
    major = int(ver.split(".")[0])
    assert major >= 1, f"Expected major >= 1, got {major}"


def test_changelog_contains_current_version():
    ver = _get_version()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"[{ver}]" in changelog, f"CHANGELOG missing [{ver}]"


def test_version_flag_available():
    """CLI source contains version callback."""
    main_py = (ROOT / "sov_cli" / "main.py").read_text(encoding="utf-8")
    assert "--version" in main_py
    assert "_version_callback" in main_py

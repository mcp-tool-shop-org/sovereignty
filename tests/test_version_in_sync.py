"""Pin: CLI-reported version stays in sync with pyproject.toml.

Wave 11 CLI-C-036 lifted the hard-coded ``SOV_VERSION = "1.4.7"`` constant
in ``sov_cli/main.py`` (four releases stale by the time it was caught) and
replaced it with a runtime resolver — ``importlib.metadata.version()`` with
a ``pyproject.toml`` fallback. This test mechanically pins that the CLI's
``--version`` flag reports the same value the package metadata declares,
so the next time someone bumps the version they only have to bump it in
one place.

If this test fails, the most likely cause is that someone added a fresh
hard-coded version constant somewhere in ``sov_cli``. Search for any
quoted ``X.Y.Z`` literal inside the package and route it through
``_resolve_version()`` instead.
"""

from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from sov_cli.main import _resolve_version, app

ROOT = Path(__file__).parent.parent
runner = CliRunner()


def _pyproject_version() -> str:
    """Read the canonical version from pyproject.toml."""
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert match, "pyproject.toml must declare a version"
    return match.group(1)


def test_resolve_version_matches_pyproject() -> None:
    """``_resolve_version()`` returns the same value pyproject.toml declares."""
    assert _resolve_version() == _pyproject_version()


def test_cli_version_flag_matches_pyproject() -> None:
    """``sov --version`` output names the pyproject.toml version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, f"--version must exit 0; output={result.output!r}"
    assert _pyproject_version() in result.output, (
        f"`sov --version` output must include {_pyproject_version()!r}; got: {result.output!r}"
    )


def test_no_hardcoded_sov_version_constant() -> None:
    """``SOV_VERSION = "x.y.z"`` constant must not reappear in sov_cli.

    The constant pattern was the root cause of CLI-C-036 (drift from
    1.4.7 → 2.0.2 across four releases). Pin its absence so a future
    refactor doesn't reintroduce it accidentally.
    """
    main_text = (ROOT / "sov_cli" / "main.py").read_text(encoding="utf-8")
    errors_text = (ROOT / "sov_cli" / "errors.py").read_text(encoding="utf-8")
    # Reject ``SOV_VERSION = "..."`` assignment (any quote / version literal).
    pattern = re.compile(r'^\s*SOV_VERSION\s*=\s*["\']', re.MULTILINE)
    assert not pattern.search(main_text), (
        "sov_cli/main.py must not declare a hardcoded SOV_VERSION constant; "
        "use _resolve_version() instead (CLI-C-036)."
    )
    assert not pattern.search(errors_text), (
        "sov_cli/errors.py must not declare a hardcoded SOV_VERSION constant."
    )


def test_self_check_reports_pyproject_version() -> None:
    """``sov self-check`` Version row matches pyproject.toml."""
    result = runner.invoke(app, ["self-check"])
    assert result.exit_code == 0, f"self-check must exit 0; output={result.output!r}"
    assert _pyproject_version() in result.output, (
        f"`sov self-check` must surface the pyproject version "
        f"{_pyproject_version()!r}; got: {result.output!r}"
    )

"""`sov --version` must not crash when neither metadata nor pyproject exists.

That is the PyInstaller binary's situation: no installed distribution
metadata unless bundled, and no pyproject.toml beside the frozen modules.
Through 2.3.2 the --version callback read pyproject.toml unguarded and every
release binary printed a traceback.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
from typer.testing import CliRunner

import sov_cli.main as cli_main


def test_version_degrades_to_unknown_when_frozen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def missing(_name: str) -> str:
        raise PackageNotFoundError("sovereignty-game")

    monkeypatch.setattr(cli_main, "_pkg_version", missing)
    # Point the module at a directory with no pyproject.toml above it.
    monkeypatch.setattr(cli_main, "__file__", str(tmp_path / "pkg" / "main.py"))

    result = CliRunner().invoke(cli_main.app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "sovereignty unknown"

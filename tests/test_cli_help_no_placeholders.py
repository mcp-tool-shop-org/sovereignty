"""Mechanical pin: no placeholder markers in any sov subcommand --help.

Stage 8-C amend (Wave 11 Pin C). Walks Typer's app structure dynamically
and runs ``--help`` against every subcommand (root, top-level commands,
sub-app commands like ``daemon start``), then asserts the output contains
zero placeholder markers (``TODO``, ``WIP``, ``FIXME``, ``XXX``,
``<placeholder>``).

Why CliRunner over subprocess: the repo's existing CLI-help tests already
use ``typer.testing.CliRunner``; matrix-leg pytest runs (3.11 / 3.12 /
3.13) don't install the package as a console script before tests, so
subprocess invocation would require an extra install step and complicate
the matrix.

New subcommands are picked up automatically — the test enumerates
``app.registered_commands`` + ``app.registered_groups`` recursively rather
than hard-coding paths.
"""

from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from sov_cli.main import app

# Placeholder markers that must never reach a user-facing help surface.
# Word-boundary matched to avoid hitting prose ("todo list" example) or
# the ellipsis-as-prose case. Lowercase variants intentionally excluded —
# overly broad and they hit legitimate prose in command examples.
PLACEHOLDER_PATTERN = re.compile(r"\b(TODO|WIP|FIXME|XXX)\b|<placeholder>")


def _enumerate_command_paths(typer_app) -> list[list[str]]:  # noqa: ANN001
    """Walk a Typer app and return every subcommand path.

    Returns a list of arg-vectors. ``[]`` represents the root
    ``sov --help``. ``["games"]`` represents ``sov games --help``.
    ``["daemon", "start"]`` represents ``sov daemon start --help``.

    Walks recursively so nested sub-apps surface. Typer 0.24's
    ``registered_commands`` is ``list[CommandInfo]`` and
    ``registered_groups`` is ``list[TyperInfo]`` — both stable enough that
    prior tests in this repo rely on adjacent internals.
    """
    paths: list[list[str]] = [[]]  # root --help

    for cmd in typer_app.registered_commands:
        cmd_name = cmd.name or cmd.callback.__name__.replace("_", "-")
        paths.append([cmd_name])

    for group in typer_app.registered_groups:
        group_name = group.name or "default"
        paths.append([group_name])
        for sub_cmd in group.typer_instance.registered_commands:
            sub_name = sub_cmd.name or sub_cmd.callback.__name__.replace("_", "-")
            paths.append([group_name, sub_name])
        # Recurse if a sub-group has its own sub-groups (not used at v2.1
        # but future-proofs the walk).
        for nested_group in group.typer_instance.registered_groups:
            nested_name = nested_group.name or "default"
            paths.append([group_name, nested_name])
            for nested_cmd in nested_group.typer_instance.registered_commands:
                nc_name = nested_cmd.name or nested_cmd.callback.__name__.replace("_", "-")
                paths.append([group_name, nested_name, nc_name])

    return paths


_COMMAND_PATHS = _enumerate_command_paths(app)


@pytest.mark.parametrize(
    "command_path",
    _COMMAND_PATHS,
    ids=[" ".join(p) if p else "<root>" for p in _COMMAND_PATHS],
)
def test_help_has_no_placeholders(command_path: list[str]) -> None:
    """``sov <path> --help`` output contains no placeholder markers."""
    runner = CliRunner()
    result = runner.invoke(app, [*command_path, "--help"])

    # --help should always exit 0 (Typer's default Click behavior). If it
    # doesn't, the help itself is broken — surface that as the failure
    # rather than silently letting placeholders slip.
    assert result.exit_code == 0, (
        f"`sov {' '.join(command_path)} --help` exited {result.exit_code}; stdout:\n{result.stdout}"
    )

    match = PLACEHOLDER_PATTERN.search(result.stdout)
    assert match is None, (
        f"`sov {' '.join(command_path)} --help` contains placeholder "
        f"{match.group()!r}.\n"
        f"Help output:\n{result.stdout}"
    )

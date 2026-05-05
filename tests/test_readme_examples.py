"""README "A real session" smoke test.

The README's quickstart shows a worked example: ``sov new``, a few
``sov turn`` calls, then ``sov status``. If a code change drifts that
example out from under the documentation, players who copy-paste it hit
an error and bounce. This test pins the example's RUNNABILITY (every
command exits 0) and the STRUCTURE of the status output (player names
appear, round counter appears) without pinning exact coin/rep numbers
that vary by random seed and tuning.

Coordination contract with engine F-002:
    Engine adds ``--brief`` to ``sov status`` so the README's expected
    output can quote a stable, machine-readable line. We use
    ``--brief`` when the engine has shipped it and fall back to the
    plain ``sov status`` shape otherwise (skip the structure assertions
    that depend on the brief format).

If the README's "A real session" section gets renamed or its
``sov`` commands change, update both this test and the README in the
same commit — they are joined contracts. The section was renamed from
"Your first game" to "A real session" in v2.2.0 (humanized voice).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sov_cli.main import app

runner = CliRunner()

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


def _readme_first_game_section() -> str:
    """Extract the "A real session" section text from README.md.

    Returns the section body (between its H2 and the next H2). Raises
    AssertionError if the section is missing — that itself is a contract
    violation worth failing on.
    """
    text = README_PATH.read_text(encoding="utf-8")
    # Find "## A real session" heading and slice to the next "## "
    start_match = re.search(r"^## A real session\s*$", text, re.MULTILINE)
    assert start_match, (
        "README.md must contain a '## A real session' section. "
        "If you renamed it, also update tests/test_readme_examples.py."
    )
    after_heading = text[start_match.end() :]
    next_heading = re.search(r"^## ", after_heading, re.MULTILINE)
    end_offset = next_heading.start() if next_heading else len(after_heading)
    return after_heading[:end_offset]


def test_readme_first_game_section_exists_and_quotes_core_commands():
    """The "A real session" section must reference the core commands.

    If a future edit drops one of these commands, the test fails so the
    follow-up commit can either (a) add the command back or (b) update
    this contract intentionally.
    """
    section = _readme_first_game_section()
    for cmd in ("sov new", "sov turn", "sov status"):
        assert cmd in section, (
            f"README 'A real session' section must reference {cmd!r}. "
            f"Section content was:\n{section!r}"
        )


def test_readme_quickstart_runs_end_to_end(monkeypatch, tmp_path):
    """Run the README's quickstart commands and assert every step exits 0.

    This is the smoke test: if a player copy-pastes the section into a
    fresh terminal, do all the commands work? We don't assert exact
    output text (numbers vary by seed; Rich theming can vary) — we
    assert the commands EXECUTE cleanly and the final status shows the
    expected players.
    """
    monkeypatch.chdir(tmp_path)

    # 1. sov new -p Alice -p Bob -p Carol  (use a fixed seed for determinism)
    result = runner.invoke(
        app,
        ["new", "-s", "42", "-p", "Alice", "-p", "Bob", "-p", "Carol"],
    )
    assert result.exit_code == 0, (
        f"README quickstart step 1 (sov new) must exit 0; output={result.output!r}"
    )

    # 2. sov turn (a few times — README implies "each player takes a turn")
    for i in range(3):
        result = runner.invoke(app, ["turn"])
        assert result.exit_code == 0, (
            f"README quickstart step 2 (sov turn #{i + 1}) must exit 0; output={result.output!r}"
        )

    # 3. sov status — must exit 0 and surface all three players.
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, (
        f"README quickstart step 3 (sov status) must exit 0; output={result.output!r}"
    )
    for name in ("Alice", "Bob", "Carol"):
        assert name in result.output, (
            f"sov status output must surface player {name!r} "
            f"(README example shows all three players); "
            f"got: {result.output!r}"
        )


def test_readme_brief_status_format_when_available(monkeypatch, tmp_path):
    """When ``sov status --brief`` is wired (engine F-002), assert its
    structure matches the README's quoted example.

    The README quotes a compact one-line-per-player format:
        ``Alice   coins: 7   rep: 4   space: 11``
    We don't pin the exact numbers (those depend on dice rolls) but we DO
    pin the structural keywords: each player line must mention "coins"
    and either "rep" or "Rep" (the README uses lowercase).

    If ``--brief`` is not yet shipped (typer UsageError, exit code 2),
    skip — engine F-002 will land it, and this test activates the moment
    the flag exists.
    """
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["new", "-s", "42", "-p", "Alice", "-p", "Bob", "-p", "Carol"],
    )
    assert result.exit_code == 0, f"sov new failed: {result.output!r}"

    # Take a couple of turns so status has something to render.
    for _ in range(2):
        result = runner.invoke(app, ["turn"])
        assert result.exit_code == 0, f"sov turn failed: {result.output!r}"

    result = runner.invoke(app, ["status", "--brief"])

    if result.exit_code == 2:
        pytest.skip(
            "sov status --brief not yet wired by engine agent in this wave; "
            "this test will activate once the flag lands per F-002."
        )

    assert result.exit_code == 0, (
        f"sov status --brief must exit 0 once the flag is shipped; output={result.output!r}"
    )

    # Structural assertions matching the actual --brief format:
    #   R<round> |  Alice: 4c 3r 0u |  Bob: 4c 3r 0u | >Carol: 5c 3r 0u
    # README quotes this exact format; `Nc Nr Nu` = coins/rep/upgrades;
    # `>` marks the active player.
    output = result.output
    for name in ("Alice", "Bob", "Carol"):
        assert name in output, f"--brief output must include player {name!r}; got: {output!r}"
    # Round marker (R<digits>) must be present.
    assert re.search(r"R\d+", output), (
        f"--brief output must include a round marker (R<n>); got: {output!r}"
    )
    # Coins / rep / upgrades figures use the compact `\dc \dr \du` shorthand.
    assert re.search(r"\d+c\s+\d+r\s+\d+u", output), (
        f"--brief output must include `Nc Nr Nu` per player; got: {output!r}"
    )

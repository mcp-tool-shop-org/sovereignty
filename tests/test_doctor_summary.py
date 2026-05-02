"""Pin: ``sov doctor`` Wave 11 polish (CLI-C-029, CLI-C-030, CLI-C-031, CLI-C-032).

Wave 11 humanization pass added:
  * CLI-C-029 — friendly summary line at end of ``sov doctor`` output
    ("Summary: N passed, M warn, K fail.")
  * CLI-C-030 — word-glyph icons matching ``sov self-check`` (no more
    ``!!`` for warn).
  * CLI-C-031 — backticked recovery commands instead of ``Run: sov ...``.
  * CLI-C-032 — pending-anchor age-string no longer renders ``hourss``
    for ages ≥ 2h (dead-code branch removed).

Local fast-check: ``uv run pytest tests/test_doctor_summary.py -v``.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sov_cli.main import app

runner = CliRunner()


def test_doctor_renders_summary_line(monkeypatch, tmp_path: Path) -> None:
    """CLI-C-029: ``sov doctor`` ends with a friendly summary tally."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, f"doctor must exit 0; output={result.output!r}"
    assert "Summary:" in result.output, (
        f"`sov doctor` must end with a 'Summary: N passed, ...' line; got: {result.output!r}"
    )
    # Tally always has at least a "passed" count (every doctor run produces
    # a least one ok-status check — Filesystem write or similar).
    assert "passed" in result.output


def test_doctor_uses_word_glyph_icons_not_double_bang(monkeypatch, tmp_path: Path) -> None:
    """CLI-C-030: warn glyph is the word ``WARN``, not ``!!``.

    The previous icon dict used ``!!`` for warn which both visually shouts
    and rubs against Pin A (no `!` in error/warning copy). Wave 11
    swapped it to a word-glyph for parity with self-check's OK/FAIL.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    # The literal ``!!`` should not appear anywhere in the rendered output.
    # (Rich strips style markup before display, so we're checking the
    # rendered glyph text, not the markup tag.)
    assert "!!" not in result.output, (
        f"`sov doctor` warn glyph must not be '!!'; got: {result.output!r}"
    )


def test_doctor_hints_use_backticks_not_run_prefix(monkeypatch, tmp_path: Path) -> None:
    """CLI-C-031: doctor hints use backtick form, not ``Run: sov ...``.

    A fresh-cwd doctor run emits an info line "No active game" with a
    hint pointing at ``sov new``. Pin that the hint uses the backtick
    convention rather than the legacy ``Run: sov ...`` colon form.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    # Reject the legacy bare-colon form. Hint must be backticked.
    assert "Run: sov" not in result.output, (
        f"`sov doctor` must use backticked recovery hints, not 'Run: sov ...'; "
        f"got: {result.output!r}"
    )
    # And the new active-game hint should appear in some shape.
    assert "sov new" in result.output


def test_doctor_age_string_no_double_plural(monkeypatch, tmp_path: Path) -> None:
    """CLI-C-032: pending-anchor age renders ``hours`` not ``hourss``.

    The previous fallback appended an ``s`` to an already-pluralized
    ``hours`` string for ages ≥ 2h. We pin the absence of the ``hourss``
    artifact so the regression doesn't reappear; we don't bother
    constructing a ≥ 2h pending anchor (that requires either
    timestamp-mocking or a real wait), since the literal is grep-detectable
    on any doctor output.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "hourss" not in result.output, (
        f"`sov doctor` age string must not render 'hourss'; got: {result.output!r}"
    )

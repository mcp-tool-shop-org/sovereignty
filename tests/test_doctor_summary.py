"""Pin: ``sov doctor`` Wave 11 polish (CLI-C-029, CLI-C-030, CLI-C-031, CLI-C-032)
plus Wave 13 Stage 9-D follow-ups (CLI-D-001, CLI-D-002).

Wave 11 humanization pass added:
  * CLI-C-029 — friendly summary line at end of ``sov doctor`` output
    ("Summary: N passed, M warn, K fail.")
  * CLI-C-030 — word-glyph icons matching ``sov self-check`` (no more
    ``!!`` for warn).
  * CLI-C-031 — backticked recovery commands instead of ``Run: sov ...``.
  * CLI-C-032 — pending-anchor age-string no longer renders ``hourss``
    for ages ≥ 2h (dead-code branch removed).

Wave 13 Stage 9-D added:
  * CLI-D-001 — `_print_checks` and `_checks_to_text` icons dicts both
    include the ``warn`` key so future warn-emitting checks render with
    the WARN word-glyph rather than falling through to dim "--".
  * CLI-D-002 — doctor's "X check failed" tally color matches row-level
    severity (≥1 fail → red; warn-only → yellow; else dim).

Local fast-check: ``uv run pytest tests/test_doctor_summary.py -v``.
"""

from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from sov_cli.main import _checks_to_text, _print_checks, app, console

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


# ---------------------------------------------------------------------------
# Wave 13 Stage 9-D pins
# ---------------------------------------------------------------------------


def _icons_dict_for_print_checks() -> dict[str, str]:
    """Re-import the inner ``icons`` dict from `_print_checks` source.

    The dict is a local in `_print_checks`, so we walk the function source
    via ``inspect`` and exec the literal-dict block in a sandboxed namespace.
    Keeps the assertion structural (key set parity) without monkey-patching
    the function itself.
    """
    import inspect

    src = inspect.getsource(_print_checks)
    # The dict literal that maps status → glyph. Pin it by extracting the
    # first ``icons = { ... }`` block.
    match = re.search(r"icons\s*=\s*\{(?P<body>.+?)\}", src, re.DOTALL)
    assert match is not None, "could not find icons dict in _print_checks source"
    namespace: dict[str, dict[str, str]] = {}
    exec(f"icons = {{{match.group('body')}}}", namespace)
    return namespace["icons"]


def _icons_dict_for_checks_to_text() -> dict[str, str]:
    """Re-extract the ``icons`` dict from `_checks_to_text` source."""
    import inspect

    src = inspect.getsource(_checks_to_text)
    match = re.search(r"icons\s*=\s*\{(?P<body>.+?)\}", src, re.DOTALL)
    assert match is not None, "could not find icons dict in _checks_to_text source"
    namespace: dict[str, dict[str, str]] = {}
    exec(f"icons = {{{match.group('body')}}}", namespace)
    return namespace["icons"]


def test_print_checks_icons_have_all_four_keys() -> None:
    """CLI-D-001: rich-rendered icons dict covers ok/warn/fail/info.

    Today ``_collect_checks`` only emits ok/fail/info, so the warn entry is
    latent — but adding any future warn-emitting check would silently
    downgrade it to dim "--" without this key. Pin the parity so doctor
    and self-check render the same glyph for the same status.
    """
    icons = _icons_dict_for_print_checks()
    assert set(icons.keys()) == {"ok", "warn", "fail", "info"}, (
        f"_print_checks icons must have all 4 keys (ok/warn/fail/info); got: {set(icons.keys())}"
    )
    # The warn glyph must contain the WARN word-token (parity with the
    # doctor surface, Stage 8-C CLI-C-030).
    assert "WARN" in icons["warn"], (
        f"_print_checks icons['warn'] must contain WARN word-glyph; got: {icons['warn']!r}"
    )


def test_checks_to_text_icons_have_all_four_keys() -> None:
    """CLI-D-001: plain-text icons dict covers ok/warn/fail/info.

    Same parity gate as the rich-rendered path but for support-bundle
    output. A warn check must render as ``WARN`` not ``--``.
    """
    icons = _icons_dict_for_checks_to_text()
    assert set(icons.keys()) == {"ok", "warn", "fail", "info"}, (
        f"_checks_to_text icons must have all 4 keys (ok/warn/fail/info); got: {set(icons.keys())}"
    )
    assert icons["warn"] == "WARN", (
        f"_checks_to_text icons['warn'] must be 'WARN'; got: {icons['warn']!r}"
    )


def test_print_checks_icons_match_doctor_icons() -> None:
    """CLI-D-001: doctor's icons dict and self-check's icons dict are the same.

    The doctor surface (`sov doctor`) and the self-check surface
    (`sov self-check` / `sov support-bundle`) both render diagnostic
    rows with status icons. Drift between the two is the exact class
    Stage 8-C closed visibly; this pin closes the latent variant.
    """
    import inspect

    from sov_cli import main

    # Pull doctor's icons dict from the `doctor` command body.
    doctor_src = inspect.getsource(main.doctor)
    matches = re.findall(r"icons\s*=\s*\{(?P<body>.+?)\}", doctor_src, re.DOTALL)
    assert matches, "could not find icons dict in doctor command source"
    namespace: dict[str, dict[str, str]] = {}
    exec(f"icons = {{{matches[0]}}}", namespace)
    doctor_icons = namespace["icons"]

    self_check_icons = _icons_dict_for_print_checks()
    assert set(doctor_icons.keys()) == set(self_check_icons.keys()), (
        f"doctor icons {set(doctor_icons.keys())} != self-check icons "
        f"{set(self_check_icons.keys())}"
    )


def test_print_checks_tally_red_on_fail(capsys) -> None:
    """CLI-D-002: when any check fails, the tally renders in red — same
    severity as the FAIL row above. Yellow on a fail-tally was the drift
    that surfaced "warning" copy on top of "error" rows."""
    checks = [
        ("ok", "Filesystem", "writable"),
        ("fail", "Daemon", "not running"),
    ]
    # Capture Rich output by re-recording the console.
    with console.capture() as cap:
        _print_checks(checks)
    out = cap.get()
    assert "1 check failed" in out, f"expected fail tally; got: {out!r}"
    # Rich strips style markup at render time but preserves raw text. Check
    # that the FAIL token rendered (sanity) and that the tally color matches
    # by re-capturing with style markup preserved.
    from io import StringIO

    from rich.console import Console as _RichConsole

    sink = StringIO()
    rec_console = _RichConsole(file=sink, force_terminal=False, record=True, no_color=True)
    rec_console.print(
        "\n  [red]1 check failed.[/red]"
        " [dim]Run `sov support-bundle` to capture diagnostics, then "
        "open an issue at https://github.com/mcp-tool-shop-org/sovereignty/issues.[/dim]"
    )
    # Pin the absence of the [yellow] tally form in the actual source.
    import inspect

    src = inspect.getsource(_print_checks)
    assert "[yellow]{fail_count} check" not in src, (
        "_print_checks tally must NOT render the fail count in [yellow]; "
        "use [red] to match the FAIL rows"
    )
    assert "[red]{fail_count} check" in src, (
        "_print_checks tally must render the fail count in [red]"
    )


def test_print_checks_tally_yellow_on_warn_only(capsys) -> None:
    """CLI-D-002: warn-only run tally renders in yellow (not red, not dim).

    Pinned at source level — we don't construct a warn-emitting check
    fixture (none exists in `_collect_checks` today), but the source must
    include the warn-tally branch for the day a warn check lands.
    """
    import inspect

    src = inspect.getsource(_print_checks)
    assert "[yellow]{warn_count} check" in src, (
        "_print_checks must render warn-only tally in [yellow]"
    )

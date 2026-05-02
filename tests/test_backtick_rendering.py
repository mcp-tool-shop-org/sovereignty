"""Pin: backticked-command render transform (CLI-D-004, Wave 13 Stage 9-D).

Pin B (`tests/test_error_hints_have_commands.py`) requires every error
factory's ``hint`` to contain ≥2 backticks (a load-bearing AST contract).
But Rich's plain ``Console`` doesn't auto-style markdown backticks, so
the literal `` ` `` characters previously surfaced in the rendered
output as small grey punctuation noise around the command.

Stage 9-D adds a presentation-layer transform that converts
``\\`cmd\\``` → ``[cyan]cmd[/cyan]`` in the print path. Pin B's contract
still sees raw backticks at AST-walk time; the operator sees a styled
command. Both invariants hold.

Local fast-check: ``uv run pytest tests/test_backtick_rendering.py -v``.
"""

from __future__ import annotations

from sov_cli.main import _render_backticks


def test_render_backticks_transforms_single_command() -> None:
    """Single backticked command → [cyan]...[/cyan]."""
    assert _render_backticks("Run `sov new`.") == "Run [cyan]sov new[/cyan]."


def test_render_backticks_transforms_multiple_commands() -> None:
    """Multiple backticked commands all transform; non-backticked text unchanged."""
    src = "Try `sov tutorial` or `sov play campfire_v1` to start."
    expected = "Try [cyan]sov tutorial[/cyan] or [cyan]sov play campfire_v1[/cyan] to start."
    assert _render_backticks(src) == expected


def test_render_backticks_preserves_text_without_backticks() -> None:
    """Plain prose passes through unchanged."""
    src = "No saved games on this workspace."
    assert _render_backticks(src) == src


def test_render_backticks_preserves_pin_b_ast_contract() -> None:
    """The transform is render-layer only — the source error factory still
    emits raw backticks (Pin B's AST walk asserts >=2 backticks per hint).
    This test verifies the transform doesn't mutate factory hints in place.
    """
    from sov_cli import errors

    err = errors.no_game_error()
    raw_hint = err.hint
    assert raw_hint is not None
    assert raw_hint.count("`") >= 2, "Pin B contract: hint must contain >= 2 backticks"

    # The transform produces a new string; the factory's hint is untouched.
    rendered = _render_backticks(raw_hint)
    assert "[cyan]" in rendered, "transform must convert backticked tokens"
    assert err.hint == raw_hint, "factory hint must not be mutated by render transform"


def test_render_backticks_handles_empty_string() -> None:
    """Empty input is handled gracefully (no transform, no exception)."""
    assert _render_backticks("") == ""


def test_render_backticks_handles_command_with_args() -> None:
    """Backticked commands with flags and args (the common case) transform."""
    src = "Try `sov anchor --checkpoint` to flush mid-game."
    expected = "Try [cyan]sov anchor --checkpoint[/cyan] to flush mid-game."
    assert _render_backticks(src) == expected


def test_render_backticks_non_greedy_match() -> None:
    """Adjacent backticked tokens render as separate spans, not one big span."""
    src = "Either `cmd-a` or `cmd-b`."
    expected = "Either [cyan]cmd-a[/cyan] or [cyan]cmd-b[/cyan]."
    assert _render_backticks(src) == expected

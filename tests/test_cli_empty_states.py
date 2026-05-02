"""Pin: canonical CLI empty-state shape (CLI-D-003, Wave 13 Stage 9-D).

Stage 8-C named the recovery commands; Stage 9-D normalizes the visual
treatment so seven empty-state surfaces share one shape:

    [dim]◯ <headline>[/dim]
    [yellow]<recovery hint>[/yellow]

The dim glyph + headline is the "nothing here yet" marker; the yellow
recovery hint names a concrete next command. Yellow is reserved for the
recovery-hint line so [yellow] alone is no longer overloaded into the
headline (`sov season-postcard` previously rendered the headline in
yellow which read as a warning).

Sites covered:
  * `sov games`               — line ~4322
  * `sov treaty list`         — line ~2545
  * `sov recap`               — line ~3160
  * `sov season-postcard`     — line ~3055 (no SEASON_FILE)
  * `sov season-postcard`     — line ~3066 (no games yet)
  * `sov anchor` (no pending) — line ~1929
  * `sov anchor` (no flush)   — line ~2050
  * `sov daemon status` none  — line ~4775

Local fast-check: ``uv run pytest tests/test_cli_empty_states.py -v``.
"""

from __future__ import annotations

import inspect
import re

from sov_cli import main


def test_sov_games_empty_state_has_canonical_shape() -> None:
    """`sov games` empty layout uses the canonical [dim]◯ ...[/dim] shape."""
    src = inspect.getsource(main.games_cmd)
    assert "[dim]◯" in src, (
        f"`sov games` empty state must use canonical [dim]◯ ...[/dim] shape; "
        f"source did not contain '[dim]◯': {src[:600]!r}"
    )
    assert "No saved games" in src, "expected 'No saved games' headline"
    assert "[yellow]" in src, "expected yellow recovery hint"


def test_sov_treaty_list_empty_state_has_canonical_shape() -> None:
    """`sov treaty list` empty uses the canonical shape."""
    src = inspect.getsource(main.treaty)
    assert "[dim]◯" in src, (
        "`sov treaty list` empty state must use canonical [dim]◯ ...[/dim] shape"
    )
    assert "no treaties" in src
    # Yellow recovery hint with `sov treaty make` example.
    assert "[yellow]Try `sov treaty make" in src


def test_sov_recap_empty_state_has_canonical_shape() -> None:
    """`sov recap` empty uses the canonical shape."""
    src = inspect.getsource(main.recap)
    assert "[dim]◯ Nothing has happened yet.[/dim]" in src
    assert "[yellow]Run `sov turn`" in src


def test_sov_season_postcard_no_season_uses_canonical_shape() -> None:
    """`sov season-postcard` no-SEASON_FILE uses the canonical shape.

    Previously the headline was [yellow] which conflated 'nothing here yet'
    with 'warning'. Stage 9-D demotes the headline to dim and reserves
    yellow for the recovery hint.
    """
    src = inspect.getsource(main.season_postcard)
    assert "[dim]◯ No season yet.[/dim]" in src
    assert "[yellow]Finish a game with `sov game-end`" in src


def test_sov_season_postcard_no_games_has_recovery_hint() -> None:
    """`sov season-postcard` no-games path now includes a recovery hint.

    Previously this surface emitted only the [yellow] headline with no
    recovery action — the operator was left without a concrete next step.
    """
    src = inspect.getsource(main.season_postcard)
    assert "[dim]◯ No games recorded yet.[/dim]" in src
    # Recovery hint follows the headline.
    assert "[yellow]Finish a game with `sov game-end` to populate the season.[/yellow]" in src


def test_sov_anchor_no_pending_uses_canonical_shape() -> None:
    """`sov anchor` no-pending paths use the canonical shape.

    Two paths today (line ~1929 early-return and line ~2050 idempotent
    no-op). Both must surface the same [dim]◯ headline + [yellow] hint.
    """
    src = inspect.getsource(main.anchor)
    # Both paths render the dim glyph + No pending.
    occurrences = src.count("[dim]◯ No pending anchors")
    assert occurrences >= 2, (
        f"`sov anchor` must use canonical empty-state shape on both no-pending "
        f"paths; got {occurrences} occurrence(s) of '[dim]◯ No pending anchors'"
    )
    # Both paths surface the same [yellow] recovery hint pointing at end-round.
    yellow_hint_count = src.count("[yellow]Run `sov end-round`")
    assert yellow_hint_count >= 2, (
        f"`sov anchor` must surface the same yellow recovery hint on both paths; "
        f"got {yellow_hint_count}"
    )


def test_sov_daemon_status_none_uses_canonical_shape() -> None:
    """`sov daemon status` no-daemon uses the canonical shape."""
    src = inspect.getsource(main)
    # `sov daemon status` is a sub-command; grep the module source to keep
    # the test independent of any internal helper layout.
    assert "[dim]◯ daemon: none[/dim]" in src
    assert "[yellow]Start one with `sov daemon start`.[/yellow]" in src


def test_canonical_empty_state_regex_matches_all_seven_sites() -> None:
    """Mechanical: the canonical regex should match the dim-glyph headline at
    every named empty-state site. The shape is one regex, applied uniformly."""
    src = inspect.getsource(main)
    canonical = re.compile(r"\[dim\]◯ [^[]+\[/dim\]")
    matches = canonical.findall(src)
    # 8 expected sites: games, treaty list, recap, postcard×2, anchor×2,
    # daemon status. (See module docstring for the inventory.)
    assert len(matches) >= 8, (
        f"expected ≥8 canonical empty-state headlines; got {len(matches)}: {matches!r}"
    )

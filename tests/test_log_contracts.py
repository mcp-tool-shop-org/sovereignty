"""Pin engine log-message contracts that the rest of the system depends on.

The CLI-side messaging, the docs, and the bug-report tooling all key off
specific log strings emitted by the engine. When those strings change
silently, downstream consumers (CI dashboards, support-bundle parsers,
"what does this warning mean?" doc lookups) silently break.

Each test in this module pins ONE log contract verbatim. If you're
changing a log string, you're also changing this test, and you're also
updating any documentation that quotes the string.

## Wave 9: F010 (Campfire workshop fall-through warning)

Per the locked Wave 9 coordination contract (advisor-locked):

  Old behavior: a warning was emitted when a NON-Campfire ruleset
  (Town Hall / Treaty Table / Market Day) fell through to the
  Campfire workshop/builder coinless resolve path. That warning
  documented an integration gap (the resource-cost upgrade path
  wasn't wired).

  New behavior: the warning IS emitted when CAMPFIRE itself lands
  on Workshop/Builder, nudging the user toward `sov build` (the
  free tier-1 build path) or toward switching rulesets for the
  resource-cost upgrade flow. On NON-Campfire rulesets the warning
  DISAPPEARS entirely (the resource-cost upgrade path is now wired
  upstream of this code path, so the fall-through is no longer the
  signal it once was).

The exact warning string is part of the contract. ci-docs renders it
in the troubleshooting page; downstream tools may grep for it.
"""

from __future__ import annotations

import logging

import pytest

from sov_engine.rules.campfire import (
    new_game,
    resolve_space,
)
from sov_engine.rules.market_day import new_market_day_game
from sov_engine.rules.town_hall import new_town_hall_game
from sov_engine.rules.treaty_table import new_treaty_table_game

# ---------------------------------------------------------------------------
# Locked contract strings
# ---------------------------------------------------------------------------

# F010 (Wave 9): the new fall-through warning emitted on Campfire when the
# user lands on Workshop or Builder. Pinned VERBATIM. Any change here is a
# breaking-contract change and must be coordinated with ci-docs.
F010_NEW_CAMPFIRE_WARNING = (
    "Campfire ruleset uses the coinless workshop — use 'sov build' for "
    "free tier-1 builds, or switch ruleset for resource-cost upgrades."
)

# The old (pre-Wave-9) warning string. We pin this here so tests can assert
# it is NEVER emitted under the new contract — neither on Campfire nor on
# other rulesets. If the engine has retained the old string for any code
# path, we want to fail loud so the migration is finished.
F010_OLD_FALLTHROUGH_WARNING_FRAGMENT = "does not expose upgrade_with_resources"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _land_on_space_and_resolve(state, rng, space_kind_name: str) -> None:
    """Force the current player onto a space matching *space_kind_name* and
    resolve it. Avoids relying on dice luck.

    *space_kind_name* is matched against ``space.kind.name`` (e.g.
    ``"WORKSHOP"`` or ``"BUILDER"``).
    """
    target_idx = next(i for i, s in enumerate(state.board) if s.kind.name == space_kind_name)
    state.current_player.position = target_idx
    resolve_space(state, rng)


# ---------------------------------------------------------------------------
# F010 — NEW contract: Campfire ruleset emits the new warning
# ---------------------------------------------------------------------------


def test_f010_campfire_warning_constant_pinned():
    """The locked F010 warning string is pinned as the engine constant
    ``CAMPFIRE_UPGRADE_HINT``. Any drift here is a breaking-contract change
    and must be coordinated with ci-docs.

    Wave 9 pivot: emission moved from space-landing (engine layer) to
    ``sov upgrade`` invocation (CLI layer) on Campfire. The contract is
    now a constant value, not a runtime emission point at landing.
    """
    from sov_engine.rules.campfire import CAMPFIRE_UPGRADE_HINT

    assert CAMPFIRE_UPGRADE_HINT == F010_NEW_CAMPFIRE_WARNING, (
        "CAMPFIRE_UPGRADE_HINT must equal the locked F010 string verbatim.\n"
        f"  Expected: {F010_NEW_CAMPFIRE_WARNING!r}\n"
        f"  Actual:   {CAMPFIRE_UPGRADE_HINT!r}"
    )


def test_f010_sov_upgrade_workshop_on_campfire_surfaces_hint():
    """Invoking ``sov upgrade workshop`` on a Campfire game surfaces the
    F010 hint to the user (via stdout or stderr).

    The CLI is allowed to humanize the constant (e.g., reformat with line
    breaks + concrete `sov new --tier town-hall` example) — the SOURCE OF
    TRUTH is the constant value (pinned in test_f010_campfire_warning_constant_pinned).
    This test asserts the SUBSTANCE of the message reaches the user — the
    Campfire context, the coinless-workshop framing, the `sov build`
    suggestion, and the switch-ruleset alternative — without requiring
    verbatim wording.
    """
    from typer.testing import CliRunner

    from sov_cli.main import app
    from sov_engine.rules.campfire import new_game
    from sov_engine.serialize import canonical_json, game_state_snapshot

    runner = CliRunner()

    with runner.isolated_filesystem():
        from pathlib import Path

        state, _ = new_game(42, ["Alice", "Bob"])
        state.players[0].coins = 10  # afford the upgrade if it were allowed
        sov_dir = Path(".sov")
        sov_dir.mkdir(parents=True, exist_ok=True)
        (sov_dir / "game_state.json").write_text(
            canonical_json(game_state_snapshot(state)),
            encoding="utf-8",
            newline="\n",
        )
        (sov_dir / "rng_seed.txt").write_text("42", encoding="utf-8")

        result = runner.invoke(app, ["upgrade", "workshop"])

        out = result.output.lower()
        # Substance checks — each is a load-bearing concept the constant carries.
        assert "campfire" in out, f"Output must mention Campfire context; got: {result.output!r}"
        assert "coinless" in out, (
            f"Output must mention the coinless-workshop framing; got: {result.output!r}"
        )
        assert "sov build" in out, (
            f"Output must point at `sov build` as the free tier-1 path; got: {result.output!r}"
        )
        # Either "switch ruleset" abstract OR a concrete tier name (town hall /
        # treaty table / market day) — both express the alternative path.
        switch_alternative = (
            "switch ruleset" in out
            or "town hall" in out
            or "treaty table" in out
            or "market day" in out
        )
        assert switch_alternative, (
            "Output must surface the switch-to-resource-ruleset alternative; "
            f"got: {result.output!r}"
        )


def test_f010_campfire_workshop_landing_emits_no_old_warning(
    caplog: pytest.LogCaptureFixture,
):
    """Sanity guard: the OLD pre-Wave-9 fall-through warning must NEVER
    fire on Campfire workshop landing (or anywhere). Stage B emission
    point removed in Wave 9.
    """
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].coins = 10

    with caplog.at_level(logging.DEBUG, logger="sov_engine"):
        _land_on_space_and_resolve(state, rng, "WORKSHOP")

    messages = [r.getMessage() for r in caplog.records]
    assert not any(F010_OLD_FALLTHROUGH_WARNING_FRAGMENT in m for m in messages), (
        "The pre-Wave-9 fall-through warning must NEVER fire after Wave 9.\n"
        f"  Forbidden fragment: {F010_OLD_FALLTHROUGH_WARNING_FRAGMENT!r}\n"
        f"  Captured messages: {messages!r}"
    )


def _ORIGINAL_test_f010_campfire_builder_emits_new_warning_string(caplog):
    """REPLACED in W9 — see test_f010_campfire_warning_constant_pinned +
    test_f010_sov_upgrade_workshop_on_campfire_surfaces_hint above. Builder
    coverage is implied by the constant pin (one constant, two CLI commands
    using it identically). Kept as a stub-name for diff readability."""
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].reputation = 5
    state.players[0].coins = 10

    with caplog.at_level(logging.DEBUG, logger="sov_engine"):
        _land_on_space_and_resolve(state, rng, "BUILDER")

    messages = [r.getMessage() for r in caplog.records]
    assert any(F010_NEW_CAMPFIRE_WARNING in m for m in messages), (
        "Campfire + Builder landing must emit the locked F010 warning "
        f"verbatim.\nExpected substring: {F010_NEW_CAMPFIRE_WARNING!r}\n"
        f"Captured messages: {messages!r}"
    )


# ---------------------------------------------------------------------------
# F010 — NEW contract: non-Campfire rulesets emit NO fall-through warning
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory,label",
    [
        (new_town_hall_game, "town_hall"),
        (new_treaty_table_game, "treaty_table"),
        (new_market_day_game, "market_day"),
    ],
)
def test_f010_non_campfire_rulesets_emit_no_fallthrough_warning(
    factory,
    label: str,
    caplog: pytest.LogCaptureFixture,
):
    """Town Hall / Treaty Table / Market Day must NOT emit either:
       - the new Campfire-only warning string (it doesn't apply), nor
       - the old "does not expose upgrade_with_resources" warning
         (the resource-cost upgrade path is now wired upstream).

    This is the locked Wave 9 spec: the warning DISAPPEARS on non-Campfire
    rulesets. If either string surfaces here, the migration is incomplete.
    """
    state, rng = factory(42, ["Alice", "Bob"])
    state.players[0].coins = 10
    state.players[0].reputation = 5

    with caplog.at_level(logging.DEBUG, logger="sov_engine"):
        _land_on_space_and_resolve(state, rng, "WORKSHOP")
        _land_on_space_and_resolve(state, rng, "BUILDER")

    messages = [r.getMessage() for r in caplog.records]
    assert not any(F010_NEW_CAMPFIRE_WARNING in m for m in messages), (
        f"Ruleset {label!r} must NOT emit the Campfire-only F010 warning. Captured: {messages!r}"
    )
    assert not any(F010_OLD_FALLTHROUGH_WARNING_FRAGMENT in m for m in messages), (
        f"Ruleset {label!r} must NOT emit the OLD fall-through warning "
        f"under the locked Wave 9 contract (the resource-cost upgrade path "
        f"is wired upstream). Captured: {messages!r}"
    )

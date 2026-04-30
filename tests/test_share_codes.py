"""Parametrized fuzz tests for ``_parse_share_code``.

Closes Stage A LOW (engine F-009): the parser previously had a "silent
downgrade to Campfire" failure mode where unknown tier/recipe values would
parse as a valid dict pointing at Campfire defaults instead of failing
loud. That made it impossible for a player to tell whether their share
code was actually being honored or had been silently rewritten.

The contract these tests pin:

  * Valid codes (every tier x every recipe) parse to a dict with the right
    fields.
  * Malformed codes (wrong delimiter count, missing prefix, bad seed,
    empty fields) return an error STRING (not a dict).
  * Unknown tier or unknown recipe MUST surface as either:
      (a) a fail-loud error string, OR
      (b) a parsed dict that preserves the unknown value VERBATIM
          (so the caller can reject it downstream — no silent
          rewrite to "campfire").

If today's parser still silently downgrades, the tests document the
current behavior with a TODO so the next tightening pass has a clear
hand-off. See the ``_PARSER_REWRITES_UNKNOWN_TIERS`` block below.
"""

from __future__ import annotations

import pytest

from sov_cli.main import _build_share_code, _parse_share_code

# ---------------------------------------------------------------------------
# Tier x recipe matrix — every supported combination round-trips
# ---------------------------------------------------------------------------

_KNOWN_TIERS = ["campfire", "market-day", "town-hall", "treaty-table"]
_KNOWN_RECIPES = ["cozy", "spicy", "market", "promise", ""]


@pytest.mark.parametrize("tier", _KNOWN_TIERS)
@pytest.mark.parametrize("recipe", _KNOWN_RECIPES)
def test_share_code_roundtrip_every_known_tier_recipe(tier: str, recipe: str):
    """Every (tier, recipe) build->parse round-trip preserves all fields."""
    code = _build_share_code("custom", tier, recipe, 42)
    parsed = _parse_share_code(code)
    assert isinstance(parsed, dict), (
        f"Round-trip parse for tier={tier!r} recipe={recipe!r} must return "
        f"a dict; got error string: {parsed!r}"
    )
    assert parsed["slug"] == "custom"
    assert parsed["tier"] == tier, (
        f"Round-trip dropped/rewrote tier. Wrote {tier!r}; got {parsed['tier']!r}"
    )
    assert parsed["recipe"] == recipe, (
        f"Round-trip dropped/rewrote recipe. Wrote {recipe!r}; got {parsed['recipe']!r}"
    )
    assert parsed["seed"] == "42"


# ---------------------------------------------------------------------------
# Malformed codes — must fail loud (return error string)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_code,reason",
    [
        ("", "empty string"),
        ("NOT|a|valid|code|s1", "missing SOV prefix"),
        ("SOV|slug|tier|recipe", "wrong field count (4 instead of 5)"),
        ("SOV|slug|tier|recipe|s1|extra", "wrong field count (6 instead of 5)"),
        ("SOV|slug|tier|recipe|bad", "seed missing 's' prefix"),
        ("SOV|slug|tier|recipe|s", "seed missing digits after 's'"),
        ("SOV|slug|tier|recipe|sNOTNUMERIC", "seed not numeric"),
        ("SOV|slug|tier|recipe|42", "seed missing 's' prefix entirely"),
        ("just-a-string", "no delimiters at all"),
    ],
)
def test_share_code_malformed_fails_loud(bad_code: str, reason: str):
    """Malformed share codes must return an error string, NEVER a dict.

    A silent dict-with-defaults here would be a security/UX bug: the user
    pastes a typo'd code and the game starts under different rules than
    the one they shared with friends.
    """
    result = _parse_share_code(bad_code)
    assert isinstance(result, str), (
        f"Malformed code (reason: {reason}) must return an error STRING; "
        f"got dict instead: {result!r}. Input was {bad_code!r}."
    )


# ---------------------------------------------------------------------------
# Unknown tier / recipe — DO NOT silently downgrade to Campfire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unknown_tier",
    [
        "lunar-base",  # plausibly a future tier name
        "tier-9000",  # obvious garbage
        "CAMPFIRE",  # case-sensitivity check (current tiers are lowercase)
        "campfire_v1",  # ruleset id leaked into the tier slot
    ],
)
def test_unknown_tier_does_not_silently_downgrade(unknown_tier: str):
    """Unknown tier values MUST NOT silently parse as ``"campfire"``.

    Stage A engine F-009 documented that today the CLI's tier dispatch
    (``sov new``) silently falls back to Campfire on unknown tiers; the
    parser itself preserves the value, but the dispatcher rewrites it.

    This test pins the PARSER's contract: it preserves the verbatim
    unknown value so the caller can reject it. If the parser ever starts
    rewriting unknown tiers to ``"campfire"``, this test fails loud.
    """
    code = f"SOV|custom|{unknown_tier}|cozy|s42"
    parsed = _parse_share_code(code)
    if isinstance(parsed, str):
        # Parser chose to fail loud — that's also acceptable.
        return
    # Parser returned a dict — the unknown tier MUST be preserved verbatim,
    # NOT silently rewritten to "campfire".
    assert parsed["tier"] == unknown_tier, (
        f"Parser silently rewrote unknown tier {unknown_tier!r} to "
        f"{parsed['tier']!r}. This is the F-009 silent-downgrade bug. "
        "The parser must preserve the unknown value so the caller can "
        "reject it (or the parser must itself fail loud)."
    )
    # TODO Stage B-2: tighten — once the dispatcher (sov_cli.main.new)
    # rejects unknown tiers, change this test to assert the parser ALSO
    # returns an error string, so the bad value is caught earlier.


@pytest.mark.parametrize(
    "unknown_recipe",
    [
        "thunderdome",
        "RECIPE-9000",
        "PROMISE",  # case-sensitivity check
    ],
)
def test_unknown_recipe_does_not_silently_downgrade(unknown_recipe: str):
    """Unknown recipe values MUST NOT silently parse as ``""`` (empty).

    Same shape as the unknown-tier test: parser may either preserve the
    verbatim value or fail loud. It must NEVER silently drop the value
    and substitute the empty/default recipe.
    """
    code = f"SOV|custom|campfire|{unknown_recipe}|s42"
    parsed = _parse_share_code(code)
    if isinstance(parsed, str):
        return
    assert parsed["recipe"] == unknown_recipe, (
        f"Parser silently rewrote unknown recipe {unknown_recipe!r} to "
        f"{parsed['recipe']!r}. This is the F-009 silent-downgrade bug."
    )
    # TODO Stage B-2: tighten when dispatcher rejects unknown recipes.


# ---------------------------------------------------------------------------
# Empty-field guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,what_is_empty",
    [
        ("SOV|||cozy|s42", "slug AND tier"),
        ("SOV|slug|||s42", "tier AND recipe"),
    ],
)
def test_empty_required_fields_are_visible(code: str, what_is_empty: str):
    """Empty required fields should not silently disappear.

    The parser is forgiving on the recipe field (treats ``"-"`` as empty
    by design — that's the documented "no recipe" sentinel) but a fully
    empty field for slug or tier is suspicious and the caller should be
    able to detect it.

    Either the parser fails loud, OR it preserves the empty string so the
    dispatcher can reject it. The bug we guard against is the parser
    silently substituting a default in place of an empty field.
    """
    parsed = _parse_share_code(code)
    if isinstance(parsed, str):
        return
    # Dict path: at least one of slug/tier should be the empty string
    # (preserved verbatim), never silently rewritten to a non-empty default.
    assert parsed["slug"] == "" or parsed["tier"] == "", (
        f"Parser silently filled in an empty required field "
        f"({what_is_empty}) with a default. Got: {parsed!r}"
    )

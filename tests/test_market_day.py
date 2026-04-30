"""Tests for Market Day (Tier 2) — fixed-price Market Board."""

from sov_engine.models import RESOURCE_NAMES, CardType, EventCard, MarketBoard
from sov_engine.rng import GameRng
from sov_engine.rules.campfire import resolve_event
from sov_engine.rules.market_day import (
    market_buy,
    market_sell,
    market_status,
    new_market_day_game,
    upgrade_with_resources,
)


def test_new_market_day_game_setup():
    state, rng = new_market_day_game(42, ["Alice", "Bob"])
    assert len(state.players) == 2
    assert state.config.ruleset == "market_day_v1"
    assert state.market_board is not None
    assert state.market_board.fixed_prices is True
    # Huge supply (999) — effectively infinite
    for r in RESOURCE_NAMES:
        assert state.market_board.supply[r] == 999
    # Players start with empty resources
    for p in state.players:
        assert p.resources == {"food": 0, "wood": 0, "tools": 0}


def test_fixed_price_board():
    mb = MarketBoard.create(2, fixed=True)
    assert mb.fixed_prices is True
    assert mb.supply["food"] == 999
    # Price is always base (2), regardless of supply
    for r in RESOURCE_NAMES:
        assert mb.price(r) == 2


def test_fixed_prices_ignore_scarcity():
    mb = MarketBoard.create(2, fixed=True)
    mb.supply["food"] = 2  # would trigger scarcity in Town Hall
    assert mb.price("food") == 2  # still 2 — fixed mode
    mb.supply["food"] = 0
    assert mb.price("food") == 2  # price unchanged even at 0


def test_fixed_prices_shift_is_noop():
    mb = MarketBoard.create(2, fixed=True)
    mb.shift_price("wood", 5)
    assert mb.price("wood") == 2  # no change
    assert mb.price_shifts["wood"] == 0  # shift wasn't recorded


def test_fixed_sell_price():
    mb = MarketBoard.create(2, fixed=True)
    sell_price = mb.sell("food")
    assert sell_price == 1  # base (2) - 1 = 1


def test_market_buy_fixed():
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 10
    old_supply = state.market_board.supply["food"]

    msg = market_buy(state, alice, "food")
    assert alice.resources["food"] == 1
    assert alice.coins == 8  # paid 2 (fixed price)
    assert state.market_board.supply["food"] == old_supply - 1
    assert "buys 1 food" in msg


def test_market_sell_fixed():
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.resources["wood"] = 2
    old_coins = alice.coins

    msg = market_sell(state, alice, "wood")
    assert alice.resources["wood"] == 1
    assert alice.coins == old_coins + 1  # earned 1 (sell price)
    assert "sells 1 wood" in msg


def test_market_status_fixed():
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    info = market_status(state)
    assert "food" in info
    assert info["food"]["price"] == 2
    assert info["food"]["supply"] == 999


def test_upgrade_workshop_fixed():
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 5
    alice.resources["wood"] = 2

    upgrade_with_resources(state, alice, "workshop")
    assert alice.upgrades == 1
    assert alice.coins == 3  # paid 2
    assert alice.resources["wood"] == 1  # paid 1 wood


def test_upgrade_builder_fixed():
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 5
    alice.reputation = 5
    alice.resources["tools"] = 1

    upgrade_with_resources(state, alice, "builder")
    assert alice.upgrades == 1
    assert alice.coins == 2  # paid 3
    assert alice.resources["tools"] == 0  # paid 1 tools


def test_market_event_noop_in_market_day():
    """Market-shift events should print flavor but not change prices."""
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    rng = GameRng(42)
    card = EventCard(
        id="evt_21",
        name="Bumper Harvest",
        card_type=CardType.EVENT,
        description="",
        effect_id="market_food_down",
    )
    resolve_event(state, card, rng)
    # Price unchanged — fixed mode ignores shifts
    assert state.market_board.price("food") == 2


def test_market_event_wood_up_noop():
    """Logging Ban should not change wood price in Market Day."""
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    rng = GameRng(42)
    card = EventCard(
        id="evt_22",
        name="Logging Ban",
        card_type=CardType.EVENT,
        description="",
        effect_id="market_wood_up",
    )
    resolve_event(state, card, rng)
    assert state.market_board.price("wood") == 2


def test_market_event_all_down_noop():
    """Good Rains should not shift prices in Market Day."""
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    rng = GameRng(42)
    card = EventCard(
        id="evt_28",
        name="Good Rains",
        card_type=CardType.EVENT,
        description="",
        effect_id="market_all_down",
    )
    resolve_event(state, card, rng)
    for r in RESOURCE_NAMES:
        assert state.market_board.price(r) == 2


def test_market_event_restock_still_works():
    """Trade Caravan adds supply even in Market Day (harmless but correct)."""
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    rng = GameRng(42)
    old_food = state.market_board.supply["food"]
    card = EventCard(
        id="evt_24",
        name="Trade Caravan",
        card_type=CardType.EVENT,
        description="",
        effect_id="market_restock",
    )
    resolve_event(state, card, rng)
    assert state.market_board.supply["food"] == old_food + 2


def test_market_event_feast_still_works():
    """Feast Day still removes food from players in Market Day."""
    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    rng = GameRng(42)
    state.players[0].resources["food"] = 3
    state.players[1].resources["food"] = 0
    card = EventCard(
        id="evt_26",
        name="Feast Day",
        card_type=CardType.EVENT,
        description="",
        effect_id="market_feast",
    )
    resolve_event(state, card, rng)
    assert state.players[0].resources["food"] == 2
    assert state.players[1].resources["food"] == 0


def test_dynamic_board_unchanged():
    """Verify Town Hall dynamic board still works (no regression)."""
    mb = MarketBoard.create(2, fixed=False)
    assert mb.fixed_prices is False
    assert mb.supply["food"] == 8  # normal supply
    mb.supply["food"] = 2
    assert mb.price("food") == 3  # scarcity kicks in
    mb.shift_price("wood", 1)
    assert mb.price("wood") == 3  # shift applied


def test_serialization_roundtrip():
    """Market Day state should serialize and deserialize correctly."""
    import json

    from sov_engine.serialize import canonical_json, game_state_snapshot

    state, _ = new_market_day_game(42, ["Alice", "Bob"])
    state.players[0].resources["food"] = 2

    snapshot = game_state_snapshot(state)
    json_str = canonical_json(snapshot)
    data = json.loads(json_str)

    # Check player resources
    assert data["players"][0]["resources"]["food"] == 2

    # Check market board with fixed_prices flag
    assert "market_board" in data
    assert data["market_board"]["fixed_prices"] is True
    assert data["market_board"]["supply"]["food"] == 999


def test_supply_pool_fixed_vs_dynamic():
    """Fixed boards get 999, dynamic boards scale with player count."""
    fixed = MarketBoard.create(2, fixed=True)
    dynamic = MarketBoard.create(2, fixed=False)
    assert fixed.supply["food"] == 999
    assert dynamic.supply["food"] == 8

"""Tests for Town Hall (Tier 2) mechanics."""

from sov_engine.models import RESOURCE_NAMES, MarketBoard
from sov_engine.rules.town_hall import (
    market_buy,
    market_sell,
    market_status,
    new_town_hall_game,
    upgrade_with_resources,
)


def test_new_town_hall_game_setup():
    state, rng = new_town_hall_game(42, ["Alice", "Bob"])
    assert len(state.players) == 2
    assert state.config.ruleset == "town_hall_v1"
    assert state.market_board is not None
    # 2 players → supply pool of 8
    for r in RESOURCE_NAMES:
        assert state.market_board.supply[r] == 8
    # Players start with empty resources
    for p in state.players:
        assert p.resources == {"food": 0, "wood": 0, "tools": 0}


def test_market_board_pricing_base():
    mb = MarketBoard.create(2)
    # Base price is 2 for all, supply is 8 (> 2), no scarcity
    for r in RESOURCE_NAMES:
        assert mb.price(r) == 2


def test_market_board_scarcity_pricing():
    mb = MarketBoard.create(2)
    mb.supply["food"] = 2  # scarce threshold
    assert mb.price("food") == 3  # base 2 + scarcity 1
    mb.supply["food"] = 1
    assert mb.price("food") == 3  # still scarce
    mb.supply["food"] = 0
    assert mb.price("food") == 3  # price unchanged, but can't buy
    assert mb.can_buy("food") is False


def test_market_board_price_shift():
    mb = MarketBoard.create(2)
    mb.shift_price("wood", 1)
    assert mb.price("wood") == 3  # base 2 + shift 1
    mb.shift_price("wood", -2)
    assert mb.price("wood") == 1  # clamped to min 1
    mb.reset_shifts()
    assert mb.price("wood") == 2  # back to base


def test_market_board_price_cap():
    mb = MarketBoard.create(2)
    mb.shift_price("tools", 5)
    assert mb.price("tools") == 4  # clamped to max 4
    mb.supply["tools"] = 1  # scarcity would add +1 but cap is 4
    assert mb.price("tools") == 4


def test_market_buy():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 10
    old_supply = state.market_board.supply["food"]

    msg = market_buy(state, alice, "food")
    assert alice.resources["food"] == 1
    assert alice.coins == 8  # paid 2 (base price)
    assert state.market_board.supply["food"] == old_supply - 1
    assert "buys 1 food" in msg


def test_market_buy_cant_afford():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 0
    msg = market_buy(state, alice, "food")
    assert "can't afford" in msg
    assert alice.resources["food"] == 0


def test_market_buy_empty_supply():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 10
    state.market_board.supply["wood"] = 0
    msg = market_buy(state, alice, "wood")
    assert "empty" in msg.lower()


def test_market_sell():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.resources["wood"] = 2
    old_supply = state.market_board.supply["wood"]
    old_coins = alice.coins

    msg = market_sell(state, alice, "wood")
    assert alice.resources["wood"] == 1
    assert alice.coins > old_coins  # earned coins
    assert state.market_board.supply["wood"] == old_supply + 1
    assert "sells 1 wood" in msg


def test_market_sell_nothing():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    msg = market_sell(state, alice, "tools")
    assert "has no tools" in msg


def test_market_status():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    info = market_status(state)
    assert "food" in info
    assert "price" in info["food"]
    assert "supply" in info["food"]


def test_upgrade_with_resources_workshop():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 5
    alice.resources["wood"] = 2

    msg = upgrade_with_resources(state, alice, "workshop")
    assert alice.upgrades == 1
    assert alice.coins == 3  # paid 2
    assert alice.resources["wood"] == 1  # paid 1 wood
    assert "upgrades" in msg.lower()


def test_upgrade_with_resources_builder():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 5
    alice.reputation = 5
    alice.resources["tools"] = 1

    msg = upgrade_with_resources(state, alice, "builder")
    assert alice.upgrades == 1
    assert alice.coins == 2  # paid 3
    assert alice.resources["tools"] == 0  # paid 1 tools
    assert "upgrades" in msg.lower()


def test_upgrade_needs_resources():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 5
    alice.resources["wood"] = 0  # no wood

    msg = upgrade_with_resources(state, alice, "workshop")
    assert alice.upgrades == 0
    assert "needs" in msg


def test_upgrade_builder_needs_rep():
    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.coins = 5
    alice.reputation = 2
    alice.resources["tools"] = 1

    msg = upgrade_with_resources(state, alice, "builder")
    assert alice.upgrades == 0
    assert "Rep >= 3" in msg


def test_supply_pool_scales_with_players():
    state2, _ = new_town_hall_game(42, ["A", "B"])
    state3, _ = new_town_hall_game(42, ["A", "B", "C"])
    state4, _ = new_town_hall_game(42, ["A", "B", "C", "D"])

    assert state2.market_board.supply["food"] == 8  # 4 + 2*2
    assert state3.market_board.supply["food"] == 10  # 4 + 3*2
    assert state4.market_board.supply["food"] == 12  # 4 + 4*2


def test_market_event_food_down():
    """Bumper Harvest should shift food price down."""
    from sov_engine.models import CardType, EventCard
    from sov_engine.rng import GameRng
    from sov_engine.rules.campfire import resolve_event

    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    rng = GameRng(42)
    card = EventCard(
        id="evt_21",
        name="Bumper Harvest",
        card_type=CardType.EVENT,
        description="",
        effect_id="market_food_down",
    )
    resolve_event(state, card, rng)
    assert state.market_board.price("food") == 1  # base 2 - 1 shift


def test_market_event_restock():
    """Trade Caravan should add 2 to each supply pool."""
    from sov_engine.models import CardType, EventCard
    from sov_engine.rng import GameRng
    from sov_engine.rules.campfire import resolve_event

    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
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


def test_market_event_fire():
    """Warehouse Fire should remove 2 from each supply pool."""
    from sov_engine.models import CardType, EventCard
    from sov_engine.rng import GameRng
    from sov_engine.rules.campfire import resolve_event

    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    rng = GameRng(42)
    old_food = state.market_board.supply["food"]
    card = EventCard(
        id="evt_25",
        name="Warehouse Fire",
        card_type=CardType.EVENT,
        description="",
        effect_id="market_fire",
    )
    resolve_event(state, card, rng)
    assert state.market_board.supply["food"] == old_food - 2


def test_market_event_feast():
    """Feast Day removes 1 food from each player who has it."""
    from sov_engine.models import CardType, EventCard
    from sov_engine.rng import GameRng
    from sov_engine.rules.campfire import resolve_event

    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
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
    msg = resolve_event(state, card, rng)
    assert state.players[0].resources["food"] == 2
    assert state.players[1].resources["food"] == 0
    assert "Alice" in msg


def test_market_event_all_down():
    """Good Rains should shift all prices down."""
    from sov_engine.models import CardType, EventCard
    from sov_engine.rng import GameRng
    from sov_engine.rules.campfire import resolve_event

    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
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
        assert state.market_board.price(r) == 1  # base 2 - 1


def test_serialization_roundtrip():
    """Town Hall state should serialize and deserialize correctly."""
    import json

    from sov_engine.serialize import canonical_json, game_state_snapshot

    state, _ = new_town_hall_game(42, ["Alice", "Bob"])
    state.players[0].resources["food"] = 2
    state.players[0].resources["wood"] = 1

    snapshot = game_state_snapshot(state)
    json_str = canonical_json(snapshot)
    data = json.loads(json_str)

    # Check player resources are in snapshot
    assert data["players"][0]["resources"]["food"] == 2
    assert data["players"][0]["resources"]["wood"] == 1

    # Check market board is in snapshot
    assert "market_board" in data
    assert data["market_board"]["supply"]["food"] == 8

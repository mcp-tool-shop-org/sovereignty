"""Coverage for the rules engine: Campfire events/spaces plus Town Hall,
Treaty Table, Market Day and small model/RNG gaps.

Every test asserts a concrete outcome (exact coin/rep/resource deltas, returned
message text, raised error, or log entry) rather than merely executing code.
"""

from __future__ import annotations

import random

import pytest

from sov_engine.content import build_event_deck
from sov_engine.models import (
    Deck as ModelDeck,
)
from sov_engine.models import (
    MarketBoard,
    MarketPrices,
    Space,
    SpaceKind,
    Stake,
    Treaty,
    TreatyStatus,
    Voucher,
    WinCondition,
)
from sov_engine.rng import GameRng
from sov_engine.rules import campfire
from sov_engine.rules.campfire import (
    apologize,
    break_promise,
    keep_promise,
    make_promise,
    new_game,
    redeem_voucher,
    resolve_event,
    resolve_help_desk,
    resolve_space,
    roll_and_move,
)
from sov_engine.rules.market_day import new_market_day_game
from sov_engine.rules.town_hall import (
    market_buy,
    market_sell,
    market_status,
    new_town_hall_game,
    upgrade_with_resources,
)
from sov_engine.rules.treaty_table import (
    _can_afford_stake,
    _next_treaty_id,
    _return_stake,
    _transfer_stake,
    check_treaty_deadlines,
    new_treaty_table_game,
    parse_stake,
    treaty_break,
    treaty_keep,
    treaty_list,
    treaty_make,
)

DASH = "—"  # em dash used in some campfire event messages

CARDS = {c.effect_id: c for c in build_event_deck()}  # type: ignore[attr-defined]


def _game(seed: int = 7):  # type: ignore[no-untyped-def]
    state, rng = new_game(seed, ["Alice", "Bob"])
    return state, rng


def _th_game(seed: int = 7):  # type: ignore[no-untyped-def]
    return new_town_hall_game(seed, ["Alice", "Bob"])


class _FixedRoll(GameRng):
    """RNG whose d6 always returns ``value`` (everything else stays seeded)."""

    def __init__(self, value: int) -> None:
        super().__init__(1)
        self.value = value

    def roll_d6(self) -> int:
        return self.value


# ---------------------------------------------------------------------------
# Deck sanity: every card in the shipped event deck has a real handler
# ---------------------------------------------------------------------------


def test_every_event_card_has_a_handler() -> None:
    assert len(CARDS) == 28
    for effect_id, card in CARDS.items():
        state, rng = _th_game()
        msg = resolve_event(state, card, rng)
        assert msg.startswith(f"EVENT: {card.name}"), effect_id
        assert "unknown effect" not in msg, effect_id


def test_unknown_event_effect_reports_its_id() -> None:
    state, rng = _game()
    card = CARDS["windfall"]
    bogus = type(card)(
        id="evt_x",
        name="Mystery",
        card_type=card.card_type,
        description="?",
        effect_id="no_such_effect",
    )
    msg = resolve_event(state, bogus, rng)
    assert msg == "EVENT: Mystery -- unknown effect 'no_such_effect'."
    assert state.players[0].coins == 5  # untouched


# ---------------------------------------------------------------------------
# Message-only events: no state change
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("effect_id", "text"),
    [
        ("supply_delay", "Upgrades cost +1 coin this round."),
        ("festival_of_plenty", "Next 2 Festival landings give +2 Rep."),
        ("drought", "No Market purchases this round."),
        ("community_dinner", "Everyone may donate 1 coin to gain +1 Rep."),
    ],
)
def test_message_only_events_leave_state_untouched(effect_id: str, text: str) -> None:
    state, rng = _game()
    before = [(p.coins, p.reputation) for p in state.players]
    card = CARDS[effect_id]
    msg = resolve_event(state, card, rng)
    assert text in msg
    assert msg.startswith(f"EVENT: {card.name}")
    assert [(p.coins, p.reputation) for p in state.players] == before


def test_supply_delay_uses_description_verbatim() -> None:
    state, rng = _game()
    card = CARDS["supply_delay"]
    assert resolve_event(state, card, rng) == f"EVENT: {card.name} {DASH} {card.description}"


def test_swindle_names_current_player() -> None:
    state, rng = _game()
    state.current_player_index = 1
    msg = resolve_event(state, CARDS["swindle"], rng)
    assert msg == f"EVENT: {CARDS['swindle'].name} -- Bob may force a voucher redemption."


def test_lost_wallet_and_awkward_favor_and_old_friend_name_current_player() -> None:
    state, rng = _game()
    lw = resolve_event(state, CARDS["lost_wallet"], rng)
    assert "Alice can't trade this turn unless someone lends them 1 coin." in lw
    af = resolve_event(state, CARDS["awkward_favor"], rng)
    assert 'Alice asks: "Can someone cover 2 coins? I\'ll pay back 3."' in af
    of = resolve_event(state, CARDS["old_friend"], rng)
    assert "Alice picks a friend. Both gain +1 Rep." in of
    assert (state.players[0].coins, state.players[0].reputation) == (5, 3)


# ---------------------------------------------------------------------------
# Stateful events
# ---------------------------------------------------------------------------


def test_boom_town_gives_everyone_a_coin() -> None:
    state, rng = _game()
    msg = resolve_event(state, CARDS["boom_town"], rng)
    assert [p.coins for p in state.players] == [6, 6]
    assert msg.endswith("everyone gains 1 coin.")


def test_storm_charges_coins_then_reputation() -> None:
    state, rng = _game()
    state.players[1].coins = 0
    msg = resolve_event(state, CARDS["storm"], rng)
    assert state.players[0].coins == 4
    assert state.players[0].reputation == 3
    assert state.players[1].coins == 0
    assert state.players[1].reputation == 2
    assert msg == f"EVENT: Storm {DASH} Alice pays 1 coin; Bob loses 1 Rep."


def test_rumor_costs_current_player_one_rep() -> None:
    state, rng = _game()
    state.current_player_index = 1
    msg = resolve_event(state, CARDS["rumor"], rng)
    assert [p.reputation for p in state.players] == [3, 2]
    assert "Bob loses 1 Rep." in msg


def test_big_order_raises_all_campfire_prices() -> None:
    state, rng = _game()
    before = state.market.as_dict()
    msg = resolve_event(state, CARDS["big_order"], rng)
    assert before == {"food": 1, "wood": 2, "tools": 3}
    assert state.market.as_dict() == {"food": 2, "wood": 3, "tools": 4}
    assert "Market prices +1 this round." in msg


def test_windfall_pays_three_coins() -> None:
    state, rng = _game()
    msg = resolve_event(state, CARDS["windfall"], rng)
    assert state.players[0].coins == 8
    assert state.players[1].coins == 5
    assert "Alice gains 3 coins." in msg


def test_trust_crisis_hits_only_low_rep_players() -> None:
    state, rng = _game()
    state.players[0].reputation = 2
    state.players[1].reputation = 6
    msg = resolve_event(state, CARDS["trust_crisis"], rng)
    assert [p.reputation for p in state.players] == [1, 6]
    assert msg == "EVENT: Trust Crisis -- Alice loses 1 Rep."


def test_trust_crisis_with_nobody_affected() -> None:
    state, rng = _game()
    for p in state.players:
        p.reputation = 5
    msg = resolve_event(state, CARDS["trust_crisis"], rng)
    assert [p.reputation for p in state.players] == [5, 5]
    assert "no one loses 1 Rep." in msg


def test_good_news_rewards_a_helper() -> None:
    state, rng = _game()
    state.players[0].helped_last_round = True
    msg = resolve_event(state, CARDS["good_news"], rng)
    assert state.players[0].coins == 7
    assert "helped someone last round. +2 coins!" in msg


def test_good_news_gives_nothing_to_a_non_helper() -> None:
    state, rng = _game()
    msg = resolve_event(state, CARDS["good_news"], rng)
    assert state.players[0].coins == 5
    assert "didn't help anyone last round. No bonus." in msg


def test_shortcut_trades_rep_for_coins() -> None:
    state, rng = _game()
    msg = resolve_event(state, CARDS["shortcut"], rng)
    assert (state.players[0].coins, state.players[0].reputation) == (8, 2)
    assert "gains 3 coins but loses 1 Rep." in msg


def test_broken_bridge_flags_skip_and_roll_consumes_it() -> None:
    state, rng = _game()
    msg = resolve_event(state, CARDS["broken_bridge"], rng)
    assert state.players[0].skip_next_move is True
    assert "will skip their next move." in msg
    assert roll_and_move(state, rng) == 0
    assert state.players[0].skip_next_move is False
    assert state.players[0].position == 0


def test_harvest_moon_tops_up_the_poorest_player() -> None:
    state, rng = _game()
    state.players[0].coins = 9
    state.players[1].coins = 1
    msg = resolve_event(state, CARDS["harvest_moon"], rng)
    assert [p.coins for p in state.players] == [9, 3]
    assert "Bob has the fewest coins. +2 coins." in msg


@pytest.mark.parametrize(
    ("start_rep", "end_rep", "text"),
    [
        (3, 4, "gains +1 Rep."),
        (7, 8, "gains +1 Rep."),
        (8, 7, "Rep is too high. -1 Rep."),
        (10, 9, "Rep is too high. -1 Rep."),
    ],
)
def test_tall_tale_boundary(start_rep: int, end_rep: int, text: str) -> None:
    state, rng = _game()
    state.players[0].reputation = start_rep
    msg = resolve_event(state, CARDS["tall_tale"], rng)
    assert state.players[0].reputation == end_rep
    assert text in msg


def test_lucky_find_chains_into_the_next_card() -> None:
    state, rng = _game()
    state.event_deck = ModelDeck(draw_pile=[CARDS["windfall"]])
    msg = resolve_event(state, CARDS["lucky_find"], rng)
    assert state.players[0].coins == 8
    assert msg.startswith(f"EVENT: {CARDS['lucky_find'].name} -- draw again! EVENT: ")
    assert "gains 3 coins" in msg
    assert state.event_deck.discard_pile == [CARDS["windfall"]]


def test_lucky_find_with_empty_deck() -> None:
    state, rng = _game()
    state.event_deck = ModelDeck()
    msg = resolve_event(state, CARDS["lucky_find"], rng)
    assert msg == f"EVENT: {CARDS['lucky_find'].name} -- but the deck is empty!"
    assert state.players[0].coins == 5


# ---------------------------------------------------------------------------
# Market-shift events (Town Hall board)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("effect_id", "resource", "shift"),
    [
        ("market_food_down", "food", -1),
        ("market_wood_up", "wood", 1),
        ("market_tools_down", "tools", -1),
        ("market_tools_up", "tools", 1),
    ],
)
def test_single_resource_price_shift_events(effect_id: str, resource: str, shift: int) -> None:
    state, rng = _th_game()
    assert state.market_board is not None
    msg = resolve_event(state, CARDS[effect_id], rng)
    expected = {"food": 0, "wood": 0, "tools": 0}
    expected[resource] = shift
    assert state.market_board.price_shifts == expected
    assert msg.startswith(f"EVENT: {CARDS[effect_id].name} -- ")
    assert f"{resource.capitalize()} price {shift:+d} this round." in msg


def test_market_all_down_shifts_every_price() -> None:
    state, rng = _th_game()
    assert state.market_board is not None
    msg = resolve_event(state, CARDS["market_all_down"], rng)
    assert state.market_board.price_shifts == {"food": -1, "wood": -1, "tools": -1}
    assert msg.endswith("All prices -1 this round.")


def test_market_restock_and_fire_move_supply_by_two() -> None:
    state, rng = _th_game()
    assert state.market_board is not None
    assert state.market_board.supply == {"food": 8, "wood": 8, "tools": 8}
    resolve_event(state, CARDS["market_restock"], rng)
    assert state.market_board.supply == {"food": 10, "wood": 10, "tools": 10}
    msg = resolve_event(state, CARDS["market_fire"], rng)
    assert state.market_board.supply == {"food": 8, "wood": 8, "tools": 8}
    assert msg.endswith("-2 from each supply pool.")


def test_market_fire_never_drives_supply_negative() -> None:
    state, rng = _th_game()
    assert state.market_board is not None
    state.market_board.supply = {"food": 1, "wood": 0, "tools": 5}
    resolve_event(state, CARDS["market_fire"], rng)
    assert state.market_board.supply == {"food": 0, "wood": 0, "tools": 3}


@pytest.mark.parametrize(
    "effect_id",
    [
        "market_food_down",
        "market_wood_up",
        "market_tools_down",
        "market_tools_up",
        "market_restock",
        "market_fire",
        "market_all_down",
    ],
)
def test_market_events_are_harmless_without_a_market_board(effect_id: str) -> None:
    state, rng = _game()  # Campfire: no market board
    assert state.market_board is None
    msg = resolve_event(state, CARDS[effect_id], rng)
    assert msg.startswith(f"EVENT: {CARDS[effect_id].name} -- ")
    assert state.market_board is None
    assert [p.coins for p in state.players] == [5, 5]


def test_market_feast_takes_one_food_from_each_holder() -> None:
    state, rng = _th_game()
    state.players[0].resources["food"] = 2
    msg = resolve_event(state, CARDS["market_feast"], rng)
    assert state.players[0].resources["food"] == 1
    assert state.players[1].resources["food"] == 0
    assert msg.endswith("Alice shared food.")


def test_market_feast_with_no_food_anywhere() -> None:
    state, rng = _th_game()
    msg = resolve_event(state, CARDS["market_feast"], rng)
    assert msg.endswith("nobody shared food.")
    assert all(p.resources["food"] == 0 for p in state.players)


# ---------------------------------------------------------------------------
# roll_and_move
# ---------------------------------------------------------------------------


def test_passing_campfire_pays_one_coin() -> None:
    state, _ = _game()
    state.players[0].position = 14
    roll = roll_and_move(state, _FixedRoll(3))
    assert roll == 3
    assert state.players[0].position == 1
    assert state.players[0].coins == 6
    assert any("passed Campfire, +1 coin" in line for line in state.log)


def test_landing_exactly_on_campfire_does_not_double_pay() -> None:
    state, _ = _game()
    state.players[0].position = 10
    roll_and_move(state, _FixedRoll(6))
    assert state.players[0].position == 0
    assert state.players[0].coins == 5  # the coin comes from resolving the space instead


def test_moving_without_wrapping_pays_nothing() -> None:
    state, _ = _game()
    roll_and_move(state, _FixedRoll(4))
    assert state.players[0].position == 4
    assert state.players[0].coins == 5
    assert "rolled 4, moved to Trade Dock (space 4)" in state.log[-1]


# ---------------------------------------------------------------------------
# resolve_space
# ---------------------------------------------------------------------------


def _at(state, pos: int) -> None:  # type: ignore[no-untyped-def]
    state.players[0].position = pos


@pytest.mark.parametrize(
    ("pos", "coins_delta", "text"),
    [
        (0, 1, "rests at Campfire. +1 coin."),
        (8, 2, "visits the Mint. +2 coins."),
        (11, 1, "uses the Faucet. +1 coin."),
    ],
)
def test_bank_spaces_pay_out(pos: int, coins_delta: int, text: str) -> None:
    state, rng = _game()
    _at(state, pos)
    msg = resolve_space(state, rng)
    assert state.players[0].coins == 5 + coins_delta
    assert text in msg
    assert state.log[-1].endswith(msg)


@pytest.mark.parametrize(
    ("pos", "text"),
    [
        (2, "is at Market. (Buy/sell handled interactively.)"),
        (4, "is at Trade Dock. (Trade handled interactively.)"),
        (7, "is at Help Desk. (Choose a player to help interactively.)"),
        (12, "is at Trade Dock. (Trade handled interactively.)"),
        (14, "is at Commons. (Vote handled interactively.)"),
    ],
)
def test_interactive_spaces_change_nothing(pos: int, text: str) -> None:
    state, rng = _game()
    _at(state, pos)
    msg = resolve_space(state, rng)
    assert msg == f"Alice {text}"
    assert (state.players[0].coins, state.players[0].reputation) == (5, 3)


def test_workshop_buys_an_upgrade() -> None:
    state, rng = _game()
    _at(state, 1)
    msg = resolve_space(state, rng)
    assert msg == "Alice builds at Workshop. -2 coins, +1 upgrade (1 total)."
    assert (state.players[0].coins, state.players[0].upgrades) == (3, 1)


def test_workshop_refuses_when_broke() -> None:
    state, rng = _game()
    state.players[0].coins = 1
    _at(state, 1)
    msg = resolve_space(state, rng)
    assert msg == "Alice can't afford Workshop (2 coins)."
    assert (state.players[0].coins, state.players[0].upgrades) == (1, 0)


def test_festival_converts_a_coin_to_rep() -> None:
    state, rng = _game()
    _at(state, 5)
    msg = resolve_space(state, rng)
    assert msg == "Alice celebrates at Festival. -1 coin, +1 Rep."
    assert (state.players[0].coins, state.players[0].reputation) == (4, 4)


def test_festival_refuses_when_broke() -> None:
    state, rng = _game()
    state.players[0].coins = 0
    _at(state, 5)
    msg = resolve_space(state, rng)
    assert msg == "Alice can't afford Festival donation."
    assert state.players[0].reputation == 3


def test_trouble_costs_a_coin_or_else_a_rep() -> None:
    state, rng = _game()
    _at(state, 6)
    assert resolve_space(state, rng) == "Alice runs into Trouble. -1 coin."
    assert (state.players[0].coins, state.players[0].reputation) == (4, 3)
    state.players[0].coins = 0
    assert resolve_space(state, rng) == "Alice runs into Trouble. -1 Rep (no coins to pay)."
    assert (state.players[0].coins, state.players[0].reputation) == (0, 2)


def test_taxman_costs_a_coin_or_else_a_rep() -> None:
    state, rng = _game()
    _at(state, 13)
    assert resolve_space(state, rng) == "Alice pays the Taxman. -1 coin."
    assert (state.players[0].coins, state.players[0].reputation) == (4, 3)
    state.players[0].coins = 0
    assert resolve_space(state, rng) == "Alice can't pay Taxman. -1 Rep."
    assert (state.players[0].coins, state.players[0].reputation) == (0, 2)


def test_builder_gates_on_rep_then_coins_then_builds() -> None:
    state, rng = _game()
    p = state.players[0]
    _at(state, 10)
    p.reputation = 2
    assert resolve_space(state, rng) == "Alice needs Rep >= 3 for Builder (has 2)."
    assert (p.coins, p.upgrades) == (5, 0)
    p.reputation = 3
    p.coins = 2
    assert resolve_space(state, rng) == "Alice can't afford Builder (3 coins)."
    assert (p.coins, p.upgrades) == (2, 0)
    p.coins = 5
    assert resolve_space(state, rng) == "Alice builds at Builder. -3 coins, +1 upgrade (1 total)."
    assert (p.coins, p.upgrades) == (2, 1)


@pytest.mark.parametrize("pos", [3, 9])
def test_rumor_mill_draws_and_resolves_an_event(pos: int) -> None:
    state, rng = _game()
    state.event_deck = ModelDeck(draw_pile=[CARDS["windfall"], CARDS["boom_town"]])
    _at(state, pos)
    msg = resolve_space(state, rng)
    assert msg == f"EVENT: {CARDS['windfall'].name} {DASH} Alice gains 3 coins."
    assert state.players[0].coins == 8
    assert state.event_deck.discard_pile == [CARDS["windfall"]]
    assert state.event_deck.draw_pile == [CARDS["boom_town"]]


def test_rumor_mill_with_no_events_left() -> None:
    state, rng = _game()
    state.event_deck = ModelDeck()
    _at(state, 3)
    assert resolve_space(state, rng) == "Event deck is empty!"


def test_crossroads_draws_a_deal_and_discards_it() -> None:
    state, rng = _game()
    top = state.deal_deck.draw_pile[0]
    count = len(state.deal_deck.draw_pile)
    _at(state, 15)
    msg = resolve_space(state, rng)
    assert msg == f"Alice draws Deal: {top.name} -- {top.description} (Accept/pass.)"
    assert len(state.deal_deck.draw_pile) == count - 1
    assert state.deal_deck.discard_pile == [top]


def test_crossroads_with_empty_deal_deck() -> None:
    state, rng = _game()
    state.deal_deck = ModelDeck()
    _at(state, 15)
    assert resolve_space(state, rng) == "Deal deck is empty!"


def test_unknown_space_kind_falls_through() -> None:
    state, rng = _game()
    state.board[0] = Space(0, "Nowhere", "bogus", "?")  # type: ignore[arg-type]
    _at(state, 0)
    assert resolve_space(state, rng) == "Alice lands on unknown space."


def test_resolve_space_covers_every_space_kind() -> None:
    state, rng = _game()
    kinds = set()
    for space in state.board:
        state.players[0].position = space.index
        state.players[0].coins = 10
        state.players[0].reputation = 5
        msg = resolve_space(state, rng)
        assert msg  # every space says something
        kinds.add(space.kind)
    assert kinds == set(SpaceKind)


# ---------------------------------------------------------------------------
# Help desk, vouchers, promises, apology guard rails
# ---------------------------------------------------------------------------


def test_help_desk_refuses_a_penniless_helper() -> None:
    state, _ = _game()
    a, b = state.players
    a.coins = 0
    assert resolve_help_desk(state, a, b) == "Alice can't afford to help (0 coins)."
    assert (a.reputation, b.reputation, b.coins) == (3, 3, 5)
    assert a.helped_last_round is False


def test_redeem_voucher_with_unknown_party() -> None:
    state, _ = _game()
    v = Voucher("v_0001", "t", issuer="Ghost", holder="Bob", face_value=2, deadline_round=3)
    assert redeem_voucher(state, v) == "Invalid voucher: player not found."
    v2 = Voucher("v_0002", "t", issuer="Alice", holder="Ghost", face_value=2, deadline_round=3)
    assert redeem_voucher(state, v2) == "Invalid voucher: player not found."
    assert [p.coins for p in state.players] == [5, 5]


def test_keep_and_break_unknown_promise_are_rejected() -> None:
    state, _ = _game()
    a = state.players[0]
    assert keep_promise(state, a, "fly") == "Alice has no such promise to keep."
    assert break_promise(state, a, "fly") == "Alice has no such promise to break."
    assert a.reputation == 3


def test_keep_and_break_known_promises_move_reputation() -> None:
    state, _ = _game()
    a = state.players[0]
    make_promise(state, a, "share")
    make_promise(state, a, "pay")
    assert keep_promise(state, a, "share") == 'Alice kept their promise: "share" +1 Rep.'
    assert a.reputation == 4
    assert break_promise(state, a, "pay") == 'Alice broke their promise: "pay" -2 Rep.'
    assert a.reputation == 2
    assert a.promises == []


def test_apologize_needs_a_coin_and_only_works_once() -> None:
    state, _ = _game()
    a, b = state.players
    a.coins = 0
    assert apologize(state, a, b) == "Alice can't afford to apologize (need 1 coin)."
    assert a.apology_used is False
    a.coins = 3
    msg = apologize(state, a, b)
    assert msg == "Alice apologizes to Bob. -1 coin to Bob, +1 Rep for Alice."
    assert (a.coins, b.coins, a.reputation) == (2, 6, 4)
    assert apologize(state, a, b) == "Alice has already used their apology this game."


def test_campfire_upgrade_hint_is_locked() -> None:
    assert "sov build" in campfire.CAMPFIRE_UPGRADE_HINT
    assert campfire.CAMPFIRE_UPGRADE_HINT.startswith("Campfire ruleset uses the coinless workshop")


# ---------------------------------------------------------------------------
# Setup validation for every ruleset
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory", "label"),
    [
        (new_game, "Campfire"),
        (new_town_hall_game, "Town Hall"),
        (new_treaty_table_game, "Treaty Table"),
        (new_market_day_game, "Market Day"),
    ],
)
@pytest.mark.parametrize("names", [["Solo"], ["A", "B", "C", "D", "E"]])
def test_player_count_bounds_are_enforced(factory, label: str, names: list[str]) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=rf"{label} supports 2-4 players\. Run `sov new"):
        factory(1, names)


@pytest.mark.parametrize(
    ("factory", "ruleset", "fixed"),
    [
        (new_town_hall_game, "town_hall_v1", False),
        (new_treaty_table_game, "treaty_table_v1", False),
        (new_market_day_game, "market_day_v1", True),
    ],
)
def test_market_rulesets_start_with_a_board_and_resources(
    factory, ruleset: str, fixed: bool
) -> None:  # type: ignore[no-untyped-def]
    state, _ = factory(3, ["A", "B", "C"], {"B": WinCondition.BELOVED})
    assert state.config.ruleset == ruleset
    assert state.market_board is not None
    assert state.market_board.fixed_prices is fixed
    assert state.market_board.supply["food"] == (999 if fixed else 10)
    assert [p.win_condition for p in state.players] == [
        WinCondition.PROSPERITY,
        WinCondition.BELOVED,
        WinCondition.PROSPERITY,
    ]
    assert all(p.resources == {"food": 0, "wood": 0, "tools": 0} for p in state.players)


# ---------------------------------------------------------------------------
# Town Hall market actions
# ---------------------------------------------------------------------------


def test_market_actions_refuse_on_campfire() -> None:
    state, _ = _game()
    p = state.players[0]
    expect = "Market Board is not active (Campfire mode)."
    assert market_buy(state, p, "food") == expect
    assert market_sell(state, p, "food") == expect
    assert market_status(state) == {}


def test_market_buy_and_sell_reject_unknown_resource() -> None:
    state, _ = _th_game()
    p = state.players[0]
    expect = "Unknown resource: gold. Choose: food, wood, tools."
    assert market_buy(state, p, "gold") == expect
    assert market_sell(state, p, "gold") == expect
    assert p.coins == 5


def test_market_buy_out_of_stock_and_too_poor() -> None:
    state, _ = _th_game()
    assert state.market_board is not None
    p = state.players[0]
    state.market_board.supply["food"] = 0
    assert market_buy(state, p, "food") == "No food left in the market. Supply is empty."
    p.coins = 1
    assert market_buy(state, p, "wood") == "Alice can't afford wood (2 coins, has 1)."
    assert p.resources["wood"] == 0


def test_market_buy_then_sell_round_trip() -> None:
    state, _ = _th_game()
    assert state.market_board is not None
    p = state.players[0]
    msg = market_buy(state, p, "wood")
    assert msg == "Alice buys 1 wood for 2 coins. (Holds 1, market has 7 left.)"
    assert (p.coins, p.resources["wood"], state.market_board.supply["wood"]) == (3, 1, 7)
    msg = market_sell(state, p, "wood")
    assert msg == "Alice sells 1 wood for 1 coins. (Holds 0, market has 8.)"
    assert (p.coins, p.resources["wood"], state.market_board.supply["wood"]) == (4, 0, 8)


def test_market_sell_without_stock() -> None:
    state, _ = _th_game()
    assert market_sell(state, state.players[0], "tools") == "Alice has no tools to sell."


def test_market_status_reports_price_and_supply() -> None:
    state, _ = _th_game()
    assert state.market_board is not None
    state.market_board.supply["tools"] = 2  # scarcity surcharge
    assert market_status(state) == {
        "food": {"price": 2, "supply": 8},
        "wood": {"price": 2, "supply": 8},
        "tools": {"price": 3, "supply": 2},
    }


def test_upgrade_with_resources_rejects_unknown_space() -> None:
    state, _ = _th_game()
    msg = upgrade_with_resources(state, state.players[0], "market")
    assert msg == "Unknown upgrade space: market."


def test_upgrade_with_resources_needs_coins_then_resource_then_succeeds() -> None:
    state, _ = _th_game()
    p = state.players[0]
    p.coins = 1
    assert upgrade_with_resources(state, p, "workshop") == (
        "Alice can't afford (2 coins needed, has 1)."
    )
    p.coins = 5
    assert upgrade_with_resources(state, p, "workshop") == "Alice needs 1 wood (has 0)."
    p.resources["wood"] = 1
    msg = upgrade_with_resources(state, p, "workshop")
    assert msg == "Alice upgrades! -2 coins, -1 wood, +1 upgrade (1 total)."
    assert (p.coins, p.resources["wood"], p.upgrades) == (3, 0, 1)


def test_upgrade_with_resources_builder_rep_gate() -> None:
    state, _ = _th_game()
    p = state.players[0]
    p.reputation = 2
    p.resources["tools"] = 1
    assert upgrade_with_resources(state, p, "builder") == (
        "Alice needs Rep >= 3 for Builder (has 2)."
    )
    p.reputation = 3
    msg = upgrade_with_resources(state, p, "builder")
    assert msg == "Alice upgrades! -3 coins, -1 tools, +1 upgrade (1 total)."
    assert (p.coins, p.resources["tools"]) == (2, 0)


# ---------------------------------------------------------------------------
# Treaty Table
# ---------------------------------------------------------------------------


def _tt():  # type: ignore[no-untyped-def]
    state, rng = new_treaty_table_game(5, ["Alice", "Bob"])
    return state, state.players[0], state.players[1]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", Stake()),
        ("   ", Stake()),
        ("2 coins", Stake(coins=2)),
        ("1 coin", Stake(coins=1)),
        ("2 coins, 1 food", Stake(coins=2, resources={"food": 1})),
        ("1 tool, 1 tools", Stake(resources={"tools": 2})),
        ("2 Wood", Stake(resources={"wood": 2})),
    ],
)
def test_parse_stake_accepts(text: str, expected: Stake) -> None:
    assert parse_stake(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("two coins", "'two' isn't a number."),
        ("coins", "Can't parse stake: 'coins'. Use '<amount> <type>' (e.g. '2 coins')."),
        ("1 2 3", "Can't parse stake: '1 2 3'. Use '<amount> <type>' (e.g. '2 coins')."),
        ("0 coins", "Stake amounts must be positive."),
        ("-1 food", "Stake amounts must be positive."),
        ("2 gold", "Unknown stake type: 'gold'. Use: coins, food, wood, tools."),
        ("6 coins", "Max 5 coins per stake."),
        ("2 food, 2 wood", "Max 3 total resource units per stake."),
    ],
)
def test_parse_stake_rejects(text: str, expected: str) -> None:
    assert parse_stake(text) == expected


def test_next_treaty_id_ignores_malformed_ids() -> None:
    state, a, b = _tt()
    t = Treaty("t_0004", "x", ["Alice", "Bob"], {}, deadline_round=3)
    junk = Treaty("weird", "x", ["Alice", "Bob"], {}, deadline_round=3)
    junk2 = Treaty("t_abc", "x", ["Alice", "Bob"], {}, deadline_round=3)
    a.active_treaties += [t, junk, junk2]
    assert _next_treaty_id(state) == "t_0005"


def test_treaty_make_rejects_self_treaty() -> None:
    state, a, _ = _tt()
    assert treaty_make(state, a, a, "x", Stake(coins=1), Stake()) == (
        "Can't make a treaty with yourself."
    )
    assert a.coins == 5 and a.active_treaties == []


def test_treaty_make_enforces_active_treaty_limits_for_both_parties() -> None:
    state, a, b = _tt()
    for _ in range(2):
        assert isinstance(treaty_make(state, a, b, "t", Stake(coins=1), Stake()), Treaty)
    assert treaty_make(state, a, b, "t", Stake(coins=1), Stake()) == (
        "Alice already has 2 active treaties. Resolve one first."
    )
    # Bob is at the limit as a partner too (he has the two treaties Alice opened).
    state2, c, d = _tt()
    d.active_treaties = [
        Treaty(f"t_{i:04d}", "x", ["Bob", "Zed"], {}, 9, TreatyStatus.ACTIVE) for i in (1, 2)
    ]
    assert treaty_make(state2, c, d, "t", Stake(coins=1), Stake()) == (
        "Bob already has 2 active treaties. Resolve one first."
    )
    assert c.coins == 5


def test_treaty_make_requires_some_stake() -> None:
    state, a, b = _tt()
    assert treaty_make(state, a, b, "t", Stake(), Stake()) == (
        "At least one party must stake something. Otherwise, use a promise."
    )


def test_treaty_make_rejects_unaffordable_stakes() -> None:
    state, a, b = _tt()
    assert treaty_make(state, a, b, "t", Stake(coins=5, resources={"food": 1}), Stake(coins=1)) == (
        "Alice can't afford that stake (needs 5 coins, 1 food)."
    )
    assert treaty_make(state, a, b, "t", Stake(coins=1), Stake(coins=1, resources={"wood": 2})) == (
        "Bob can't afford that stake (needs 1 coin, 2 wood)."
    )
    assert (a.coins, b.coins) == (5, 5)


def test_treaty_keep_returns_stakes_and_pays_rep() -> None:
    state, a, b = _tt()
    a.resources["food"] = 2
    treaty = treaty_make(
        state,
        a,
        b,
        "swap",
        Stake(coins=2, resources={"food": 2}),
        Stake(coins=1),
        duration_rounds=2,
    )
    assert isinstance(treaty, Treaty)
    assert treaty.treaty_id == "t_0001"
    assert treaty.deadline_round == 3
    assert (a.coins, a.resources["food"], b.coins) == (3, 0, 4)
    assert treaty_list(a) == [treaty] and treaty_list(b) == [treaty]

    msg = treaty_keep(state, treaty)
    assert msg == "Treaty t_0001 honored! Alice and Bob get their stakes back. +1 Rep each."
    assert (a.coins, a.resources["food"], b.coins) == (5, 2, 5)
    assert (a.reputation, b.reputation) == (4, 4)
    assert treaty.status is TreatyStatus.KEPT
    assert treaty_keep(state, treaty) == "Treaty t_0001 is already kept."


def test_treaty_break_forfeits_breakers_stake() -> None:
    state, a, b = _tt()
    b.resources["wood"] = 1
    treaty = treaty_make(
        state, a, b, "deal", Stake(coins=2, resources={"tools": 0}), Stake(resources={"wood": 1})
    )
    assert isinstance(treaty, Treaty)
    assert (a.coins, b.resources["wood"]) == (3, 0)

    msg = treaty_break(state, treaty, "Bob")
    assert msg == (
        "Treaty t_0001 BROKEN by Bob! Alice claims Bob's stake (1 wood). Bob loses 3 Rep."
    )
    assert treaty.status is TreatyStatus.BROKEN
    assert (a.coins, a.resources.get("wood", 0)) == (5, 1)
    assert b.reputation == 0
    assert b.resources["wood"] == 0
    assert treaty_break(state, treaty, "Bob") == "Treaty t_0001 is already broken."


def test_treaty_break_rejects_outsiders_and_missing_players() -> None:
    state, a, b = _tt()
    treaty = treaty_make(state, a, b, "deal", Stake(coins=1), Stake())
    assert isinstance(treaty, Treaty)
    assert treaty_break(state, treaty, "Mallory") == "Mallory is not a party to treaty t_0001."
    assert treaty.status is TreatyStatus.ACTIVE

    ghost = Treaty("t_0009", "x", ["Alice", "Ghost"], {}, 9)
    assert treaty_break(state, ghost, "Alice") == "Player not found."
    assert ghost.status is TreatyStatus.BROKEN


def test_stake_helpers_move_resources() -> None:
    _, a, b = _tt()
    stake = Stake(coins=2, resources={"food": 2, "wood": 1})
    assert stake.total_value() == 5
    assert not _can_afford_stake(a, stake)  # coins fine, no food
    a.resources.update(food=2, wood=1)
    assert _can_afford_stake(a, stake)
    a.resources["wood"] = 0
    assert not _can_afford_stake(a, stake)  # short one wood

    _transfer_stake(b, stake)
    assert (b.coins, b.resources["food"], b.resources["wood"]) == (7, 2, 1)
    _return_stake(b, stake)
    assert (b.coins, b.resources["food"], b.resources["wood"]) == (9, 4, 2)


def test_check_treaty_deadlines_auto_keeps_each_treaty_once() -> None:
    state, a, b = _tt()
    treaty = treaty_make(state, a, b, "deal", Stake(coins=2), Stake(coins=1), duration_rounds=1)
    assert isinstance(treaty, Treaty)
    state.current_round = 2  # not yet past deadline (2 == deadline)
    assert check_treaty_deadlines(state) == []
    state.current_round = 3
    msgs = check_treaty_deadlines(state)
    assert msgs == ["Treaty t_0001 honored! Alice and Bob get their stakes back. +1 Rep each."]
    assert (a.coins, b.coins) == (5, 5)
    assert (a.reputation, b.reputation) == (4, 4)
    assert check_treaty_deadlines(state) == []


# ---------------------------------------------------------------------------
# models.py / rng.py gaps
# ---------------------------------------------------------------------------


def test_has_won_is_false_for_unknown_win_condition() -> None:
    state, _ = _game()
    p = state.players[0]
    p.win_condition = "mystery"  # type: ignore[assignment]
    p.coins = 99
    assert p.has_won() is False


@pytest.mark.parametrize(
    ("condition", "attr", "value"),
    [
        (WinCondition.PROSPERITY, "coins", 20),
        (WinCondition.BELOVED, "reputation", 10),
        (WinCondition.BUILDER, "upgrades", 4),
    ],
)
def test_check_winner_records_winner_and_log(
    condition: WinCondition, attr: str, value: int
) -> None:
    state, _ = _game()
    assert state.check_winner() is None
    assert state.game_over is False
    p = state.players[1]
    p.win_condition = condition
    setattr(p, attr, value)
    assert state.check_winner() == "Bob"
    assert state.game_over is True
    assert state.winner == "Bob"
    assert state.log[-1].endswith(f"Bob wins by {condition.value}!")


def test_deck_reshuffles_discards_when_draw_pile_is_empty() -> None:
    cards = list(build_event_deck())[:5]
    deck = ModelDeck(discard_pile=list(cards))
    expected = list(cards)
    random.Random(11).shuffle(expected)
    drawn = deck.draw(GameRng(11))
    assert drawn is expected[0]
    assert deck.draw_pile == expected[1:]
    assert deck.discard_pile == []


def test_deck_draw_returns_none_when_everything_is_empty() -> None:
    assert ModelDeck().draw(GameRng(1)) is None


def test_market_prices_as_dict_and_board_edge_cases() -> None:
    assert MarketPrices(food=4, wood=5, tools=6).as_dict() == {"food": 4, "wood": 5, "tools": 6}
    board = MarketBoard.create(2)
    board.supply["food"] = 0
    assert board.can_buy("food") is False
    assert board.buy("food") == -1
    assert board.supply["food"] == 0


def test_game_rng_choice_and_randint_follow_the_seeded_stream() -> None:
    rng = GameRng(42)
    ref = random.Random(42)
    assert rng.choice(["a", "b", "c", "d"]) == ref.choice(["a", "b", "c", "d"])
    assert rng.randint(3, 9) == ref.randint(3, 9)


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        ("nope", "rng_state must be a 3-element sequence"),
        ([1, 2], "rng_state must be a 3-element sequence"),
        ([3, 5, None], "rng_state internals must be a sequence"),
    ],
)
def test_game_rng_setstate_rejects_malformed_state(bad: object, message: str) -> None:
    rng = GameRng(1)
    with pytest.raises(ValueError, match=message):
        rng.setstate(bad)


def test_game_rng_state_round_trips() -> None:
    a = GameRng(9)
    a.roll_d6()
    saved = a.getstate()
    nxt = [a.roll_d6() for _ in range(5)]
    b = GameRng(123)
    b.setstate(saved)
    assert [b.roll_d6() for _ in range(5)] == nxt

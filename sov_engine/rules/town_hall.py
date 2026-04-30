"""Town Hall (Tier 2) rules — Campfire + Market Board with resources and scarcity."""

from __future__ import annotations

from sov_engine.content import build_board, build_deal_deck, build_event_deck
from sov_engine.models import (
    RESOURCE_NAMES,
    Deck,
    GameConfig,
    GameState,
    MarketBoard,
    MarketPrices,
    PlayerState,
    WinCondition,
)
from sov_engine.rng import GameRng

# Re-export everything from Campfire so callers get the full rule set
from sov_engine.rules.campfire import (  # noqa: F401
    accept_deal,
    apologize,
    break_promise,
    check_deal_deadlines,
    check_voucher_deadlines,
    complete_deal,
    issue_voucher,
    keep_promise,
    make_promise,
    redeem_voucher,
    resolve_event,
    resolve_help_desk,
    resolve_space,
    roll_and_move,
)

# Public surface — both the names defined here AND the Campfire re-exports.
# Listed explicitly so ``from sov_engine.rules.town_hall import *`` is
# deterministic and ``treaty_table.py`` (which also re-exports this module)
# does not silently drop or pick up symbols.
__all__ = [
    # Game setup
    "new_town_hall_game",
    # Market actions defined here
    "market_buy",
    "market_sell",
    "market_status",
    "upgrade_with_resources",
    # Re-exports from Campfire
    "accept_deal",
    "apologize",
    "break_promise",
    "check_deal_deadlines",
    "check_voucher_deadlines",
    "complete_deal",
    "issue_voucher",
    "keep_promise",
    "make_promise",
    "redeem_voucher",
    "resolve_event",
    "resolve_help_desk",
    "resolve_space",
    "roll_and_move",
]

# ---------------------------------------------------------------------------
# Town Hall game setup
# ---------------------------------------------------------------------------

WORKSHOP_WOOD_COST = 1  # Workshop upgrade: 2 coins + 1 Wood
BUILDER_TOOLS_COST = 1  # Builder upgrade: 3 coins + 1 Tools


def new_town_hall_game(
    seed: int,
    player_names: list[str],
    win_conditions: dict[str, WinCondition] | None = None,
) -> tuple[GameState, GameRng]:
    """Create a fresh Town Hall game — Campfire + Market Board."""
    if len(player_names) < 2 or len(player_names) > 4:
        raise ValueError("Town Hall supports 2-4 players")

    rng = GameRng(seed)
    config = GameConfig(seed=seed, ruleset="town_hall_v1")
    wc = win_conditions or {}

    players = [
        PlayerState(
            name=name,
            win_condition=wc.get(name, WinCondition.PROSPERITY),
            resources={r: 0 for r in RESOURCE_NAMES},
        )
        for name in player_names
    ]

    board = build_board()
    events = build_event_deck()
    deals = build_deal_deck()

    rng.shuffle(events)
    rng.shuffle(deals)

    market_board = MarketBoard.create(len(player_names))

    state = GameState(
        config=config,
        players=players,
        board=board,
        event_deck=Deck(draw_pile=events),
        deal_deck=Deck(draw_pile=deals),
        market=MarketPrices(),
        market_board=market_board,
    )
    state.add_log(f"Town Hall game started. Seed: {seed}. Players: {', '.join(player_names)}")
    return state, rng


# ---------------------------------------------------------------------------
# Market actions (Town Hall only)
# ---------------------------------------------------------------------------


def market_buy(
    state: GameState,
    player: PlayerState,
    resource: str,
) -> str:
    """Buy 1 resource from the market. Returns description."""
    mb = state.market_board
    if mb is None:
        return "Market Board is not active (Campfire mode)."
    if resource not in RESOURCE_NAMES:
        return f"Unknown resource: {resource}. Choose: {', '.join(RESOURCE_NAMES)}."
    if not mb.can_buy(resource):
        return f"No {resource} left in the market. Supply is empty."
    cost = mb.price(resource)
    if player.coins < cost:
        return f"{player.name} can't afford {resource} ({cost} coins, has {player.coins})."

    paid = mb.buy(resource)
    player.adjust_coins(-paid)
    player.resources[resource] = player.resources.get(resource, 0) + 1
    held = player.resources[resource]
    left = mb.supply[resource]
    msg = (
        f"{player.name} buys 1 {resource} for {paid} coins. (Holds {held}, market has {left} left.)"
    )
    state.add_log(msg)
    return msg


def market_sell(
    state: GameState,
    player: PlayerState,
    resource: str,
) -> str:
    """Sell 1 resource back to the market. Returns description."""
    mb = state.market_board
    if mb is None:
        return "Market Board is not active (Campfire mode)."
    if resource not in RESOURCE_NAMES:
        return f"Unknown resource: {resource}. Choose: {', '.join(RESOURCE_NAMES)}."
    held = player.resources.get(resource, 0)
    if held < 1:
        return f"{player.name} has no {resource} to sell."

    earned = mb.sell(resource)
    player.adjust_coins(earned)
    player.resources[resource] -= 1
    left_held = player.resources[resource]
    left_supply = mb.supply[resource]
    msg = (
        f"{player.name} sells 1 {resource} for {earned} coins. "
        f"(Holds {left_held}, market has {left_supply}.)"
    )
    state.add_log(msg)
    return msg


def market_status(state: GameState) -> dict[str, dict[str, int]]:
    """Return current market prices and supply. For display."""
    mb = state.market_board
    if mb is None:
        return {}
    return {r: {"price": mb.price(r), "supply": mb.supply.get(r, 0)} for r in RESOURCE_NAMES}


# ---------------------------------------------------------------------------
# Resource-cost upgrades (Town Hall variant)
# ---------------------------------------------------------------------------


def upgrade_with_resources(
    state: GameState,
    player: PlayerState,
    space_kind: str,
) -> str:
    """Upgrade at Workshop or Builder, paying resources too (Town Hall).

    Workshop: 2 coins + 1 Wood.
    Builder: 3 coins + 1 Tools (+ Rep >= 3).
    """
    if space_kind == "workshop":
        coin_cost = 2
        res_name = "wood"
        res_cost = WORKSHOP_WOOD_COST
    elif space_kind == "builder":
        coin_cost = 3
        res_name = "tools"
        res_cost = BUILDER_TOOLS_COST
        if player.reputation < 3:
            return f"{player.name} needs Rep >= 3 for Builder (has {player.reputation})."
    else:
        return f"Unknown upgrade space: {space_kind}."

    held = player.resources.get(res_name, 0)
    if player.coins < coin_cost:
        return f"{player.name} can't afford ({coin_cost} coins needed, has {player.coins})."
    if held < res_cost:
        return f"{player.name} needs {res_cost} {res_name} (has {held})."

    player.adjust_coins(-coin_cost)
    player.resources[res_name] -= res_cost
    player.upgrades += 1
    u = player.upgrades
    msg = (
        f"{player.name} upgrades! -{coin_cost} coins, -{res_cost} {res_name}, "
        f"+1 upgrade ({u} total)."
    )
    state.add_log(msg)
    return msg

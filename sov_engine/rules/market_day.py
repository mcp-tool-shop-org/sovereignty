"""Market Day (Tier 2) rules — Campfire + fixed-price Market Board.

Market Day teaches buying, holding, and spending resources without
the complexity of scarcity pricing or event-driven price shifts.
Prices are always 2 coins. Supply never runs out.

"Store prices." — not "living market."
"""

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

# Re-export market actions from Town Hall (they work with any MarketBoard)
from sov_engine.rules.town_hall import (  # noqa: F401
    market_buy,
    market_sell,
    market_status,
    upgrade_with_resources,
)

# ---------------------------------------------------------------------------
# Market Day game setup
# ---------------------------------------------------------------------------


def new_market_day_game(
    seed: int,
    player_names: list[str],
    win_conditions: dict[str, WinCondition] | None = None,
) -> tuple[GameState, GameRng]:
    """Create a Market Day game — Campfire + fixed-price Market Board."""
    if len(player_names) < 2 or len(player_names) > 4:
        raise ValueError(
            "Market Day supports 2-4 players. Run `sov new -p Alice -p Bob` for 2-player."
        )

    rng = GameRng(seed)
    config = GameConfig(seed=seed, ruleset="market_day_v1")
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

    # Fixed prices, huge supply — the gentle introduction
    market_board = MarketBoard.create(len(player_names), fixed=True)

    state = GameState(
        config=config,
        players=players,
        board=board,
        event_deck=Deck(draw_pile=events),
        deal_deck=Deck(draw_pile=deals),
        market=MarketPrices(),
        market_board=market_board,
    )
    state.add_log(f"Market Day game started. Seed: {seed}. Players: {', '.join(player_names)}")
    return state, rng

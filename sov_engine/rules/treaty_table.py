"""Treaty Table rules — Town Hall + Treaties with Stakes."""

from __future__ import annotations

from sov_engine.content import build_board, build_deal_deck, build_event_deck
from sov_engine.models import (
    MAX_ACTIVE_TREATIES,
    RESOURCE_NAMES,
    STAKE_CAP_COINS,
    STAKE_CAP_RESOURCES,
    TREATY_REP_BONUS,
    TREATY_REP_PENALTY,
    Deck,
    GameConfig,
    GameState,
    MarketBoard,
    MarketPrices,
    PlayerState,
    Stake,
    Treaty,
    TreatyStatus,
    WinCondition,
)
from sov_engine.rng import GameRng

# Re-export everything from Town Hall (which includes Campfire)
from sov_engine.rules.town_hall import (  # noqa: F401
    accept_deal,
    apologize,
    break_promise,
    check_deal_deadlines,
    check_voucher_deadlines,
    complete_deal,
    issue_voucher,
    keep_promise,
    make_promise,
    market_buy,
    market_sell,
    market_status,
    redeem_voucher,
    resolve_event,
    resolve_help_desk,
    resolve_space,
    roll_and_move,
    upgrade_with_resources,
)


def _next_treaty_id(state: GameState) -> str:
    """Derive the next treaty ID from existing treaties in the game state."""
    max_num = 0
    for p in state.players:
        for t in p.active_treaties:
            # Parse "t_0003" → 3
            try:
                num = int(t.treaty_id.split("_")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                pass
    return f"t_{max_num + 1:04d}"


# ---------------------------------------------------------------------------
# Treaty Table game setup
# ---------------------------------------------------------------------------


def new_treaty_table_game(
    seed: int,
    player_names: list[str],
    win_conditions: dict[str, WinCondition] | None = None,
) -> tuple[GameState, GameRng]:
    """Create a Treaty Table game — Town Hall + Treaty Stakes."""
    if len(player_names) < 2 or len(player_names) > 4:
        raise ValueError("Treaty Table supports 2-4 players")

    rng = GameRng(seed)
    config = GameConfig(seed=seed, ruleset="treaty_table_v1")
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
    state.add_log(
        f"Treaty Table game started. Seed: {seed}. "
        f"Players: {', '.join(player_names)}"
    )
    return state, rng


# ---------------------------------------------------------------------------
# Stake parsing
# ---------------------------------------------------------------------------


def parse_stake(text: str) -> Stake | str:
    """Parse '2 coins, 1 food' into a Stake. Returns error string on failure."""
    if not text.strip():
        return Stake()

    coins = 0
    resources: dict[str, int] = {}

    parts = [p.strip() for p in text.split(",")]
    for part in parts:
        tokens = part.split()
        if len(tokens) != 2:
            return (
                f"Can't parse stake: '{part}'. "
                "Use '<amount> <type>' (e.g. '2 coins')."
            )
        try:
            amount = int(tokens[0])
        except ValueError:
            return f"'{tokens[0]}' isn't a number."
        if amount <= 0:
            return "Stake amounts must be positive."

        kind = tokens[1].lower().rstrip("s")
        if kind == "coin":
            coins += amount
        elif kind in ("food", "wood", "tool"):
            resource_name = "tools" if kind == "tool" else kind
            resources[resource_name] = resources.get(resource_name, 0) + amount
        else:
            return f"Unknown stake type: '{tokens[1]}'. Use: coins, food, wood, tools."

    stake = Stake(coins=coins, resources=resources)
    if stake.coins > STAKE_CAP_COINS:
        return f"Max {STAKE_CAP_COINS} coins per stake."
    if sum(stake.resources.values()) > STAKE_CAP_RESOURCES:
        return f"Max {STAKE_CAP_RESOURCES} total resource units per stake."
    return stake


# ---------------------------------------------------------------------------
# Escrow helpers
# ---------------------------------------------------------------------------


def _can_afford_stake(player: PlayerState, stake: Stake) -> bool:
    """Check if a player can put up this stake."""
    if player.coins < stake.coins:
        return False
    for resource, amount in stake.resources.items():
        if player.resources.get(resource, 0) < amount:
            return False
    return True


def _escrow_stake(player: PlayerState, stake: Stake) -> None:
    """Remove staked assets from player's holdings."""
    player.adjust_coins(-stake.coins)
    for resource, amount in stake.resources.items():
        player.resources[resource] = player.resources.get(resource, 0) - amount


def _return_stake(player: PlayerState, stake: Stake) -> None:
    """Return escrowed assets to a player."""
    player.adjust_coins(stake.coins)
    for resource, amount in stake.resources.items():
        player.resources[resource] = player.resources.get(resource, 0) + amount


def _transfer_stake(to_player: PlayerState, stake: Stake) -> None:
    """Transfer forfeited stake to the harmed party."""
    to_player.adjust_coins(stake.coins)
    for resource, amount in stake.resources.items():
        to_player.resources[resource] = (
            to_player.resources.get(resource, 0) + amount
        )


def _stake_desc(stake: Stake) -> str:
    """Human-readable stake description."""
    parts: list[str] = []
    if stake.coins > 0:
        parts.append(f"{stake.coins} coin{'s' if stake.coins != 1 else ''}")
    for res, amt in sorted(stake.resources.items()):
        if amt > 0:
            parts.append(f"{amt} {res}")
    return ", ".join(parts) if parts else "nothing"


# ---------------------------------------------------------------------------
# Core treaty operations
# ---------------------------------------------------------------------------


def treaty_make(
    state: GameState,
    maker: PlayerState,
    partner: PlayerState,
    text: str,
    maker_stake: Stake,
    partner_stake: Stake,
    duration_rounds: int = 3,
) -> Treaty | str:
    """Create a treaty. Both parties escrow stakes immediately.

    Returns the Treaty on success, or an error string.
    """
    if maker.name == partner.name:
        return "Can't make a treaty with yourself."

    maker_active = [
        t for t in maker.active_treaties if t.status == TreatyStatus.ACTIVE
    ]
    if len(maker_active) >= MAX_ACTIVE_TREATIES:
        return (
            f"{maker.name} already has {MAX_ACTIVE_TREATIES} active treaties. "
            "Resolve one first."
        )

    partner_active = [
        t for t in partner.active_treaties if t.status == TreatyStatus.ACTIVE
    ]
    if len(partner_active) >= MAX_ACTIVE_TREATIES:
        return (
            f"{partner.name} already has {MAX_ACTIVE_TREATIES} active treaties. "
            "Resolve one first."
        )

    if maker_stake.is_empty() and partner_stake.is_empty():
        return "At least one party must stake something. Otherwise, use a promise."

    if not _can_afford_stake(maker, maker_stake):
        return (
            f"{maker.name} can't afford that stake "
            f"(needs {_stake_desc(maker_stake)})."
        )
    if not _can_afford_stake(partner, partner_stake):
        return (
            f"{partner.name} can't afford that stake "
            f"(needs {_stake_desc(partner_stake)})."
        )

    treaty = Treaty(
        treaty_id=_next_treaty_id(state),
        text=text,
        parties=[maker.name, partner.name],
        stakes={maker.name: maker_stake, partner.name: partner_stake},
        deadline_round=state.current_round + duration_rounds,
        status=TreatyStatus.ACTIVE,
        created_round=state.current_round,
    )

    _escrow_stake(maker, maker_stake)
    _escrow_stake(partner, partner_stake)

    maker.active_treaties.append(treaty)
    partner.active_treaties.append(treaty)

    msg = (
        f"Treaty {treaty.treaty_id}: {maker.name} and {partner.name} agree: "
        f'"{text}" — stakes: {maker.name} puts up {_stake_desc(maker_stake)}, '
        f"{partner.name} puts up {_stake_desc(partner_stake)} "
        f"(due R{treaty.deadline_round})"
    )
    state.add_log(msg)
    return treaty


def treaty_keep(state: GameState, treaty: Treaty) -> str:
    """Both parties honored the treaty. Return all stakes. +1 Rep each."""
    if treaty.status != TreatyStatus.ACTIVE:
        return f"Treaty {treaty.treaty_id} is already {treaty.status.value}."

    treaty.status = TreatyStatus.KEPT

    for player_name, stake in treaty.stakes.items():
        player = next(
            (p for p in state.players if p.name == player_name), None
        )
        if player:
            _return_stake(player, stake)
            player.adjust_rep(TREATY_REP_BONUS)

    parties = " and ".join(treaty.parties)
    msg = (
        f"Treaty {treaty.treaty_id} honored! {parties} get their stakes back. "
        f"+{TREATY_REP_BONUS} Rep each."
    )
    state.add_log(msg)
    return msg


def treaty_break(
    state: GameState, treaty: Treaty, breaker_name: str,
) -> str:
    """One party broke the treaty. Breaker forfeits stake to harmed party."""
    if treaty.status != TreatyStatus.ACTIVE:
        return f"Treaty {treaty.treaty_id} is already {treaty.status.value}."
    if breaker_name not in treaty.parties:
        return f"{breaker_name} is not a party to treaty {treaty.treaty_id}."

    treaty.status = TreatyStatus.BROKEN

    harmed_name = [n for n in treaty.parties if n != breaker_name][0]
    harmed = next(
        (p for p in state.players if p.name == harmed_name), None
    )
    breaker = next(
        (p for p in state.players if p.name == breaker_name), None
    )

    if not breaker or not harmed:
        return "Player not found."

    # Breaker's stake goes to harmed party
    breaker_stake = treaty.stakes.get(breaker_name, Stake())
    _transfer_stake(harmed, breaker_stake)

    # Harmed party gets their own stake back
    harmed_stake = treaty.stakes.get(harmed_name, Stake())
    _return_stake(harmed, harmed_stake)

    # Rep penalty for breaker
    breaker.adjust_rep(TREATY_REP_PENALTY)

    msg = (
        f"Treaty {treaty.treaty_id} BROKEN by {breaker_name}! "
        f"{harmed_name} claims {breaker_name}'s stake "
        f"({_stake_desc(breaker_stake)}). "
        f"{breaker_name} loses {abs(TREATY_REP_PENALTY)} Rep."
    )
    state.add_log(msg)
    return msg


def treaty_list(player: PlayerState) -> list[Treaty]:
    """List all treaties for a player."""
    return list(player.active_treaties)


def check_treaty_deadlines(state: GameState) -> list[str]:
    """Auto-keep expired treaties. Call at end of each round.

    If neither party called break before the deadline, the treaty
    is considered honored — stakes return, +1 Rep each.
    """
    messages: list[str] = []
    seen: set[str] = set()
    for player in state.players:
        for t in player.active_treaties:
            if t.treaty_id in seen:
                continue
            if (
                t.status == TreatyStatus.ACTIVE
                and state.current_round > t.deadline_round
            ):
                seen.add(t.treaty_id)
                msg = treaty_keep(state, t)
                messages.append(msg)
    return messages

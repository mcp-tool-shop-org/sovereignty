"""Campfire (Tier 1) rules — space resolution, events, vouchers, deals."""

from __future__ import annotations

from sov_engine.content import build_board, build_deal_deck, build_event_deck
from sov_engine.models import (
    BOARD_SIZE,
    ActiveDeal,
    DealCard,
    DealStatus,
    Deck,
    EventCard,
    GameConfig,
    GameState,
    MarketPrices,
    PlayerState,
    SpaceKind,
    Voucher,
    VoucherCard,
    VoucherStatus,
    WinCondition,
)
from sov_engine.rng import GameRng

# ---------------------------------------------------------------------------
# Game setup
# ---------------------------------------------------------------------------


def new_game(
    seed: int,
    player_names: list[str],
    win_conditions: dict[str, WinCondition] | None = None,
) -> tuple[GameState, GameRng]:
    """Create a fresh Campfire game."""
    if len(player_names) < 2 or len(player_names) > 4:
        raise ValueError("Campfire supports 2-4 players")

    rng = GameRng(seed)
    config = GameConfig(seed=seed)
    wc = win_conditions or {}

    players = [
        PlayerState(
            name=name,
            win_condition=wc.get(name, WinCondition.PROSPERITY),
        )
        for name in player_names
    ]

    board = build_board()
    events = build_event_deck()
    deals = build_deal_deck()

    rng.shuffle(events)
    rng.shuffle(deals)

    state = GameState(
        config=config,
        players=players,
        board=board,
        event_deck=Deck(draw_pile=events),
        deal_deck=Deck(draw_pile=deals),
        market=MarketPrices(),
    )
    state.add_log(f"Game started. Seed: {seed}. Players: {', '.join(player_names)}")
    return state, rng


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------


def roll_and_move(state: GameState, rng: GameRng) -> int:
    """Roll d6, move current player, handle passing Campfire. Returns roll value."""
    roll = rng.roll_d6()
    player = state.current_player
    old_pos = player.position
    new_pos = (old_pos + roll) % BOARD_SIZE

    # passing through or landing on Campfire earns 1 coin
    passed_campfire = new_pos < old_pos or (old_pos == 0 and roll >= BOARD_SIZE)
    if passed_campfire and new_pos != 0:
        player.adjust_coins(1)
        state.add_log(f"{player.name} passed Campfire, +1 coin")

    player.position = new_pos
    space = state.board[new_pos]
    state.add_log(f"{player.name} rolled {roll}, moved to {space.name} (space {new_pos})")
    return roll


# ---------------------------------------------------------------------------
# Space resolution
# ---------------------------------------------------------------------------


def resolve_space(state: GameState, rng: GameRng) -> str:
    """Resolve the effect of the current player's space. Returns a description."""
    player = state.current_player
    space = state.board[player.position]

    match space.kind:
        case SpaceKind.CAMPFIRE:
            player.adjust_coins(1)
            msg = f"{player.name} rests at Campfire. +1 coin."
        case SpaceKind.WORKSHOP:
            msg = _resolve_workshop(player, state)
        case SpaceKind.MARKET:
            msg = f"{player.name} is at Market. (Buy/sell handled interactively.)"
        case SpaceKind.RUMOR_MILL:
            msg = _resolve_rumor_mill(state, rng)
        case SpaceKind.TRADE_DOCK:
            msg = f"{player.name} is at Trade Dock. (Trade handled interactively.)"
        case SpaceKind.FESTIVAL:
            msg = _resolve_festival(player, state)
        case SpaceKind.TROUBLE:
            msg = _resolve_trouble(player, state)
        case SpaceKind.HELP_DESK:
            msg = f"{player.name} is at Help Desk. (Choose a player to help interactively.)"
        case SpaceKind.MINT:
            player.adjust_coins(2)
            msg = f"{player.name} visits the Mint. +2 coins."
        case SpaceKind.BUILDER:
            msg = _resolve_builder(player, state)
        case SpaceKind.FAUCET:
            player.adjust_coins(1)
            msg = f"{player.name} uses the Faucet. +1 coin."
        case SpaceKind.TAXMAN:
            msg = _resolve_taxman(player, state)
        case SpaceKind.COMMONS:
            msg = f"{player.name} is at Commons. (Vote handled interactively.)"
        case SpaceKind.CROSSROADS:
            msg = _resolve_crossroads(state, rng)
        case _:
            msg = f"{player.name} lands on unknown space."

    state.add_log(msg)
    return msg


def _resolve_workshop(player: PlayerState, state: GameState) -> str:
    cost = 2
    if player.coins >= cost:
        player.adjust_coins(-cost)
        player.upgrades += 1
        u = player.upgrades
        return f"{player.name} builds at Workshop. -{cost} coins, +1 upgrade ({u} total)."
    return f"{player.name} can't afford Workshop ({cost} coins)."


def _resolve_builder(player: PlayerState, state: GameState) -> str:
    cost = 3
    if not player.can_use_builder():
        return f"{player.name} needs Rep >= 3 for Builder (has {player.reputation})."
    if player.coins >= cost:
        player.adjust_coins(-cost)
        player.upgrades += 1
        u = player.upgrades
        return f"{player.name} builds at Builder. -{cost} coins, +1 upgrade ({u} total)."
    return f"{player.name} can't afford Builder ({cost} coins)."


def _resolve_festival(player: PlayerState, state: GameState) -> str:
    if player.coins >= 1:
        player.adjust_coins(-1)
        player.adjust_rep(1)
        return f"{player.name} celebrates at Festival. -1 coin, +1 Rep."
    return f"{player.name} can't afford Festival donation."


def _resolve_trouble(player: PlayerState, state: GameState) -> str:
    # AI/CLI picks: lose coin if possible, otherwise rep
    if player.coins >= 1:
        player.adjust_coins(-1)
        return f"{player.name} runs into Trouble. -1 coin."
    player.adjust_rep(-1)
    return f"{player.name} runs into Trouble. -1 Rep (no coins to pay)."


def _resolve_taxman(player: PlayerState, state: GameState) -> str:
    if player.coins >= 1:
        player.adjust_coins(-1)
        return f"{player.name} pays the Taxman. -1 coin."
    player.adjust_rep(-1)
    return f"{player.name} can't pay Taxman. -1 Rep."


def _resolve_rumor_mill(state: GameState, rng: GameRng) -> str:
    card = state.event_deck.draw(rng)
    if card is None:
        return "Event deck is empty!"
    result = resolve_event(state, card, rng)  # type: ignore[arg-type]
    state.event_deck.discard(card)
    return result


def _resolve_crossroads(state: GameState, rng: GameRng) -> str:
    card = state.deal_deck.draw(rng)
    if card is None:
        return "Deal deck is empty!"
    player = state.current_player
    state.deal_deck.discard(card)
    desc = card.description
    return f"{player.name} draws Deal: {card.name} -- {desc} (Accept/pass.)"


# ---------------------------------------------------------------------------
# Event resolution
# ---------------------------------------------------------------------------


def resolve_event(state: GameState, card: EventCard, rng: GameRng) -> str:
    """Resolve an event card's effect. Returns description."""
    player = state.current_player
    eid = card.effect_id

    match eid:
        case "supply_delay":
            # Handled as a round modifier — logged for awareness
            return f"EVENT: {card.name} — {card.description}"

        case "boom_town":
            for p in state.players:
                p.adjust_coins(1)
            return f"EVENT: {card.name} — everyone gains 1 coin."

        case "storm":
            results = []
            for p in state.players:
                if p.coins >= 1:
                    p.adjust_coins(-1)
                    results.append(f"{p.name} pays 1 coin")
                else:
                    p.adjust_rep(-1)
                    results.append(f"{p.name} loses 1 Rep")
            return f"EVENT: {card.name} — {'; '.join(results)}."

        case "rumor":
            # Simplified: player just loses 1 rep (vouch mechanic is interactive)
            player.adjust_rep(-1)
            return f"EVENT: {card.name} — {player.name} loses 1 Rep. (Vouch mechanic: interactive.)"

        case "big_order":
            state.market.food += 1
            state.market.wood += 1
            state.market.tools += 1
            return f"EVENT: {card.name} — Market prices +1 this round."

        case "festival_of_plenty":
            return f"EVENT: {card.name} — Next 2 Festival landings give +2 Rep."

        case "swindle":
            n = player.name
            return f"EVENT: {card.name} -- {n} may force a voucher redemption."

        case "windfall":
            player.adjust_coins(3)
            return f"EVENT: {card.name} — {player.name} gains 3 coins."

        case "drought":
            return f"EVENT: {card.name} — No Market purchases this round."

        case "trust_crisis":
            affected = [p for p in state.players if p.reputation < 3]
            for p in affected:
                p.adjust_rep(-1)
            names = [p.name for p in affected] or ["no one"]
            return f"EVENT: {card.name} — {', '.join(names)} loses 1 Rep."

        case _:
            return f"EVENT: {card.name} — unknown effect '{eid}'."


# ---------------------------------------------------------------------------
# Help Desk (interactive helper)
# ---------------------------------------------------------------------------


def resolve_help_desk(state: GameState, helper: PlayerState, target: PlayerState) -> str:
    """Helper gives target 1 coin; both gain +1 Rep."""
    if helper.coins < 1:
        return f"{helper.name} can't afford to help (0 coins)."
    helper.adjust_coins(-1)
    target.adjust_coins(1)
    helper.adjust_rep(1)
    target.adjust_rep(1)
    h, t = helper.name, target.name
    msg = f"{h} helps {t}. -1 coin for {h}, +1 coin for {t}, both +1 Rep."
    state.add_log(msg)
    return msg


# ---------------------------------------------------------------------------
# Voucher operations
# ---------------------------------------------------------------------------

_voucher_counter = 0


def issue_voucher(
    state: GameState,
    issuer: PlayerState,
    holder: PlayerState,
    template: VoucherCard,
    face_value: int | None = None,
    deadline_rounds: int | None = None,
) -> Voucher | str:
    """Issue a voucher from issuer to holder. Returns Voucher or error string."""
    global _voucher_counter

    if not issuer.can_issue_voucher():
        return f"{issuer.name} can't issue vouchers (Rep {issuer.reputation} < 2)."

    fv = face_value if template.negotiable and face_value is not None else template.face_value
    dr = deadline_rounds if template.negotiable and deadline_rounds is not None else template.deadline_rounds  # noqa: E501
    template.default_penalty_rep if not template.negotiable else max(1, (fv + 1) // 2)

    _voucher_counter += 1
    v = Voucher(
        voucher_id=f"v_{_voucher_counter:04d}",
        template_id=template.id,
        issuer=issuer.name,
        holder=holder.name,
        face_value=fv,
        deadline_round=state.current_round + dr,
    )
    issuer.vouchers_issued.append(v)
    holder.vouchers_held.append(v)
    dl = v.deadline_round
    msg = f"{issuer.name} issues voucher to {holder.name}: {fv} coins, due R{dl}."
    state.add_log(msg)
    return v


def redeem_voucher(state: GameState, voucher: Voucher) -> str:
    """Holder redeems a voucher. Issuer pays or defaults."""
    issuer = next((p for p in state.players if p.name == voucher.issuer), None)
    holder = next((p for p in state.players if p.name == voucher.holder), None)
    if not issuer or not holder:
        return "Invalid voucher: player not found."
    if voucher.status != VoucherStatus.ACTIVE:
        return f"Voucher {voucher.voucher_id} is already {voucher.status.value}."

    pay_amount = voucher.face_value
    if issuer.is_trusted_issuer():
        pay_amount += 1  # trusted issuer bonus

    if issuer.coins >= pay_amount:
        issuer.adjust_coins(-pay_amount)
        holder.adjust_coins(pay_amount)
        voucher.status = VoucherStatus.REDEEMED
        msg = f"Voucher redeemed: {issuer.name} pays {pay_amount} to {holder.name}."
    else:
        voucher.status = VoucherStatus.DEFAULTED
        # Find penalty from template (simplified: use face_value // 2 + 1)
        penalty = max(1, (voucher.face_value + 1) // 2)
        issuer.adjust_rep(-penalty)
        msg = f"Voucher DEFAULT: {issuer.name} can't pay {pay_amount}. -{penalty} Rep."

    state.add_log(msg)
    return msg


def check_voucher_deadlines(state: GameState) -> list[str]:
    """Check all active vouchers for deadline expiry. Call at end of each round."""
    messages = []
    for player in state.players:
        for v in player.vouchers_issued:
            if v.status == VoucherStatus.ACTIVE and state.current_round > v.deadline_round:
                v.status = VoucherStatus.DEFAULTED
                penalty = max(1, (v.face_value + 1) // 2)
                player.adjust_rep(-penalty)
                msg = f"Voucher expired: {player.name} defaults on {v.voucher_id}. -{penalty} Rep."
                state.add_log(msg)
                messages.append(msg)
    return messages


# ---------------------------------------------------------------------------
# Deal operations
# ---------------------------------------------------------------------------

_deal_counter = 0


def accept_deal(state: GameState, player: PlayerState, card: DealCard) -> ActiveDeal:
    """Player accepts a deal card."""
    global _deal_counter
    _deal_counter += 1
    deal = ActiveDeal(
        deal_id=f"d_{_deal_counter:04d}",
        template_id=card.id,
        player=player.name,
        deadline_round=state.current_round + card.deadline_rounds,
        reward_coins=card.reward_coins,
        reward_rep=card.reward_rep,
        penalty_rep=card.penalty_rep,
    )
    player.active_deals.append(deal)
    state.add_log(f"{player.name} accepts deal: {card.name} (due round {deal.deadline_round})")
    return deal


def complete_deal(state: GameState, player: PlayerState, deal: ActiveDeal) -> str:
    """Mark a deal as completed and award the reward."""
    if deal.status != DealStatus.ACTIVE:
        return f"Deal {deal.deal_id} is already {deal.status.value}."
    deal.status = DealStatus.COMPLETED
    player.adjust_coins(deal.reward_coins)
    player.adjust_rep(deal.reward_rep)
    rc, rr = deal.reward_coins, deal.reward_rep
    msg = f"{player.name} completes deal {deal.deal_id}. +{rc} coins, +{rr} Rep."
    state.add_log(msg)
    return msg


def check_deal_deadlines(state: GameState) -> list[str]:
    """Check all active deals for deadline expiry. Call at end of each round."""
    messages = []
    for player in state.players:
        for d in player.active_deals:
            if d.status == DealStatus.ACTIVE and state.current_round > d.deadline_round:
                d.status = DealStatus.FAILED
                player.adjust_rep(-d.penalty_rep)
                msg = f"Deal expired: {player.name} fails {d.deal_id}. -{d.penalty_rep} Rep."
                state.add_log(msg)
                messages.append(msg)
    return messages

"""Core data models for Sovereignty."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WinCondition(StrEnum):
    PROSPERITY = "prosperity"  # 20 coins
    BELOVED = "beloved"  # 10 reputation
    BUILDER = "builder"  # 4 upgrades


class SpaceKind(StrEnum):
    CAMPFIRE = "campfire"
    WORKSHOP = "workshop"
    MARKET = "market"
    RUMOR_MILL = "rumor_mill"
    TRADE_DOCK = "trade_dock"
    FESTIVAL = "festival"
    TROUBLE = "trouble"
    HELP_DESK = "help_desk"
    MINT = "mint"
    BUILDER = "builder"
    FAUCET = "faucet"
    TAXMAN = "taxman"
    COMMONS = "commons"
    CROSSROADS = "crossroads"


class CardType(StrEnum):
    EVENT = "event"
    DEAL = "deal"
    VOUCHER = "voucher"


class VoucherStatus(StrEnum):
    ACTIVE = "active"
    REDEEMED = "redeemed"
    DEFAULTED = "defaulted"


class DealStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


@dataclass
class Space:
    index: int
    name: str
    kind: SpaceKind
    description: str


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------


@dataclass
class Card:
    id: str
    name: str
    card_type: CardType
    description: str
    flavor: str = ""


@dataclass
class EventCard(Card):
    effect_id: str = ""  # maps to a handler in the rules module


@dataclass
class DealCard(Card):
    reward_coins: int = 0
    reward_rep: int = 0
    penalty_rep: int = 0
    deadline_rounds: int = 0


@dataclass
class VoucherCard(Card):
    face_value: int = 0
    deadline_rounds: int = 0
    default_penalty_rep: int = 0
    negotiable: bool = False


# ---------------------------------------------------------------------------
# Voucher instance (issued during play)
# ---------------------------------------------------------------------------


@dataclass
class Voucher:
    voucher_id: str
    template_id: str  # references VoucherCard.id
    issuer: str  # player name
    holder: str  # player name
    face_value: int
    deadline_round: int  # absolute round number
    status: VoucherStatus = VoucherStatus.ACTIVE


# ---------------------------------------------------------------------------
# Deal instance (accepted during play)
# ---------------------------------------------------------------------------


@dataclass
class ActiveDeal:
    deal_id: str
    template_id: str  # references DealCard.id
    player: str
    deadline_round: int
    status: DealStatus = DealStatus.ACTIVE
    reward_coins: int = 0
    reward_rep: int = 0
    penalty_rep: int = 0


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

REP_MIN = 0
REP_MAX = 10
STARTING_COINS = 5
STARTING_REP = 3


@dataclass
class PlayerState:
    name: str
    coins: int = STARTING_COINS
    reputation: int = STARTING_REP
    upgrades: int = 0
    position: int = 0  # board space index
    win_condition: WinCondition = WinCondition.PROSPERITY
    vouchers_held: list[Voucher] = field(default_factory=list)
    vouchers_issued: list[Voucher] = field(default_factory=list)
    active_deals: list[ActiveDeal] = field(default_factory=list)

    def adjust_coins(self, amount: int) -> int:
        """Add/subtract coins. Returns actual change (can't go below 0)."""
        old = self.coins
        self.coins = max(0, self.coins + amount)
        return self.coins - old

    def adjust_rep(self, amount: int) -> int:
        """Add/subtract reputation. Clamped to [0, 10]. Returns actual change."""
        old = self.reputation
        self.reputation = max(REP_MIN, min(REP_MAX, self.reputation + amount))
        return self.reputation - old

    def can_issue_voucher(self) -> bool:
        return self.reputation >= 2

    def can_use_builder(self) -> bool:
        return self.reputation >= 3

    def is_trusted_issuer(self) -> bool:
        return self.reputation >= 5

    def has_won(self) -> bool:
        if self.win_condition == WinCondition.PROSPERITY:
            return self.coins >= 20
        if self.win_condition == WinCondition.BELOVED:
            return self.reputation >= 10
        if self.win_condition == WinCondition.BUILDER:
            return self.upgrades >= 4
        return False


# ---------------------------------------------------------------------------
# Deck
# ---------------------------------------------------------------------------


@dataclass
class Deck:
    draw_pile: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)

    def draw(self, rng: Any) -> Card | None:
        """Draw the top card. Reshuffles discard if draw pile is empty."""
        if not self.draw_pile and self.discard_pile:
            self.draw_pile = list(self.discard_pile)
            self.discard_pile.clear()
            rng.shuffle(self.draw_pile)
        if not self.draw_pile:
            return None
        card = self.draw_pile.pop(0)
        return card

    def discard(self, card: Card) -> None:
        self.discard_pile.append(card)


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------


@dataclass
class MarketPrices:
    food: int = 1
    wood: int = 2
    tools: int = 3

    def as_dict(self) -> dict[str, int]:
        return {"food": self.food, "wood": self.wood, "tools": self.tools}


# ---------------------------------------------------------------------------
# Game config + state
# ---------------------------------------------------------------------------

BOARD_SIZE = 16
MAX_ROUNDS = 15


@dataclass
class GameConfig:
    seed: int
    ruleset: str = "campfire_v1"
    max_players: int = 4
    max_rounds: int = MAX_ROUNDS
    board_size: int = BOARD_SIZE


@dataclass
class GameState:
    config: GameConfig
    players: list[PlayerState] = field(default_factory=list)
    board: list[Space] = field(default_factory=list)
    event_deck: Deck = field(default_factory=Deck)
    deal_deck: Deck = field(default_factory=Deck)
    market: MarketPrices = field(default_factory=MarketPrices)
    current_round: int = 1
    current_player_index: int = 0
    turn_in_round: int = 0
    game_over: bool = False
    winner: str | None = None
    log: list[str] = field(default_factory=list)

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def add_log(self, message: str) -> None:
        self.log.append(f"R{self.current_round}T{self.turn_in_round}: {message}")

    def advance_turn(self) -> None:
        """Move to the next player. If everyone has gone, advance the round."""
        self.turn_in_round += 1
        self.current_player_index += 1
        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
            self.turn_in_round = 0
            self.current_round += 1
            if self.current_round > self.config.max_rounds:
                self._resolve_tiebreak()

    def _resolve_tiebreak(self) -> None:
        """After max rounds, highest combined score wins."""
        self.game_over = True

        def score(p: PlayerState) -> float:
            return (p.coins / 2) + p.reputation + (p.upgrades * 3)

        best = max(self.players, key=score)
        self.winner = best.name
        self.add_log(f"Time's up! {best.name} wins by tiebreak (score: {score(best):.1f})")

    def check_winner(self) -> str | None:
        """Check if any player has achieved their win condition."""
        for p in self.players:
            if p.has_won():
                self.game_over = True
                self.winner = p.name
                self.add_log(
                    f"{p.name} wins by {p.win_condition.value}!"
                )
                return p.name
        return None

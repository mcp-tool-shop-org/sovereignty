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


class TreatyStatus(StrEnum):
    ACTIVE = "active"
    KEPT = "kept"
    BROKEN = "broken"


# ---------------------------------------------------------------------------
# Treaty constants
# ---------------------------------------------------------------------------

MAX_ACTIVE_TREATIES = 2
STAKE_CAP_COINS = 5
STAKE_CAP_RESOURCES = 3
TREATY_REP_PENALTY = -3
TREATY_REP_BONUS = 1


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
    tags: tuple[str, ...] = ()  # content tags for session recipe filtering


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
# Stake + Treaty (issued during play)
# ---------------------------------------------------------------------------


@dataclass
class Stake:
    """Collateral put up for a treaty."""

    coins: int = 0
    resources: dict[str, int] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return self.coins == 0 and not any(v > 0 for v in self.resources.values())

    def total_value(self) -> int:
        return self.coins + sum(self.resources.values())


@dataclass
class Treaty:
    """A binding agreement between two players with escrowed stakes."""

    treaty_id: str
    text: str
    parties: list[str]  # exactly 2 player names
    stakes: dict[str, Stake]  # player_name -> their stake
    deadline_round: int  # absolute round number
    status: TreatyStatus = TreatyStatus.ACTIVE
    created_round: int = 0


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

REP_MIN = 0
REP_MAX = 10
STARTING_COINS = 5
STARTING_REP = 3


RESOURCE_NAMES = ("food", "wood", "tools")


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
    promises: list[str] = field(default_factory=list)  # active promise texts
    helped_last_round: bool = False  # for "Good News Travels" event
    skip_next_move: bool = False  # for "Broken Bridge" event
    apology_used: bool = False  # once per game
    toasted: bool = False  # once per game — The Toast
    resources: dict[str, int] = field(default_factory=dict)  # Town Hall: food/wood/tools
    active_treaties: list[Treaty] = field(default_factory=list)

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

MARKET_BASE_PRICE = 2
MARKET_PRICE_MIN = 1
MARKET_PRICE_MAX = 4


def _supply_pool_size(num_players: int) -> int:
    """Supply per resource based on player count: 2p=6, 3p=8, 4p=10."""
    return 4 + (num_players * 2)


@dataclass
class MarketPrices:
    """Simple price tracker (Campfire tier — prices reset each round)."""

    food: int = 1
    wood: int = 2
    tools: int = 3

    def as_dict(self) -> dict[str, int]:
        return {"food": self.food, "wood": self.wood, "tools": self.tools}


@dataclass
class MarketBoard:
    """Market board with supply pools. Fixed or dynamic pricing."""

    supply: dict[str, int] = field(default_factory=dict)
    base_prices: dict[str, int] = field(default_factory=dict)
    price_shifts: dict[str, int] = field(default_factory=dict)
    fixed_prices: bool = False  # Market Day: no scarcity, no shifts

    @classmethod
    def create(cls, num_players: int, *, fixed: bool = False) -> MarketBoard:
        """Create a market board. fixed=True for Market Day (store prices)."""
        pool = 999 if fixed else _supply_pool_size(num_players)
        return cls(
            supply={r: pool for r in RESOURCE_NAMES},
            base_prices={r: MARKET_BASE_PRICE for r in RESOURCE_NAMES},
            price_shifts={r: 0 for r in RESOURCE_NAMES},
            fixed_prices=fixed,
        )

    def price(self, resource: str) -> int:
        """Effective price. Fixed mode: always base. Dynamic: base + shift + scarcity."""
        base = self.base_prices.get(resource, MARKET_BASE_PRICE)
        if self.fixed_prices:
            return base
        shift = self.price_shifts.get(resource, 0)
        scarcity = 1 if self.supply.get(resource, 0) <= 2 else 0
        return max(MARKET_PRICE_MIN, min(MARKET_PRICE_MAX, base + shift + scarcity))

    def can_buy(self, resource: str) -> bool:
        """True if any supply remains."""
        return self.supply.get(resource, 0) > 0

    def buy(self, resource: str) -> int:
        """Remove 1 from supply, return effective price. Caller pays."""
        if not self.can_buy(resource):
            return -1
        cost = self.price(resource)
        self.supply[resource] -= 1
        return cost

    def sell(self, resource: str) -> int:
        """Add 1 to supply, return sell price (1 below buy price)."""
        base = self.base_prices.get(resource, MARKET_BASE_PRICE)
        if self.fixed_prices:
            sell_price = max(1, base - 1)
        else:
            shift = self.price_shifts.get(resource, 0)
            sell_price = max(1, base + shift - 1)
        self.supply[resource] = self.supply.get(resource, 0) + 1
        return sell_price

    def shift_price(self, resource: str, amount: int) -> None:
        """Shift a resource price. No-op in fixed-price mode."""
        if self.fixed_prices:
            return
        self.price_shifts[resource] = self.price_shifts.get(resource, 0) + amount

    def reset_shifts(self) -> None:
        """Clear event-driven price shifts at end of round."""
        for r in self.price_shifts:
            self.price_shifts[r] = 0


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
    market_board: MarketBoard | None = None  # Town Hall only
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

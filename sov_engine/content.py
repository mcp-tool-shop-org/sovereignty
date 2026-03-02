"""Card and board content for Campfire v1."""

from __future__ import annotations

from sov_engine.models import (
    Card,
    CardType,
    DealCard,
    EventCard,
    Space,
    SpaceKind,
    VoucherCard,
)


def build_board() -> list[Space]:
    """Create the 16-space Campfire board."""
    return [
        Space(0, "Campfire", SpaceKind.CAMPFIRE, "Safe. Collect 1 coin if you pass through."),
        Space(1, "Workshop", SpaceKind.WORKSHOP, "Pay 2 coins to gain 1 Upgrade."),
        Space(2, "Market", SpaceKind.MARKET, "Buy or sell 1 resource at Market Price."),
        Space(3, "Rumor Mill", SpaceKind.RUMOR_MILL, "Draw an Event card."),
        Space(4, "Trade Dock", SpaceKind.TRADE_DOCK, "Propose a trade with any player."),
        Space(5, "Festival", SpaceKind.FESTIVAL, "Donate 1 coin to gain +1 Reputation."),
        Space(6, "Trouble", SpaceKind.TROUBLE, "Lose 1 coin OR lose 1 Reputation."),
        Space(7, "Help Desk", SpaceKind.HELP_DESK, "Give another player 1 coin; both gain +1 Rep."),
        Space(8, "Mint", SpaceKind.MINT, "Gain 2 coins from the bank."),
        Space(9, "Rumor Mill", SpaceKind.RUMOR_MILL, "Draw an Event card."),
        Space(10, "Builder", SpaceKind.BUILDER, "Pay 3 coins for 1 Upgrade. Requires Rep >= 3."),
        Space(11, "Faucet", SpaceKind.FAUCET, "Gain 1 coin from the bank."),
        Space(12, "Trade Dock", SpaceKind.TRADE_DOCK, "Propose a trade with any player."),
        Space(13, "Taxman", SpaceKind.TAXMAN, "Pay 1 coin. Can't pay? Lose 1 Rep instead."),
        Space(14, "Commons", SpaceKind.COMMONS, "Vote: if majority agrees, everyone gains 1 coin."),
        Space(15, "Crossroads", SpaceKind.CROSSROADS, "Draw a Deal card. Accept or pass."),
    ]


def build_event_deck() -> list[Card]:
    """Create the 10 Event cards for Campfire v1."""
    return [
        EventCard(
            id="evt_01",
            name="Supply Delay",
            card_type=CardType.EVENT,
            description="Upgrades cost +1 coin this round.",
            flavor="The shipment's late. Again.",
            effect_id="supply_delay",
        ),
        EventCard(
            id="evt_02",
            name="Boom Town",
            card_type=CardType.EVENT,
            description="Every player gains 1 coin.",
            flavor="Trade is good. Everyone's eating.",
            effect_id="boom_town",
        ),
        EventCard(
            id="evt_03",
            name="Storm",
            card_type=CardType.EVENT,
            description="Every player must pay 1 coin or lose 1 Reputation.",
            flavor="Batten down the hatches.",
            effect_id="storm",
        ),
        EventCard(
            id="evt_04",
            name="Rumor",
            card_type=CardType.EVENT,
            description="Lose 1 Rep unless another player vouches for you (they risk 1 Rep).",
            flavor="People are talking...",
            effect_id="rumor",
        ),
        EventCard(
            id="evt_05",
            name="Big Order",
            card_type=CardType.EVENT,
            description="Market prices +1 this round.",
            flavor="A caravan just arrived with deep pockets.",
            effect_id="big_order",
        ),
        EventCard(
            id="evt_06",
            name="Festival of Plenty",
            card_type=CardType.EVENT,
            description="Next 2 Festival landings give +2 Rep instead of +1.",
            flavor="The whole town is celebrating.",
            effect_id="festival_of_plenty",
        ),
        EventCard(
            id="evt_07",
            name="Swindle",
            card_type=CardType.EVENT,
            description="Force one voucher redemption NOW (issuer pays or loses 2 Rep).",
            flavor="Time to collect.",
            effect_id="swindle",
        ),
        EventCard(
            id="evt_08",
            name="Windfall",
            card_type=CardType.EVENT,
            description="You gain 3 coins.",
            flavor="Lucky day.",
            effect_id="windfall",
        ),
        EventCard(
            id="evt_09",
            name="Drought",
            card_type=CardType.EVENT,
            description="No one can buy at the Market this round.",
            flavor="Nothing on the shelves.",
            effect_id="drought",
        ),
        EventCard(
            id="evt_10",
            name="Trust Crisis",
            card_type=CardType.EVENT,
            description="All players with Rep < 3 lose 1 additional Rep.",
            flavor="When trust is low, it falls further.",
            effect_id="trust_crisis",
        ),
    ]


def build_deal_deck() -> list[Card]:
    """Create the 10 Deal/Voucher cards for Campfire v1."""
    deals: list[Card] = [
        DealCard(
            id="deal_01",
            name="Supply Run",
            card_type=CardType.DEAL,
            description="Deliver 3 coins to any other player within 2 rounds.",
            reward_coins=0,
            reward_rep=2,
            penalty_rep=1,
            deadline_rounds=2,
        ),
        DealCard(
            id="deal_02",
            name="Builder's Promise",
            card_type=CardType.DEAL,
            description="Build 1 Upgrade within 3 rounds.",
            reward_coins=1,
            reward_rep=1,
            penalty_rep=1,
            deadline_rounds=3,
        ),
        DealCard(
            id="deal_03",
            name="Generosity Pledge",
            card_type=CardType.DEAL,
            description="Give 1 coin to each other player (this turn or next).",
            reward_coins=0,
            reward_rep=3,
            penalty_rep=2,
            deadline_rounds=2,
        ),
        DealCard(
            id="deal_04",
            name="Market Watcher",
            card_type=CardType.DEAL,
            description="Buy or sell at Market on your next 2 Market landings.",
            reward_coins=2,
            reward_rep=1,
            penalty_rep=1,
            deadline_rounds=4,
        ),
        DealCard(
            id="deal_05",
            name="Peacekeeper",
            card_type=CardType.DEAL,
            description="Help at least 1 player at Help Desk within 3 rounds.",
            reward_coins=0,
            reward_rep=2,
            penalty_rep=1,
            deadline_rounds=3,
        ),
    ]
    vouchers: list[Card] = [
        VoucherCard(
            id="vouch_01",
            name="Small Loan",
            card_type=CardType.VOUCHER,
            description="IOU: 2 coins, due within 3 rounds.",
            face_value=2,
            deadline_rounds=3,
            default_penalty_rep=2,
        ),
        VoucherCard(
            id="vouch_02",
            name="Big Loan",
            card_type=CardType.VOUCHER,
            description="IOU: 4 coins, due within 4 rounds.",
            face_value=4,
            deadline_rounds=4,
            default_penalty_rep=3,
        ),
        VoucherCard(
            id="vouch_03",
            name="Favor Owed",
            card_type=CardType.VOUCHER,
            description="IOU: 1 coin + free Help Desk action, due within 3 rounds.",
            face_value=1,
            deadline_rounds=3,
            default_penalty_rep=2,
        ),
        VoucherCard(
            id="vouch_04",
            name="Trade Credit",
            card_type=CardType.VOUCHER,
            description="IOU: 3 coins, redeemable only at Trade Dock.",
            face_value=3,
            deadline_rounds=4,
            default_penalty_rep=2,
        ),
        VoucherCard(
            id="vouch_05",
            name="Blank Voucher",
            card_type=CardType.VOUCHER,
            description="Negotiable IOU: 1-5 coins, 1-5 rounds.",
            face_value=0,
            deadline_rounds=0,
            default_penalty_rep=0,
            negotiable=True,
        ),
    ]
    return deals + vouchers

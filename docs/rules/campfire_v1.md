# Sovereignty: Campfire — Tier 1 Rules (v1)

## Overview

2–4 players. ~30 minutes. No devices required.

You're building a small community. Trade, keep your promises, and earn the trust
of your neighbors — or don't, and see what happens.

## Setup

1. Each player starts with **5 Coins** and **3 Reputation**.
2. Place all players on space 0 (Campfire).
3. Shuffle the Event deck (face down) and the Deal deck (face down).
4. Each player picks a **victory path** (secret or public, group decides):
   - **Prosperity:** First to reach 20 Coins.
   - **Beloved:** First to reach 10 Reputation.
   - **Builder:** First to complete 4 Upgrades.
5. Determine turn order (youngest first, or roll dice).

## Turn loop

On your turn:

1. **Roll** a d6.
2. **Move** that many spaces clockwise around the board.
3. **Resolve** the space you land on (see Board reference).
4. **Optional trade:** propose one trade to any other player (coins, vouchers, resources).
5. **End turn.** Play passes clockwise.

## Meters

### Coins
- Spent to buy upgrades, pay costs, and fulfill deals.
- Gained from spaces, events, and trades.
- **No maximum.** Minimum is 0 (you can't go negative).
- If you must pay coins and can't, you lose 1 Reputation instead per coin owed.

### Reputation
- Represents how much others trust you.
- **Range: 0 to 10.** Can't go below 0 or above 10.
- Gained by helping others, fulfilling deals, and redeeming vouchers on time.
- Lost by breaking deals, defaulting on vouchers, and bad events.

### Reputation gates
- **Rep < 2:** You cannot issue new Vouchers. Others won't trust your promises.
- **Rep >= 3:** Required to use the Builder space (space 10).
- **Rep >= 5:** Your Vouchers are worth face value +1 (trusted issuer bonus).
- **Rep >= 8:** You may propose trades to 2 players per turn instead of 1.

## Upgrades

- Purchased at Workshop (2 coins) or Builder (3 coins, requires Rep >= 3).
- Track upgrades on your player mat.
- Upgrades have no gameplay effect in Tier 1 — they're purely a victory condition.
- (In Tier 2, upgrades will grant abilities.)

## Vouchers

A Voucher is a promise: "I will pay you X coins by round Y."

### Issuing
- Any player with Rep >= 2 can issue a Voucher during a trade.
- Write the face value (coins owed) and deadline (round number) on the card.
- Hand the Voucher to the other player.

### Transferring
- Vouchers can be traded to other players like any asset.
- The issuer's obligation doesn't change — they still owe the holder.

### Redeeming
- The holder may present the Voucher on any turn (theirs or the issuer's).
- The issuer must pay the face value immediately.
- If the issuer has Rep >= 5, they pay face value +1 (trusted issuer bonus).

### Default
- If the deadline passes and the Voucher hasn't been redeemed or paid:
  - The issuer **automatically defaults**.
  - The issuer loses Reputation equal to the penalty on the Voucher card.
  - The holder gets nothing (the Voucher is discarded).
- If the issuer can't pay when the Voucher is presented:
  - Same as default. Issuer loses Rep, Voucher is discarded.

## Deals

- Drawn at Crossroads (space 15).
- You may **accept** (commit to the terms) or **pass** (discard, no penalty).
- If accepted, track the Deal on your player mat with the deadline.
- Complete it by the deadline → gain the reward.
- Fail to complete → suffer the penalty.

## Events

- Drawn at Rumor Mill (spaces 3 and 9).
- Resolve immediately. Effects last "this round" unless stated otherwise.
- A **round** = one full cycle of all players taking a turn.

## Market

Simple market with 3 posted prices. Prices start at:
- **Food:** 1 coin
- **Wood:** 2 coins
- **Tools:** 3 coins

When you land on Market (space 2), you may buy or sell 1 resource at the posted price.
- Resources have no inherent use in Tier 1 — they're trade goods.
- Event cards may shift prices temporarily.

## Winning

The first player to achieve their chosen victory condition wins:
- **Prosperity:** Hold 20+ Coins at the start of your turn.
- **Beloved:** Hold 10 Reputation at the start of your turn.
- **Builder:** Have 4+ Upgrades at the start of your turn.

If no one has won after 15 rounds, the player with the highest combined score wins:
`(Coins / 2) + (Reputation) + (Upgrades * 3)`

## Round tracking

A **round** begins when the first player starts their turn and ends when
the last player finishes. Track the current round number.

At the end of each round, the CLI assistant (if used) can produce a
**Round Proof** — a JSON file that captures the game state and can be
independently verified.

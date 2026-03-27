---
title: How to Play
description: Core rules — promises, trading, goals, and the apology.
sidebar:
  order: 2
---

Sovereignty teaches through consequences, not terminology. Here's how a game works.

## Setup

Each player starts with **5 coins** and **3 reputation** (clamped between 0 and 10). The board has 16 spaces arranged in a loop. Roll a die, move forward, and land on spaces that give you choices: trade, help someone, take a risk, or draw a card.

## Cards

**28 Event cards** read like moments — situations that affect all players or force individual choices. The deck includes 20 core events and 8 market-shift events that trigger in Town Hall games.

**12 Deal cards** force conversation — offers, trades, and agreements between players. Each deal has a deadline and a reward for completion, plus a reputation penalty for failure.

**10 Voucher cards** are IOUs you issue to another player. You need at least 2 reputation to issue a voucher. If you default, you lose reputation. Trusted issuers (reputation 5 or higher) pay a bonus when redeeming.

## The promise rule

Once per round, say "I promise..." out loud and commit to something specific. The table decides if you kept it:

- **Keep your promise:** +1 reputation
- **Break your promise:** -2 reputation

## The apology

Once per game, if you broke a promise, you can publicly apologize. Pay 1 coin to the person you wronged, and regain +1 reputation.

## Goals

Pick a goal at the start — secret or public:

| Goal | Win condition |
|------|-------------|
| **Prosperity** | Reach 20 coins |
| **Beloved** | Reach 10 reputation |
| **Builder** | Complete 4 upgrades |

## Winning

A player wins immediately by achieving their chosen goal (20 coins for Prosperity, 10 reputation for Beloved, 4 upgrades for Builder). If nobody achieves their goal after 15 rounds, the highest combined score wins. The tiebreak formula weighs coins, reputation, and upgrades: `(coins / 2) + reputation + (upgrades * 3)`.

## The board

The board has 16 spaces arranged in a loop. Some space types appear more than once (Rumor Mill is at positions 3 and 9, Trade Dock at 4 and 12). When you pass through or land on Campfire (position 0), you gain 1 coin.

| Space | Effect |
|-------|--------|
| **Campfire** (0) | Safe. +1 coin when you pass through or land on it |
| **Workshop** (1) | Pay 2 coins for +1 upgrade |
| **Market** (2) | Buy or sell 1 resource at market price |
| **Rumor Mill** (3, 9) | Draw an Event card |
| **Trade Dock** (4, 12) | Propose a trade with any player |
| **Festival** (5) | Donate 1 coin for +1 reputation |
| **Trouble** (6) | Lose 1 coin or 1 reputation |
| **Help Desk** (7) | Give another player 1 coin; both gain +1 reputation |
| **Mint** (8) | Gain 2 coins from the bank |
| **Builder** (10) | Pay 3 coins for +1 upgrade (requires reputation 3 or higher) |
| **Faucet** (11) | Gain 1 coin from the bank |
| **Taxman** (13) | Pay 1 coin, or lose 1 reputation if broke |
| **Commons** (14) | Vote: if majority agrees, everyone gains 1 coin |
| **Crossroads** (15) | Draw a Deal card. Accept or pass |

## The Toast

Once per game, anyone at the table can raise a toast to a player. Name something they did right. The toasted player gains +1 reputation. Each player can only be toasted once.

```bash
sov toast Alice
```

## Recipes

Recipes set the mood for a session by filtering the card deck:

```bash
sov new --recipe cozy -p Alice -p Bob
```

Available recipes: `cozy`, `spicy`, `market`, `promise`.

---
title: How to Play
description: Core rules — promises, trading, goals, and the apology.
sidebar:
  order: 2
---

Sovereignty teaches through consequences, not terminology. Here's how a game works.

## Setup

Each player starts with **5 coins** and **3 reputation**. The board has 16 spaces. Roll a die, move, and land on spaces that give you choices: trade, help someone, take a risk, or draw a card.

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

After 15 rounds, the highest combined score wins. The tiebreak formula weighs coins, reputation, and upgrades: `(coins / 2) + reputation + (upgrades * 3)`. Your goal influences strategy, but the final score is what matters.

## The board

The board has 16 spaces. Each space has a distinct effect:

| Space | Effect |
|-------|--------|
| **Campfire** | Safe. +1 coin when you pass through or land on it |
| **Workshop** | Pay 2 coins for +1 upgrade |
| **Market** | Buy or sell 1 resource at market price |
| **Rumor Mill** | Draw an Event card |
| **Trade Dock** | Propose a trade with any player |
| **Festival** | Donate 1 coin for +1 reputation |
| **Trouble** | Lose 1 coin or 1 reputation |
| **Help Desk** | Give another player 1 coin; both gain +1 reputation |
| **Mint** | Gain 2 coins from the bank |
| **Builder** | Pay 3 coins for +1 upgrade (requires reputation 3 or higher) |
| **Faucet** | Gain 1 coin from the bank |
| **Taxman** | Pay 1 coin, or lose 1 reputation if broke |
| **Commons** | Vote: if majority agrees, everyone gains 1 coin |
| **Crossroads** | Draw a Deal card. Accept or pass |

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

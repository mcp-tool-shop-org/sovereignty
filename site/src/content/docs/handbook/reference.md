---
title: Reference
description: Full CLI command reference for the Sovereignty console.
sidebar:
  order: 5
---

## Game setup

| Command | Description |
|---------|-------------|
| `sov tutorial` | Learn to play in 60 seconds with a guided demo |
| `sov new -p <names>` | Start a new Campfire game |
| `sov new --recipe <name> -p <names>` | Start with a recipe (cozy/spicy/market/promise) |
| `sov new --tier <tier> -p <names>` | Pick a tier (campfire/market-day/town-hall/treaty-table) |
| `sov new --code "SOV\|..." -p <names>` | Play from a share code |
| `sov new --seed <n> -p <names>` | Set the RNG seed (default: 42) |

## Gameplay

| Command | Description |
|---------|-------------|
| `sov turn` | Roll, move, and resolve your space |
| `sov status` | Show current game state for all players |
| `sov board` | Show the board layout and player positions |
| `sov recap` | Review what happened this round |
| `sov end-round` | Generate a round proof (SHA-256 fingerprint) |

## Promises and social

| Command | Description |
|---------|-------------|
| `sov promise make "text"` | Make a promise out loud |
| `sov promise keep "text"` | Mark a promise as kept (+1 reputation) |
| `sov promise break "text"` | Mark a promise as broken (-2 reputation) |
| `sov apologize <player>` | Apologize for a broken promise (once per game, costs 1 coin, +1 reputation) |
| `sov offer "text" --to <player>` | Propose a trade to another player |
| `sov toast <player>` | Raise a toast (+1 reputation, once per player per game) |
| `sov vote mvp <player>` | Vote for Table's Choice (MVP) |
| `sov vote chaos <player>` | Vote for Chaos Gremlin |
| `sov vote promise "text"` | Vote for Best Promise |

## Treaties (Treaty Table tier only)

| Command | Description |
|---------|-------------|
| `sov treaty make "text" --with <player> --stake "amount"` | Create a binding treaty with escrowed stakes |
| `sov treaty keep <treaty_id>` | Mark a treaty as honored (stakes returned, +1 reputation each) |
| `sov treaty break <treaty_id>` | Break a treaty (breaker forfeits stake, -3 reputation) |
| `sov treaty list` | Show your active treaties |

## Market (Town Hall and Treaty Table tiers)

| Command | Description |
|---------|-------------|
| `sov market` | Show market prices and supply levels |
| `sov market buy <resource>` | Buy 1 resource (food/wood/tools) |
| `sov market sell <resource>` | Sell 1 resource back to the market |

## Scenario commands

| Command | Description |
|---------|-------------|
| `sov scenario list` | Browse available scenario packs |
| `sov scenario code <name> -s <seed>` | Generate a share code |
| `sov scenario lint` | Validate scenario files |

## Diary Mode (XRPL Testnet)

| Command | Description |
|---------|-------------|
| `sov wallet` | Create a funded Testnet wallet (free) |
| `sov anchor [proof_file]` | Post proof hash to XRPL Testnet (default: latest proof) |
| `sov verify <proof_file> --tx <txid>` | Verify a proof against an on-chain record |

## End of game

| Command | Description |
|---------|-------------|
| `sov game-end` | Final scores, Story Points, and season update |
| `sov postcard` | Shareable game summary for screenshots |
| `sov season-postcard` | Season standings across multiple games |

## Diagnostics

| Command | Description |
|---------|-------------|
| `sov doctor` | Pre-flight check before play night |
| `sov self-check` | Diagnose your environment (paste into bug reports) |
| `sov support-bundle` | Write a diagnostic zip for bug reports |
| `sov feedback` | Generate an issue-ready play report |
| `sov --version` | Show version and exit |

## Links

The links below open on GitHub (external — leaves this site).

- [GitHub Repository](https://github.com/mcp-tool-shop-org/sovereignty) — source code and releases
- [Full Rules (Campfire v1)](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/rules/campfire_v1.md) — the canonical rule reference
- [Print & Play](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/print-and-play.md) — print the cards and play tabletop
- [Report a bug or ask a question](https://github.com/mcp-tool-shop-org/sovereignty/issues/new/choose) — pick the matching template

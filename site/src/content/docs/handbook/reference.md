---
title: Reference
description: Full CLI command reference for the Sovereignty console.
sidebar:
  order: 5
---

## Game commands

| Command | Description |
|---------|-------------|
| `sov tutorial` | Learn in 60 seconds |
| `sov new -p <names>` | Start a new game |
| `sov new --recipe <name> -p <names>` | Start with a recipe (cozy/spicy/market/promise) |
| `sov new --tier <tier> -p <names>` | Pick a tier directly |
| `sov new --code "SOV\|..." -p <names>` | Play from a share code |
| `sov turn` | Roll, land, resolve |
| `sov end-round` | Generate round proof |
| `sov recap` | What happened this round |
| `sov game-end` | Final scores + Story Points |

## Promise and treaty commands

| Command | Description |
|---------|-------------|
| `sov promise make "text"` | Make a promise out loud |
| `sov treaty make "name" --with <player> --stake "amount"` | Create a binding treaty |

## Scenario commands

| Command | Description |
|---------|-------------|
| `sov scenario list` | Browse scenario packs |
| `sov scenario code <name> -s <seed>` | Generate a share code |
| `sov scenario lint` | Validate scenario files |

## Diary mode commands

| Command | Description |
|---------|-------------|
| `sov wallet` | Create a Testnet wallet |
| `sov anchor` | Post proof hash to XRPL |
| `sov verify proof.json --tx <txid>` | Verify against on-chain record |

## Utility commands

| Command | Description |
|---------|-------------|
| `sov doctor` | Pre-flight check before play night |
| `sov postcard` | Shareable game summary |
| `sov feedback` | Issue-ready play report |
| `sov season-postcard` | Season standings across games |

## Links

- [GitHub Repository](https://github.com/mcp-tool-shop-org/sovereignty)
- [Full Rules (Campfire v1)](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/rules/campfire_v1.md)
- [Print & Play](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/print-and-play.md)

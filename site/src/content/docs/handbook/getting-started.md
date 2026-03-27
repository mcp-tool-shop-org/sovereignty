---
title: Getting Started
description: Install the Sovereignty console and play your first game.
sidebar:
  order: 1
---

Sovereignty can be played as a physical board game (print the cards, grab a die and coins) or with the digital console that keeps score.

## Install the console

No Python required — downloads a prebuilt binary:

```bash
npx @mcptoolshop/sovereignty tutorial
```

Or install with Python:

```bash
pipx install sovereignty-game
```

## Tutorial

Run the built-in tutorial to learn the basics:

```bash
sov tutorial
```

## Start a game

Create a new game with 2–4 players:

```bash
sov new -p Alice -p Bob -p Carol
```

Take turns:

```bash
sov turn
```

End a round and generate a proof:

```bash
sov end-round
```

## Print and play

For the physical version, print the cards and reference sheets from the `assets/print/` directory. You need:

- 28 Event cards (20 core + 8 market-shift for Town Hall)
- 22 Deal and Voucher cards (12 Deals + 10 Vouchers)
- A six-sided die
- Coins (real or tokens)

See the [full rules](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/rules/campfire_v1.md) for details.

## Next steps

- Learn the [core rules](/sovereignty/handbook/how-to-play/)
- Explore [tiers and scenarios](/sovereignty/handbook/tiers/)
- Try [Diary Mode](/sovereignty/handbook/diary-mode/) for on-chain verification

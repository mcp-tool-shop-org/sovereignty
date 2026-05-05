---
title: Print and Play
description: Print Sovereignty's full board game — board, cards, player mats, quick references — and play tonight without a screen.
sidebar:
  order: 7
---

Sit down with two or three friends. Print a few pages, find a die and some coins, and you have the whole game on the table in twenty minutes.

The print pack ships as ready-to-print PDFs with embedded fonts and crop marks where they matter. No drawing the board, no guessing margins — just hit print.

## The print pack

Grab everything in one document, or pull individual sheets:

- **[The whole package — Sovereignty-Print-Pack.pdf](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/Sovereignty-Print-Pack.pdf)** (11 pages) — print this and you're set.

Or per-artifact:

- [Board](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/board.pdf) — the 16-space Campfire loop, 1 page.
- [Player mat](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/mat.pdf) — coins, reputation, promises, upgrades. One per player.
- [Quick reference](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/quickref.pdf) — board spaces, turn order, promise rules, scoring.
- [Event cards](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/events.pdf) — 20 cards, 9-up grid, 3 pages.
- [Deal cards](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/deals.pdf) — 10 cards, 2 pages.
- [Voucher cards](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/vouchers.pdf) — 10 IOUs between players, 2 pages.
- [Treaty quick reference](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/pdf/treaty.pdf) — Tier 3 only.

## Which sheets do I need?

Depends on the tier you're playing.

| Tier | Print | Pages |
|------|---------------|-------|
| Campfire | Board + mat + quick ref + event cards + deal cards + voucher cards | 9 |
| Market Day | Same as Campfire (resources tracked on player mat) | 9 |
| Town Hall | Same as Campfire (market prices on the board margin) | 9 |
| Treaty Table | Everything above + treaty quick ref | 10 |

Print double-sided to save paper. New to the tiers? See [Tiers and Scenarios](/sovereignty/handbook/tiers/).

## What else you need

- One six-sided die.
- Roughly 40 coins or tokens — pennies, buttons, bottle caps, anything you can count.
- A position marker per player (different colored buttons, different coins).
- For Market Day / Town Hall / Treaty Table: resource tokens in three colors for food, wood, and tools.

That's the whole table.

## Print this page directly

This page itself is print-friendly. Hit **Cmd-P** (macOS) or **Ctrl-P** (Windows / Linux) and the site's print stylesheet will:

- Hide the navigation, sidebar, and footer.
- Switch to a serif body font for sustained reading.
- Show full URLs after links (useful when the printed page is the only reference at the table).
- Avoid awkward page breaks inside tables.

The full tier-by-tier setup walkthrough — coin counts, starting reputation, goal selection — lives in the [print-and-play guide](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/print-and-play.md) on GitHub.

## Re-rendering the PDFs

The visual contract — palette, typography, border treatment — is locked in [`docs/visual-language.md`](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/visual-language.md). Source files for re-rendering live in [`assets/print/source/`](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/assets/print/source/README.md) — JSX components, render scripts, and a step-by-step recipe for producing the PDFs from scratch with headless Chromium.

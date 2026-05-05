# Sovereignty — Print & Play

Everything you need to play tonight. No screens at the table.

## What to print

The full Tier 1 print pack ships as ready-to-print PDFs. One file per artifact, plus a combined Sovereignty-Print-Pack.pdf with all 11 sheets in one document.

| File | Pages | What it is |
|------|-------|------------|
| [`assets/print/pdf/Sovereignty-Print-Pack.pdf`](../assets/print/pdf/Sovereignty-Print-Pack.pdf) | 11 | The whole package — print this and you're set |
| [`assets/print/pdf/board.pdf`](../assets/print/pdf/board.pdf) | 1 | Campfire board (16 spaces, square loop) |
| [`assets/print/pdf/mat.pdf`](../assets/print/pdf/mat.pdf) | 1 | Player mat — coins / rep / upgrades / promises (one per player) |
| [`assets/print/pdf/quickref.pdf`](../assets/print/pdf/quickref.pdf) | 1 | Quick reference — board spaces, turn order, promise rules |
| [`assets/print/pdf/treaty.pdf`](../assets/print/pdf/treaty.pdf) | 1 | Treaty Table quick reference (Tier 3 only) |
| [`assets/print/pdf/events.pdf`](../assets/print/pdf/events.pdf) | 3 | 20 Event cards, 9-up grid (cut along lines) |
| [`assets/print/pdf/deals.pdf`](../assets/print/pdf/deals.pdf) | 2 | 10 Deal cards |
| [`assets/print/pdf/vouchers.pdf`](../assets/print/pdf/vouchers.pdf) | 2 | 10 Voucher cards (IOUs between players) |

The PDFs are vector with embedded fonts (Cormorant Garamond, IM Fell English, JetBrains Mono, ZapfDingbats) — they print cleanly on any home printer at US Letter portrait. Source files for re-rendering live in [`assets/print/source/`](../assets/print/source/README.md).

## Which tier are you playing?

| Tier | What to print | Pages |
|------|--------------|-------|
| **Campfire** | Board + Player mat + Quick ref + Event cards + Deal cards + Voucher cards | 9 |
| **Market Day** | Same as Campfire (resources tracked on player mat) | 9 |
| **Town Hall** | Same as Campfire (market prices tracked on board margin) | 9 |
| **Treaty Table** | Everything above + Treaty quick ref | 10 |

Print double-sided to save paper.

## What else you need

- 1 six-sided die
- Coins or tokens (pennies, buttons, whatever — about 40 total)
- Position markers — different colored buttons or bottle caps, one per player
- **Market Day / Town Hall / Treaty Table:** Resource tokens in 3 colors (Food, Wood, Tools — buttons, beads, or colored paper squares)

## Setup (2 minutes)

1. Cut the Event cards and Deal cards. Shuffle each deck face-down.
2. Each player takes a Player Mat.
3. Everyone starts with **5 coins** and **3 reputation**. Mark your mat.
4. Pick your secret goal: **Prosperity** (20 coins), **Beloved** (10 rep), or **Builder** (4 upgrades).
5. Everyone starts on space 0 (Campfire). Youngest goes first.

## How to play

**On your turn:**
1. Roll the d6. Move that many spaces clockwise (0 through 15, wrapping around).
2. Do what the space says (see Quick Reference).
3. **The Offer** (optional): make one Offer out loud.
4. End your turn.

**Promises:** Once per round, say "I promise..." and state what you'll do. Keep it = +1 Rep. Break it = -2 Rep. The table decides.

**The Apology:** Once per game, if you broke a promise, you can apologize. Pay 1 coin to the person you wronged. Regain +1 Rep.

**Winning:** First to hit their goal wins. After 15 rounds, highest score wins:
`(Coins / 2) + Reputation + (Upgrades * 3)`

## What the console does (optional)

If someone has a laptop handy, `sov` tracks everything for you:

```bash
pipx install sovereignty-game       # one-time install
sov new -p Alice -p Bob -p Carol     # start a game
sov turn                             # roll, move, resolve
sov promise make "I'll help you"     # track a promise
sov recap                            # what happened this round
sov end-round                        # generate a tamper-proof receipt
```

The console is optional. The game works fine with just paper and dice.

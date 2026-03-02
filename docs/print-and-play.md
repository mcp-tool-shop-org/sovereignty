# Sovereignty: Campfire — Print & Play

Everything you need to play tonight. No screens required.

## What to print

| File | Pages | What it is |
|------|-------|------------|
| `assets/print/event-cards.md` | 2 | 20 Event cards (cut along lines) |
| `assets/print/deal-cards.md` | 2 | 20 Deal & Voucher cards (cut along lines) |
| `assets/print/player-mat.md` | 1 | Player mat (one per player, tracks coins/rep/promises) |
| `assets/print/quick-ref.md` | 1 | Quick reference: board spaces, turn order, Promise rules |

**Total: ~6 pages.** Print double-sided to save paper.

## What else you need

- 1 six-sided die
- Coins or tokens (pennies, buttons, whatever — you need ~40 total)
- Something to mark board position (different colored buttons, bottle caps)
- A piece of paper to draw the board (or just count spaces 0-15)

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
3. Optionally: propose one trade to any player.
4. End your turn.

**Promises:** Once per round, say "I promise..." and state what you'll do. Keep it = +1 Rep. Break it = -2 Rep. The table decides.

**The Apology:** Once per game, if you broke a promise, you can apologize. Pay 1 coin to the person you wronged. Regain +1 Rep.

**Winning:** First to hit their goal wins. After 15 rounds, highest score wins:
`(Coins / 2) + Reputation + (Upgrades * 3)`

## What the console does (optional)

If someone has a laptop handy, `sov` tracks everything for you:
- `sov new -p Alice -p Bob -p Carol` — start a game
- `sov turn` — roll, move, resolve
- `sov promise make "I'll help you"` — track a promise
- `sov recap` — what happened this round
- `sov end-round` — generate a tamper-proof receipt

The console is optional. The game works fine with just paper and dice.

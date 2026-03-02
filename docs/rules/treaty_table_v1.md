# Treaty Table (Tier 3) — Full Rules

**Status: Playable.**

Treaty Table = Town Hall + one new mechanic: **Stakes**.

Everything from Town Hall still applies: the board, events, deals, vouchers,
promises, the apology rule, the market board with scarcity, resources, and
the three win conditions. Treaty Table adds one thing: treaties.

## The one mechanic: Treaties with Stakes

A Treaty is a Promise with something on the line. Two players negotiate
out loud, put up collateral, and shake on it. If someone breaks the treaty,
they lose their stake to the other party.

### Making a treaty

1. Two players agree on terms out loud. ("I'll defend your market position
   for 3 rounds if you don't buy tools.")
2. Each party puts up a **stake** — coins, resources, or both.
3. Stakes are escrowed immediately (deducted from holdings).
4. The treaty has a deadline (default: 3 rounds).

```
sov treaty make "defend Bob's market for 3 rounds" --with Bob --stake "2 coins" --their-stake "1 food"
```

### Keeping a treaty

When both parties honor the terms, either party (or the table) calls keep:

```
sov treaty keep t_0001
```

- Both players get their stakes back.
- Both players gain **+1 Rep**.

### Breaking a treaty

When one party violates the terms, the table calls break:

```
sov treaty break t_0001 --breaker Alice
```

- The breaker's stake goes to the harmed party.
- The harmed party gets their own stake back.
- The breaker loses **3 Rep** (worse than a promise break's -2).

### Deadlines

If neither party calls break before the deadline, the treaty is
automatically honored — stakes return, +1 Rep each. This is the generous
interpretation: if nobody complained, it was kept.

### Limits

| Rule | Limit |
|------|-------|
| Active treaties per player | 2 |
| Max coins per stake | 5 |
| Max resource units per stake | 3 total |

At least one party must stake something. If nobody stakes anything,
use a regular promise instead.

### Stake types

- **Coins**: `"2 coins"`, `"5 coins"`
- **Resources**: `"1 food"`, `"1 wood, 1 tools"`
- **Mixed**: `"3 coins, 1 food"`

## Why this and not something else

The tier ladder teaches one concept at a time:

| Tier | What you learn |
|------|----------------|
| 1 | Your word matters (Promises) |
| 2 | Markets have moods (Scarcity) |
| 3 | Agreements have teeth (Stakes) |

Stakes are the natural evolution of Promises. In Campfire, you lose Rep
if you break your word. In Treaty Table, you lose something tangible.

## What Treaty Table is NOT

- **Not a courtroom.** There's no judge. The table decides if a treaty
  was kept or broken, the same way they decide about promises.
- **Not governance.** No votes, no policies, no alliances, no roles.
- **Not permanent.** Treaties have deadlines. Everything expires.
- **Not required.** You can play a full game without ever making a treaty.
  Some tables will love them. Others will never use them. Both are fine.

## Diary Mode interaction

Treaty text is included in the game state snapshot. When you anchor a
round proof to XRPL, the exact wording of every active treaty becomes
part of the permanent record. You can't claim you agreed to something
different later.

## CLI reference

```
sov treaty make "terms" --with <player> --stake "2 coins" [--their-stake "1 food"] [--duration 3]
sov treaty list                          # show all treaties
sov treaty keep <id>                     # both honored it
sov treaty break <id> --breaker <name>   # someone broke it
```

## Starting a Treaty Table game

```
sov new --tier treaty-table -p Alice -p Bob -p Carol
```

This gives you everything from Town Hall (market board, resources,
scarcity pricing) plus the treaty mechanic. Recommended for 3-4
players, 12-15 rounds, 75-90 minutes.

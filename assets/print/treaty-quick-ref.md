# Quick Reference — Treaty Table

## What's a Treaty?

A promise with teeth. You put up coins or resources as collateral.
Break it, and you lose your stake to the other party.

## Treaty Lifecycle

```
make  →  ACTIVE  →  keep  →  stakes returned, +1 Rep each
                 →  break →  breaker's stake goes to harmed party, -3 Rep
                 →  deadline passes →  auto-kept (generous interpretation)
```

## Stake Types

| Type | Examples |
|------|----------|
| Coins | "2 coins", "5 coins" |
| Resources | "1 food", "1 wood, 1 tools" |
| Mixed | "2 coins, 1 food" |

## Limits

| Rule | Limit |
|------|-------|
| Active treaties per player | 2 |
| Max coins per stake | 5 |
| Max resource units per stake | 3 |
| Treaty makes per turn | 1 |

## Keep vs Break

| Outcome | What happens |
|---------|-------------|
| **Keep** | Both players get their stakes back. +1 Rep each. |
| **Break** | Breaker's stake goes to harmed party. Harmed party gets their own stake back. Breaker loses 3 Rep. |
| **Deadline** | If neither party calls break, the treaty is considered honored. Stakes return. |

## Console Commands

```
sov treaty make "help each other" --with Bob --stake "2 coins"
sov treaty make "trade pact" --with Carol --stake "1 food" --their-stake "1 wood"
sov treaty list
sov treaty keep t_0001
sov treaty break t_0001 --breaker Alice
```

## What Treaty Table is NOT

- Not a courtroom. There's no judge — the table decides.
- Not governance. No votes, no policies, no alliances.
- Not permanent. Treaties have deadlines. Everything expires.
- Not required. You can play a full game without ever making a treaty.

It's just stakes. Put something on the line, or stick with promises.

---

_Sovereignty: Treaty Table v1.0 — Quick Reference_

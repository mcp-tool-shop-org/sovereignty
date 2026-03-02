# Market Day (Tier 2) — Rules

Market Day = Campfire + a gentle Market Board.

Everything from Campfire still applies: the board, events, deals, vouchers,
promises, the apology rule, and the three win conditions. Market Day adds
resources with fixed prices — no scarcity, no surprises.

## What's new

### Resources

Three resources exist: **Food**, **Wood**, and **Tools**.
Players start with none. You get them by buying from the Market.

### Market Board

The Market has a huge supply of each resource. It never runs out.

All prices are **fixed at 2 coins**. They don't change.
No scarcity. No event-driven price shifts. Just store prices.

### Buying and selling

When you land on **Market** (space 2), you may buy or sell up to 2 resources.

- **Buy**: Pay 2 coins. Take 1 resource.
- **Sell**: Return 1 resource. Receive 1 coin.

The Market is a shop, not a casino. You buy what you need, sell what you don't.

### Upgrades now cost resources

In Market Day, upgrades require resources in addition to coins:

- **Workshop**: 2 coins + 1 Wood
- **Builder**: 3 coins + 1 Tools (still requires Rep >= 3)

This creates a reason to visit the Market before you can build.

### Market-shift events

The deck still contains market-shift event cards (Bumper Harvest, Logging Ban,
etc.). In Market Day, they print their flavor text but have **no mechanical
effect** — prices stay fixed.

## Win conditions

Same three as Campfire. No new win conditions.

- **Prosperity**: 20 coins
- **Beloved**: 10 reputation
- **Builder**: 4 upgrades

Resources don't directly count toward any win condition, but they're
needed for building upgrades.

## CLI commands

```
sov new --tier market-day -p Alice -p Bob   # start a Market Day game
sov market                                   # show market board
sov market buy food                          # buy 1 food
sov market sell wood -p Bob                  # Bob sells 1 wood
sov turn                                     # same as Campfire
```

## Design notes

Market Day is the gentle introduction to resources. It teaches three things:

1. **Buying**: Spend coins to get resources.
2. **Holding**: Decide what to keep and what to spend.
3. **Spending**: Use resources to upgrade.

That's it. No scarcity. No dynamic pricing. No supply drama.

When players are comfortable with "owning stuff," they graduate to
Town Hall, where the market comes alive with scarcity and events.

### Tier ladder

| Tier | Name        | One new thing              |
|------|-------------|----------------------------|
| 1    | Campfire    | Coins, rep, promises       |
| 2    | Market Day  | Resources (fixed prices)   |
| 3    | Town Hall   | Dynamic market (scarcity)  |
| 4    | Treaty Table| Governance (planned)       |

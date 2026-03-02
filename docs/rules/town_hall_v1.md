# Town Hall (Tier 2) — Rules

Town Hall = Campfire + one new mechanic: the **Market Board**.

Everything from Campfire still applies: the board, events, deals, vouchers,
promises, the apology rule, and the three win conditions. Town Hall adds
resources, supply pools, and scarcity pricing.

## What's new

### Resources

Three resources exist: **Food**, **Wood**, and **Tools**.
Players start with none. You get them by buying from the Market.

### Market Board

A shared supply of each resource sits in the middle of the table.
Supply scales with player count:

| Players | Supply per resource |
|---------|-------------------|
| 2       | 8                 |
| 3       | 10                |
| 4       | 12                |

### Buying and selling

When you land on **Market** (space 2), you may buy or sell up to 2 resources.

- **Buy**: Pay the current price in coins. Take 1 token from the supply.
- **Sell**: Return 1 token to the supply. Receive the sell price (1 below buy price, minimum 1).

### Pricing

All resources start at base price **2 coins**.

**Scarcity**: When a resource's supply drops to 2 or fewer, its price goes up by 1.
When supply hits 0, nobody can buy it until supply is replenished.

**Events**: Some event cards shift prices up or down by 1 for the round.
Price shifts reset at end of round. Effective price is always clamped to **1-4**.

### Upgrades now cost resources

In Town Hall, upgrades require resources in addition to coins:

- **Workshop**: 2 coins + 1 Wood
- **Builder**: 3 coins + 1 Tools (still requires Rep >= 3)

This creates a reason to visit the Market before you can build.

## Market-shift events

Eight new event cards affect the market:

| Card | Effect |
|------|--------|
| Bumper Harvest | Food price -1 this round |
| Logging Ban | Wood price +1 this round |
| Tinker's Arrival | Tools price -1 this round |
| Trade Caravan | +2 to each supply pool |
| Warehouse Fire | -2 from each supply pool |
| Feast Day | Each player with Food loses 1 Food |
| Tool Shortage | Tools price +1 this round |
| Good Rains | All prices -1 this round |

In Campfire games, these cards still appear but have no mechanical effect
(the market board doesn't exist in Campfire).

## Win conditions

Same three as Campfire. No new win conditions.

- **Prosperity**: 20 coins
- **Beloved**: 10 reputation
- **Builder**: 4 upgrades

Resources don't directly count toward any win condition, but they're
the key to building upgrades efficiently.

## CLI commands

```
sov new --tier town-hall -p Alice -p Bob    # start a Town Hall game
sov market                                   # show market board
sov market buy food                          # buy 1 food
sov market sell wood -p Bob                  # Bob sells 1 wood
sov turn                                     # same as Campfire
```

## Design notes

Town Hall adds exactly one layer of complexity on top of Campfire:
resource management. Players must now decide when to buy resources,
what to stockpile, and when to sell. Scarcity creates natural tension
at the table without adding complicated rules.

The market is shared. Your purchases affect everyone's prices.
That's the whole point.

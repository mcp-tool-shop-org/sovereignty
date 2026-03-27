---
title: Tiers and Scenarios
description: Three tiers of complexity and curated scenario packs.
sidebar:
  order: 3
---

Sovereignty has three tiers of complexity. Start simple, add depth when ready.

## Three tiers

| Tier | Name | What it adds |
|------|------|-------------|
| 1 | **Campfire** | Coins, reputation, promises, IOUs, vouchers |
| 2 | **Town Hall** | Shared market board with supply pools, resource scarcity, dynamic pricing, resource-cost upgrades |
| 3 | **Treaty Table** | Binding treaties with escrowed stakes — promises with teeth |

Core rules are stable through v1.x. Each tier includes everything from the tiers below it.

```bash
sov new --tier campfire -p Alice -p Bob
sov new --tier town-hall -p Alice -p Bob -p Carol
sov new --tier treaty-table -p Alice -p Bob -p Carol
```

### Market Day (variant)

Market Day is a gentler introduction to resources. It uses a fixed-price market board where prices are always 2 coins and supply never runs out. Use it as a stepping stone between Campfire and Town Hall.

```bash
sov new --tier market-day -p Alice -p Bob
```

### Town Hall details

Town Hall adds three resources: **food**, **wood**, and **tools**. A shared market board tracks supply per resource. Prices shift based on scarcity (supply 2 or fewer raises the price by 1) and events. Workshop upgrades cost 2 coins + 1 wood. Builder upgrades cost 3 coins + 1 tools.

### Treaty Table details

Treaties are binding agreements between two players. Both sides put up collateral (coins and/or resources) in escrow. If one side breaks the treaty, the other gets both stakes. If honored, stakes are returned and both gain +1 reputation. Each player can have at most 2 active treaties. Stake caps: 5 coins, 3 total resource units. Breaking a treaty costs -3 reputation.

## Scenario packs

Scenarios add vibes — no new rules. Each pack sets a tier, recipe, and mood.

| Scenario | Tier | Best for |
|----------|------|----------|
| Cozy Night | Campfire / Market Day | First game, mixed groups |
| Market Panic | Town Hall | Economy drama |
| Promises Matter | Campfire | Trust and commitment |
| Treaty Night | Treaty Table | High-stakes agreements |

### Using scenarios

Browse available scenarios:

```bash
sov scenario list
```

Generate a share code for a scenario:

```bash
sov scenario code cozy-night -s 42
```

Start a game from a share code:

```bash
sov new --code "SOV|..." -p Alice -p Bob
```

### Validate custom scenarios

If you create your own scenario files:

```bash
sov scenario lint
```

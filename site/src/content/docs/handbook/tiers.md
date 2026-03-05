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
| 1 | **Campfire** | Coins, reputation, promises, IOUs |
| 2 | **Town Hall** | Shared market, resource scarcity, dynamic pricing |
| 3 | **Treaty Table** | Binding treaties with escrow stakes — promises with teeth |

Core rules are stable through v1.x. Each tier includes everything from the tiers below it.

```bash
sov new --tier treaty-table -p Alice -p Bob -p Carol
```

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

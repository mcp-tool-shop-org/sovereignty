# Sovereignty

A board game about trust, trade, and keeping your word.

[![CI](https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg)](https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Play tonight

Print the cards, grab a die and some coins, sit down with 2-4 people.
No screens required. Takes about 30 minutes.

**[Print & Play guide](docs/print-and-play.md)** | **[Full rules](docs/rules/campfire_v1.md)** | **[Play with strangers](docs/play-with-strangers.md)**

## Or use the console

```bash
pip install sovereignty-game

sov tutorial                         # learn in 60 seconds
sov new -p Alice -p Bob -p Carol     # start a game
sov turn                             # roll, land, resolve
sov promise make "I'll help Bob"     # say it out loud
sov recap                            # what happened this round
sov postcard                         # shareable summary
```

The console keeps score. You keep your word.

## How it works

You start with **5 coins** and **3 reputation**. Roll a die, move around
a 16-space board, and land on spaces that give you choices: trade, help
someone, take a risk, or draw a card.

**20 Event cards** read like moments: *"Has anyone seen a small leather
pouch?"* (Lost Wallet) or *"Nobody saw... right?"* (Found a Shortcut).

**20 Deal cards** force conversation: *"Spot me 2 coins? I'll pay 3 back."*
or *"I've got your back if you've got mine."*

**The Promise rule:** Once per round, say "I promise..." out loud and
commit to something. Keep it: +1 reputation. Break it: -2 reputation.
The table decides.

**The Apology:** Once per game, if you broke a promise, publicly apologize.
Pay 1 coin to who you wronged, regain +1 reputation.

**Pick your goal** (secret or public):
- **Prosperity** — reach 20 coins
- **Beloved** — reach 10 reputation
- **Builder** — complete 4 upgrades

After 15 rounds, highest combined score wins.

## What is Diary Mode?

Every round, the console can produce a **proof** — a fingerprint of the
game state. If anyone changes the score, the fingerprint won't match.

Optionally, that fingerprint can be posted to the **XRPL Testnet** — a
public ledger. Think of it as writing the score on a wall that nobody
can erase.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Only the host needs a wallet. Nobody else touches a screen. The game
works perfectly without anchoring — it's just the diary that remembers.

## Three tiers (building up)

| Tier | Name | Status | What it adds |
|------|------|--------|-------------|
| 1 | **Campfire** | Playable | Coins, reputation, promises, IOUs |
| 2 | **Town Hall** | Planned | Shared market, resource scarcity |
| 3 | **Treaty Table** | Planned | Governance, policy cards, alliances |

## Project structure

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 38 tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
```

## Development

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## Design principle

> "Teach through consequences, not terminology."

Players learn by doing: issuing IOUs, breaking promises, trading at
shifting prices. The concepts map to Web3 primitives — wallets, tokens,
trust lines — but players don't need to know that to have fun.

## License

MIT

---

Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/)

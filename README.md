# Sovereignty

A strategy game about governance, trust, and trade.

Offline tabletop board game with optional XRPL online verification.

[![CI](https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg)](https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What is this?

Sovereignty is a board game where players build communities and compete through
trade, trust, and governance. It teaches real economic and Web3 concepts through
play — no jargon, no lectures.

**Three tiers of complexity:**

| Tier | Name | What it teaches |
|------|------|----------------|
| 1 | **Campfire** | Wallets, payments, receipts, IOUs |
| 2 | **Town Hall** | Markets, credit, trust mechanics |
| 3 | **Treaty Table** | Governance, policy, adversarial play |

The game is fully playable offline with printed cards and tokens. An optional
XRPL Testnet layer adds verifiable receipts and enables remote play.

## Quick start

```bash
# Install
pip install sovereignty-game

# Start a game
sov new --seed 42 -p Alice -p Bob -p Carol

# Play turns
sov turn

# Show the board
sov board

# Generate a round proof
sov end-round

# Verify a proof file
sov verify .sov/proofs/round_001.proof.json
```

## Design principle

> "Teach through consequences, not terminology."

Players learn by doing: issuing IOUs, breaking promises (and losing reputation),
trading at shifting market prices, and voting on collective action. The concepts
map directly to Web3 primitives — wallets, tokens, trust lines, DEX — but
players don't need to know that to have fun.

## Game overview (Tier 1: Campfire)

- **Players:** 2-4
- **Time:** ~30 minutes
- **Components:** 16-space board, 10 Event cards, 10 Deal/Voucher cards

**Two meters:**
- **Coins** — earned, spent, traded
- **Reputation** — earned by keeping promises, lost by breaking them

**Three ways to win (pick one before play):**
- **Prosperity:** Reach 20 coins
- **Beloved:** Reach 10 reputation
- **Builder:** Complete 4 upgrades

## Round proofs

Every round, the CLI can produce a **proof file** — a JSON document containing
the canonical game state and its SHA-256 hash. Anyone can independently verify
the proof:

```bash
sov verify round_003.proof.json
# -> Proof valid. Round 3, hash matches.
```

This is the foundation for online play: proofs can be anchored to XRPL Testnet
so remote players can't fudge their game state.

## Project structure

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # XRPL transport layer (NullTransport for offline, XRPL stub)
  sov_cli/          # Typer CLI ("Round Console")
  tests/            # pytest suite
  docs/             # Game design docs (board, cards, rules)
```

## Roadmap

- [x] **Phase 1:** Campfire MVP — engine + CLI + round proofs
- [ ] **Phase 2:** XRPL anchoring — online play with commit/reveal
- [ ] **Phase 3:** Tier 2 (Town Hall) — markets + trust gates
- [ ] **Phase 4:** Tier 3 (Treaty Table) — governance + policy cards

## Development

```bash
# Clone
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty

# Install with dev deps
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check .
```

## Platform support

| Platform | Status |
|----------|--------|
| Linux | Tier 1 (primary) |
| macOS | Tier 2 (best effort) |
| Windows | Tier 3 (best effort) |

## License

MIT

---

Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/)

# Start Here

Two paths. Pick the one that fits.

## I want to play tonight

You need a table, 2-4 people, a six-sided die, and some coins or tokens.

**Step 1: Print the kit**

Print [the play kit](../assets/print/) — about 6 pages. Cut the cards.
Full walkthrough: [Print & Play guide](print-and-play.md)

**Step 2: Learn the rules**

Read the [Quick Reference](../assets/print/quick-ref.md) — one page, everything you need.
Full rules if you want them: [Campfire rules](rules/campfire_v1.md)

**Step 3: Play**

Youngest goes first. Roll, move, do what the space says.
The [Play with Strangers](play-with-strangers.md) guide has a ready-to-read
social script if you're hosting for people who've never played.

**Optional: use the console**

If someone at the table has a laptop, the console tracks score for you:

```bash
pip install sovereignty-game
sov new -p Alice -p Bob -p Carol
```

The console is optional. The game works fine with just paper and dice.

---

## I want to hack on it

**Step 1: Clone and run tests**

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

**Step 2: Understand the structure**

```
sov_engine/          # Pure game logic — no I/O, no CLI
  models.py          # Data classes (GameState, Card, Player, etc.)
  content.py         # All cards — events, deals, vouchers (with tags)
  rules/campfire.py  # Tier 1 rules
  rules/town_hall.py # Tier 2 rules (market + resources)
  hashing.py         # Round proof generation
  rng.py             # Deterministic RNG
  serialize.py       # JSON snapshot format

sov_transport/       # Ledger backends (XRPL Testnet, null)
sov_cli/             # Typer CLI (the "Round Console")
tests/               # pytest suite
docs/                # Rules, guides, print-and-play
assets/print/        # Printable cards, player mat, quick reference
```

**Step 3: Pick a task**

| Task | Difficulty | Where to look |
|------|-----------|----------------|
| Add an Event card | Easy | `sov_engine/content.py` |
| Add a Deal card | Easy | `sov_engine/content.py` |
| Tag a card | Easy | `sov_engine/content.py` |
| Write a recipe | Easy | Tags in `content.py` + CLI `--recipe` |
| Fix a rule | Medium | `sov_engine/rules/campfire.py` |
| Add a CLI command | Medium | `sov_cli/main.py` |
| Add a board space | Hard | `models.py` + `campfire.py` + tests |

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full guide.

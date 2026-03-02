# Contributing to Sovereignty

The easiest way to contribute is to add a card. You don't need to touch
the engine, the CLI, or any infrastructure.

## Adding an Event card

Events live in `sov_engine/content.py` inside `campfire_events()`.

```python
EventCard(
    id="evt_29",
    name="Barn Raising",
    description="Everyone at the table gains +1 coin if they all agree to help.",
    flavor="Many hands, one roof.",
    tags=("cozy", "help"),
),
```

**Checklist:**
- [ ] Unique `id` — next number in sequence (evt_29, evt_30, ...)
- [ ] `name` — short, evocative, sounds like a moment
- [ ] `description` — what happens mechanically (coins, rep, trades)
- [ ] `flavor` — one line of human voice (not rules text)
- [ ] `tags` — at least one from: `cozy`, `spicy`, `market`, `promise`, `repair`, `help`
- [ ] Not too swingy — no "+10 coins" or "everyone loses all rep"
- [ ] Works with 2-4 players, no edge cases at player count extremes

## Adding a Deal card

Deals also live in `content.py` inside `campfire_deals()`.

```python
DealCard(
    id="deal_13",
    name="Neighborhood Watch",
    description="Promise to block one trade against the player to your left. Reward: +2 Rep.",
    flavor="I've got your back.",
    tags=("promise", "help"),
),
```

Same checklist as Events, plus:
- [ ] Involves conversation between players (not solo effects)
- [ ] Clear reward and clear consequence for failure

## Adding a Voucher

Vouchers are IOUs between players. Same file, `campfire_vouchers()`.

```python
VoucherCard(
    id="vouch_11",
    name="Potluck Pledge",
    face_value=2,
    deadline_rounds=3,
    default_penalty=1,
    flavor="Bring something to the table.",
    tags=("cozy", "promise"),
),
```

- [ ] `face_value` — 1-4 coins (keep it small)
- [ ] `deadline_rounds` — 2-4 rounds (enough time to pay)
- [ ] `default_penalty` — rep loss if they don't pay (usually 1)

## Tagging cards

Tags control session recipe filtering (`sov new --recipe cozy`).

| Tag | Vibe | Examples |
|-----|------|----------|
| `cozy` | Warm, communal, low-conflict | Festival, Harvest Moon, Community Dinner |
| `spicy` | Risk, conflict, surprises | Storm, Rumor, Swindle |
| `market` | Trade, prices, resources | Supply Delay, Big Order, Price Drop |
| `promise` | Commitments, trust | Builder's Promise, The Long Game |
| `repair` | Fixing relationships | Old Friend, Apology-adjacent deals |
| `help` | Aiding other players | Lost Wallet, Mutual Aid Pact |

Cards can have multiple tags. A card tagged `("cozy", "help")` appears
in both `--recipe cozy` and `--recipe help` sessions.

## Writing in human voice

Sovereignty cards should sound like someone telling a story at a table,
not like a rulebook.

| Instead of | Write |
|-----------|-------|
| "Player receives 2 coins" | "Someone left you 2 coins on the step" |
| "All players lose 1 reputation" | "Word gets around. Everyone side-eyes everyone." |
| "Trade is prohibited this turn" | "Nobody's buying today." |

The `flavor` field is where personality lives. The `description` field
can be more mechanical, but still keep it conversational.

## Running tests

```bash
uv run pytest tests/ -v
uv run ruff check .
```

All tests must pass. Lint must be clean. No exceptions.

## Code contributions

For engine or CLI changes:

1. Read the relevant code first (`sov_engine/` or `sov_cli/`)
2. Write tests for new behavior
3. Keep the engine pure — no I/O in `sov_engine/`, all I/O in `sov_cli/`
4. Match existing style (type hints, docstrings on public functions)

## Release cadence

Content changes (new cards, rule tweaks) and engine changes ship together.
Major version bumps only happen when rules change in a way that would break
old proof verification (Diary Mode hash format changes).

| Change type | Version bump |
|------------|-------------|
| New cards, tag changes, CLI polish | Patch (1.0.x) |
| New mechanics, new spaces, new tier | Minor (1.x.0) |
| Proof format change, save format change | Major (x.0.0) |

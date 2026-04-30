# Contributing to Sovereignty

The easiest way to contribute is to add a card. You don't need to touch
the engine, the CLI, or any infrastructure.

## Dev environment in 5 commands

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --frozen --dev
uv run pytest tests/ -v
uv run sov tutorial
```

If `uv` isn't installed, get it from [astral.sh/uv](https://docs.astral.sh/uv/).
The `--frozen` flag matches CI exactly so you don't get version drift.

## Where things live (domain ownership)

The repo is split into a small number of domains. PRs that stay in one
domain are easy to review; PRs that touch many are usually the symptom of
a missing seam somewhere.

| Domain | Path | What lives here |
|--------|------|-----------------|
| Engine | `sov_engine/` | Pure game logic — models, rules, serialization, hashing. No I/O. |
| Transport | `sov_transport/` | XRPL anchoring + offline ledger. The only network code. |
| CLI | `sov_cli/` | Typer commands, console output, file I/O glue. |
| Tests | `tests/` | One test module per code module. Mirrors the source tree. |
| ci-docs | root `*.md`, `docs/`, `.github/`, lint configs | Docs, issue/PR templates, CI workflow, lint config. |
| Frontend | `site/` | Astro landing page + Starlight handbook content. |

Atomic file writes (game state, proofs, season files) go through
`sov_engine/io_utils.py::atomic_write_text` — don't re-implement the
tmp-file-then-`os.replace` dance in callers.

## Running just a slice of the tests

The full suite is fast (under a minute), but during iteration you usually
only need one slice:

```bash
# Engine only — pure logic, no XRPL
uv run pytest tests/test_engine_*.py tests/test_models.py tests/test_serialize.py -v

# Transport only — XRPL + offline ledger
uv run pytest tests/test_transport_*.py tests/test_xrpl_*.py -v

# Everything (what CI runs)
uv run pytest tests/ -v -W error::DeprecationWarning -W error::PendingDeprecationWarning
```

Match patterns to your actual test filenames; the root names above are
the convention but not all modules use them yet.

## Dogfood swarms

Some of the larger refactors (the v2.0.0rc1 health pass, the structured
error work) ran as parallel-agent "dogfood swarms" rather than single PRs.
The convention is documented in the maintainer's memory directory; for
contributors the relevant takeaway is: if your change touches more than
one domain at once, please split it into one PR per domain so the swarm
playbook can review them independently.

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

## Sharing Scenario Packs

Scenario packs are fan fiction for governance. Zero code needed.

1. Copy `docs/scenarios/_TEMPLATE.md`
2. Fill in every field — the vibe paragraph is the most important part
3. Test it: play the scenario with your start command
4. Submit a PR adding your file to `docs/scenarios/`

Good scenarios have a clear mood and a "what success feels like" sentence.
The template has everything you need. Read the existing packs in
`docs/scenarios/` for inspiration.

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

## Running the full gate

The dev-env section above gets you set up; this is the gate every PR
must pass. It's also what `bash scripts/verify.sh` runs (currently lint
+ tests; the format and mypy steps are CI-only until parking F-022 is
resolved):

```bash
uv run pytest tests/ -v -W error::DeprecationWarning -W error::PendingDeprecationWarning
uv run ruff check .
uv run ruff format --check .
uv run mypy sov_engine sov_transport sov_cli
```

All tests must pass. Lint must be clean. mypy must be clean. No exceptions.

## Logging and diagnostics

The CLI uses the stdlib `logging` module. Override the level with the
`SOV_LOG_LEVEL` env var (`DEBUG` / `INFO` / `WARNING` / `ERROR`):

```bash
SOV_LOG_LEVEL=DEBUG uv run sov play
```

Warnings (e.g. "Ruleset X does not expose upgrade_with_resources; falling
back to Campfire workshop") write to stderr at WARNING level by default.

For machine-readable diagnostic output, `sov doctor`, `sov self-check`, and
`sov support-bundle` all accept `--json`. The schema is documented in
[docs/cli-json-output.md](docs/cli-json-output.md) — when adding a new
diagnostic field, register its `name` there and add a contract test.

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

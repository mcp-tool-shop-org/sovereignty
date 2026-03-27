<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/sovereignty/readme.png" width="400" alt="Sovereignty">
</p>

<p align="center">
  A board game about trust, trade, and keeping your word.
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## Play tonight

Print the cards, grab a die and some coins, sit down with 2-4 people.
No screens required. Takes about 30 minutes.

**[Start here](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[Full rules](docs/rules/campfire_v1.md)** | **[Play with strangers](docs/play-with-strangers.md)**

## Or use the console

**No Python required** (downloads a prebuilt binary):

```bash
npx @mcptoolshop/sovereignty tutorial
```

Or with Python:

```bash
pipx install sovereignty-game
sov tutorial
sov new -p Alice -p Bob -p Carol
```

<details>
<summary>Full command reference</summary>

```bash
sov new --recipe cozy -p ...         # curated vibe (cozy/spicy/market/promise)
sov new --tier treaty-table -p ...   # pick a tier
sov new --code "SOV|..." -p ...      # play from a share code
sov tutorial                         # learn in 60 seconds
sov turn                             # roll, land, resolve
sov status                           # show current game state
sov board                            # show the board layout
sov recap                            # what happened this round
sov promise make "I'll help Bob"     # say it out loud
sov promise keep "I'll help Bob"     # kept it: +1 Rep
sov promise break "text"             # broke it: -2 Rep
sov apologize Bob                    # once per game, pay 1 coin, +1 Rep
sov offer "2 coins for 1 wood" --to Bob  # make a trade offer
sov treaty make "pact" --with Bob --stake "2 coins"  # binding treaty
sov treaty list                      # show your treaties
sov market                           # show market prices + supply
sov market buy food                  # buy a resource (Town Hall+)
sov market sell wood                 # sell a resource (Town Hall+)
sov vote mvp Alice                   # table votes: mvp/chaos/promise
sov toast Alice                      # +1 Rep, once per player per game
sov end-round                        # generate round proof
sov game-end                         # final scores + Story Points
sov postcard                         # shareable summary
sov season-postcard                  # season standings across games
sov feedback                         # issue-ready play report
sov scenario list                    # browse scenario packs
sov scenario code cozy-night -s 42   # generate a share code
sov scenario lint                    # validate scenario files
sov doctor                           # pre-flight check before play night
sov self-check                       # diagnose your environment
sov support-bundle                   # diagnostic zip for bug reports
```

</details>

The console keeps score. You keep your word.

## How it works

You start with **5 coins** and **3 reputation**. Roll a die, move around
a 16-space board, and land on spaces that give you choices: trade, help
someone, take a risk, or draw a card.

**28 Event cards** read like moments: *"Has anyone seen a small leather
pouch?"* (Lost Wallet) or *"Nobody saw... right?"* (Found a Shortcut).
Includes 8 market-shift events for Town Hall games.

**22 Deal & Voucher cards** force conversation: *"Spot me 2 coins? I'll
pay 3 back."* or *"I've got your back if you've got mine."* Deals set
goals with deadlines; Vouchers are IOUs you issue to other players.

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

## Three tiers

| Tier | Name | Status | What it adds |
|------|------|--------|-------------|
| 1 | **Campfire** | Playable | Coins, reputation, promises, IOUs |
| 2 | **Town Hall** | Playable | Shared market, resource scarcity |
| 3 | **Treaty Table** | Playable | Treaties with stakes — promises with teeth |

Core rules are stable through v1.x. See [roadmap](docs/roadmap.md).

## Scenario packs

Zero new rules. Just vibes. Each pack sets a tier, recipe, and mood.

| Scenario | Tier | Best for |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Campfire / Market Day | First game, mixed groups |
| [Market Panic](docs/scenarios/market-panic.md) | Town Hall | Economy drama |
| [Promises Matter](docs/scenarios/promises-matter.md) | Campfire | Trust and commitment |
| [Treaty Night](docs/scenarios/treaty-night.md) | Treaty Table | High-stakes agreements |

`sov scenario list` to browse from the console.

## Project structure

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 147 tests
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

## Contributing

The easiest way to contribute is to [add a card](CONTRIBUTING.md).
No engine knowledge needed — just a name, a description, and some flavor text.

## Security

Wallet seeds, game state, and proof files — what to share and what not to.
No telemetry, no analytics, no phone-home. The only optional network call is XRPL Testnet anchoring.

See [SECURITY.md](SECURITY.md).

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Seed leakage via proofs | Proofs contain hashes only, never seeds |
| Seed in git | `.sov/` gitignored; `sov wallet` warns |
| Game state manipulation | Round proofs hash full state; `sov verify` detects tampering |
| XRPL anchor spoofing | Proof hash anchored on-chain; mismatch detection in verify |
| Player name privacy | Game state is local-only; proofs don't include names |

## License

MIT

---

Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/)

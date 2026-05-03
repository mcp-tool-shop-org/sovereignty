<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/sovereignty/readme.png" width="400" alt="Sovereignty">
</p>

<p align="center">
  A board game about trust, trade, and keeping your word.
</p>

<p align="center">
  Sit down with 2-4 friends, roll a die, move around a board, and try to
  end up with more coins or more goodwill than anyone else. Make promises
  out loud — keep them and people trust you, break them and they don't.
  No prior games like this needed. No screens at the table.
</p>

<!--
  Badge style policy (Stage D / W7CIDOCS-001): all badges use shields.io
  default `flat` style for visual consistency. Each shields.io URL pins
  `cacheSeconds=3600` so cold-cache renders fall back to the last known
  value rather than going blank when the upstream registry is slow. The
  CI badge is GitHub's first-party SVG and is exempt — GitHub serves it
  from camo with its own cache.
-->
<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## Install + first game

The fastest path — install, then start playing:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` is the no-config quickstart — one human plus a default opponent on the Campfire ruleset. For multi-player at the table, use `sov new -p Alice -p Bob -p Carol`. For a guided 60-second walkthrough, use `sov tutorial`.

No Python? The `npx` path downloads a prebuilt binary:

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Your first game

Once you and 2-3 friends are at the table, the console runs the round and
you do the talking. A real session looks like this:

```bash
# Start a game with three players
sov new -p Alice -p Bob -p Carol

# Each player takes a turn — roll, land, resolve
sov turn

# Check where everyone stands
sov status

# When everyone has gone, close the round
sov end-round
```

`sov status` shows a Rich-formatted table with player coins, rep, upgrades,
position, and goal. For a quick one-line glance between turns:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = coins / rep / upgrades; `>` marks the active player.)

Repeat for 15 rounds. `sov game-end` prints the final scores.

- **Multiple saved games** (v2.1+): `sov games` lists saves; `sov resume <game-id>` switches between them.
- **Batched anchoring** (v2.1+): `sov anchor` at game-end batches all pending rounds into a single XRPL transaction — one verifiable chain pointer per game. Use `sov anchor --checkpoint` for mid-game flush.
- **Network selection** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (or `SOV_XRPL_NETWORK` env var; default `testnet`).
- **Daemon mode** (v2.1+, optional): `sov daemon start` runs a localhost HTTP/JSON server for desktop integration and background chain polling. See [Daemon mode](#daemon-mode-optional-v21) below.
- **Audit Viewer desktop app** (v2.1+, optional): `npm --prefix app run tauri dev`. See [Desktop app](#desktop-app-optional-v21) below.

> Want a guided in-app walkthrough first? Run `sov tutorial`.
> Want to play with no software at all? See [Print & Play](docs/print-and-play.md).
> Want a deeper rules tour? See [Start here](docs/start_here.md) or
> the [full handbook](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

The inline `sov turn` example above shows what a round looks like in the
console; for the v2.1 desktop visualization, see [Desktop app](#desktop-app-optional-v21) below.

## Play without the console

Print the cards, grab a die and some coins, sit down with 2-4 people.
The game works fully on the table.

**[Start here](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[Full rules](docs/rules/campfire_v1.md)** | **[Play with strangers](docs/play-with-strangers.md)**

<details>
<summary>Full command reference</summary>

```bash
sov play campfire_v1                 # no-config quickstart (v2.1+) — alias for sov new
sov new --recipe cozy -p ...         # curated vibe (cozy/spicy/market/promise)
sov new --tier treaty-table -p ...   # pick a tier
sov new --code "SOV|..." -p ...      # play from a share code
sov games                            # list saved games (multi-save, v2.1+)
sov games --json                     # machine-readable saves list (v2.1+)
sov resume <game-id>                 # switch to a saved game (v2.1+)
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
sov anchor                           # batch pending rounds to XRPL (v2.1+)
sov anchor --checkpoint              # mid-game flush (v2.1+)
sov anchor --network mainnet         # network selection (v2.1+)
sov verify --tx <txid>               # confirm a proof is anchored on chain
sov daemon start [--readonly]        # localhost HTTP/JSON daemon (v2.1+)
sov daemon status                    # running | stale | none
sov daemon stop                      # SIGTERM + cleanup
sov postcard                         # shareable summary
sov season                           # season standings across games (v2.1+)
sov season-postcard                  # printable season recap
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

## Daemon mode (optional, v2.1+)

For desktop integration (Audit Viewer, Tauri shell) or background chain polling, run sovereignty as a localhost HTTP daemon:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

Daemon binds to `127.0.0.1` on a random port; connection details (port + bearer token) live in `.sov/daemon.json`. One daemon per project root. See [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) for the full IPC contract.

## Desktop app (optional, v2.1+)

The Audit Viewer is the v2.1 desktop app — a Tauri shell (Rust + webview) that runs the audit viewer and a read-only game view on top of the daemon.

### Install (binaries)

v2.1.0 ships pre-built binaries on the [GitHub Releases page](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest):

- **macOS (universal):** `sovereignty-app-2.1.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux:** Run from source for v2.1 (`npm --prefix app run tauri dev`); AppImage build deferred to v2.2 (Ubuntu 24.04 runner FUSE / linuxdeploy interaction needs investigation). Linux users still get the CLI binary `sovereignty-2.1.0-linux-x64` for `sov` itself.

You also need the Python daemon backing the app: `pip install 'sovereignty-game[daemon]'==2.1.0`.

> **First-launch warning is expected.** macOS will say "unidentified developer" — control-click the .app, choose Open, confirm. Windows SmartScreen will say "unrecognized publisher" — click "More info" then "Run anyway." Both warnings reflect that v2.1 ships with build-provenance attestation only (verify with `gh attestation verify`), not OS-level code signing. Workspace-level signing infrastructure ships in v2.2.

### Verify provenance

Every release artifact carries a SLSA build-provenance attestation. Verify before running:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

A clean verification proves the binary was built from a specific commit, by the release workflow, in this repo. Different layer of trust than OS-level code signing — the binary still triggers the OS warning, but its supply-chain provenance is cryptographically pinned.

### Run from source

If you'd rather build from source (or the binary won't run on your platform):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

The Tauri shell auto-starts a readonly daemon on launch and auto-stops it on exit. Externally-started daemons (`sov daemon start`) stay alive across shell restarts.

See [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) for the full contract.

<p align="center">
  <img src="site/public/screenshots/audit-viewer.png" alt="Audit Viewer — XRPL-anchored proofs visualized as a collapsible per-game list with per-round verify status" width="640">
  <br>
  <em>Audit Viewer — XRPL-anchored proofs verifiable per round.</em>
</p>

<p align="center">
  <img src="site/public/screenshots/game-shell.png" alt="Game Shell — passive real-time display of the active game with player resource cards and round timeline" width="640">
  <br>
  <em>Game Shell — passive real-time display of the active game.</em>
</p>

<p align="center">
  <img src="site/public/screenshots/settings.png" alt="Settings — daemon network selector (testnet / mainnet / devnet) with daemon connection status" width="640">
  <br>
  <em>Settings — daemon network selection and configuration.</em>
</p>

The Audit Viewer ships with three views:

- **`/audit`** — XRPL-anchored proof viewer. Collapsible per-game list, per-round anchor status, "Verify all rounds" runs local proof recompute + chain lookup in series. The auditor's view: confirm a game ran honestly without reading raw JSON.
- **`/game`** — passive real-time state display for the active game. Player resource cards, round timeline, last-20 SSE events log. Read-only; play in the CLI in another terminal.
- **`/settings`** — daemon config display + network switcher (testnet / mainnet / devnet) with mainnet-confirmation guardrail.

Full view spec at [docs/v2.1-views.md](docs/v2.1-views.md).

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
  tests/            # Engine, transport, and CLI tests
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
| Game state manipulation | Round proofs `envelope_hash` covers `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players`, and `state`. `sov verify` detects tampering across the full envelope. Proof format v1 is no longer supported in v2.0.0+. |
| XRPL anchor spoofing | Proof hash anchored on-chain; mismatch detection in verify |
| Player name privacy | Player names ARE included in proofs (top-level `players` list and inside player snapshots). For private play, do not publish `proof.json` or share postcards. |

## License

MIT

---

Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/)

---
title: Getting Started
description: Install the Sovereignty console and play your first game.
sidebar:
  order: 1
---

Sovereignty can be played as a physical board game (print the cards, grab a die and coins) or with the digital console that keeps score.

## Install the console

No Python required — downloads a prebuilt binary:

```bash
npx @mcptoolshop/sovereignty tutorial
```

Or install with Python:

```bash
pipx install sovereignty-game
```

## Tutorial

Run the built-in tutorial to learn the basics:

```bash
sov tutorial
```

## Start a game

Create a new game with 2–4 players:

```bash
sov new -p Alice -p Bob -p Carol
```

Take turns:

```bash
sov turn
```

End a round and generate a proof:

```bash
sov end-round
```

## Print and play

For the physical version, print the cards and reference sheets from the `assets/print/` directory. You need:

- 28 Event cards (20 core + 8 market-shift for Town Hall)
- 22 Deal and Voucher cards (12 Deals + 10 Vouchers)
- A six-sided die
- Coins (real or tokens)

See the [full rules](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/docs/rules/campfire_v1.md) for details.

## Multiple games at once (v2.1+)

`sov` keeps every game you start under `.sov/games/<game-id>/`. Starting a new game no longer overwrites the old one.

```bash
sov games            # list all saved games (active marked with *)
sov resume s42       # switch the active game pointer to s42
sov games --json     # structured output for scripts
```

The active-game pointer at `.sov/active-game` tracks which game `sov turn`, `sov status`, etc. operate on. Existing v1.x layouts (`.sov/game_state.json`) auto-migrate transparently on first v2.1 invocation.

## Daemon mode (v2.1+, optional)

The daemon is an optional HTTP/JSON server that backs the desktop app and external audit tools. Install with the `[daemon]` extra:

```bash
pip install 'sovereignty-game[daemon]'==2.1.0

sov daemon start --readonly   # for the audit viewer
sov daemon status             # check pid/port/network/readonly
sov daemon stop               # clean shutdown
```

The daemon binds to `127.0.0.1:<random-port>` with bearer-token auth. It serves audit reads + anchor writes (full mode); readonly mode is sufficient for the audit viewer alone.

## Audit Viewer desktop app (v2.1+)

The Audit Viewer visualizes XRPL-anchored proofs as collapsible per-game lists with per-round verify status. Three views ship:

- `/audit` — XRPL-anchored proof viewer; "Verify all rounds" runs local proof recompute + chain lookup in series
- `/game` — passive real-time state display for the active game
- `/settings` — daemon config + network switcher (testnet / mainnet / devnet) with mainnet-confirmation guardrail

Install the desktop binary from the [GitHub Releases page](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest). Three platforms:

- macOS universal (Intel + Apple Silicon): `sovereignty-app-2.1.0-darwin-universal.dmg`
- Windows x64: `sovereignty-app-2.1.0-win-x64.msi`
- Linux x64: `sovereignty-app-2.1.0-linux-x64.AppImage`

### First-launch warning is expected

v2.1 ships with build-provenance attestation only — not OS-level code signing.

- **macOS**: control-click the .app → Open → "Are you sure?" → Open
- **Windows**: SmartScreen says "unrecognized publisher" → "More info" → "Run anyway"
- **Linux**: AppImage just runs

### Verify supply-chain provenance

Every release artifact carries a SLSA build-provenance attestation:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

A clean verification proves the binary was built from a specific commit, by the release workflow, in this repo. Different layer of trust than OS-level code signing — the binary still triggers the OS warning, but its supply-chain provenance is cryptographically pinned. Workspace-level signing infrastructure ships in v2.2.

## Network selection (v2.1+)

`sov` defaults to XRPL Testnet. Switch via flag or env:

```bash
sov anchor --network testnet     # default
sov anchor --network mainnet     # real XRP, real cost
sov anchor --network devnet      # short-lived test ledger

export SOV_XRPL_NETWORK=mainnet   # alternative: env var
```

**Mainnet warning**: anchoring on mainnet costs real XRP (~$0.0002/game). Mainnet has no faucet — set `XRPL_SEED` to a funded mainnet seed. The Audit Viewer's network switcher shows a confirmation dialog before crossing the testnet→mainnet boundary.

## Next steps

- Learn the [core rules](/sovereignty/handbook/how-to-play/)
- Explore [tiers and scenarios](/sovereignty/handbook/tiers/)
- Try [Diary Mode](/sovereignty/handbook/diary-mode/) for on-chain verification

# Security

Sovereignty is a board game that optionally connects to the XRPL Testnet.
Here's what to know about keeping things safe.

## Wallet seeds

If you use Diary Mode (`sov wallet`), the CLI creates a Testnet wallet
stored locally in `.sov/wallet.json`. This file contains your seed.

**Rules:**

- Never paste wallet seeds into GitHub issues, Discord, or any public channel
- Never commit `.sov/` to version control (it's in `.gitignore`)
- Testnet seeds aren't "real money," but treating them carelessly builds bad habits
- If you share a game directory, delete `.sov/wallet.json` first

## Environment variables

The CLI reads wallet config from `.sov/wallet.json` by default.
No environment variables contain secrets unless you configure them yourself.

## Game state files

`.sov/game_state.json` contains player names and scores. It's local-only
and not sensitive, but don't commit it to public repos with real names
if privacy matters to your group.

## Proof files

Round proofs (`.sov/proofs/*.json`) contain hashes, not raw game data.
They're safe to share — that's the whole point.

## Telemetry

Sovereignty collects no telemetry, analytics, or usage data. The only
network call is the optional XRPL Testnet anchoring (Diary Mode), which
you explicitly trigger with `sov anchor`. The game works fully offline.

## Reporting issues

If you find a security issue in the game engine, CLI, or XRPL transport,
open a GitHub issue or email 64996768+mcp-tool-shop@users.noreply.github.com.

This is a board game, not critical infrastructure. Responsible disclosure
is appreciated but we won't make you wait 90 days for a patch.

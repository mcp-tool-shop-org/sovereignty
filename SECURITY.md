# Security

Sovereignty is a board game that optionally connects to the XRPL Testnet.
Here's what to know about keeping things safe.

## Wallet seeds

If you use Diary Mode (`sov wallet`), the CLI creates a Testnet wallet
stored locally in `.sov/wallet_seed.txt`. This file contains your seed.

**Rules:**

- Never paste wallet seeds into GitHub issues, Discord, or any public channel
- Never commit `.sov/` to version control (it's in `.gitignore`)
- Testnet seeds aren't "real money," but treating them carelessly builds bad habits
- If you share a game directory, delete `.sov/wallet_seed.txt` first

## Environment variables

The CLI reads wallet config from `.sov/wallet_seed.txt` by default.
The optional `XRPL_SEED` environment variable can override the on-disk seed
for ephemeral or CI-style use.

**Treat `XRPL_SEED` as equivalent to `wallet_seed.txt`:**

- Never export it persistently in `~/.zshrc`, `~/.bashrc`, or your shell rc
- Never paste it into shared shells, screenshots, or terminal recordings
- Prefer scoping it to a single command (`XRPL_SEED=... sov anchor`) over
  exporting it for the whole session
- If you must use it in CI, pass it through your platform's secret store
  and unset it after the command (parking F-593530-020)

The `SOV_LOG_LEVEL` env var (`DEBUG` / `INFO` / `WARNING` / `ERROR`) is the
standard way to override the CLI's log verbosity. It contains no secrets but
is documented here because the canonical incident-response flow relies on it
to capture full diagnostic output.

## Game state files

`.sov/game_state.json` contains player names and scores. It's local-only
and not sensitive, but don't commit it to public repos with real names
if privacy matters to your group.

## Proof envelope hash (v2)

As of v2.0.0, round proofs use the **v2 envelope hash** format. The
`envelope_hash` field covers the full bound envelope:

| Field           | Purpose                                              |
|-----------------|------------------------------------------------------|
| `game_id`       | Binds the proof to a specific game session           |
| `round`         | Binds the proof to a specific round number           |
| `ruleset`       | Binds the proof to the rule pack used                |
| `rng_seed`      | Binds the proof to the RNG seed for this game        |
| `timestamp_utc` | Records when the round closed (informational)        |
| `players`       | Top-level player list (names included — see below)   |
| `state`         | Full snapshot of resources, positions, scores, queue |

**v1 → v2 migration:**

- Proof format v1 is **rejected** in v2.0.0+ — `sov verify` will refuse it.
- To verify a legacy proof produced by sovereignty < 2.0.0, install the
  matching legacy version: `pipx install 'sovereignty-game<2.0.0'` and run
  `sov verify` from that environment.
- v2 proofs are not backward-compatible with the v1 verifier.

**Non-goals:**

- `envelope_hash` binds a proof to its `game_id` and `round` but does **not**
  bind it to a wall-clock. Replay protection (e.g., refusing a proof whose
  `timestamp_utc` falls outside an expected window) is the responsibility
  of the verifier, not the hash.

The README threat-model row for "Game state manipulation" is the source of
truth for this field list — keep this section in sync with it.

## Proof files

Round proofs (`.sov/proofs/*.json`) contain both the `envelope_hash` and the
full game state snapshot used to compute it.

**Player names ARE included** in proofs (top-level `players` list and inside
each player snapshot inside `state`). The hash alone is safe to share publicly;
**do not publish `proof.json` files or postcards if private play matters** to
your group. Anonymise names before sharing.

## Telemetry

Sovereignty collects no telemetry, analytics, or usage data. The only
network call is the optional XRPL Testnet anchoring (Diary Mode), which
you explicitly trigger with `sov anchor`. The game works fully offline.

## Diagnostic output for incident response

`sov doctor`, `sov self-check`, and `sov support-bundle` all accept a
`--json` flag that emits a machine-readable diagnostic envelope. The
canonical schema lives in [docs/cli-json-output.md](docs/cli-json-output.md).
This is the format we ask for when triaging an issue — please attach the
JSON output (with seeds redacted) rather than a raw terminal screenshot.

## Reporting issues

If you find a security issue in the game engine, CLI, or XRPL transport,
open a GitHub issue or email 64996768+mcp-tool-shop@users.noreply.github.com.

This is a board game, not critical infrastructure. Responsible disclosure
is appreciated but we won't make you wait 90 days for a patch.

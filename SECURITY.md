# Security

Sovereignty is a board game that optionally connects to the XRPL Testnet.
Here's what to know about keeping things safe.

## Found a security issue?

Please report it — we'd rather hear it from you than read about it later.

**Preferred:** open a GitHub issue with the `security` label so the fix is
public and traceable:

```bash
gh issue create --label security --title "..." --body "..."
```

For anything you'd rather not file in the open (e.g. a working exploit
against a player who has not yet upgraded), open a GitHub private advisory.
Do not email — there is no mailbox on this project.

https://github.com/mcp-tool-shop-org/sovereignty/security/advisories/new

```bash
gh api repos/mcp-tool-shop-org/sovereignty/security-advisories
```

When reporting, please include:

- The version you're on (`sov --version` or `pip show sovereignty-game`).
- The output of `sov support-bundle --json` (seeds redacted by default).
- Repro steps — the smaller the better.

This is a board game, not critical infrastructure. We won't make you wait
90 days for a patch — responsible disclosure is appreciated, fast turnaround
is the norm.

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

**Mainnet prefers the OS keychain** (via the `keyring` package: Windows
Credential Manager, macOS Keychain, or libsecret). Store with
`XRPL_SEED=<seed> sov wallet --network mainnet` — the seed is never printed.
Plaintext `.sov/wallet_seed.txt` remains for testnet/devnet only; do not use
it as the primary mainnet store. CI/sandbox hosts without an OS secret store
get `KEYRING_UNAVAILABLE` rather than a silent plaintext write.

Seed resolution precedence is `--signer-file` > OS keychain (mainnet) >
`.sov/wallet_seed.txt` > `XRPL_SEED`. The env var is the last fallback; it
does **not** override an on-disk wallet file or a keychain entry. Use
`XRPL_SEED` only when those higher-precedence stores are empty (ephemeral
or CI-style use).

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

## Desktop updater signing (names only)

GitHub Actions secrets used by `publish.yml` `build-tauri-binaries` to minisign
Tauri updater artifacts. **Names only — never commit, print, or log values:**

- `TAURI_SIGNING_PRIVATE_KEY`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`

The matching public key is committed in `app/src-tauri/tauri.conf.json` under
`plugins.updater.pubkey`. The workflow injects the two secrets into the Tauri
build environment as `secrets.TAURI_SIGNING_PRIVATE_KEY` and
`secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. Do not generate a new keypair.

OS-level Apple Developer ID / Authenticode signing is still gated skip
(JOB-028 hold). Unsigned OS binaries remain allowed; first-launch OS warnings
stay until those secrets exist.

## Game state files

Game state lives at `.sov/games/<game-id>/state.json` (v2.1+ multi-save).
It contains player names and scores. It's local-only and not sensitive,
but don't commit it to public repos with real names if privacy matters
to your group. The v1 path `.sov/game_state.json` is a migration source
only — first v2.1+ invocation auto-migrates it.

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

**v1 → v2 migration:** see [docs/migration-v1-to-v2.md](docs/migration-v1-to-v2.md)
for the full migration guide (verifier compatibility, on-chain anchor format,
tooling field-rename checklist, tamper-detection coverage).

**Non-goals:**

- `envelope_hash` binds a proof to its `game_id` and `round` but does **not**
  bind it to a wall-clock. Replay protection (e.g., refusing a proof whose
  `timestamp_utc` falls outside an expected window) is the responsibility
  of the verifier, not the hash.

The README threat-model row for "Game state manipulation" is the source of
truth for this field list — keep this section in sync with it.

## Proof files

Round proofs (`.sov/games/<game-id>/proofs/*.json`) contain both the
`envelope_hash` and the full game state snapshot used to compute it.
The v1 path `.sov/proofs/` is a migration source only.

**Player names ARE included** in proofs (top-level `players` list and inside
each player snapshot inside `state`). The hash alone is safe to share publicly;
**do not publish `proof.json` files or postcards if private play matters** to
your group. Anonymise names before sharing.

## Telemetry

Sovereignty collects no telemetry, analytics, or usage data. CLI tabletop
play is fully offline. Optional network paths, all operator-triggered:

- XRPL anchoring (`sov anchor`) — Testnet by default; Diary Mode can
  target mainnet (real XRP).
- The desktop updater plugin polls
  `https://github.com/mcp-tool-shop-org/sovereignty/releases/latest/download/latest.json`
  when the Tauri shell is running.

## Diagnostic output for incident response

`sov doctor`, `sov self-check`, and `sov support-bundle` all accept a
`--json` flag that emits a machine-readable diagnostic envelope. The
canonical schema lives in [docs/cli-json-output.md](docs/cli-json-output.md).
This is the format we ask for when triaging an issue — please attach the
JSON output (with seeds redacted) rather than a raw terminal screenshot.

## Reporting issues

See [Found a security issue?](#found-a-security-issue) at the top of this
document.

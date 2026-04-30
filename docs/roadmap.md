# Roadmap

## Where we are: v2.0.0 (next ship)

The next release is **v2.0.0** (currently `2.0.0rc1`). It's a hard cut on
the proof format plus a production-hardening pass:

- **Proof format v2.** `envelope_hash` covers the full bound envelope
  (game_id, round, ruleset, rng_seed, timestamp_utc, players, state).
  Format v1 is rejected. See [migration-v1-to-v2.md](migration-v1-to-v2.md)
  for the verifier/tooling/on-chain anchor migration.
- **Production hardening.** Atomic writes everywhere, secret-lifecycle
  scrubbing on XRPL anchors, structured loggers, mypy strict in CI,
  release-pipeline ordering (PyPI fail-closes if binaries fail), supply-chain
  guards (pip-audit + gitleaks + dependabot pip+npm).
- **Tier completeness holds.** Campfire / Town Hall / Treaty Table all
  remain "Playable" per the README — the rules engine itself is unchanged.

See [CHANGELOG.md](../CHANGELOG.md) for the full `[2.0.0rc1]` entry.

## Stability through v1.x → v2.x

The core mechanics of Sovereignty are stable. The learning ladder
(Campfire, Market Day, Town Hall, Treaty Table) is set. The rules engine
won't change unless something is genuinely broken.

What this means in practice:

- **Rules are frozen.** Coins, reputation, promises, apologies, toasts,
  IOUs, resources, scarcity pricing, treaties — these work. They ship as-is.
- **Most changes are content.** New scenario packs, new cards, better docs,
  community contributions. The engine stays still while the library grows.
- **CLI may gain commands** for quality-of-life (lint, diagnostics, export)
  but existing commands won't change their behavior.

## What's coming after v2.0.0

The work deferred from the v2.0.0 dogfood swarm — App UI plus several
transport/engine generalizations — is captured in
**[v2.1-roadmap.md](v2.1-roadmap.md)**. Open questions there cover:

- App UI framework choice (Tauri / Textual / Electron / PyQt)
- App UI scope (full game UI, audit viewer for XRPL proofs, or both)
- Distribution channel
- Transport / engine generalizations: LedgerTransport ABC, async sibling,
  mainnet anchors, multi-tx consolidation, daemon mode, `sov undo`,
  `sov resume <game-id>`

Decision happens after v2.0.0 ships. Either a separate dogfood swarm or a
focused initiative; framework choice is the first review gate.

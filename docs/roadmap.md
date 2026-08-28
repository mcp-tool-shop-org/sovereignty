# Roadmap

## Where we are: v2.3.1

Git tag **v2.3.1** (2026-08-28) publishes the 2.3.0 feature set (`sov undo`, OS-keychain mainnet seeds, additive `GET /games/{id}/verify/{round}`, Linux AppImage wiring, Tauri updater) plus Health A recovery so PyPI is not blocked by Tauri. Git tag **v2.3.0** remains a source-only tag with empty GitHub Release assets — do not pin `==2.3.0`.

v2.0.0 / `2.0.0rc1` language lives only in [CHANGELOG](../CHANGELOG.md) history.

## Already shipped (through 2.2.1, plus 2.3.0 source)

- **Proof format v2.** `envelope_hash` covers the full bound envelope. Format v1 is rejected. See [migration-v1-to-v2.md](migration-v1-to-v2.md).
- **Production hardening.** Atomic writes, secret-lifecycle scrubbing on XRPL anchors, structured loggers, mypy strict in CI, release-pipeline ordering.
- **Supply-chain scanning.** v2.3.0 replaced gitleaks with TruffleHog OSS (`--results=verified`); scanning stays advisory. Do not re-add gitleaks.
- **Multi-save, daemon, Audit Viewer, print pack** — shipped in v2.1 / v2.2.
- **Batched anchoring.** ≤8 memos per AccountSet; a typical 16-round Campfire game → 2 txs.
- **`sov undo`, OS keychain, Tauri updater plugin** — shipped in 2.3.0 source. Do not re-implement them.

Tier completeness holds: Campfire / Town Hall / Treaty Table remain "Playable" per the README.

## Stability through v1.x → v2.x

The core mechanics of Sovereignty are stable. The learning ladder
(Campfire, Market Day, Town Hall, Treaty Table) is set. The rules engine
won't change unless something is genuinely broken.

What this means in practice:

- **Rules are frozen.** Coins, reputation, promises, apologies, toasts,
  IOUs, resources, scarcity pricing, treaties — these work. They ship as-is.
- **Most changes are content.** New scenario packs, new cards, better docs,
  community contributions. The engine stays still while the library grows.
- **CLI may gain quality-of-life commands** but existing commands won't
  change their behavior. `sov undo` is last-turn only (cleared by end-round).

## What's next

Forward work is **[v2.2-backlog.md](v2.2-backlog.md)** (shipped 2.3.0 items
marked done there). Open items include OS-level Apple Developer ID /
Authenticode signing (workspace-level; still deferred), Linux RPM,
`AsyncLedgerTransport` ABC, and test-hygiene leftovers.

Do not treat [v2.1-roadmap.md](v2.1-roadmap.md) as the current plan — that
file is the historical v2.0 → v2.1 decision record. App UI, daemon, and
`sov undo` already shipped.

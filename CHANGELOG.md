# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## v2.1.0 (unreleased)

### Added

- Multi-save model: persistence layer is now plural under `.sov/games/<game-id>/`. Switch between saved games with the new `sov resume <game-id>` command; list all saves with `sov games`.
- `.sov/active-game` pointer file tracks which game is current.
- Auto-migration from v1 layout (`.sov/game_state.json`) on first invocation under v2.1 — one-shot, transparent, with a stderr notice.

### Added (Wave 2)

- XRPL network parameterization: `XRPLTransport(network=XRPLNetwork.TESTNET|MAINNET|DEVNET)` replaces `XRPLTestnetTransport`. Single class, single module (`sov_transport.xrpl`). Endpoint table built-in; `url=` kwarg overrides.
- Multi-tx anchor consolidation: rounds queue in `.sov/games/<game-id>/pending-anchors.json` and flush as a single Payment with N memos at game-end (or via `sov anchor --checkpoint` mid-game). One verifiable chain pointer per game — Sovereignty's audit thesis intact.
- New `sov anchor --network <network>` flag. Network selection precedence: CLI flag → `SOV_XRPL_NETWORK` env var → `testnet` default.
- New `sov anchor --checkpoint` flag for mid-game flush.
- Verify contract split: `verify_proof_local(proof_path)` (pure local recompute) and `proof_anchor_status(proof_path, transport) -> AnchorStatus` (3-state: ANCHORED / PENDING / MISSING) live in new `sov_engine.proof` module.
- `sov status --brief` extended with 3-state per round + `pending_count` field (additive — schema_version unchanged).
- `sov doctor` adds a `pending_anchors` check.
- `transport.explorer_tx_url(txid)` returns the network-correct explorer URL — fixes the v2.0.2 testnet-URL leak in CLI surfaces.
- 4 new structured error codes: `MAINNET_FAUCET_REJECTED`, `ANCHOR_PENDING`, `INVALID_NETWORK`, `MAINNET_UNDERFUNDED`.

### Changed

- `sov new` now writes to `.sov/games/<game-id>/` and sets the active-game pointer.

### Changed (Wave 2)

- `sov anchor` (no args) post-game-end now batches all pending rounds into a single XRPL transaction. Operators don't need to anchor each round individually.
- `LedgerTransport.verify()` deprecated in favor of `is_anchored_on_chain()`. Same behavior; new name reflects what it actually does (chain lookup, not local recompute). Removed in v2.2.

### Deprecated (Wave 2 — removed in v2.2)

- `XRPLTestnetTransport` → use `XRPLTransport(network=XRPLNetwork.TESTNET)`.
- `fund_testnet_wallet()` → use `fund_dev_wallet(network=XRPLNetwork.TESTNET)`.
- `sov anchor <proof_file>` (single-round legacy form) → pending entries auto-batch at game-end; use `--checkpoint` for mid-game flush.
- `LedgerTransport.verify()` → `is_anchored_on_chain()`.

### Notes

- `.sov/wallet_seed.txt` and `.sov/season.json` remain at `.sov/` root (cross-game state).
- State `schema_version` stays `1` — multi-save is a layout reorg, not a content change.
- See [docs/multi-save.md](docs/multi-save.md) for the operator-facing reference.
- Mainnet wallet seed management beyond plain-file `.sov/wallet_seed.txt` is explicit out-of-scope for v2.1 — deferred to v2.2 (keychain integration / hardware wallet support).
- Existing v2.0.2 testnet anchors continue to verify cleanly under v2.1; the multi-memo verify path is forward-compatible with single-memo legacy.

### Added (Wave 3)

- `sov daemon` HTTP/JSON daemon: long-running localhost server (Starlette + uvicorn) for IPC-driven consumers (Tauri shell, audit viewer). 8 read endpoints + 2 write endpoints + SSE event stream.
- `AsyncXRPLTransport`: real-async sibling to `XRPLTransport` using `xrpl-py.AsyncJsonRpcClient`. Same retry policy, secret scrub, and BatchEntry contract; used by daemon's anchor flow.
- Shared internals module `sov_transport.xrpl_internals` lifted from `xrpl.py` — pure helpers + types consumed by sync + async impls. No behavior change in sync `XRPLTransport`.
- `sov daemon start [--readonly] [--network <n>] [--seed-env VAR | --signer-file PATH]` — detached background daemon. Token + port written to `.sov/daemon.json`.
- `sov daemon stop` — clean SIGTERM + cleanup.
- `sov daemon status` — `running` / `stale` / `none`.
- `sov daemon` (no subcommand) — foreground server (test/dev mode).
- `sov status --brief` extended with daemon presence (human + `--json`).
- 4 new structured error codes: `DAEMON_READONLY`, `DAEMON_AUTH_MISSING`, `DAEMON_AUTH_INVALID`, `DAEMON_PORT_BUSY`.
- New `[daemon]` opt-in extra: `pip install 'sovereignty-game[daemon]'` for users who want the desktop IPC surface; CLI-only users don't pay the dep cost.
- SSE event stream `GET /events`: `daemon.ready`, `daemon.shutdown`, `anchor.pending_added`, `anchor.batch_complete`, `game.state_changed`, `error`. Fire-and-forget — reconnecting clients re-fetch state (no `Last-Event-ID` buffer in v2.1).

### Notes (Wave 3)

- Daemon serves audit + anchor coordination only. Gameplay verbs (`sov play`, `sov upgrade`, etc.) stay CLI-only in v2.1; v2.2+ may extend if Tauri shell UX demands it.
- Wallet seed is loaded once at daemon start and held in memory only; never written to `.sov/daemon.json`. `tests/test_daemon_seed_leak.py` mechanically pins the trust boundary.
- CORS is `*` on the localhost daemon (bearer token is the actual auth gate). Locked at the contract level so Wave 4 (Tauri shell) doesn't break on origin restrictions.
- State-change detection is 1s mtime polling when ≥1 SSE client is connected — cross-platform, no fsevents/inotify in v2.1.
- One daemon per project root. Multi-daemon coordination is v2.2+.

### Added (Wave 4)
- Tauri 2 desktop shell scaffold at `app/`: Rust shell hosts a webview window with React 19 + Vite 6 + TypeScript 5.7 frontend. Run locally with `npm --prefix app run tauri dev` after `npm install --prefix app && cargo build --manifest-path app/src-tauri/Cargo.toml`.
- 4 Tauri commands for daemon discovery + lifecycle: `daemon_status`, `daemon_start(readonly, network)`, `daemon_stop`, `get_daemon_config`. Webview talks directly to daemon over HTTP/SSE for everything else (no Rust proxy hop).
- Frontend hooks `useDaemon` (Context provider) + `useDaemonEvents` (SSE subscription) for v2.1 daemon connection state.
- Typed daemon client (`app/src/lib/daemonClient.ts`) with bearer-token injection. Manual TypeScript mirror at `app/src/types/daemon.ts` of the daemon IPC contract.
- 4 placeholder routes: `/`, `/audit`, `/game`, `/settings`. Audit viewer and game shell content land in Wave 5.
- Mechanical type-sync test at `tests/test_daemon_types_ts_in_sync.py` — every SSE event type and daemon error code from `docs/v2.1-daemon-ipc.md` must appear as a TypeScript string literal in `app/src/types/daemon.ts`. Drift fails CI.
- New `[daemon]` opt-in extra picks up the Tauri shell at install time: `pip install 'sovereignty-game[daemon]'` for Python users; standalone Tauri binary distribution lands in Wave 11.

### Changed (Wave 4)
- CI workflow extended with Rust + Node toolchains. Cargo and npm caches added to keep CI minutes reasonable. Single-OS (ubuntu-latest) per workspace policy; cross-platform release matrix lands in Wave 11.

### Notes (Wave 4)
- Tauri shell is the **window manager + IPC bridge only** in v2.1. It does not contain views or hold wallet seeds — daemon owns the trust boundary, audit viewer + game shell content arrives in Wave 5.
- `Cargo.lock` is tracked (binary, not library — standard Rust binary practice).
- Default daemon spawn mode from the shell is `--readonly`. Game shell (Wave 5) decision deferred — if anchor capability is needed, a Wave 5 advisor call adds the toggle.
- Distribution (cross-platform release matrix, code signing, notarization, GitHub Release artifacts, npm-launcher Tauri-binary wrapper) is **out of scope for Wave 4** — coordinated as part of Wave 11 Treatment alongside the existing PyPI + npm-launcher CLI flow.
- v2.1 ships React + Vite + TypeScript matching GlyphStudio's stack for skill compounding. Sovereignty is not a monorepo (single `app/`, npm not pnpm).

### Added (Wave 5)
- `/audit` view — XRPL-anchored proof viewer. Collapsible per-game list with per-round anchor status (`anchored` / `pending` / `missing`), truncated txid, explorer links, and a "Verify all rounds" flow that runs `verify_proof_local` (browser-side canonical hash recompute via Web Crypto) + `is_anchored_on_chain` per round in series. Sequential by design — XRPL has implicit per-IP rate limits. Per-round progress, cancel button, session-cached results.
- `/game` view — passive real-time state display for the active game. Header (game-id, ruleset, round indicator, player count, live pulse), per-player resource cards (`coins`, `reputation`, `upgrades`, `vouchers`, `deals`, `treaties`; Town Hall ruleset adds `food`/`wood`/`tools`), round timeline dot strip, and last-20 SSE events log. Read-only — gameplay verbs stay CLI-only.
- `/settings` view — daemon config display + network switcher with three guardrails: refuses on externally-started daemon, refuses with non-empty pending-anchors, prompts a `<dialog>` confirm when crossing the mainnet boundary ("Mainnet anchors cost real XRP").
- `/` index polish — empty-state onboarding when no games exist, daemon connection pill, large nav links to `/audit` and `/game`.
- 8 shared components: `Pill`, `EmptyState`, `LoadingSpinner`, `ConfirmDialog`, `ExpandableRow`, `EventFeed`, `RoundTimeline`, `PlayerCard`. Hand-built with CSS modules; no component library, no charting library.
- Theme tokens (`--sov-bg`, `--sov-fg`, `--sov-accent`, …) in `app/src/styles/theme.css` matching Sovereignty's existing dark branding.
- Game state TypeScript types at `app/src/types/game.ts`, manually mirroring the UI-consumed subset of `sov_engine/models.py`. Pinned by `tests/test_game_types_ts_in_sync.py` (parametrized over 18 fields — gameplay-internal fields deliberately omitted so schema additions don't break CI).
- SSE consumption is payload-driven for `anchor.pending_added` and `anchor.batch_complete` (audit viewer flips rounds in place from the event payload, no re-fetch); only `game.state_changed` triggers a single re-fetch (state JSON is too large for SSE).
- New frontend dev dep: `msw` (Mock Service Worker) — daemon endpoint mocks for vitest tests; daemon does not run in CI.

### Changed (Wave 5)
- Wave 4's placeholder routes (`Audit.tsx`, `Game.tsx`, `Settings.tsx`, `Index.tsx`) replaced with full Wave 5 views.
- `useDaemon` context extended to expose `started_by_shell` (read from `daemon_status` Tauri command response) so `/settings` can enforce the externally-started-daemon guardrail.

### Notes (Wave 5)
- Player primitive vocabulary is `coins` (NOT votes), matching `sov_engine/models.py` `PlayerState`. Real fields: `coins`, `reputation`, `upgrades`, `vouchers_held`, `active_deals`, `active_treaties`, plus `resources` (food/wood/tools) for Town Hall ruleset only.
- Resources row in `PlayerCard` is ruleset-aware: rendered when `state.config.ruleset.startsWith("town_hall")`, omitted otherwise (cleaner Campfire UX).
- Semantic HTML is non-negotiable: `<details><summary>` for collapsibles, `<select>` for dropdowns, `<dialog>` for modals, `<ul aria-live="polite">` for live regions, `aria-current="page"` for active nav, `aria-busy` on long-running buttons. Pinned at the spec level because Mike has reduced vision and div+role degrades keyboard nav silently.
- Bundle-size budget: ≤ 400KB raw / ≤ 120KB gzipped. Wave 4 baseline was 220KB / 69KB; Wave 5 adds the views + components within budget.
- Component libraries (Mantine / MUI / Radix / shadcn / Chakra) and charting libraries (d3 / recharts / chart.js) deliberately rejected for v2.1. Hand-built CSS modules + semantic HTML keep the bundle lean and the accessibility contract enforceable.
- E2E test framework (Playwright / Cypress) deferred to v2.2+. v2.1 ships with vitest + msw daemon mocks at the unit level.
- Replay walkthrough view and cross-game anchor index deferred to v2.2 — neither has a known consumer at v2.1 scope.

## [2.0.2] - 2026-04-30

### Fixed

- Renamed `.github/workflows/release.yml` back to `publish.yml` to match the pre-existing PyPI Trusted Publisher record. The workflow filename was changed in v1.4.7 (consolidating `publish.yml` + `release-binaries.yml` into one file) but PyPI's publisher entry was never updated, so OIDC `invalid-publisher` blocked v2.0.0 + v2.0.1 PyPI publishes. v2.0.2 is functionally identical to v2.0.1 (and v2.0.0); only the workflow filename changed.

### Note

- **`sovereignty-game==2.0.0` and `==2.0.1` are not on PyPI.** PyPI users should `pip install sovereignty-game==2.0.2`. GitHub Release v2.0.0 / v2.0.1 / v2.0.2 binaries (consumed by `npx @mcptoolshop/sovereignty`) all ship the same code.

## [2.0.1] - 2026-04-30

### Fixed

- `publish.yml` wheel-smoke gate (added in v2.0.0 as Stage B "fail-closed" hardening) had a bash strict-mode interaction with `ls`'s exit code on no-match globs. The gate fired on its own first run and blocked PyPI publish for v2.0.0. v2.0.1 fixes the gate; functionally identical to v2.0.0 binaries published to GitHub Release.

### Note

- **`sovereignty-game==2.0.0` is not available on PyPI.** PyPI users should `pip install sovereignty-game==2.0.1`. GitHub Release v2.0.0 binaries (consumed by `npx @mcptoolshop/sovereignty`) and PyPI v2.0.1 ship the same code from the same source tree.

## [2.0.0] - 2026-04-30

### BREAKING

- **Proof format v2.** `state_hash` field renamed to `envelope_hash`; envelope hash now covers all top-level fields (`game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players`, `state`). Proof format v1 is no longer supported — `verify_proof` raises `ProofFormatError` on legacy proofs. Tamper tests added for each envelope field. **Migration guide:** [docs/migration-v1-to-v2.md](docs/migration-v1-to-v2.md).
- **XRPL anchor memo ruleset.** Per-round XRPL memo now reflects the active ruleset instead of hardcoding `campfire_v1`.
- **`game_id` format aligned to `s{seed}`** in proof envelope, season records, and anchor memos (was `sov_{seed}` in some sites). Third-party verifiers joining memo↔proof by `game_id` now work without translation.
- **Envelope hash wire format.** `_compute_envelope_hash` returns a raw 64-char hex digest; the `sha256:` algorithm tag is added at the wire/memo layer only (was double-prefixed `sha256:sha256:<hex>` on chain pre-fix).

### Added

- `sov --version` / `-V` flag (Typer callback with `importlib.metadata` + `pyproject.toml` fallback).
- `sov status --brief` flag (one-line per-player summary, suitable for between-turn glance).
- `sov self-check` command for environment diagnostics.
- `sov support-bundle` command for bug-report diagnostics (seeds redacted by default).
- `--json` flag on `sov doctor`, `sov self-check`, and `sov support-bundle` emitting the `{timestamp, command, status, fields[]}` envelope. Schema documented in [docs/cli-json-output.md](docs/cli-json-output.md).
- Structured loggers across `sov_engine`, `sov_cli`, `sov_transport`. `SOV_LOG_LEVEL` env var overrides the default WARNING-on-stderr.
- `ProofErrorKind` enum so `proof_invalid_error` distinguishes "modified" vs "unsupported version" hints (no more misleading "may have been tampered" on a v1 proof).
- Schema-versioned game-state snapshots (`schema_version: 1`); `_load_game` raises `STATE_VERSION_MISMATCH` on unknown versions.
- `Voucher.penalty_rep` field stores `template.default_penalty_rep` at issue; `redeem_voucher` and `check_voucher_deadlines` use it instead of recomputing.
- `_voucher_counter` / `_deal_counter` migrated from module globals onto `GameState.next_voucher_id` / `next_deal_id` (round-trips through snapshot; replay determinism guaranteed).
- `LedgerTransport.get_memo_text` promoted to ABC; `NullTransport` overrides.
- HTTPS-by-default XRPL transport constructor with `allow_insecure` escape hatch; `submit_and_wait` wrapped in 3-attempt retry with exponential backoff and 30s deadline.
- `anchors.json` persisted after every successful `transport.anchor()` (per-round + FINAL) so `postcard` / `feedback` can read what they always claimed to.
- `_atomic_write` helper applied uniformly across `STATE_FILE`, `SEASON_FILE`, `RNG_SEED_FILE`, `save_proof`, `anchors.json` (consolidated in `sov_engine/io_utils.py::atomic_write_text`).
- Real-XRPL-Testnet integration test (gated behind `RUN_INTEGRATION=1`) covering the full anchor → verify round-trip.
- Pre-publish wheel smoke test in `publish.yml` (fresh venv, `pip install dist/sovereignty-game-*.whl`, `sov --version` / `sov --help` / `sov self-check --json | jq .status`) so `pypa/gh-action-pypi-publish` fails closed if the wheel can't import or boot.
- Issue templates (bug, feature, scenario) and `PULL_REQUEST_TEMPLATE.md` in `.github/`.
- Favicons (svg, apple-touch, 32x32, 16x16) and 1200x630 OG / Twitter image at `site/public/og-image.png`. Anchor-nav hardened with base-prefixed absolute hrefs.
- Shell-completion docs in CONTRIBUTING.md (`sov --install-completion` via Typer).
- `docs/v2.1-roadmap.md` capturing deferred App UI + transport/engine generalizations.
- `docs/migration-v1-to-v2.md` consolidating the v1→v2 proof migration guidance previously fragmented across SECURITY.md and CHANGELOG.

### Fixed

- `state.log` now persists across save/reload cycles (Promise Keeper / Most Helpful / Treaty Keeper / Table's Choice awards previously never fired across multi-turn play).
- Treaty counter derived from game state instead of module-level global (prevents duplicate treaty IDs across game loads — carried in from 1.4.7 lineage).
- XRPL transport secret lifecycle: anchor() body wrapped to suppress traceback locals leaking the wallet seed; secret scrubbed in `finally` block via `del wallet, signer`. Regression test asserts signer not in raised repr.
- XRPL memo parsing validates length (≤1024 bytes) and decodes safely; malformed memos no longer crash `verify()` / `get_memo_text()`.
- `verify()` substring-match flaw: structured parse on `|` and equality check; rejects empty `expected_hash`.
- `_extract_memos` handles list-wrapped tx variant and non-dict guards (graceful WARNING degradation, not crash).
- `_load_game` raises `STATE_CORRUPT` (`SovError`) on JSON / enum / `OSError`; no more bare tracebacks reach the user.
- `upgrade_with_resources` fall-through: defensive `logger.warning` surfaces the silent fall to Campfire's coinless workshop.
- README threat-model row referenced "timestamp" but the engine field is `timestamp_utc`. Aligned (CHANGELOG was already correct).
- BUILD.md PyInstaller pin out of sync with `publish.yml` (`>=6.9.0` vs `==6.11.1`); BUILD.md now matches the workflow.
- `site/src/content/docs/handbook/` content sync: cleared stale `dist/` + AppleDouble droppings (`._index.md`, `._reference.md`) blocking Astro's content collection.

### Changed

- mypy strict now runs in CI (was configured but never invoked); `continue-on-error` dropped — gate is blocking.
- CI matrix adds Python 3.13 with `fail-fast: false`; `uv sync --frozen`; ruff `--output-format=github`; ruff format check; curated `-W error` filters; daily 14:00 UTC canary cron.
- Top-level `permissions: contents: read` on `ci.yml` (least-privilege).
- Third-party GitHub Actions pinned to commit SHAs; provenance attestation added to released binaries AND the checksum manifest.
- PyInstaller pinned to exact version (`==6.11.1`) for reproducible release builds.
- `publish.yml`: publish job `needs: [build-binaries]` so PyPI fail-closes if binaries fail (npm consumers can't hit a 404 on a major version bump).
- New advisory CI job: `pip-audit` + `gitleaks`.
- `dependabot.yml`: pip + npm ecosystems added; dev-dep grouping.
- SECURITY.md rewritten to mirror README threat-model rows exactly (v2 envelope field list including `timestamp_utc`, player-names-in-proofs warning, XRPL_SEED guidance, SOV_LOG_LEVEL); v1→v2 migration text relocated to dedicated guide.
- BUILD.md gained release-pipeline-ordering section + recovery runbook.
- CONTRIBUTING.md: `SOV_LOG_LEVEL`, F010 warning string, JSON contract pointers, shell completions section.
- README hero badges: PyPI version (with `include_prereleases` for the 2.0.0rc1 stream), Python versions, License, Landing Page; standardized to `style=flat` with `cacheSeconds` pinning (3600s dynamic, 86400s static).
- `docs/roadmap.md` refreshed: v2.0.0 next-ship narrative + pointer to `v2.1-roadmap.md` (was "no v2 planned").

### Known limitations

- Root landing page OG / Twitter meta tags are not rendered. Blocked on upstream site-theme `<slot name="head"/>` ([mcp-tool-shop-org/site-theme#5](https://github.com/mcp-tool-shop-org/site-theme/issues/5)). Handbook subroutes are unaffected (Starlight handles its own head).
- `--json` output mode is currently on diagnostic commands only (`sov doctor`, `sov self-check`, `sov support-bundle`). `sov status` / `board` / `recap` / `market` / `season-postcard` / `scenario list` pending v2.1; tracked in [docs/v2.1-roadmap.md](docs/v2.1-roadmap.md).
- Site-theme `npmUrl` is being used to point at PyPI as a band-aid (link renders correctly but label still reads "npm"). Upstream `packageUrl` proposal: [mcp-tool-shop-org/site-theme#4](https://github.com/mcp-tool-shop-org/site-theme/issues/4).

### Notes

- Install the rc track: `pip install --pre sovereignty-game`. Stable v1.4.x users are unaffected until 2.0.0 final.
- App UI deliverable deferred to v2.1 — see [docs/v2.1-roadmap.md](docs/v2.1-roadmap.md).

## [1.4.7] - 2026-03-20

### Fixed

- Treaty counter derived from game state instead of module-level global (prevents duplicate treaty IDs across game loads)
- SECURITY.md: corrected wallet filename (`wallet_seed.txt`, not `wallet.json`)
- SECURITY.md: corrected proof file description (proofs contain full state, not just hashes)
- Wallet seed no longer printed to terminal in `sov wallet` output
- `_load_game()` return type no longer uses `type: ignore` suppression (`GameRng` now imported at module level)

### Changed

- PyPI classifier updated from Beta to Production/Stable
- Combined `publish.yml` + `release-binaries.yml` into single `publish.yml` workflow
- Removed `uv.lock` from `.gitignore` (lock files should be tracked)
- Version bump to 1.4.7

## [1.4.6] - 2026-03-19

### Added

- Starlight handbook integrated into landing page

## [1.4.5] - 2026-03-19

### Added

- `sov support-bundle` command for bug report diagnostics
- Canary job in CI workflow (manual smoke test)

## [1.4.4] - 2026-03-19

### Fixed

- `sov self-check` resilience improvements
- PyInstaller: collect xrpl data files for binary builds

## [1.4.3] - 2026-03-19

### Added

- `sov self-check` command for environment diagnostics
- BUILD.md documentation for PyInstaller builds

## [1.4.2] - 2026-03-18

### Added

- `__main__.py` entry point for PyInstaller binary builds
- PyPI publish workflow (trusted publishing via OIDC)
- Release binaries workflow (Linux, macOS ARM, Windows)
- `npx @mcptoolshop/sovereignty` install option

### Fixed

- PyInstaller: collect rich submodules for unicode data

## [1.4.1] - 2026-03-02

### Added

- Structured error handling: `SovError` dataclass with code, message, hint, retryable
- 15 error factory functions covering all CLI failure modes
- Shipcheck compliance (SHIP_GATE.md, SCORECARD.md, verify script)
- Threat model in README
- Landing page via @mcptoolshop/site-theme
- README translations (8 languages)
- Brand logo migrated to central brand repo

### Changed

- All 47 CLI error exits now use structured `_fail(SovError)` pattern
- No raw `console.print("[red]..."); raise typer.Exit(1)` remains
- SECURITY.md expanded with no-telemetry statement

## [1.4.0] - 2026-03-01

### Added

- Season Postcard command with league table and rivalry tracking
- Season stats across multiple games
- Game-end season recording

## [1.3.0] - 2026-02-28

### Added

- Scenario system: list, code, lint (YAML-based game configuration)
- Share codes for reproducible games
- Recipe filters: cozy, spicy, market
- Scenario linting with deck validation

## [1.2.0] - 2026-02-27

### Added

- Treaty Table tier: binding agreements with escrow stakes
- Treaty make, keep, break mechanics
- Resource stakes (coins + food/wood/tools)
- Treaty deadline enforcement

## [1.1.0] - 2026-02-26

### Added

- Town Hall tier: dynamic Market Board with supply/demand pricing
- Market Day tier: fixed-price Market Board
- Buy, sell, market status commands
- Resource system (food, wood, tools)
- Price shifts based on scarcity

## [1.0.0] - 2026-02-25

### Added

- Campfire tier: roll, move, resolve, promise, keep, break
- CLI via Typer + Rich console output
- Deterministic RNG (seeded)
- Round proofs with SHA-256 hashing
- XRPL Testnet anchoring (optional)
- Proof verification (local + on-chain)
- Wallet management
- Postcard, recap, board, toast commands
- Doctor pre-flight check
- Tutorial mode
- 7 test modules, all offline
- CI workflow (Python 3.11 + 3.12, ruff, pytest)

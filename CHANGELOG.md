# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.1] - 2026-04-30

### Fixed

- `release.yml` wheel-smoke gate (added in v2.0.0 as Stage B "fail-closed" hardening) had a bash strict-mode interaction with `ls`'s exit code on no-match globs. The gate fired on its own first run and blocked PyPI publish for v2.0.0. v2.0.1 fixes the gate; functionally identical to v2.0.0 binaries published to GitHub Release.

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
- Pre-publish wheel smoke test in `release.yml` (fresh venv, `pip install dist/sovereignty-game-*.whl`, `sov --version` / `sov --help` / `sov self-check --json | jq .status`) so `pypa/gh-action-pypi-publish` fails closed if the wheel can't import or boot.
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
- BUILD.md PyInstaller pin out of sync with `release.yml` (`>=6.9.0` vs `==6.11.1`); BUILD.md now matches the workflow.
- `site/src/content/docs/handbook/` content sync: cleared stale `dist/` + AppleDouble droppings (`._index.md`, `._reference.md`) blocking Astro's content collection.

### Changed

- mypy strict now runs in CI (was configured but never invoked); `continue-on-error` dropped — gate is blocking.
- CI matrix adds Python 3.13 with `fail-fast: false`; `uv sync --frozen`; ruff `--output-format=github`; ruff format check; curated `-W error` filters; daily 14:00 UTC canary cron.
- Top-level `permissions: contents: read` on `ci.yml` (least-privilege).
- Third-party GitHub Actions pinned to commit SHAs; provenance attestation added to released binaries AND the checksum manifest.
- PyInstaller pinned to exact version (`==6.11.1`) for reproducible release builds.
- `release.yml`: publish job `needs: [build-binaries]` so PyPI fail-closes if binaries fail (npm consumers can't hit a 404 on a major version bump).
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
- Combined `publish.yml` + `release-binaries.yml` into single `release.yml` workflow
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

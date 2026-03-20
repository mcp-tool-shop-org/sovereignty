# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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

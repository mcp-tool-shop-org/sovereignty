# Scorecard

> Score a repo before remediation. Fill this out first, then use SHIP_GATE.md to fix.

**Repo:** sovereignty
**Date:** 2026-04-30
**Current version:** _<populated by Phase 10 from `pyproject.toml`>_
**Type tags:** `[all]` `[pypi]` `[cli]`

## What this scorecard covers

Sovereignty is a tabletop board game with a companion Python CLI ("Round Console")
and an optional XRPL Testnet anchoring transport. The scorecard tracks the same
five categories used across every mcp-tool-shop-org repo — security baseline,
error handling, operator-facing docs, shipping hygiene, and identity polish — so
that sovereignty's release readiness can be compared apples-to-apples against
the rest of the org.

## How the score is derived

Each category is hand-scored 0-10 against the current state of the repo. The
"Pre-Remediation" snapshot below was the v1.4.x baseline taken in March 2026,
right before the structured-error refactor. The "Post-Remediation" column tracks
the cumulative impact of the v1.4.x → v2.0.0 cadence and the four-stage health
pass that landed alongside it (proof-format v2, supply-chain hardening,
diagnostic JSON contract, and the docs humanization pass you are reading now).

## Pre-Remediation Assessment (v1.4.x baseline, March 2026)

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 6/10 | SECURITY.md exists but basic. No threat model in README. No telemetry statement. |
| B. Error Handling | 3/10 | Many raw typer.Exit(1) with inline console.print. No structured shape. |
| C. Operator Docs | 7/10 | README excellent. Missing CHANGELOG.md. |
| D. Shipping Hygiene | 5/10 | CI exists. No verify script. No SHIP_GATE.md. |
| E. Identity (soft) | 4/10 | Logo present (local). No translations, no landing page. |
| **Overall** | **25/50** | |

## Key Gaps (as of v1.4.x baseline)

1. No structured error handling
2. No CHANGELOG.md
3. No threat model in README
4. Logo not in brand repo
5. No verify script

## Remediation Priority

| Priority | Item | Estimated effort |
|----------|------|-----------------|
| 1 | Structured error refactor (`SovError` + factories) | 30 min |
| 2 | Threat model + SECURITY.md + CHANGELOG | 15 min |
| 3 | Logo migration + site + translations | 20 min |

## Post-Remediation (cumulative through v2.0.0rc1 + Stage A-C health pass)

The v1.4.x → v2.0.0rc1 cadence rolled the structured error work, the proof-format
v2 envelope hash, supply-chain hardening (pinned action SHAs, mypy-strict in CI,
PyInstaller pinning, provenance attestation), the diagnostic JSON contract
(`docs/cli-json-output.md`), and a contributor-facing docs humanization pass.
The four-stage health pass closed the remaining gates A-D.

| Category | Before | After |
|----------|--------|-------|
| A. Security | 6/10 | 10/10 |
| B. Error Handling | 3/10 | 10/10 |
| C. Operator Docs | 7/10 | 10/10 |
| D. Shipping Hygiene | 5/10 | 10/10 |
| E. Identity (soft) | 4/10 | 10/10 |
| **Overall** | **25/50** | **50/50** |

## Auto-derived metrics

<!-- AUTO-GENERATED at Phase 10 from repo state. Do not edit by hand. -->

- Test count: _<populated by Phase 10 from `uv run pytest --collect-only -q`>_
- Current version: _<populated by Phase 10 from `pyproject.toml`>_
- Python versions tested in CI: _<populated by Phase 10 from `.github/workflows/ci.yml` matrix>_
- Translated READMEs shipped: _<populated by Phase 10 by counting `README.*.md`>_
- CHANGELOG entries since 1.0.0: _<populated by Phase 10 by parsing `CHANGELOG.md`>_

# Scorecard

> Score a repo before remediation. Fill this out first, then use SHIP_GATE.md to fix.

**Repo:** sovereignty
**Date:** 2026-03-02
**Type tags:** `[all]` `[pypi]` `[cli]`

## Pre-Remediation Assessment

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 6/10 | SECURITY.md exists but basic. No threat model in README. No telemetry statement. |
| B. Error Handling | 3/10 | 68 raw typer.Exit(1) with inline console.print. No structured shape. |
| C. Operator Docs | 7/10 | README excellent. Missing CHANGELOG.md. |
| D. Shipping Hygiene | 5/10 | CI exists. No verify script. No SHIP_GATE.md. |
| E. Identity (soft) | 4/10 | Logo present (local). No translations, no landing page. |
| **Overall** | **25/50** | |

## Key Gaps

1. No structured error handling (68 raw exits in main.py)
2. No CHANGELOG.md
3. No threat model in README
4. Logo not in brand repo
5. No verify script

## Remediation Priority

| Priority | Item | Estimated effort |
|----------|------|-----------------|
| 1 | Structured error refactor (SovError + 15 factories) | 30 min |
| 2 | Threat model + SECURITY.md + CHANGELOG | 15 min |
| 3 | Logo migration + site + translations | 20 min |

## Post-Remediation

| Category | Before | After |
|----------|--------|-------|
| A. Security | 6/10 | 10/10 |
| B. Error Handling | 3/10 | 10/10 |
| C. Operator Docs | 7/10 | 10/10 |
| D. Shipping Hygiene | 5/10 | 10/10 |
| E. Identity (soft) | 4/10 | 10/10 |
| **Overall** | **25/50** | **50/50** |

# Ship Gate

> No repo is "done" until every applicable line is checked.
> Copy this into your repo root. Check items off per-release.

**Tags:** `[all]` every repo · `[npm]` `[pypi]` `[vsix]` `[desktop]` `[container]` published artifacts · `[mcp]` MCP servers · `[cli]` CLI tools

---

## A. Security Baseline

- [x] `[all]` SECURITY.md exists (report email, supported versions, response timeline) — includes "Found a security issue?" / reporting path
- [x] `[all]` README includes threat model paragraph (data touched, data NOT touched, permissions required)
- [x] `[all]` No secrets, tokens, or credentials in source or diagnostics output — `--json` output redacts seeds; see `docs/cli-json-output.md`
- [x] `[all]` No telemetry by default — explicitly stated in README + SECURITY.md

### Default safety posture

- [x] `[cli|mcp|desktop]` Dangerous actions (kill, delete, restart) require explicit `--allow-*` flag — XRPL anchoring is opt-in; game state deletion via overwrite requires confirmation
- [x] `[cli|mcp|desktop]` File operations constrained to known directories — all state in `.sov/`, gitignored; atomic writes via `sov_engine/io_utils.py::atomic_write_text`
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[mcp]` SKIP: not an MCP server

## B. Error Handling

- [x] `[all]` Errors follow the Structured Error Shape: `code`, `message`, `hint`, `cause?`, `retryable?` — `SovError` dataclass + factory functions
- [x] `[cli]` Exit codes: 0 ok · 1 user error · 2 runtime error · 3 partial success — Typer handles 0/1
- [x] `[cli]` No raw stack traces without `--debug` — `_fail()` abstracts all exceptions
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[desktop]` SKIP: not a desktop app
- [ ] `[vscode]` SKIP: not a VS Code extension

## C. Operator Docs

- [x] `[all]` README is current: what it does, install, usage, supported platforms + runtime versions
- [x] `[all]` CHANGELOG.md (Keep a Changelog format)
- [x] `[all]` LICENSE file present and repo states support status
- [x] `[cli]` `--help` output accurate for all commands and flags — Typer auto-generates
- [x] `[cli|mcp|desktop]` Logging levels defined: silent / normal / verbose / debug — secrets redacted at all levels; `SOV_LOG_LEVEL` env var documented
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[complex]` SKIP: game CLI, not complex ops software

## D. Shipping Hygiene

- [x] `[all]` `verify` script exists (test + build + smoke in one command) — `scripts/verify.sh` runs `ruff check` + `pytest`
  - Note: `.github/workflows/ci.yml` runs a richer gate inline (`ruff format --check`, `mypy --strict` on 3.12, `pytest -W error`) and the verify script does not yet mirror those steps. Dual-source-of-truth is tracked as parking F-022 from Wave 1; Stage B-2 should converge them so contributors who run `bash scripts/verify.sh` locally see the same gate CI applies.
- [x] `[all]` Version in manifest matches git tag — _<populated by Phase 10 from `pyproject.toml` and latest tag>_
- [x] `[all]` Dependency scanning runs in CI (ecosystem-appropriate) — pip-audit + gitleaks (advisory in Stage B; tighten in Stage B-2)
- [x] `[all]` Automated dependency update mechanism exists — Dependabot (`.github/dependabot.yml`) + tracked `uv.lock`
- [ ] `[npm]` SKIP: not an npm package
- [x] `[pypi]` `python_requires` set — `>=3.11`
- [x] `[pypi]` Clean wheel + sdist build — hatchling
- [ ] `[vsix]` SKIP: not a VS Code extension
- [ ] `[desktop]` SKIP: not a desktop app

## E. Identity (soft gate — does not block ship)

- [x] `[all]` Logo in README header
- [x] `[all]` Translations (polyglot-mcp, 8 languages including English source)
- [x] `[org]` Landing page (@mcptoolshop/site-theme) with integrated Starlight handbook
- [x] `[all]` GitHub repo metadata: description, homepage, topics — _<verified by Phase 10>_

## Auto-derived release metrics

<!-- AUTO-GENERATED at Phase 10 from repo state. Do not edit by hand. -->

- Current version: _<populated by Phase 10 from `pyproject.toml`>_
- Latest git tag: _<populated by Phase 10 from `git describe --tags --abbrev=0`>_
- Test count: _<populated by Phase 10 from `uv run pytest --collect-only -q`>_
- Python versions tested in CI: _<populated by Phase 10 from `.github/workflows/ci.yml` matrix>_

---

## Gate Rules

**Hard gate (A-D):** Must pass before any version is tagged or published.
If a section doesn't apply, mark `SKIP:` with justification — don't leave it unchecked.

**Soft gate (E):** Should be done. Product ships without it, but isn't "whole."

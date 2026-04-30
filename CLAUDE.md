# Sovereignty — Repo Instructions

Strategy game about governance, trust, and trade. Offline tabletop play (Python CLI) + XRPL online verification of round proofs. **Currently v2.0.2 — shipped 2026-04-30.** Distribution: `pip install sovereignty-game==2.0.2` and `npx @mcptoolshop/sovereignty`.

Global instructions in `~/.claude/CLAUDE.md` always apply. This file holds sovereignty-specific context that isn't discoverable from code or git history.

## Voice Narration

Use the `speakline` skill (`~/.claude/skills/speakline/speak`, Kokoro neural TTS, default voice Adam) to narrate substantive replies and milestones. Mike has reduced vision and prefers to listen. Full rules in the global CLAUDE.md.

## Build / verify

```bash
uv sync --all-extras            # set up venv (UV_LINK_MODE=copy on T9-Shared)
uv run pytest                   # 263 tests as of v2.0.2 (was 147 baseline pre-swarm)
uv run ruff check .             # lint (clean is mandatory before commit)
uv run ruff format --check .    # format (clean is mandatory)
uv run mypy sov_engine sov_transport sov_cli   # strict, BLOCKING in CI
sov self-check                  # CLI smoke
sov doctor --json               # machine-readable diagnostics (v2.0.0)
```

If `.venv/` shows `Lib/Scripts` capitalisation it's a stale Windows-style venv from cross-rig sync — `rm -rf .venv && UV_LINK_MODE=copy uv sync --all-extras`. Use `dot_clean -m .` first if you hit `._<name>` resource-fork errors during install.

To run real-XRPL-Testnet integration tests (skipped by default): `RUN_INTEGRATION=1 uv run pytest tests/test_xrpl_integration.py`. Hits live testnet + faucet; opt-in only.

## Completed dogfood swarm (2026-04-29 → 2026-04-30)

Swarm ID `swarm-1777521714-8de3` — 9 waves, 6 days of agent work compressed into one session. 8 swarm tags + 3 release tags. Tests 147 → 263 (+116). Shipcheck 100% pass throughout.

### Wave timeline

| Wave | Phase | Tag | Commit | Outcome |
|---|---|---|---|---|
| 0 | Pre-flight | `swarm-save-1777521714` | `a5b3961` | Save point + .gitignore for `.artifact/` |
| 1 | Stage A audit | — | — | 83 findings (20 HIGH / 31 MED / 32 LOW) — incl. 3 corroborated P1s (XRPL secret, memo parse DoS, hashing scope) |
| 2 | Stage A amend | `swarm-amend-wave-2-1777521714` | `e06a9d4` | 21 findings closed, v1.4.7 → 2.0.0rc1, +44 tests |
| 3 | Stage A re-audit | — | — | All 17 originally-flagged HIGHs verified closed; 2 cross-domain string drifts surfaced |
| 4 | Stage A inline drift fix | `swarm-stage-a-complete-1777521714` | `cebb1bd` | Closed `sha256:` double-prefix + `game_id` divergence |
| 5 | Stage B amend (proactive) | `swarm-stage-b-complete-1777521714` | `8915541` | Atomic writes everywhere, schema_version, anchors.json, supply chain hardening, +18 tests |
| 6 | Stage C amend (humanization) | `swarm-stage-c-complete-1777521714` | `c92bd80` | `sov_engine/io_utils.py` consolidation, error-message recovery commands, issue/PR templates, README install-first |
| 7 | Stage D amend (visual polish) | `swarm-stage-d-complete-1777521714` | `55b4e43` | Favicons (5), 1200×630 OG card, anchor nav hardening |
| 8 | Feature audit | — | — | 44 features surfaced; 24 approved (lean — App UI deferred to v2.1) |
| 9 | Feature execute | `swarm-feature-pass-complete-1777521714` | `961708e` | `sov upgrade workshop|builder` wiring, `sov status --brief`, real-XRPL integration test, +18 more tests |

### Release tags + distribution outcome

| Tag | Commit | GitHub Release binaries | PyPI | Why |
|---|---|---|---|---|
| `v2.0.0` | `7df9970` | ✓ shipped | ✗ blocked | Smoke-gate self-bug (Wave 9 fix worked but biting itself on first run) |
| `v2.0.1` | `add027b` | ✓ shipped | ✗ blocked | Workflow filename mismatch (`release.yml` vs PyPI Trusted Publisher's `publish.yml`) — latent gap from pre-swarm v1.4.7 consolidation, missed in Stage A audit |
| `v2.0.2` | `173adca` | ✓ shipped | ✓ live | Renamed workflow back to `publish.yml` |

All three releases ship the same source tree. PyPI v2 line starts at v2.0.2; v2.0.0/v2.0.1 GitHub Release pages carry cross-reference callouts.

### App UI / generalization deferrals

Captured in `docs/v2.1-roadmap.md`. Four open App UI questions (framework / scope / distribution / design tooling), plus seven transport/engine generalizations (LedgerTransport ABC, async sibling, mainnet anchor, multi-tx consolidation, daemon mode, `sov undo`, multi-save model).

### Two upstream site-theme issues filed

- [#4 packageUrl slot](https://github.com/mcp-tool-shop-org/site-theme/issues/4) — `npmUrl` is a band-aid for PyPI; need generalized slot
- [#5 head-slot](https://github.com/mcp-tool-shop-org/site-theme/issues/5) — root landing page bypasses Starlight; OG/Twitter meta missing on landing (handbook subroutes covered via Starlight head config)

When site-theme 0.3.0 ships either, drop the `HACK:` comments in `site/src/site-config.ts:9` (#4) and `site/src/pages/index.astro` near the `<BaseLayout>` slot (#5).

### Audit-miss accountability

Two latent gaps slipped through the Stage A audit and only surfaced at Phase 10 ship time:

1. **release.yml wheel-smoke gate strict-mode bug** (`ls` no-match exit 2 + pipefail killing the script before defensive empty check) — fixed in v2.0.1.
2. **Workflow filename ↔ PyPI Trusted Publisher mismatch** — pre-swarm v1.4.7 commit `944b745` consolidated `publish.yml` + `release-binaries.yml` into `release.yml` but never updated PyPI's publisher record. Stage A's CI/Docs audit reviewed `.github/workflows/` deeply (9 HIGH findings landed) but didn't cross-check workflow filenames against PyPI publisher claims. Fixed in v2.0.2.

Stage B-2 audit-lens improvement note for next swarm: cross-check workflow filenames against external auth records (PyPI Trusted Publishers, npm provenance, etc.) during the supply-chain audit pass.

## Decisions worth knowing

- **Proof format v2 hard cut** (not backward-compat): `state_hash` → `envelope_hash` covers full envelope (game_id, round, ruleset, rng_seed, timestamp_utc, players, state). `proof_version: 2`. v1 proofs raise `ProofFormatError` with migration text pointing at `pipx install 'sovereignty-game<2.0.0'` for legacy verify.
- **State schema_version** mirrors proof_version naming. Currently `schema_version: 1`. Bump on any field rename or removal; new optional fields don't require a bump.
- **Atomic writes**: single helper `sov_engine/io_utils.py::atomic_write_text` (Stage C consolidated the duplicate). Used for state, season, rng_seed, proof, anchors.json — all four persistence paths uniformly.
- **XRPL memo format**: `sha256:<hex>` prefix, single occurrence — engine emits prefixed; transport `verify()` does structured `split('|')` then `sha256:` equality. The `envelope_hash` field value is raw 64-char hex (the prefix is added at the wire/memo layer only). Don't double-prefix — that incident burned us in Stage A Wave 4.
- **game_id format**: `s{seed}` everywhere (proof envelope, season record, anchor memos). Anchor memos read `proof_data["game_id"]` so the source of truth flows from the proof. Don't drift to `sov_{seed}` — that mismatch was the second Wave 4 incident.
- **F010 contract**: locked Campfire-upgrade hint string lives as `CAMPFIRE_UPGRADE_HINT` in `sov_engine/rules/campfire.py`. Surfaced when user invokes `sov upgrade workshop|builder` on Campfire (which has no resource-cost upgrade). Pinned by `tests/test_log_contracts.py`.
- **Logger names**: `sov_engine`, `sov_cli`, `sov_transport`. Override via `SOV_LOG_LEVEL` env var (default WARNING on stderr).
- **JSON output schema** (locked, `docs/cli-json-output.md`): `{timestamp ISO8601, command str, status ok|warn|fail|info, fields[{name, status, value, message?}]}`. On `sov doctor` / `self-check` / `support-bundle` only — broader `--json` coverage is v2.x+ work.
- **App UI is v2.1, not v2.0.** Deferred per advisor recommendation after Health Pass — keeping the v2.0 release lean. Roadmap stub at `docs/v2.1-roadmap.md`.

## Hard rules

- **Never run translations from Claude... usually.** README is in 8 languages (`README.{es,fr,hi,it,ja,pt-BR,zh}.md`). Default: Mike runs polyglot-mcp locally in PowerShell. See `memory/translation-workflow.md`. Exception: when Mike explicitly authorizes Claude to run them in-session, run via `node /Volumes/T9-Shared/AI/polyglot-mcp/scripts/translate-all.mjs <readme-path>` (uses local Ollama TranslateGemma 12B; no Claude API spend).
- **Exclusive file ownership during swarm waves.** No agent edits a file outside its assigned domain. Cross-check with `git diff --name-only` after every amend wave.
- **Stage explicitly with `git add <file>`** — never `git add .` (would catch `.artifact/` scratch files, AppleDouble droppings on T9, and other untracked noise).
- **mypy strict is blocking in CI** (Stage B graduated it from advisory). Type regressions fail the build — fix at the source, don't add `# type: ignore`.
- **Build must pass after every amend wave** before commit: `ruff check . && ruff format --check . && mypy sov_engine sov_transport sov_cli && pytest`.

## Where things live

- **Game vocabulary**: rulesets are Campfire / Town Hall / Treaty Table / Market Day. Mechanics: vouchers (promises with deadlines), deals (trades), treaties (multi-round agreements), anchors (XRPL memos), postcards (season recap output).
- **Persistence**: `.sov/game_state.json` (current game, schema_version=1), `.sov/proofs/*.json` (round + final proofs, includes `anchors.json` index added Stage B), `.sov/rng_seed.txt` (deterministic seed). All atomic-written via `sov_engine/io_utils.py::atomic_write_text`.
- **Landing page + handbook**: `site/` (Astro + Starlight via @mcptoolshop/site-theme), live at https://mcp-tool-shop-org.github.io/sovereignty/. Two `HACK:` comments link to upstream issues #4 (`packageUrl`) and #5 (`<slot name="head"/>`).
- **Release pipeline**: `.github/workflows/publish.yml` ships PyPI + PyInstaller binaries (3 platforms) + npm-launcher. PyPI publish gates on `needs: [build-binaries]` (fail-closed) + wheel-smoke gate (fresh-venv install + `sov self-check --json` status check). Renamed from `release.yml` in v2.0.2 to match the pre-existing PyPI Trusted Publisher record.
- **Repo-knowledge DB**: `mcp-tool-shop-org/sovereignty` indexed at `/Users/michaelfrilot/AI/repos/data/knowledge.db` (last sync at v2.0.2).

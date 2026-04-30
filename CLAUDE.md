# Sovereignty — Repo Instructions

Strategy game about governance, trust, and trade. Offline tabletop play (Python CLI) + XRPL online verification of round proofs. Currently **v2.0.0rc1** on the rc track to v2.0.0 final.

Global instructions in `~/.claude/CLAUDE.md` always apply. This file holds sovereignty-specific context that isn't discoverable from code or git history.

## Voice Narration

Use the `speakline` skill (`~/.claude/skills/speakline/speak`, Kokoro neural TTS, default voice Adam) to narrate substantive replies and milestones. Mike has reduced vision and prefers to listen. Full rules in the global CLAUDE.md.

## Build / verify

```bash
uv sync --all-extras            # set up venv (UV_LINK_MODE=copy on T9-Shared)
uv run pytest                   # 209 tests as of stage-b-complete
uv run ruff check .             # lint (clean is mandatory before commit)
uv run ruff format --check .    # format (clean is mandatory)
uv run mypy sov_engine sov_transport sov_cli   # strict, BLOCKING in CI
sov self-check                  # CLI smoke
sov doctor --json               # machine-readable diagnostics (added Stage B)
```

If `.venv/` shows `Lib/Scripts` capitalisation it's a stale Windows-style venv from cross-rig sync — `rm -rf .venv && UV_LINK_MODE=copy uv sync --all-extras`. Use `dot_clean -m .` first if you hit `._<name>` resource-fork errors during install.

## Active dogfood swarm

Swarm ID `swarm-1777521714-8de3` (control-plane DB at `/Volumes/T9-Shared/AI/dogfood-lab/testing-os/swarms/control-plane.db`).

| Stage | Status | Tag | Commit |
|---|---|---|---|
| Save point | ✓ | `swarm-save-1777521714` | a5b3961 |
| Stage A amend | ✓ | `swarm-amend-wave-2-1777521714` | e06a9d4 |
| Stage A complete (re-audit + drift fix) | ✓ | `swarm-stage-a-complete-1777521714` | cebb1bd |
| Stage B complete (proactive) | ✓ | `swarm-stage-b-complete-1777521714` | 8915541 |
| Stage C (humanization) | pending | — | — |
| Stage D (visual polish) | pending | — | — |
| Feature Pass (incl. App UI) | pending | — | — |
| Phase 9 (final test) | pending | — | — |
| Phase 10 (Full Treatment redux + v2.0.0 cut) | pending | — | — |

If a session resumes mid-swarm: read this table first, then the per-wave artifacts under `swarms/swarm-1777521714-8de3/`. Domain map is **5 agents**: engine (`sov_engine/**`, `sov_cli/**`, `scripts/**`), transport (`sov_transport/**`), tests (`tests/**`), ci-docs (`docs/**`, `.github/**`, root `*.md`, root configs), frontend (`site/**`, `assets/**`).

## Decisions worth knowing

- **Proof format v2 hard cut** (not backward-compat): `state_hash` → `envelope_hash` covers full envelope (game_id, round, ruleset, rng_seed, timestamp_utc, players, state). `proof_version: 2`. v1 proofs raise `ProofFormatError` with migration text pointing at `pipx install 'sovereignty-game<2.0.0'` for legacy verify.
- **State schema_version** mirrors proof_version naming. Currently `schema_version: 1`. Bump on any field rename or removal; new optional fields don't require a bump.
- **Atomic writes**: all four persistence paths (state, season, proof, rng_seed) go through `_atomic_write` in `sov_cli/main.py:174` (and `_atomic_write_text` in `sov_engine/hashing.py:35` — duplicate helper, consolidation queued for Stage C).
- **XRPL memo format**: `sha256:<hex>` prefix, single occurrence — engine emits prefixed; transport `verify()` does structured `split('|')` then `sha256:` equality. Don't double-prefix — that incident burned us in Stage A Wave 4.
- **game_id format**: `sov_{seed}` everywhere (proof envelope, season record, anchor memo). Don't drift to `s{seed}` — that incident also burned us in Wave 4.
- **App UI for v2.0.0** is in scope but designed/built during Feature Pass. Open questions: framework (Tauri/Textual/Electron/PyQt), scope (full game vs audit viewer vs both), distribution. Don't predecide — surface in Phase 6 review.

## Hard rules

- **Never run translations from Claude.** README is in 8 languages (`README.{es,fr,hi,it,ja,pt-BR,zh}.md`). Mike runs polyglot-mcp locally in PowerShell. See `memory/translation-workflow.md`. Translations regenerate at Phase 10 step 2 — don't edit translated READMEs by hand.
- **Exclusive file ownership during swarm waves.** No agent edits a file outside its assigned domain. Cross-check with `git diff --name-only` after every amend wave.
- **Stage explicitly with `git add <file>`** — never `git add .` (would catch `.artifact/` scratch files and other untracked noise).
- **mypy strict is now blocking in CI** (Stage B graduated it from advisory). Type regressions fail the build — fix at the source, don't add `# type: ignore`.
- **Build must pass after every amend wave** before commit: `ruff check . && ruff format --check . && mypy sov_engine sov_transport sov_cli && pytest`.

## Where things live

- **Game vocabulary**: rulesets are Campfire / Town Hall / Treaty Table / Market Day. Mechanics: vouchers (promises with deadlines), deals (trades), treaties (multi-round agreements), anchors (XRPL memos), postcards (season recap output).
- **Persistence**: `.sov/game_state.json` (current game), `.sov/proofs/*.json` (round + final proofs, includes `anchors.json` index added in Stage B), `.sov/rng_seed.txt` (deterministic seed).
- **Landing page + handbook**: `site/` (Astro + Starlight via @mcptoolshop/site-theme), live on GitHub Pages. The `npmUrl` in `site/src/site-config.ts` is a HACK pointing at PyPI — upstream `packageUrl` proposal is filed against site-theme.
- **Release pipeline**: `.github/workflows/publish.yml` ships PyPI + PyInstaller binaries (3 platforms) + npm-launcher. PyPI publish gates on `needs: [build-binaries]` (Stage B fix — fail-closed). Renamed from `release.yml` in v2.0.2 to match the pre-existing PyPI Trusted Publisher record.

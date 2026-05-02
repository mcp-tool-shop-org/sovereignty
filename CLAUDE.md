# Sovereignty — Repo Instructions

Strategy game about governance, trust, and trade. Offline tabletop play (Python CLI) + XRPL online verification of round proofs. **Currently v2.0.2 — shipped 2026-04-30.** Distribution: `pip install sovereignty-game==2.0.2` and `npx @mcptoolshop/sovereignty`.

Global instructions in `~/.claude/CLAUDE.md` always apply. This file holds sovereignty-specific context that isn't discoverable from code or git history.

## Voice Narration

Use the `speakline` skill (`~/.claude/skills/speakline/speak`, Kokoro neural TTS, default voice Adam) to narrate substantive replies and milestones. Mike has reduced vision and prefers to listen. Full rules in the global CLAUDE.md.

## Build / verify

```bash
uv sync --all-extras            # set up venv (UV_LINK_MODE=copy on T9-Shared)
uv run pytest                   # 490 Python tests post-Wave-5 (also: 23 cargo, 101 vitest)
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

- **Pin D — theme-token discipline grep (v2.1 Wave 9 Stage D)**: `scripts/check-theme-tokens.sh` greps `app/src/**/*.{tsx,module.css}` for bare `#hex` / `rgba?(` outside `app/src/styles/theme.css`. Allowlist: `var(--sov-*)`, CSS keywords (`transparent`, `currentColor`, etc.), `color-mix(in srgb, var(--sov-*) ...)`, `/* legacy: ... */` migration markers. The `\b` word-boundary on `\brgba?\(` is what excludes `srgb,` inside `color-mix` from false-firing — that's the lesson from Pin A's `!`/em-dash false-fire. Integrated into ci.yml `tauri-and-frontend` job + `scripts/verify.sh` as a peer-level gate alongside Pin A.
- **Loading-state pattern (v2.1 Wave 9 Stage D)**: four-rule decision tree, not a per-surface lookup. **(1)** Skeleton for initial route loads (Audit / Game / Settings layout shapes are known). **(2)** Spinner with `aria-busy="true"` for inline ops. **(3)** Invisible for SSE state updates — the event feed itself is the signal; no flicker on `state_changed`. **(4)** Bespoke per-flow UI for long flows (Wave 5 verify-all + Wave 9 daemon-restart). Adding a new loading surface? Pick the rule, don't invent a fifth.
- **PanicModal mount: App root, OUTSIDE `<DaemonProvider>` (v2.1 Wave 9 Stage D)**: shell panic and daemon disconnect have different scope. PanicModal inside DaemonProvider would mean a shell panic preventing DaemonProvider from initializing → modal never mounts. App root mount keeps panic visibility independent of daemon state. Pinned mechanically by `app/src/App.test.tsx` consumer-listener pin (mirrors Stage 8-C SSE-banner consumer pin) — render `<App />` and assert at least one `shell-panic` listener registered.
- **Panic-event channel (v2.1 Wave 9 Stage D — Stage 8-C carryover)**: Rust `install_panic_hook()` in `app/src-tauri/src/lib.rs` emits `app.emit("shell-panic", PanicPayload { message, location, timestamp_iso })`. The 3-field shape is mechanically pinned in `panic_emit_tests::panic_payload_serializes_with_stable_field_names`; adding a 4th field requires both Rust + TS-mirror update + test bump. Frontend `app/src/components/PanicModal.tsx` consumes via `@tauri-apps/api/event::listen`. `ShellError::Panic` variant lives in `app/src/types/daemon.ts` (mixed daemon+shell error union); carve-out to `types/shell.ts` deferred to v2.2 if shell-error set grows.
- **Empty-state glyphs (v2.1 Wave 9 Stage D)**: inline SVG only — `EmptyState` component takes a `glyph?: ReactNode` prop. Three glyphs ship with v2.1: `EmptyBoxGlyph` (no games), `PausedGameGlyph` (no active game), `DisconnectedPlugGlyph` (daemon down). All use `currentColor` for theme alignment, `role="img"` + `aria-label` for accessibility. ~900 bytes total bundle delta. **NO image assets** (preserves Wave 4 lean-bundle principle: 255KB / 80KB gzipped at v2.1 Wave 9, well under 400/120 budget).
- **`:focus-visible` baseline (v2.1 Wave 9 Stage D)**: `:focus-visible { outline: 2px solid var(--sov-accent); outline-offset: 2px; }` in `globals.css`. Per-component overrides where shape demands. Mike has reduced vision — keyboard focus is real, not theoretical. Pinned by Vitest snapshot.
- **Pill text token (v2.1 Wave 9 Stage D)**: pill variants (success/warn/error/accent) keep tinted bg + colored border, but text uses `var(--sov-fg)` (not the saturated foreground token like `--sov-error`). Saturated-fg-on-tint failed AA 4.5:1 at 2.7–4.3:1; `--sov-fg-on-tint` clean. Apply pattern: `bg = var(--sov-X-bg)`, `border = var(--sov-X-border)`, `color = var(--sov-fg)`.
- **SSE banner UX (v2.1 Wave 9 Stage D)**: `position: sticky; top: 0; z-index: 100;` (above route content, below `<dialog>` z=10000). Auto-dismisses when daemon `status` flips back to `running`; manual dismiss preserved as redundant escape. Slide-in + fade animation 200ms `cubic-bezier(0.4, 0, 0.2, 1)` wrapped in `@media (prefers-reduced-motion: no-preference)`. Color token `--sov-warn` (recoverable, not fatal).
- **Three mechanical pins for voice/help/hint discipline (v2.1 Wave 8 Stage C)**: copy quality is enforced at CI, not by reviewer judgment. Pin A: `scripts/check-voice.sh` greps for `please|you should|you might|oops|whoops|sorry` everywhere + trailing `!"` and emoji codepoints in `sov_cli/errors.py` + `app/src-tauri/src/commands.rs` only (game flavor strings legitimately use `!`). Integrated into ci.yml lint-and-test as a fast pre-test gate. Pin B: `tests/test_error_hints_have_commands.py` AST-walks `sov_cli/errors.py` factories asserting every non-None `hint=` contains ≥2 backticks. Pin C: `tests/test_cli_help_no_placeholders.py` dynamically walks Typer's app structure and asserts zero `TODO|WIP|FIXME|XXX|<placeholder>` matches in `--help` output. Adding a new factory? It must ship with a backticked-command hint or Pin B fails. Adding a subcommand? `--help` must be placeholder-free or Pin C fails. Adding any user-facing emit? Voice grep applies.
- **Recursive AST walk for inline-codes regression test (v2.1 Wave 8 Stage C)**: `tests/test_errors_registry_no_inline_codes.py` was previously a hardcoded list of files; converted to recursive `.py` walk over `sov_daemon/` + `sov_cli/`. Detects any `SovError(code=<string-literal>, ...)` constructed OUTSIDE `sov_cli/errors.py` and fails with file + line + code. Pins the boundary mechanically — same pattern as `tests/test_daemon_types_ts_in_sync.py` and `tests/test_game_types_ts_in_sync.py`. Adding a new daemon error? Add the factory to `sov_cli/errors.py` and import + use it; don't inline-construct.
- **`sov play <ruleset>` thin alias (v2.1 Wave 8 Stage C)**: `sov play campfire_v1` is the no-config quickstart — aliases to `sov new` with default solo-vs-AI roster (1 human + 1 random AI opponent). Power users still use `sov new -p Alice -p Bob -p Carol` for multi-player at the table. `sov tutorial` stays as the interactive walkthrough. Smoke test in `tests/test_sov_play_alias.py`. Empty-state copy + README quickstart + onboarding panels all reference this exact spelling.
- **Version resolved dynamically (v2.1 Wave 8 Stage C)**: removed `SOV_VERSION = "1.4.7"` hardcoded constant from `sov_cli/main.py` (4 releases stale). All `--version` / self-check / support-bundle / feedback-report sites resolve via `importlib.metadata.version("sovereignty-game")` with a `pyproject.toml` fallback. Pinned by `tests/test_version_in_sync.py`. Don't reintroduce a hardcoded version constant.
- **Daemon-disconnected banner consumer wiring (v2.1 Wave 8 Stage C)**: `useDaemonEvents` already dispatched a `daemonConnectionLost` CustomEvent after retry exhaust, but no consumer listened — SSE silently died after ~63s. Wave 5's reconnect work was incomplete. Wired `app/src/components/DaemonDisconnectedBanner.tsx` mounted at the App root inside `<DaemonProvider>` so all routes see the banner. Reconnect button calls `useDaemon.refresh()`. This was the only genuine Stage A miss in the Stage 8-C audit; remaining HIGH-by-impact items were Stage C carryovers (3 daemon-down empty states + 1 stale version constant).
- **Daemon-down empty states name `sov daemon start` (v2.1 Wave 8 Stage C)**: `app/src/routes/Audit.tsx`, `Game.tsx`, `Settings.tsx` all surface a backticked recovery command when the daemon is not running. Settings previously had NO empty state at all (fieldsets just disabled). Snapshot tests pin the recovery-command strings.
- **CI pytest deprecation filter ordering (v2.1 Wave 8 Stage C)**: `.github/workflows/ci.yml` registers `-W` flags in CLI order at the front of `warnings.filters`, so the last-listed (=most-specific) filter wins for that module while the broad error filter still catches our own deprecations. `uvicorn 0.46` imports `websockets.legacy` + `websockets.server`, both deprecated in `websockets 14.0`; the warning fires inside the SSE fixture's asyncio uvicorn-startup task, which pyproject-level `filterwarnings` can't reach. Order in CI command: error filters FIRST, third-party ignores LAST. `scripts/verify.sh` mirrors. Don't reorder without re-testing the SSE suite.
- **Audit viewer is the v2.1 differentiator (Wave 5)**: XRPL-anchored proofs visualized as collapsible games + per-round verify flow. The product answer to "why does Sovereignty have a UI." Reference: `docs/v2.1-views.md`.
- **Game shell is read-only (Wave 5)**: passive real-time display. Gameplay verbs stay CLI-only per Wave 3 §10. Operator plays in CLI; shell shows what's happening.
- **Component-library-free (Wave 5)**: hand-built CSS modules + semantic HTML. No Mantine / MUI / Radix / shadcn / Chakra. Bundle lean, accessibility contract enforceable, scope discipline preserved. v2.2+ may revisit if specific primitive needs justify the dep.
- **Semantic HTML is non-negotiable (Wave 5)**: `<details>`/`<select>`/`<dialog>`/`<ul aria-live>` over div+role patterns. Mike has reduced vision; keyboard nav + screen reader support is real, not theoretical. Without semantic elements, agents reach for div+role and accessibility regresses silently.
- **Network switcher requires three guardrails (Wave 5)**: externally-started-daemon refuse, pending-anchors refuse, mainnet `<dialog>` confirm with explicit "real XRP" copy. Pinned at spec level so the v2.1 UX doesn't ship a footgun.
- **Tauri shell is window manager + IPC bridge only (v2.1 Wave 4)**: it doesn't contain views (those land Wave 5) or hold wallet seeds (daemon owns the trust boundary). 4 Tauri commands max — webview talks directly to daemon over HTTP/SSE for everything else. Reference: `docs/v2.1-tauri-shell.md`.
- **React + Vite + TypeScript for the shell (v2.1 Wave 4)**: matches GlyphStudio for skill compounding. Sovereignty is not a monorepo (single `app/`, npm not pnpm). Don't add Solid, pnpm workspaces, or codegen for v2.1.
- **`Cargo.lock` is tracked (v2.1 Wave 4)**: Tauri shell is a binary, not a library. Standard Rust binary practice.
- **Distribution deferred to Wave 11 (v2.1 Wave 4)**: cross-platform release matrix, code signing, notarization, Tauri-binary GitHub Release artifacts, npm-launcher wrapper for the Tauri binary all land at Treatment time alongside the existing PyPI/npm-launcher CLI flow. `memory/full-treatment.md` will need its own brief expansion at that point.
- **Default daemon spawn from shell is `--readonly` (v2.1 Wave 4)**: audit viewer doesn't need anchor capability; readonly is the safer default. Game shell (Wave 5) decides if it needs full mode.
- **Daemon mode is HTTP/JSON over localhost (v2.1 Wave 3)**: not Unix socket, not subprocess-per-call. Tauri webview / audit viewer fetch with bearer token. Random port per project root. SSE for push updates (one-way server→client; no Last-Event-ID buffer in v2.1). Reference: `docs/v2.1-daemon-ipc.md`.
- **Daemon serves audit + anchor only (v2.1 Wave 3)**: gameplay verbs stay CLI-only. Tauri shell + audit viewer agents must NOT assume gameplay endpoints exist on the daemon. v2.2+ extends if needed.
- **Wallet seed loads once at daemon start, never per-request (v2.1 Wave 3)**: held in memory only. Never logged. Never serialized to `.sov/daemon.json`. The `tests/test_daemon_seed_leak.py` test mechanically pins this trust boundary.
- **CORS is `*` on the daemon (v2.1 Wave 3)**: bearer token is the actual auth gate; CORS origin restrictions add no real security on a localhost-bound port. Locked at contract level so agents don't default-restrict and break Wave 4.
- **No `AsyncLedgerTransport` ABC (v2.1 Wave 3)**: same logic as Wave 2's Signer-protocol skip — don't abstract without a second async impl pulling on it.
- **Audit-ergonomics drives anchor batching, not cost (v2.1 Wave 2)**: XRPL fees are negligible (~$0.0002/game), so cost-driven batching doesn't earn complexity. The thesis is one verifiable chain pointer per game, not 16 — sovereignty's audit story breaks down with a scattered tx trail. Reference: `docs/v2.1-bridge-changes.md`.
- **Multi-memo, not single-memo packed (v2.1 Wave 2)**: a Payment with N memos (one SOV grammar line per memo) batches N rounds in a single tx. `MAX_ROUNDS=15` + final = 16 hashes; packed into one memo overflows the 1024-byte cap (~1152 bytes). Multi-memo also reuses existing `verify()` memo iteration — minimal wire-layer change. Forward-compatible with future high-round rulesets without split logic.
- **Verify split: local vs chain (v2.1 Wave 2)**: `verify_proof_local(proof_path)` (pure-Python, no chain hit) and `proof_anchor_status(proof_path, transport)` (3-state ANCHORED / PENDING / MISSING) replace the conflated v2.0.2 `verify(...)` semantic. Engine owns 3-state composition; transport returns plain bool from `is_anchored_on_chain`.
- **Network selection precedence (v2.1 Wave 2)**: `--network` CLI flag > `SOV_XRPL_NETWORK` env var > `testnet` default.
- **Multi-save model (v2.1)**: persistence is plural at `.sov/games/<game-id>/`. Game-id format is `s{seed}` (existing convention from `sov_engine/hashing.py`). Active-game pointer at `.sov/active-game`. Cross-game files (`wallet_seed.txt`, `season.json`) stay at `.sov/` root. Reference: `docs/multi-save.md`.
- **Proof format v2 hard cut** (not backward-compat): `state_hash` → `envelope_hash` covers full envelope (game_id, round, ruleset, rng_seed, timestamp_utc, players, state). `proof_version: 2`. v1 proofs raise `ProofFormatError` with migration text pointing at `pipx install 'sovereignty-game<2.0.0'` for legacy verify.
- **State schema_version** mirrors proof_version naming. Currently `schema_version: 1`. Bump on any field rename or removal; new optional fields don't require a bump.
- **Atomic writes**: single helper `sov_engine/io_utils.py::atomic_write_text` (Stage C consolidated the duplicate). Used for state, season, rng_seed, proof, anchors.json — all four persistence paths uniformly. Token-bearing files (`daemon.json`, `pending-anchors.json`, `rng_seed.txt`, `wallet_seed.txt`) write with `mode=0o600` (owner-only, Stage A hardening). Default mode for non-secret files is `0o644`.
- **XRPL memo format**: `sha256:<hex>` prefix, single occurrence — engine emits prefixed; transport `verify()` does structured `split('|')` then `sha256:` equality. The `envelope_hash` field value is raw 64-char hex (the prefix is added at the wire/memo layer only). Don't double-prefix — that incident burned us in Stage A Wave 4.
- **game_id format**: `s{seed}` everywhere (proof envelope, season record, anchor memos). Anchor memos read `proof_data["game_id"]` so the source of truth flows from the proof. Don't drift to `sov_{seed}` — that mismatch was the second Wave 4 incident.
- **F010 contract**: locked Campfire-upgrade hint string lives as `CAMPFIRE_UPGRADE_HINT` in `sov_engine/rules/campfire.py`. Surfaced when user invokes `sov upgrade workshop|builder` on Campfire (which has no resource-cost upgrade). Pinned by `tests/test_log_contracts.py`.
- **Logger names**: `sov_engine`, `sov_cli`, `sov_transport`, `sov_daemon` (Wave 3). Override via `SOV_LOG_LEVEL` env var (default WARNING on stderr).
- **Structured daemon logging (v2.1 Wave 7 Stage B)**: default stays human-readable. `sov daemon` and `sov daemon start` accept `--log-format=json` → JSON-lines to stderr. Each line contains `timestamp_iso`, `level`, `logger`, `event` (stable token, e.g. `"anchor.submit"`), plus per-event structured fields. The field-name registry lives at `sov_daemon/log_fields.py`; new daemon code consults the registry before inventing fields. Adding a new structured field? Extend the registry first — don't free-style.
- **ChainLookupResult is Python-only (v2.1)**: `is_anchored_on_chain` returns a `ChainLookupResult` StrEnum (FOUND / NOT_FOUND / LOOKUP_FAILED), but the engine collapses it to `AnchorStatus` (anchored / pending / missing) at `sov_engine/proof.py` before any value crosses the daemon → frontend boundary. The 3-state distinction is an internal transport↔engine contract for surfacing transient lookup failure separately from definitive not-found; the frontend deliberately does NOT see it. No TS mirror in `app/src/types/daemon.ts` is required at v2.1. v2.2 may surface the 3-state if the audit viewer UX needs it; at that point extend `tests/test_daemon_types_ts_in_sync.py` and add the TS mirror together.
- **Python↔TS mirror discipline (v2.1 Wave 4)**: where Python defines a string-literal contract (`StrEnum`, `TypedDict` field name, error code), the TS mirror in `app/src/types/{daemon,game}.ts` must list the same literals. Pinned mechanically: `tests/test_daemon_types_ts_in_sync.py` and `tests/test_game_types_ts_in_sync.py` grep-assert every Python literal appears in the TS file (parametrized; one test case per literal). Adding a new Python literal? Extend the test. Drift fails CI. Currently covered: SSE event types, daemon error codes (mixed-origin daemon+shell), `XRPLNetwork`, `AnchorStatus`, game-state UI-consumed subset (~18 fields). Intentionally NOT mirrored: `ChainLookupResult` (Python-only, see above), `BatchEntry` (server-side only — engine→transport contract; frontend never constructs a batch). Add a comment + extend the test if a v2.2+ feature surfaces either to the UI.
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
- **Persistence**: Multi-save layout under `.sov/games/<game-id>/{state.json, rng_seed.txt, proofs/, pending-anchors.json}` (game-id is `s{seed}`). `.sov/active-game` pointer tracks the current game. Cross-game state (`wallet_seed.txt`, `season.json`) stays at `.sov/` root. State `schema_version=1` (unchanged — multi-save and pending-anchors are layout, not content). Versioned JSON files (`pending-anchors.json`, `daemon.json`, `state.json`, `migration-state.json`, and v2.1 `anchors.json` + `season.json` wrappers) carry a `schema_version` field validated at read via the centralized `sov_engine.schemas.read_versioned` helper; `anchors.json` accepts a bare-dict shape on read for backward compatibility (pre-v2.1 layout) and writes the wrapped `{schema_version, anchors}` shape going forward. All persistence atomic-written via `sov_engine/io_utils.py::atomic_write_text`. v1 layout (`.sov/game_state.json`) auto-migrates on first v2.1 invocation. Multi-save reference: `docs/multi-save.md`. Bridge/anchor changes: `docs/v2.1-bridge-changes.md`.
- **Daemon**: `sov_daemon/` package (Starlette + uvicorn behind `[daemon]` opt-in extra). One daemon per project root, bound to `127.0.0.1:<random>`. State at `.sov/daemon.json` (pid + port + token + network + readonly + started_iso; seed never written here). Endpoints: `docs/v2.1-daemon-ipc.md` §4. SSE event stream at `/events`. Started via `sov daemon start [--readonly]`; stopped via `sov daemon stop`.
- **Transport internals**: `sov_transport/xrpl_internals.py` (Wave 3 extraction) lifts pure helpers + types — `XRPLNetwork`, `_NETWORK_TABLE`, `MainnetFaucetError`, `_format_memo`, `_classify_submit_error`, retry constants — so sync `XRPLTransport` (`xrpl.py`) and `AsyncXRPLTransport` (`xrpl_async.py`) share one source of truth. No I/O. Reference: `docs/v2.1-daemon-ipc.md` §2.
- **Desktop shell (v2.1)**: `app/` (Rust at `app/src-tauri/`, frontend at `app/src/`). React 19 + Vite 6 + TypeScript 5.7 + Tauri 2. 4 Tauri commands; webview talks directly to daemon for HTTP/SSE. Reference: `docs/v2.1-tauri-shell.md`. Local dev: `npm --prefix app run tauri dev`. Cross-platform release matrix is Wave 11 (Treatment).
- **Views (v2.1 Wave 5)**: `app/src/routes/{Audit,Game,Settings,Index}.tsx` consuming the daemon over HTTP/SSE. Shared components in `app/src/components/`. Theme tokens in `app/src/styles/theme.css` (single source of truth — `globals.css` references tokens, doesn't define colors). Pin D (`scripts/check-theme-tokens.sh`, v2.1 Wave 9) greps `app/src/**/*.{tsx,module.css}` for hardcoded `#hex` / `rgba?(` outside `theme.css`; allowlist covers `var(--sov-*)`, CSS keywords (`transparent`, `currentColor`, etc.), `color-mix(var(--sov-*) ...)`, and `/* legacy: ... */` migration markers. Game state TS types in `app/src/types/game.ts` (UI-consumed subset of `sov_engine/models.py`, pinned by `tests/test_game_types_ts_in_sync.py`). Reference: `docs/v2.1-views.md`.
- **Loading-state pattern (v2.1 Wave 9 Stage D)**: four-rule decision tree, not a per-surface lookup. **(1)** Skeleton for initial route loads — layout shape is known on Audit / Game / Settings. **(2)** Spinner with `aria-busy="true"` for inline operations (per-game expansion, doctor-button click, settings-save). **(3)** Invisible for SSE state updates — the event feed itself is the signal; no flicker on `state_changed`. **(4)** Bespoke per-flow UI for long multi-state flows (Wave 5 verify-all already shipped; Wave 9 locks daemon-restart). Same shape as the semantic-HTML rule: it's a discipline, not a list. Adding a new loading surface? Pick the rule, don't invent a fifth.
- **Landing page + handbook**: `site/` (Astro + Starlight via @mcptoolshop/site-theme), live at https://mcp-tool-shop-org.github.io/sovereignty/. Two `HACK:` comments link to upstream issues #4 (`packageUrl`) and #5 (`<slot name="head"/>`).
- **Release pipeline**: `.github/workflows/publish.yml` ships PyPI + PyInstaller binaries (3 platforms) + npm-launcher. PyPI publish gates on `needs: [build-binaries]` (fail-closed) + wheel-smoke gate (fresh-venv install + `sov self-check --json` status check). Renamed from `release.yml` in v2.0.2 to match the pre-existing PyPI Trusted Publisher record.
- **Repo-knowledge DB**: `mcp-tool-shop-org/sovereignty` indexed at `/Users/michaelfrilot/AI/repos/data/knowledge.db` (last sync at v2.0.2).

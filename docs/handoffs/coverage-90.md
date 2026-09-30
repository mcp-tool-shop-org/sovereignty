# Handoff: Python coverage 72.5% → 90%+

**Written:** 2026-09-29 · **Baseline commit:** `0184f54` · **For:** one executing session (Sonnet), working in `E:/AI/sovereignty` on `main`.

## Goal

Raise line coverage of `sov_engine`, `sov_transport`, `sov_cli` and `sov_daemon` from **72.5%** to **at least 90%**, then lock it in with a CI gate so it cannot slide back.

Done means all of these are true:

1. `coverage report` total is **≥ 90.0%** locally (command below).
2. The Codecov project figure on `main` is **≥ 90%**. Codecov read 71.4% at baseline; it runs slightly below the local number.
3. CI enforces it: `fail_under = 90` and a `codecov.yml` project target (Phase 7).
4. Every CI gate is green: ruff, ruff format, mypy strict on Linux, pytest with deprecations-as-errors, vitest, cargo, Atlas.

This is test work. Product code changes only when a test exposes a real bug (see "Bugs you find").

## Baseline, measured

5,975 statements, 1,643 missed. Reaching 90% means covering about **1,050 more lines**.

```bash
uv sync --all-extras
uv run pytest tests/ -q --cov=sov_engine --cov=sov_transport --cov=sov_cli --cov=sov_daemon --cov-report=term-missing:skip-covered
```

| File | Stmts | Missed | Covered |
|---|---:|---:|---:|
| `sov_cli/main.py` | 2283 | **954** | 58.2% |
| `sov_daemon/server.py` | 607 | 200 | 67.1% |
| `sov_engine/rules/campfire.py` | 379 | 90 | 76.3% |
| `sov_daemon/lifecycle.py` | 377 | 87 | 76.9% |
| `sov_engine/io_utils.py` | 371 | 57 | 84.6% |
| `sov_transport/xrpl_async.py` | 211 | 51 | 75.8% |
| `sov_transport/xrpl.py` | 213 | 35 | 83.6% |
| `sov_engine/proof.py` | 155 | 31 | 80.0% |
| `sov_cli/errors.py` | 154 | 27 | 82.5% |
| `sov_engine/wallet_seed.py` | 69 | 21 | 69.6% |
| `sov_daemon/events.py` | 170 | 17 | 90.0% |
| `sov_daemon/__main__.py` | 41 | 13 | 68.3% |
| everything else | 955 | 60 | — |

## Rules

- **Assert behaviour.** Every new test asserts an outcome: exit code *and* output text, state on disk, a returned value, or an error code. A test that only executes lines is not acceptable.
- **No gaming.**
  - No `omit` of whole modules.
  - No blanket `# pragma: no cover`.
  - Only the exclusions listed under "Allowed exclusions" are permitted. Report their line count in the final summary.
- **Offline only.**
  - No test touches the XRPL, the faucet, or any network.
  - Use the fakes listed under "Reuse these". The `RUN_INTEGRATION=1` tests stay opt-in and skipped.
- **Keep CI fast.** The suite runs in about 20–60 s. Keep the new tests under +60 s total, and never use `sleep`.
- **CI flags apply locally.** Run with the same `-W error::DeprecationWarning` flags CI uses (see `.github/workflows/ci.yml`, "Run tests").
- **Existing pins still apply.**
  - Voice pin `scripts/check-voice.sh`.
  - Hint pin `tests/test_error_hints_have_commands.py`.
  - Help pin `tests/test_cli_help_no_placeholders.py`.
  - Mirror pins `tests/test_*_ts_in_sync.py`.
- **Git hygiene.**
  - Stage explicitly with `git add <file>`, never `git add .`.
  - The untracked `swarms/` directory is not yours; leave it alone.
  - Commit once per phase.
- **Atlas.** After adding test files, run `npx --yes @dogfood-lab/atlas@1.20.0 map`, commit `atlas/`, and confirm `atlas check` passes.
- **No verification stage.** Per the 2026-09-29 standing rules, no verifier pass or jury is needed. The test suite and CI are the check.
- **No Ollama Cloud.** If you use local models, local only.

## Reuse these (do not build new harnesses)

| Need | Use |
|---|---|
| Run CLI commands | `typer.testing.CliRunner` + `monkeypatch.chdir(tmp_path)`. See `tests/test_anchor_cli.py` (`runner`, `_seed_game`) and `tests/test_cli_integration.py`. |
| A game on disk | `sov play campfire_v1` / `sov new -p A -p B` through the runner, or `_seed_game` in `tests/test_daemon_amend_wave7.py`. |
| Fake xrpl-py | `fake_xrpl` fixture / `_install_fake_xrpl_modules` in `tests/test_xrpl_amend_regressions.py`. |
| Faucet | `tests/test_fund_dev_wallet.py` stubs `sov_transport.xrpl.fund_dev_wallet`. |
| Keychain | `memory_keyring` fixture in `tests/test_wallet_keychain.py` (in-memory backend; never `keyrings.alt`). |
| Daemon HTTP | `build_app(DaemonConfig(...))` + Starlette `TestClient`; see `_build_app` in `tests/test_daemon_auth.py`. |
| Local HTTP stub | `pytest-httpserver` (already a dev dependency). |
| Campfire counters | the autouse `_reset_campfire_counters` fixture in `tests/conftest.py` already isolates them. |

If a helper is useful to three or more new test files, move it into `tests/conftest.py`. Otherwise keep it local.

## Phases (highest yield first)

Each phase lists the uncovered lines by function at baseline. Re-measure after each phase and record the total in the tally.

### Phase 1: CLI commands in `sov_cli/main.py` (target: cover ≥ 600 of 954)

Uncovered lines by command or helper:

| Lines | Function | Lines | Function |
|---:|---|---:|---|
| 77 | `treaty` | 25 | `promise` |
| 65 | `feedback` | 24 | `offer` |
| 60 | `season-postcard` | 24 | `vote` |
| 53 | `game-end` | 22 | `verify` |
| 50 | `doctor` | 19 | `_market_moment` |
| 47 | `scenario` | 18 | `wallet` |
| 46 | `tutorial` | 16 | `apologize` |
| 41 | `postcard` | 15 | `board` |
| 34 | `recap` | 14 | `turn`, `_postcard_highlights`, `daemon status` |
| 32 | `upgrade` | 12 | `daemon stop`, `_status_json_payload`, `_doctor_check_schema_version_currency` |
| 26 | `anchor` | 11 | `_sort_key` |
| 26 | `market` | ≤ 9 | about 25 smaller helpers |

For each command, cover:
- the happy path;
- each error exit (no active game, wrong tier, bad argument, unknown player, and so on), asserting both the exit code and the error code or hint;
- the `--json` shape where the command has one.

Command-specific notes:
- **`tutorial`** prompts for input; drive it with `runner.invoke(app, ["tutorial"], input="...")`.
- **`treaty` and `market`** need the Treaty Table and Town Hall tiers (`sov new --tier treaty-table|town-hall`).
- **`anchor`, `verify` and `wallet`** go through the fakes. Never go to the network.

### Phase 2: rules (`sov_engine/rules/campfire.py`, target ≥ 80 of 90)

- `resolve_event` (61 lines): parametrize over every event card, forcing the draw through the seeded RNG or by setting the deck. Assert each card's effect on coins, rep and resources.
- `resolve_space` (10), `_resolve_crossroads` (7), and the single-line branches of the other `_resolve_*` functions.
- Mop up `treaty_table.py` (13) and `town_hall.py` (8) in the same pass.

### Phase 3: daemon (`sov_daemon/server.py`, target ≥ 150 of 200)

- The anchor path, with a fake async client:
  - `_check_wallet_balance_or_raise` (21)
  - `_reserve_base_drops_from_server_state` (19) and `_fetch_reserve_base_drops` (10)
  - `flush_pending_anchors` (20) and `_do_anchor` (14)
  - `_async_xrpl_client` (9)
- Test both success and each failure (underfunded, reserve lookup fails, submit fails). Assert the HTTP status and the error code.
- `_proof_path_for_round` (21): every round-key shape, and path-traversal rejection.
- `counted_receive` (13): the 1 MiB body cap. Over-limit returns 413; check the actual status.
- The error branches in `games_handler`, `proofs_list_handler`, `verify_round_handler` and `_read_state` (7–8 each).
- Also `sov_daemon/events.py` (17): `_poll_once`, `get_chain_cache`, and the broadcast edge cases.

### Phase 4: transports (`xrpl.py` 35, `xrpl_async.py` 51, target ≥ 70)

- `_submit` in both transports (21 and 28): success, each `_classify_submit_error` class, and timeout/retry exhaustion. Reuse `fake_xrpl`.
- `is_anchored_on_chain`: found, not found, lookup failed.
- `get_memo_text`: all three response envelope shapes (`tx_json.Memos`, `Memos`, `tx.Memos`).
- `_maybe_aclose` in the async transport, and `sov_transport/null.py` (6).

### Phase 5: persistence and errors (target ≥ 120)

- **`io_utils.py` (57):**
  - `atomic_write_text` failure cleanup (make the rename raise, then assert no temp file is left);
  - `_recover_partial_migration`, `migrate_v1_layout` and the breadcrumb read/write;
  - `_quarantine_malformed`;
  - `_locked_pending_index`.
- **`proof.py` (31):** the legacy bare-dict `anchors.json` → wrapped migration, a malformed proof, and `verify_proof_local` mismatch.
- **`errors.py` (27):** call every uncovered factory. Assert its `code` and that `hint` carries backticked commands (the existing pin enforces the format).
- **`wallet_seed.py` (21):** `set`, `get` and `clear` of the mainnet seed with `memory_keyring`, plus the keyring-unavailable path.

### Phase 6: lifecycle (`sov_daemon/lifecycle.py` 87, `__main__.py` 13, target ≥ 50)

- `stop_daemon`, `start_daemon`, `_is_sov_daemon_pid`, `_spawn_detached` and `_read_handshake`/`_write_handshake` edge cases via `monkeypatch`: no handshake, stale PID, recycled PID, and a spawn that never becomes healthy. Do not start real daemons in these unit tests.
- `__main__.py`: `_parse_log_format_arg` and `_maybe_double_fork` with `os.fork` monkeypatched. POSIX only; skip on win32.

### Phase 7: lock it in

1. In `pyproject.toml`:

   ```toml
   [tool.coverage.run]
   source = ["sov_engine", "sov_transport", "sov_cli", "sov_daemon"]

   [tool.coverage.report]
   fail_under = 90
   exclude_also = [
       "if TYPE_CHECKING:",
       'if __name__ == "__main__":',
       "raise NotImplementedError",
   ]
   ```

   Plus the Windows-only exclusions below.

2. Add `codecov.yml` at the repo root:

   ```yaml
   coverage:
     status:
       project:
         default:
           target: 90%
           threshold: 1%
       patch:
         default:
           target: 90%
   ```

3. Confirm the 3.12 CI cell now fails when coverage drops. Test it on a scratch branch by deleting a test file, see red, then discard the branch.

4. Add a CHANGELOG `[Unreleased]` → `### Internal` line with the final percentage.

## Allowed exclusions (and nothing else)

CI runs on Linux, so these can never execute there.

- Windows-only helpers in `sov_daemon/lifecycle.py`: `_pid_alive_windows`, `_windows_process_command_line`, `_windows_process_image_name`, `_terminate_windows`, and the `sys.platform == "win32"` arm of `_spawn_detached`/`stop_daemon`. Mark each with `# pragma: no cover - windows only`.
- `sov_cli/__main__.py` (3 lines, a `python -m` shim).
- The three `exclude_also` patterns above.

This is roughly 40 lines, which is under 1% of the denominator. If you think something else needs excluding, stop and list it in your summary instead of excluding it.

## Bugs you find

Coverage work finds bugs. This session already found two: the wheel shipped without `sov_daemon`, and the frozen binary crashed on `--version`.

When a new test exposes a real defect:

1. Fix it in the smallest change.
2. Keep the test that caught it.
3. Add a `### Fixed` line under CHANGELOG `[Unreleased]`.
4. List it in your summary.

If the fix would change behaviour a player or operator sees, or it touches the daemon's trust boundary, do not fix it. Leave the test marked `xfail(strict=True)` with a reason, and flag it for the Director.

## Tally (fill in as you go)

| After | Missed | Total % | Commit |
|---|---:|---:|---|
| Baseline | 1643 | 72.5 | `0184f54` |
| Phase 1 | 660 | 89.0 | `84d51cd` |
| Phase 2 | 539 | 91.0 | `ae1eb42` |
| Phase 3 | 316 | 94.7 | `9fb4a78` |
| Phase 4 | 220 | 96.3 | `6a55aa9` |
| Phase 5 | 108 | 98.2 | `7c66029` |
| Phase 6 | 8 | 99.9 | (this commit) |
| Phase 7 (gate on) | | | |

## Final summary to the Director

Report:
- the final local and Codecov percentages;
- the number of excluded lines;
- the bugs found and fixed, plus any left as `xfail`;
- the CI run URL on the gate commit.

End with a recommendation on whether to cut **v2.3.3**. `main` already carries the frozen-binary `--version` fix, the in-repo npx launcher and coverage, none of which a release has shipped yet.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | 2 | Baseline commit, the exact coverage command, and the Atlas version are pinned. The model is set by the kickoff (Sonnet 5.5). |
| ANDON_AUTHORITY | 2 | Every phase commit must pass all CI gates. Phase 7 makes `fail_under = 90` a hard stop. A trust-boundary bug halts to the Director (`xfail(strict=True)`). |
| NAMED_COMPENSATORS | 2 | No irreversible actions: commits to `main` only, no publish, tag or release. Compensator: `git revert <sha>`. Owner: executing session. |
| DECOMPOSE_BY_SECRETS | 2 | Phases split along module boundaries (CLI / rules / daemon / transport / persistence / lifecycle), which change independently. |
| UNCERTAINTY_GATED_HUMANS | 2 | The Director is asked only about extra exclusions, behaviour-changing bug fixes, and the v2.3.3 release call. |
| EXTERNAL_VERIFIER | n/a | No specialized claims. The tests and CI are the check (standing rule 3, 2026-09-29). |

#!/usr/bin/env bash
# Verify script — lint + voice + test in one command. Mirrors the CI
# `lint-and-test` job order so devs hit the same gates locally.
# Usage: bash scripts/verify.sh

set -euo pipefail

echo "=== Lint ==="
uv run ruff check .

echo ""
echo "=== Format check ==="
uv run ruff format --check .

echo ""
echo "=== Voice anti-pattern gate ==="
# CI-TOOLING-C-005: mirrors the CI lint-and-test step. Slot between the
# format/type gates and pytest so a copy-style regression fails fast.
bash scripts/check-voice.sh

echo ""
echo "=== Theme-token discipline gate ==="
# CI-TOOLING-D-003: mirrors the CI tauri-and-frontend step (Pin D).
# Peer-level with the voice gate (two grep scripts, two failures
# readable on their own) — bare hex / rgba? outside theme.css fails
# fast before pytest spins up.
bash scripts/check-theme-tokens.sh

echo ""
echo "=== Tests ==="
# Mirrors the CI ``Run tests`` step: strict deprecation filter + curated
# third-party ignores. See .github/workflows/ci.yml for the rationale on
# the websockets/uvicorn ignore ordering.
uv run pytest tests/ -v \
  -W error::DeprecationWarning \
  -W error::PendingDeprecationWarning \
  -W "ignore::DeprecationWarning:websockets" \
  -W "ignore::DeprecationWarning:websockets.legacy" \
  -W "ignore::DeprecationWarning:uvicorn.protocols.websockets.websockets_impl"

echo ""
echo "All checks passed."

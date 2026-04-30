## What does this PR do?

<!-- One or two sentences. -->

## Why?

<!-- The problem this solves; link to issue if relevant (`Fixes #123`). -->

## How was this tested?

- [ ] `bash scripts/verify.sh` passes locally (or `uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy sov_engine sov_transport sov_cli`)
- [ ] New tests added for new behavior
- [ ] Documentation updated (README, handbook under `site/src/content/docs/handbook/`, CHANGELOG under `[Unreleased]`)

## Breaking changes?

<!-- Any user-visible behavior changes, CLI flag removals, file-format
     changes? If yes, document under CHANGELOG ## [Unreleased] ### BREAKING
     and bump the appropriate version component. -->

## Checklist

- [ ] Followed [CONTRIBUTING.md](../CONTRIBUTING.md)
- [ ] Stayed within one domain (engine / transport / cli / tests / ci-docs / frontend) — see CONTRIBUTING for the convention
- [ ] No secrets or wallet seeds in commits or test fixtures
- [ ] If adding/changing the proof envelope, bumped `PROOF_VERSION` and added a migration test (see `tests/test_proof_format.py` patterns)
- [ ] If touching shared atomic-write paths, used `sov_engine/io_utils.py::atomic_write_text` rather than re-implementing

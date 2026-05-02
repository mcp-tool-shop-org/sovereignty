"""Pin doc↔code consistency: SSE events + error codes from
docs/v2.1-daemon-ipc.md must appear as TS string literals in
app/src/types/daemon.ts. Drift fails CI."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TYPES_TS = REPO_ROOT / "app" / "src" / "types" / "daemon.ts"

SSE_EVENTS = {
    "daemon.ready",
    "daemon.shutdown",
    "anchor.pending_added",
    "anchor.batch_complete",
    "game.state_changed",
    "error",
}

DAEMON_ERROR_CODES = {
    "DAEMON_READONLY",
    "DAEMON_AUTH_MISSING",
    "DAEMON_AUTH_INVALID",
    "DAEMON_PORT_BUSY",
    "DAEMON_NOT_INSTALLED",
    "MAINNET_FAUCET_REJECTED",
    "ANCHOR_PENDING",
}


@pytest.mark.parametrize("literal", sorted(SSE_EVENTS | DAEMON_ERROR_CODES))
def test_daemon_ts_contains_literal(literal: str) -> None:
    """Every SSE event type and daemon error code must appear as a
    string literal in app/src/types/daemon.ts."""
    if not TYPES_TS.exists():
        pytest.skip("app/src/types/daemon.ts not present (pre-Wave-4)")
    text = TYPES_TS.read_text(encoding="utf-8")
    found = (f'"{literal}"' in text) or (f"'{literal}'" in text)
    assert found, (
        f"missing TS literal {literal!r} in {TYPES_TS} — "
        f"docs/v2.1-daemon-ipc.md added it but types/daemon.ts did not mirror"
    )

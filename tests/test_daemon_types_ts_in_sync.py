"""Pin doc↔code consistency: SSE events + error codes from
docs/v2.1-daemon-ipc.md must appear as TS string literals in
app/src/types/daemon.ts. Drift fails CI.

Stage 7-B amend (BACKEND-B-004) extends the pin to ``AnchorStatus`` and
``XRPLNetwork`` enum values — the type-sync test previously only covered
SSE events + DaemonErrorCode. The new ``ENUM_LITERAL_VALUES`` union slot is
the coordination point for parallel domain agents (docs adds error codes;
backend adds enum values) so neither edit collides on ``DAEMON_ERROR_CODES``.
"""

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
    # Daemon-emitted codes from docs/v2.1-daemon-ipc.md §4
    "DAEMON_READONLY",
    "DAEMON_AUTH_MISSING",
    "DAEMON_AUTH_INVALID",
    "DAEMON_PORT_BUSY",
    "DAEMON_NOT_INSTALLED",
    # Wallet / anchor-flow codes surfaced through daemon (docs/v2.1-bridge-changes.md §8)
    "MAINNET_FAUCET_REJECTED",
    "ANCHOR_PENDING",
    "MAINNET_UNDERFUNDED",
    "INVALID_NETWORK",
    # Stage 7-B Wave 7 consolidation: 8 inline daemon SovError sites swept into
    # sov_cli/errors.py factories (sov_daemon/server.py imports them). Mirror
    # coverage now matches the post-consolidation registry. Daemon's TS union
    # enumerates every code that can cross the wire on a 4xx/5xx response.
    # Shell-emitted ShellError variants (DaemonNotRunning, DaemonStopFailed,
    # ConfigFileMissing, ...) are tracked by SHELL_ERROR_CODES below — distinct
    # union, distinct naming convention (PascalCase Rust variants).
    "INVALID_GAME_ID",
    "INVALID_ROUND",
    "GAME_NOT_FOUND",
    "PROOF_NOT_FOUND",
    "PROOF_UNREADABLE",
    "XRPL_NOT_INSTALLED",
    "ANCHOR_FAILED",
}

# Tauri shell ShellError variants (Rust → TS via #[serde(tag = "code")]). Stage
# 7-B TAURI-SHELL-B-002 added the TS mirror at app/src/types/daemon.ts. Pinned
# here so a Rust-side variant addition or rename surfaces in CI. Naming is
# PascalCase (Rust enum variant names verbatim) — separate from the snake_case
# DAEMON_ERROR_CODES because the wire shape is distinct (tagged union, not a
# string-literal field).
SHELL_ERROR_CODES = {
    "DaemonNotRunning",
    "DaemonStartFailed",
    "DaemonNotInstalled",
    "ConfigFileMissing",
    "ConfigFileMalformed",
    "ConfigSchemaUnsupported",
    "SubprocessFailed",
}

# AnchorStatus + XRPLNetwork enum-value mirrors (BACKEND-B-004). Sourced from
# the canonical Python definitions so adding a new enum member triggers a TS
# mirror gap on the next pytest run — no manual literal maintenance.
ANCHOR_STATUS_VALUES = {"anchored", "pending", "missing"}
XRPL_NETWORK_VALUES = {"testnet", "mainnet", "devnet"}

# Union slot for parallel agents: every Python-side string union mirrored to
# TS lands here. Docs agent extends DAEMON_ERROR_CODES; backend agent extends
# ANCHOR_STATUS_VALUES / XRPL_NETWORK_VALUES; the parametrize set merges all.
ENUM_LITERAL_VALUES = ANCHOR_STATUS_VALUES | XRPL_NETWORK_VALUES


@pytest.mark.parametrize("literal", sorted(SSE_EVENTS | DAEMON_ERROR_CODES | SHELL_ERROR_CODES))
def test_daemon_ts_contains_literal(literal: str) -> None:
    """Every SSE event type, daemon error code, and shell error variant must
    appear as a string literal in app/src/types/daemon.ts."""
    if not TYPES_TS.exists():
        pytest.skip("app/src/types/daemon.ts not present (pre-Wave-4)")
    text = TYPES_TS.read_text(encoding="utf-8")
    found = (f'"{literal}"' in text) or (f"'{literal}'" in text)
    assert found, (
        f"missing TS literal {literal!r} in {TYPES_TS} — "
        f"docs/v2.1-daemon-ipc.md / docs/v2.1-tauri-shell.md added it but "
        f"types/daemon.ts did not mirror"
    )


@pytest.mark.parametrize("literal", sorted(ENUM_LITERAL_VALUES))
def test_daemon_ts_contains_enum_literal(literal: str) -> None:
    """Every Python-side string-union enum value mirrored to TS must appear
    as a string literal in app/src/types/daemon.ts.

    Source of truth in v2.1: ``sov_engine.proof.AnchorStatus`` (StrEnum
    members "anchored" / "pending" / "missing") and
    ``sov_transport.xrpl_internals.XRPLNetwork`` ("testnet" / "mainnet" /
    "devnet"). Drift would surface only at runtime when an engine value the
    TS doesn't accept hits the wire (the AnchorStatus value lights up every
    anchor.json row in app/src/routes/Audit.tsx).
    """
    if not TYPES_TS.exists():
        pytest.skip("app/src/types/daemon.ts not present (pre-Wave-4)")
    text = TYPES_TS.read_text(encoding="utf-8")
    found = (f'"{literal}"' in text) or (f"'{literal}'" in text)
    assert found, (
        f"missing TS literal {literal!r} in {TYPES_TS} — "
        f"AnchorStatus / XRPLNetwork mirror gap (Stage 7-B BACKEND-B-004)"
    )


def test_anchor_status_values_match_python_enum() -> None:
    """ANCHOR_STATUS_VALUES tracks ``sov_engine.proof.AnchorStatus`` members.

    Importing the StrEnum here means an engine-side addition (e.g.
    ``AnchorStatus.UNKNOWN`` for a v2.2 lookup-failed UX state) immediately
    fails this test, forcing a coordinated TS mirror update."""
    from sov_engine.proof import AnchorStatus

    assert {s.value for s in AnchorStatus} == ANCHOR_STATUS_VALUES, (
        "ANCHOR_STATUS_VALUES drifted from sov_engine.proof.AnchorStatus — "
        "sync the constant and add the new value to app/src/types/daemon.ts"
    )


def test_xrpl_network_values_match_python_enum() -> None:
    """XRPL_NETWORK_VALUES tracks ``sov_transport.xrpl_internals.XRPLNetwork``."""
    from sov_transport.xrpl_internals import XRPLNetwork

    assert {n.value for n in XRPLNetwork} == XRPL_NETWORK_VALUES, (
        "XRPL_NETWORK_VALUES drifted from sov_transport.xrpl_internals.XRPLNetwork — "
        "sync the constant and add the new value to app/src/types/daemon.ts"
    )

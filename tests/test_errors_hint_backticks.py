"""Smoke gate: every CLI-emitted SovError factory ships a backticked hint.

Pin B (the canonical AST gate) lives in ``tests/test_error_hints_have_commands.py``
and is owned by the ci-tooling agent in this wave. This file is a domain-
local smoke test that exercises the factories the cli agent *added* or
*touched* in Wave 11 — so a hint regression in those factories surfaces
even before Pin B lands.

Coverage:
  * ``payload_too_large_error`` (new) — daemon-cross-domain factory.
  * ``sse_subscribers_exhausted_error`` (new) — daemon-cross-domain factory.
  * Recovery-hint sweep targets (CLI-C-001 … CLI-C-013, C-016) — every
    factory's ``hint`` field contains ≥2 backticks.

If this test fails, Pin B will fail too — fix the hint at the source.
"""

from __future__ import annotations

import pytest

from sov_cli import errors


def _backtick_count(text: str) -> int:
    return text.count("`")


def test_payload_too_large_error_hint_has_backticks() -> None:
    err = errors.payload_too_large_error(limit_bytes=1_048_576)
    assert err.code == "PAYLOAD_TOO_LARGE"
    assert _backtick_count(err.hint) >= 2, (
        f"payload_too_large_error.hint must contain >= 2 backticks; got: {err.hint!r}"
    )


def test_sse_subscribers_exhausted_error_hint_has_backticks() -> None:
    err = errors.sse_subscribers_exhausted_error(active=8, cap=8)
    assert err.code == "SSE_SUBSCRIBERS_EXHAUSTED"
    assert _backtick_count(err.hint) >= 2, (
        f"sse_subscribers_exhausted_error.hint must contain >= 2 backticks; got: {err.hint!r}"
    )


@pytest.mark.parametrize(
    ("factory_call", "label"),
    [
        (lambda: errors.no_game_error(), "no_game_error"),
        (lambda: errors.game_over_error("Alice"), "game_over_error"),
        (lambda: errors.player_count_error(1), "player_count_error(1)"),
        (lambda: errors.player_count_error(5), "player_count_error(5)"),
        (lambda: errors.invalid_action_error("foo", "make/keep/break"), "invalid_action_error"),
        (lambda: errors.no_proof_error(), "no_proof_error"),
        (lambda: errors.proof_file_error("/tmp/x"), "proof_file_error"),
        (
            lambda: errors.upgrade_unavailable_error("Campfire"),
            "upgrade_unavailable_error",
        ),
        (lambda: errors.reset_error(), "reset_error"),
        (lambda: errors.daemon_readonly_error(), "daemon_readonly_error"),
        (lambda: errors.daemon_auth_missing_error(), "daemon_auth_missing_error"),
        (lambda: errors.daemon_auth_invalid_error(), "daemon_auth_invalid_error"),
        (lambda: errors.daemon_port_busy_error(8080), "daemon_port_busy_error"),
        (lambda: errors.daemon_stop_failed_error("OSError"), "daemon_stop_failed_error"),
        (lambda: errors.scenario_error("nope"), "scenario_error"),
        (lambda: errors.treaty_error("nope"), "treaty_error"),
        (lambda: errors.market_error("nope"), "market_error"),
        (
            lambda: errors.daemon_invalid_game_id_error("bad"),
            "daemon_invalid_game_id_error",
        ),
        (lambda: errors.daemon_invalid_round_error("99"), "daemon_invalid_round_error"),
        (lambda: errors.daemon_game_not_found_error("s42"), "daemon_game_not_found_error"),
        (
            lambda: errors.daemon_proof_not_found_error("s42", "3"),
            "daemon_proof_not_found_error",
        ),
        (
            lambda: errors.daemon_proof_unreadable_error("OSError"),
            "daemon_proof_unreadable_error",
        ),
        (
            lambda: errors.daemon_invalid_network_error("foo"),
            "daemon_invalid_network_error",
        ),
        (
            lambda: errors.daemon_xrpl_not_installed_error("ImportError"),
            "daemon_xrpl_not_installed_error",
        ),
        (
            lambda: errors.daemon_anchor_failed_error("RuntimeError", "boom"),
            "daemon_anchor_failed_error",
        ),
    ],
)
def test_factory_hint_has_backticks(factory_call, label) -> None:
    """Every Wave-11-touched factory's hint contains >= 2 backticks (Pin B)."""
    err = factory_call()
    assert err.hint, f"{label}.hint must be non-empty"
    count = _backtick_count(err.hint)
    assert count >= 2, (
        f"{label}.hint must contain >= 2 backticks (backtick-quoted command); "
        f"got {count} in: {err.hint!r}"
    )

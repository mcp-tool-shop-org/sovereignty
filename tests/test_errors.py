"""Tests for Sovereignty structured error handling."""

from __future__ import annotations

from sov_cli.errors import (
    SovError,
    anchor_error,
    anchor_mismatch_error,
    game_over_error,
    invalid_action_error,
    market_error,
    no_active_promise_error,
    no_game_error,
    no_proof_error,
    no_season_error,
    no_wallet_error,
    player_count_error,
    player_not_found_error,
    proof_file_error,
    proof_invalid_error,
    reset_error,
    scenario_error,
    share_code_error,
    treaty_error,
    wallet_error,
)


def test_sov_error_user_message_with_hint():
    err = SovError(code="TEST_CODE", message="Something broke.", hint="Try again.")
    msg = err.user_message()
    assert msg == "[TEST_CODE] Something broke.\n  Hint: Try again."


def test_sov_error_user_message_without_hint():
    err = SovError(code="TEST_CODE", message="Something broke.", hint="")
    msg = err.user_message()
    assert msg == "[TEST_CODE] Something broke."
    assert "Hint" not in msg


def test_sov_error_retryable_default_false():
    err = SovError(code="X", message="x", hint="x")
    assert err.retryable is False


def test_no_game_error():
    err = no_game_error()
    assert err.code == "STATE_NO_GAME"
    assert "No active game" in err.message
    assert "sov new" in err.hint
    assert err.retryable is False


def test_game_over_error_interpolates_winner():
    err = game_over_error("Alice")
    assert err.code == "STATE_GAME_OVER"
    assert "Alice" in err.message
    assert "won" in err.message
    assert err.retryable is False


def test_player_count_error_too_few():
    err = player_count_error(1)
    assert err.code == "INPUT_PLAYERS"
    assert "at least 2" in err.message
    assert err.retryable is False


def test_player_count_error_too_many():
    err = player_count_error(5)
    assert err.code == "INPUT_PLAYERS"
    assert "Maximum 4" in err.message
    assert err.retryable is False


def test_player_not_found_error_interpolates_name():
    err = player_not_found_error("Zara")
    assert err.code == "INPUT_PLAYER_NAME"
    assert "Zara" in err.message
    assert "sov status" in err.hint


def test_share_code_error_passes_detail():
    err = share_code_error("Bad checksum")
    assert err.code == "INPUT_SHARE_CODE"
    assert err.message == "Bad checksum"
    assert "sov scenario code" in err.hint


def test_wallet_error_is_retryable():
    err = wallet_error("timeout")
    assert err.code == "NET_WALLET"
    assert "timeout" in err.message
    assert err.retryable is True


def test_anchor_error_is_retryable():
    err = anchor_error("connection reset")
    assert err.code == "NET_ANCHOR"
    assert "connection reset" in err.message
    assert err.retryable is True


def test_input_and_state_errors_not_retryable():
    """All INPUT_* and STATE_* errors should be non-retryable."""
    non_retryable = [
        no_game_error(),
        game_over_error("Bob"),
        player_count_error(1),
        player_not_found_error("X"),
        invalid_action_error("bad", "good"),
        share_code_error("bad"),
        no_proof_error(),
        proof_file_error("/tmp/x.json"),
        proof_invalid_error("bad hash"),
        anchor_mismatch_error(),
        no_wallet_error("SOV_SEED"),
        no_active_promise_error("build bridge"),
        scenario_error("not found"),
        treaty_error("expired"),
        market_error("closed"),
        no_season_error(),
        reset_error(),
    ]
    for err in non_retryable:
        assert err.retryable is False, f"{err.code} should not be retryable"


def test_reset_error_has_actionable_hint():
    """Stage C humanization (W6): reset_error now points the user at where
    sovereignty looks for state, since the most common cause of "no game"
    is running the CLI from a different cwd than where the .sov/ folder lives."""
    err = reset_error()
    assert err.code == "STATE_NO_DATA"
    assert err.hint != ""
    assert ".sov" in err.hint
    # Hint surfaces in user_message when present
    assert "Hint" in err.user_message() or err.hint in err.user_message()


# ---------------------------------------------------------------------------
# Wave-7 CLI-001 / CLI-005: new factories
# ---------------------------------------------------------------------------


def test_invalid_game_id_error_shape() -> None:
    """``invalid_game_id_error`` surfaces the operator-passed value verbatim.

    The repr-rendering preserves control chars and surrounding whitespace
    so the operator sees exactly what they typed (or what an attacker
    tried to inject) without breaking the message layout.
    """
    from sov_cli.errors import invalid_game_id_error

    err = invalid_game_id_error("s17/../s42")
    assert err.code == "INPUT_GAME_ID"
    assert "s17/../s42" in err.message
    assert "sov games" in err.hint
    assert "sov resume" in err.hint
    assert err.retryable is False


def test_invalid_game_id_error_repr_renders_control_chars() -> None:
    """Control chars must be visible in the message via repr()."""
    from sov_cli.errors import invalid_game_id_error

    err = invalid_game_id_error("s42\n")
    # repr() escapes the newline as \n so the message stays one line.
    assert "\\n" in err.message


def test_daemon_not_installed_error_shape() -> None:
    """``daemon_not_installed_error`` carries the underlying ImportError detail."""
    from sov_cli.errors import daemon_not_installed_error

    err = daemon_not_installed_error("No module named 'sov_daemon'")
    assert err.code == "DAEMON_NOT_INSTALLED"
    assert "No module named 'sov_daemon'" in err.message
    assert "sovereignty-game[daemon]" in err.hint
    assert err.retryable is False


def test_daemon_not_running_error_shape() -> None:
    """``daemon_not_running_error`` is parameterless and points at lifecycle commands."""
    from sov_cli.errors import daemon_not_running_error

    err = daemon_not_running_error()
    assert err.code == "DAEMON_NOT_RUNNING"
    assert "No daemon" in err.message
    assert "sov daemon start" in err.hint
    assert "sov daemon status" in err.hint
    assert err.retryable is False


def test_daemon_stop_failed_error_carries_detail() -> None:
    """``daemon_stop_failed_error`` carries the underlying exception detail."""
    from sov_cli.errors import daemon_stop_failed_error

    err = daemon_stop_failed_error("Permission denied")
    assert err.code == "DAEMON_STOP_FAILED"
    assert "Permission denied" in err.message
    assert ".sov/daemon.json" in err.hint
    assert err.retryable is False


def test_anchor_pending_error_renders_round_keys() -> None:
    """``anchor_pending_error`` formats round_keys list and points at `sov anchor`."""
    from sov_cli.errors import anchor_pending_error

    err = anchor_pending_error(["1", "FINAL"])
    assert err.code == "ANCHOR_PENDING"
    assert "1, FINAL" in err.message
    assert "sov anchor" in err.hint


def test_anchor_pending_error_handles_empty_list() -> None:
    """Empty round_keys still produces a sensible message.

    Wave 11 (CLI-C-015) replaced the previous "Round(s) (none)" mixed
    plural/singular form with runtime-pluralized sentence-case copy.
    The empty-list path now produces a clean "No rounds queued..." line
    rather than a "Round(s) (none)" awkward shell-form.
    """
    from sov_cli.errors import anchor_pending_error

    err = anchor_pending_error([])
    assert err.code == "ANCHOR_PENDING"
    # Empty list = sentence describing the lack of queued rounds.
    assert "no rounds" in err.message.lower()


def test_mainnet_underfunded_error_renders_xrp() -> None:
    """``mainnet_underfunded_error`` shows both drops and XRP (consumed by daemon)."""
    from sov_cli.errors import mainnet_underfunded_error

    err = mainnet_underfunded_error(balance_drops=500_000, required_drops=10_000_000)
    assert err.code == "MAINNET_UNDERFUNDED"
    # 500000 drops = 0.5 XRP
    assert "0.5 XRP" in err.message
    # 10000000 drops = 10 XRP
    assert "10 XRP" in err.message
    # Both raw drop counts also surface for explorer-balance matching.
    assert "500000 drops" in err.message
    assert "10000000 drops" in err.message
    assert "testnet" in err.hint

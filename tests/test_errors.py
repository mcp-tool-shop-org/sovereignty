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

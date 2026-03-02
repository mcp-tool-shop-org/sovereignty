"""Structured error handling for Sovereignty CLI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SovError:
    """Structured error shape for user-facing messages.

    Follows the pattern: code + message + actionable hint.
    No stack traces. No jargon. Just what happened and what to try next.
    """

    code: str
    message: str
    hint: str
    retryable: bool = False

    def user_message(self) -> str:
        """Format for console output."""
        parts = [f"[{self.code}] {self.message}"]
        if self.hint:
            parts.append(f"  Hint: {self.hint}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Factory functions — one per failure category
# ---------------------------------------------------------------------------


def no_game_error() -> SovError:
    """No active game found."""
    return SovError(
        code="STATE_NO_GAME",
        message="No active game.",
        hint="Run: sov new -p Alice -p Bob",
    )


def game_over_error(winner: str) -> SovError:
    """Game is already over."""
    return SovError(
        code="STATE_GAME_OVER",
        message=f"The game is over. {winner} won.",
        hint="Wrap up: sov game-end",
    )


def player_count_error(count: int) -> SovError:
    """Invalid number of players."""
    if count < 2:
        return SovError(
            code="INPUT_PLAYERS",
            message="Need at least 2 players.",
            hint="Use: sov new -p Name1 -p Name2",
        )
    return SovError(
        code="INPUT_PLAYERS",
        message="Maximum 4 players.",
        hint="Remove some -p flags.",
    )


def player_not_found_error(name: str) -> SovError:
    """Named player doesn't exist in this game."""
    return SovError(
        code="INPUT_PLAYER_NAME",
        message=f"Player '{name}' not found.",
        hint="Check spelling. Use: sov status",
    )


def invalid_action_error(action: str, valid: str) -> SovError:
    """Invalid CLI action argument."""
    return SovError(
        code="INPUT_ACTION",
        message=f"Unknown action: '{action}'.",
        hint=f"Use: {valid}",
    )


def share_code_error(detail: str) -> SovError:
    """Share code couldn't be parsed."""
    return SovError(
        code="INPUT_SHARE_CODE",
        message=detail,
        hint="Use: sov scenario code",
    )


def no_proof_error() -> SovError:
    """No proof files found."""
    return SovError(
        code="STATE_NO_PROOF",
        message="No proof files found.",
        hint="Run: sov end-round",
    )


def proof_file_error(path: str) -> SovError:
    """Proof file not found."""
    return SovError(
        code="IO_PROOF",
        message=f"Proof file not found: {path}",
        hint="Check the path. List proofs: ls .sov/proofs/",
    )


def proof_invalid_error(detail: str) -> SovError:
    """Proof verification failed."""
    return SovError(
        code="STATE_PROOF_INVALID",
        message=f"Local proof invalid. {detail}",
        hint="The proof file may have been modified.",
    )


def anchor_mismatch_error() -> SovError:
    """Anchor TX memo doesn't match proof hash."""
    return SovError(
        code="NET_ANCHOR_MISMATCH",
        message="Anchor mismatch. TX memo doesn't match.",
        hint="The proof hash and on-chain memo differ.",
    )


def wallet_error(detail: str) -> SovError:
    """Wallet operation failed."""
    return SovError(
        code="NET_WALLET",
        message=f"Wallet operation failed: {detail}",
        hint="The Testnet faucet may be temporarily down. Try again in a minute.",
        retryable=True,
    )


def no_wallet_error(seed_env: str) -> SovError:
    """No wallet seed found."""
    return SovError(
        code="CONFIG_NO_WALLET",
        message="No wallet seed found.",
        hint=f"Set {seed_env} env var, or use --signer-file. Create a wallet: sov wallet",
    )


def anchor_error(detail: str) -> SovError:
    """Anchor submission failed."""
    return SovError(
        code="NET_ANCHOR",
        message=f"Anchor failed: {detail}",
        hint="The game still works fine offline.",
        retryable=True,
    )


def no_active_promise_error(text: str) -> SovError:
    """No matching promise to keep/break."""
    return SovError(
        code="INPUT_PROMISE",
        message=f"No active promise matching: '{text}'.",
        hint="Check: sov status",
    )


def scenario_error(detail: str) -> SovError:
    """Scenario operation failed."""
    return SovError(
        code="INPUT_SCENARIO",
        message=detail,
        hint="Run: sov scenario list",
    )


def treaty_error(detail: str) -> SovError:
    """Treaty operation failed."""
    return SovError(
        code="INPUT_TREATY",
        message=detail,
        hint="Check: sov treaty list",
    )


def market_error(detail: str) -> SovError:
    """Market operation failed."""
    return SovError(
        code="INPUT_MARKET",
        message=detail,
        hint="Check: sov market",
    )


def no_season_error() -> SovError:
    """No season data found."""
    return SovError(
        code="STATE_NO_SEASON",
        message="No season data yet.",
        hint="Finish a game first: sov game-end",
    )


def reset_error() -> SovError:
    """Reset state directory not found."""
    return SovError(
        code="STATE_NO_DATA",
        message="Nothing to reset. No .sov/ directory found.",
        hint="",
    )

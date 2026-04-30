"""Structured error handling for Sovereignty CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# ProofErrorKind distinguishes the *reason* a proof failed verification so
# the CLI can render an actionable hint. "MODIFIED" means the bytes don't
# match the recorded hash (likely tampered or corrupted). "UNSUPPORTED_VERSION"
# means the file is well-formed but uses a proof_version this binary does not
# understand (typically a legacy v1 proof — install sovereignty <2.0.0).
ProofErrorKind = Literal["MODIFIED", "UNSUPPORTED_VERSION", "UNKNOWN"]


class ProofFormatError(Exception):
    """Raised when a proof file uses an unsupported format version.

    As of sovereignty v2.0.0, only proof_version 2 is supported. v1 proofs
    (which only hashed the embedded ``state`` and left envelope metadata
    unsigned) cannot be verified by this binary.
    """


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
        message="No active game found in .sov/.",
        hint=(
            "Start one with: sov new -p Alice -p Bob   (swap in your players' names, 2-4 total)."
        ),
    )


def game_over_error(winner: str) -> SovError:
    """Game is already over."""
    return SovError(
        code="STATE_GAME_OVER",
        message=f"The game is over. {winner} won.",
        hint="Record the season and start a new game: sov game-end, then sov new -p ...",
    )


def player_count_error(count: int) -> SovError:
    """Invalid number of players."""
    if count < 2:
        return SovError(
            code="INPUT_PLAYERS",
            message=f"Need at least 2 players (got {count}).",
            hint="Add another -p flag, e.g.: sov new -p Alice -p Bob",
        )
    return SovError(
        code="INPUT_PLAYERS",
        message=f"Maximum 4 players (got {count}).",
        hint="Drop a -p flag and try again.",
    )


def player_not_found_error(name: str) -> SovError:
    """Named player doesn't exist in this game."""
    return SovError(
        code="INPUT_PLAYER_NAME",
        message=f"Player '{name}' is not in this game.",
        hint="Run `sov status` to see the active player names (case-sensitive).",
    )


def invalid_action_error(action: str, valid: str) -> SovError:
    """Invalid CLI action argument."""
    return SovError(
        code="INPUT_ACTION",
        message=f"Unknown action: '{action}'.",
        hint=f"Use one of: {valid}",
    )


def share_code_error(detail: str) -> SovError:
    """Share code couldn't be parsed."""
    return SovError(
        code="INPUT_SHARE_CODE",
        message=detail,
        hint=(
            "Generate a fresh share code with `sov scenario code`, "
            "or pick a scenario from `sov scenario list`."
        ),
    )


def no_proof_error() -> SovError:
    """No proof files found."""
    return SovError(
        code="STATE_NO_PROOF",
        message="No proof files found in .sov/proofs/.",
        hint=(
            "Generate one with: sov end-round   "
            "(closes the current round and writes a round_NNN.proof.json)."
        ),
    )


def proof_file_error(path: str) -> SovError:
    """Proof file not found."""
    return SovError(
        code="IO_PROOF",
        message=f"Proof file not found: {path}",
        hint=(
            "Double-check the path. To list available proofs: "
            "ls .sov/proofs/   (or omit the path to use the latest)."
        ),
    )


def proof_invalid_error(
    detail: str,
    kind: ProofErrorKind = "UNKNOWN",
) -> SovError:
    """Proof verification failed.

    ``kind`` distinguishes tampering from forward/backward-incompatible
    proof versions so the user gets the right next step. The ``detail``
    string from the engine (esp. for UNSUPPORTED_VERSION) is preserved
    verbatim in the user-facing message so the actionable text the
    engine raised is not lost when the CLI wraps it.
    """
    if kind == "UNSUPPORTED_VERSION":
        # Engine's ProofFormatError text already names the recovery options
        # ("install sovereignty <2.0.0 OR re-run the original game"). Keep
        # it in the message; mirror the bullet form in the hint so callers
        # who only render `hint` still see the choice.
        hint = (
            "Either install sovereignty <2.0.0 to verify this legacy proof, "
            "or re-run the original game under v2.0.0+ to regenerate a v2 proof."
        )
    elif kind == "MODIFIED":
        hint = (
            "The proof bytes don't match the recorded hash — the file was "
            "edited, corrupted, or truncated. If you have the original game "
            "save, re-run `sov end-round` to regenerate the proof."
        )
    else:
        hint = (
            "The proof file may have been modified. "
            "Re-run `sov end-round` from the original save to regenerate it."
        )
    return SovError(
        code="STATE_PROOF_INVALID",
        message=f"Local proof invalid. {detail}",
        hint=hint,
    )


def state_corrupt_error(detail: str) -> SovError:
    """On-disk game state could not be parsed (corrupted save).

    ``detail`` should already include the underlying exception class and
    message so the operator has something concrete to grep / report.
    """
    return SovError(
        code="STATE_CORRUPT",
        message=(
            f"Saved game state is unreadable.\n"
            f"  Underlying error: {detail}\n"
            "  To recover, delete the corrupted save and start a new game:\n"
            "    rm .sov/game_state.json .sov/rng_seed.txt\n"
            "    sov new -p Alice -p Bob   # use your actual player names\n"
            "  If you need to preserve the file for debugging, move it instead:\n"
            "    mv .sov/game_state.json .sov/game_state.json.bak"
        ),
        hint=(
            "Run `sov support-bundle` first if you plan to file a bug — "
            "it captures the diagnostic context maintainers need."
        ),
    )


def state_version_mismatch_error(found: object) -> SovError:
    """Saved state uses a schema_version this binary doesn't understand.

    Tells the operator (a) what schema this save was written with,
    (b) what this binary supports, (c) the exact recovery commands.
    """
    # Local import to avoid circular CLI<->errors dependency at module load.
    _supported: int | str
    try:
        from sov_cli.main import SUPPORTED_STATE_SCHEMA_VERSION as _supported
    except Exception:
        _supported = "?"
    return SovError(
        code="STATE_VERSION_MISMATCH",
        message=(
            f"Saved game state schema_version={found!r} is not supported "
            f"by this sovereignty binary (supports v{_supported}).\n"
            "  Most likely you upgraded sovereignty across a save-format bump.\n"
            "  To recover, either:\n"
            "    1) Re-install the sovereignty version that wrote this save, OR\n"
            "    2) Archive the old save and start fresh:\n"
            "         mv .sov/game_state.json .sov/game_state.json.bak\n"
            "         sov new -p Alice -p Bob   # use your actual player names"
        ),
        hint=(
            "If you needed that save, downgrade sovereignty before deleting — "
            "this binary cannot read it."
        ),
    )


def anchor_mismatch_error() -> SovError:
    """Anchor TX memo doesn't match proof hash."""
    return SovError(
        code="NET_ANCHOR_MISMATCH",
        message=("Anchor mismatch — the on-chain memo doesn't match this proof's hash."),
        hint=(
            "Either you passed the wrong --tx (check anchors.json), "
            "or the proof file changed after it was anchored. "
            "If you re-ran end-round after anchoring, the new hash won't match."
        ),
    )


def wallet_error(detail: str) -> SovError:
    """Wallet operation failed."""
    return SovError(
        code="NET_WALLET",
        message=f"Wallet operation failed: {detail}",
        hint=(
            "The XRPL Testnet faucet is occasionally rate-limited or down. "
            "Wait ~60 seconds and re-run `sov wallet`. "
            "Status check: https://xrpl.org/xrp-testnet-faucet.html"
        ),
        retryable=True,
    )


def no_wallet_error(seed_env: str) -> SovError:
    """No wallet seed found."""
    return SovError(
        code="CONFIG_NO_WALLET",
        message="No wallet seed found — anchoring requires an XRPL Testnet wallet.",
        hint=(
            f"Pick one of: (1) set {seed_env} in your environment, "
            "(2) pass --signer-file <path> to a file containing the seed, or "
            "(3) generate a new Testnet wallet with `sov wallet` "
            "(seed saved to .sov/wallet_seed.txt — gitignored)."
        ),
    )


def anchor_error(detail: str) -> SovError:
    """Anchor submission failed."""
    return SovError(
        code="NET_ANCHOR",
        message=f"Anchor submission failed: {detail}",
        hint=(
            "Anchoring is optional — your game state is intact and proofs are saved "
            "locally. Try again in a minute (XRPL Testnet can be flaky), or skip "
            "anchoring and continue play."
        ),
        retryable=True,
    )


def no_active_promise_error(text: str) -> SovError:
    """No matching promise to keep/break."""
    return SovError(
        code="INPUT_PROMISE",
        message=f"No active promise matching: '{text}'.",
        hint=("Run `sov status` to see active promises (text must match exactly, case-sensitive)."),
    )


def scenario_error(detail: str) -> SovError:
    """Scenario operation failed."""
    return SovError(
        code="INPUT_SCENARIO",
        message=detail,
        hint="See available scenarios with: sov scenario list",
    )


def treaty_error(detail: str) -> SovError:
    """Treaty operation failed."""
    return SovError(
        code="INPUT_TREATY",
        message=detail,
        hint=("List your active treaties with `sov treaty list` (treaty IDs look like t_0001)."),
    )


def market_error(detail: str) -> SovError:
    """Market operation failed."""
    return SovError(
        code="INPUT_MARKET",
        message=detail,
        hint="See current prices and your balance with: sov market",
    )


def no_season_error() -> SovError:
    """No season data found."""
    return SovError(
        code="STATE_NO_SEASON",
        message="No season data yet — seasons start after the first game ends.",
        hint="Finish a game with `sov game-end` to start tracking the season.",
    )


def reset_error() -> SovError:
    """Reset state directory not found."""
    return SovError(
        code="STATE_NO_DATA",
        message="Nothing to reset — no .sov/ directory in the current working directory.",
        hint=(
            "Sovereignty stores state in a `.sov/` folder next to where you run "
            "the CLI. If you expected a game here, check your working directory "
            "(`pwd`)."
        ),
    )

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


def insufficient_resources_error(
    target: str,
    needed: dict[str, int],
    have: dict[str, int],
    hint: str,
) -> SovError:
    """Player can't afford an upgrade — name what's needed, have, and the next step.

    ``target`` is the upgrade space ("workshop" / "builder").
    ``needed`` and ``have`` map resource name -> count (e.g. {"coins": 2, "wood": 1}).
    ``hint`` is the actionable next-step string the caller has computed
    (e.g. "Earn 1 more coin via 'sov market sell'.").

    Mirrors the Stage C humanization standard: structured code +
    plain-English message + exactly-one actionable next step. Pluralizes
    "coin/coins" but keeps resource names lowercase singular ("wood",
    "tools") — they're mass nouns in the game's vocabulary.
    """

    def _fmt(parts: dict[str, int]) -> str:
        chunks: list[str] = []
        for name, count in parts.items():
            if name == "coins":
                unit = "coin" if count == 1 else "coins"
                chunks.append(f"{count} {unit}")
            else:
                chunks.append(f"{count} {name}")
        return " + ".join(chunks) if chunks else "nothing"

    return SovError(
        code="INPUT_UPGRADE",
        message=(f"Cannot upgrade {target}: need {_fmt(needed)}, have {_fmt(have)}."),
        hint=hint,
    )


def upgrade_rep_error(target: str, needed: int, have: int, hint: str) -> SovError:
    """Player lacks the reputation gate for an upgrade (e.g. Builder needs Rep >= 3)."""
    return SovError(
        code="INPUT_UPGRADE",
        message=(f"Cannot upgrade {target}: need Rep >= {needed}, have {have}."),
        hint=hint,
    )


def upgrade_unavailable_error(ruleset_name: str) -> SovError:
    """The current ruleset doesn't expose resource-cost upgrades.

    Used when ``sov upgrade ...`` is called on Campfire (which uses the
    coinless build path via ``sov build`` instead).
    """
    return SovError(
        code="INPUT_UPGRADE",
        message=(
            f"Resource-cost upgrades are not available on {ruleset_name}. "
            "This ruleset uses the coinless workshop."
        ),
        hint=(
            "Use 'sov build' for free tier-1 builds, or start a new game on "
            "Town Hall / Treaty Table / Market Day for resource-cost upgrades:"
            "\n    sov new --tier town-hall -p Alice -p Bob"
        ),
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


def no_active_game_error() -> SovError:
    """No active game pointer and the layout has zero or multiple games.

    Distinct from ``no_game_error`` (which fires when the entire ``.sov/``
    layout is empty). This one fires when saved games exist but the CLI
    cannot pick one without operator input — typically after a fresh
    multi-save migration where the user has more than one save.
    """
    return SovError(
        code="STATE_NO_ACTIVE_GAME",
        message="No active game.",
        hint=(
            "Run `sov games` to list saved games, then `sov resume <game-id>` "
            "to pick one. Or `sov new` to start fresh."
        ),
    )


# ---------------------------------------------------------------------------
# v2.1 bridge errors (per docs/v2.1-bridge-changes.md §8)
# ---------------------------------------------------------------------------


def mainnet_faucet_rejected_error() -> SovError:
    """Mainnet has no faucet — operator must provide a funded mainnet seed.

    Surfaced when ``fund_dev_wallet(MAINNET)`` raises ``MainnetFaucetError``;
    the CLI translates that to this structured shape so the user gets a
    plain-English next step instead of a raw exception.
    """
    return SovError(
        code="MAINNET_FAUCET_REJECTED",
        message="mainnet has no faucet.",
        hint=(
            "Set XRPL_SEED to a funded mainnet wallet, "
            "or run `sov wallet --network testnet` to generate a play-money "
            "Testnet wallet instead."
        ),
    )


def anchor_pending_error(round_keys: list[str]) -> SovError:
    """One or more rounds are queued in pending-anchors.json, not yet on chain.

    ``round_keys`` follows the existing anchors.json convention (stringified
    round number ``"1"``…``"15"`` or ``"FINAL"``). Empty list still produces
    a sensible message — the rounds field renders as "(none)".
    """
    rounds_str = ", ".join(round_keys) if round_keys else "(none)"
    return SovError(
        code="ANCHOR_PENDING",
        message=(f"Round(s) {rounds_str} are queued in pending-anchors.json, not yet on chain."),
        hint="Run `sov anchor` to flush pending anchors in a single batched tx.",
    )


def invalid_network_error(value: str) -> SovError:
    """User supplied a network value that isn't one of {testnet, mainnet, devnet}.

    Surfaced by ``sov anchor --network <bad>`` and any other CLI / config
    surface that resolves a network string.
    """
    return SovError(
        code="INVALID_NETWORK",
        message=f"'{value}' is not a valid XRPL network.",
        hint="Valid networks: testnet, mainnet, devnet.",
    )


def mainnet_underfunded_error(balance_drops: int, required_drops: int) -> SovError:
    """Mainnet wallet balance is below the reserve+fee floor for an anchor batch.

    Drops are XRPL's smallest unit (1 XRP = 1_000_000 drops). The message
    surfaces both the raw drop count and an XRP rendering so the operator
    can match against an explorer balance directly.
    """

    def _drops_to_xrp(drops: int) -> str:
        return f"{drops / 1_000_000:.6f}".rstrip("0").rstrip(".") or "0"

    have_xrp = _drops_to_xrp(balance_drops)
    need_xrp = _drops_to_xrp(required_drops)
    return SovError(
        code="MAINNET_UNDERFUNDED",
        message=(
            f"Mainnet wallet underfunded: have {have_xrp} XRP "
            f"({balance_drops} drops), need {need_xrp} XRP "
            f"({required_drops} drops) to cover reserve + fee."
        ),
        hint=(
            "Top up the mainnet wallet, or switch to testnet with "
            "`sov anchor --network testnet` (testnet XRP is play money)."
        ),
    )


# ---------------------------------------------------------------------------
# v2.1 daemon errors (per docs/v2.1-daemon-ipc.md §7)
# ---------------------------------------------------------------------------


def daemon_readonly_error() -> SovError:
    """A write endpoint was called against a daemon started with --readonly.

    Surfaced by the daemon HTTP layer (anchor / anchor-checkpoint endpoints)
    when readonly mode is active, and re-emitted here so CLI surfaces that
    proxy daemon responses can render the structured shape consistently.
    """
    return SovError(
        code="DAEMON_READONLY",
        message="daemon started with --readonly; anchor endpoints disabled",
        hint="restart without --readonly to enable anchoring",
    )


def daemon_auth_missing_error() -> SovError:
    """Authorization header missing on a daemon HTTP request."""
    return SovError(
        code="DAEMON_AUTH_MISSING",
        message="Authorization header missing on daemon request",
        hint=("include `Authorization: Bearer <token>`; token is in `.sov/daemon.json`"),
    )


def daemon_auth_invalid_error() -> SovError:
    """Authorization token does not match the daemon's bearer token."""
    return SovError(
        code="DAEMON_AUTH_INVALID",
        message="Authorization token does not match daemon's token",
        hint="re-read token from `.sov/daemon.json` or restart daemon",
    )


def daemon_port_busy_error(port: int) -> SovError:
    """Daemon could not bind because the requested port is already in use.

    Spec §6 selects a fresh random port at every start; this surfaces when
    a manually-pinned port (or a rare race) collides.
    """
    return SovError(
        code="DAEMON_PORT_BUSY",
        message=f"Port {port} already in use",
        hint=(
            "stop the conflicting process or restart `sov daemon start` "
            "(which selects a fresh random port)"
        ),
    )


# ---------------------------------------------------------------------------
# v2.1 daemon lifecycle errors (CLI-emitted, factory-style — Wave 7 CLI-005)
# ---------------------------------------------------------------------------
#
# Three daemon errors were originally emitted as inline ``SovError(...)`` in
# ``sov_cli/main.py`` (the ``daemon`` Typer subapp). Wave 6 audit CLI-005
# flagged the inline pattern as drift from the rest of the module's
# factory-per-failure-category convention; Wave 7 amend lifts them here so
# downstream humanization passes (and any future translators) see them
# alongside the rest of the registry.


def daemon_not_installed_error(detail: str) -> SovError:
    """The optional ``[daemon]`` extra is not installed.

    ``detail`` is the underlying ``ImportError`` message captured at the
    boundary; it gives the operator something concrete to grep when
    diagnosing a stripped install.
    """
    return SovError(
        code="DAEMON_NOT_INSTALLED",
        message=f"Daemon support is not installed: {detail}",
        hint="Install the daemon extra: pip install 'sovereignty-game[daemon]'",
    )


def daemon_not_running_error() -> SovError:
    """No daemon is recorded for this project root."""
    return SovError(
        code="DAEMON_NOT_RUNNING",
        message="No daemon is recorded for this project root.",
        hint=(
            "Start one with `sov daemon start`, or check "
            "`sov daemon status` to inspect the recorded state."
        ),
    )


def daemon_stop_failed_error(detail: str) -> SovError:
    """``stop_daemon`` raised an unexpected exception.

    ``detail`` is the underlying exception's stringification; it preserves
    the operator-actionable context the inline call site previously
    surfaced.
    """
    return SovError(
        code="DAEMON_STOP_FAILED",
        message=f"Daemon stop failed: {detail}",
        hint=("Inspect `.sov/daemon.json` for the recorded pid, then kill it manually if needed."),
    )


# ---------------------------------------------------------------------------
# v2.1 game-id validation (CLI + engine path-traversal guard — Wave 7 CLI-001)
# ---------------------------------------------------------------------------


def invalid_game_id_error(value: str) -> SovError:
    """Operator passed a game-id that fails the persistence-layer allowlist.

    The allowlist matches the existing ``f"s{seed}"`` convention used
    throughout the codebase (proof envelopes, season records, anchor memos)
    and explicitly rejects ``..``, path separators, NUL, newlines, and any
    other character that could escape ``.sov/games/<id>/`` when used to
    construct a per-game path.

    The ``value`` is echoed back via ``repr()`` so control characters and
    leading/trailing whitespace are visible to the operator without
    breaking the message layout.
    """
    return SovError(
        code="INPUT_GAME_ID",
        message=f"Invalid game-id: {value!r}.",
        hint=(
            "Game-ids match the ``s<seed>`` convention (e.g. ``s42``). "
            "Run `sov games` to list saved games, then "
            "`sov resume <game-id>` to pick one."
        ),
    )


# ---------------------------------------------------------------------------
# v2.1 daemon HTTP error registry (Stage 7-B amend, CLI-B-001 + CLI-B-012)
# ---------------------------------------------------------------------------
#
# Eight error codes were emitted as inline string literals in
# ``sov_daemon/server.py`` (4xx/5xx error paths reachable from every
# endpoint). The Stage 7-B amend lifts them into factories here so:
#
#   1. There is one canonical message + hint per code (was: drift between
#      ``INVALID_NETWORK`` in ``invalid_network_error`` vs the inline at
#      ``server.py:815`` — different messages, same code).
#   2. The TS ``DaemonErrorCode`` mirror has a single source of truth to
#      enumerate against.
#   3. Future humanization passes touch one file, not two.
#
# Naming convention: ``daemon_<concept>_error`` to mirror the existing
# ``daemon_readonly_error`` / ``daemon_auth_missing_error`` block above.


def daemon_invalid_game_id_error(value: str) -> SovError:
    """HTTP 400 — the path-param ``game_id`` does not match ``s<digits>``.

    Daemon-side counterpart to ``invalid_game_id_error`` (CLI-side
    Typer-Exit). Same code, daemon-flavored message + hint so
    ``GET /games/<bad>/state`` produces a clean 400 response with an
    operator-actionable next step.
    """
    return SovError(
        code="INVALID_GAME_ID",
        message=f"game_id {value!r} does not match the allowed format",
        hint="game_id must match s<digits> (e.g. s42). GET /games to list valid ids.",
    )


def daemon_invalid_round_error(value: str) -> SovError:
    """HTTP 400 — the path-param ``round`` is neither ``1..15`` nor ``FINAL``.

    Surfaced when the daemon's anchor-status / proof-detail endpoints
    receive a round identifier that fails the allowlist. The hint names
    the canonical shapes the daemon accepts.
    """
    return SovError(
        code="INVALID_ROUND",
        message=f"round {value!r} is not a valid round identifier",
        hint="rounds are integers 1..15 or the literal FINAL.",
    )


def daemon_game_not_found_error(game_id: str) -> SovError:
    """HTTP 404 — no saved game with the requested id on disk.

    Surfaced by the daemon's ``GET /games/<id>/state``,
    ``GET /games/<id>/proofs``, ``GET /games/<id>/pending-anchors``, and
    ``POST /games/<id>/anchor`` paths when the per-game directory is
    absent. Hint points at the listing endpoint.
    """
    return SovError(
        code="GAME_NOT_FOUND",
        message=f"no saved game with id '{game_id}'",
        hint="GET /games to list saved games.",
    )


def daemon_proof_not_found_error(game_id: str, round_key: str) -> SovError:
    """HTTP 404 — the requested round has no proof file on disk.

    Surfaced by the daemon's ``GET /games/<id>/proofs/<round>`` and
    ``GET /games/<id>/anchor-status/<round>`` paths. Hint directs the
    consumer at the proofs-listing endpoint so they can pick a real
    round key.
    """
    return SovError(
        code="PROOF_NOT_FOUND",
        message=f"no proof for round '{round_key}' in game '{game_id}'",
        hint="GET /games/{game_id}/proofs to list available rounds.",
    )


def daemon_proof_unreadable_error(exc_type: str) -> SovError:
    """HTTP 500 — the proof file exists but cannot be parsed.

    ``exc_type`` is the underlying exception class name
    (``OSError`` / ``JSONDecodeError`` / etc.) — preserves the operator-
    diagnostic shape the inline emit at ``server.py:479`` carried.
    """
    return SovError(
        code="PROOF_UNREADABLE",
        message=f"proof file exists but could not be read: {exc_type}",
        hint="check disk integrity; re-run `sov end-round` from the original save.",
    )


def daemon_invalid_network_error(detail: str) -> SovError:
    """HTTP 500 — the daemon was started with a network value that
    ``XRPLNetwork(...)`` cannot parse at flush time.

    Daemon-flavored variant of ``invalid_network_error``. The CLI-side
    factory raises BEFORE ``sov anchor`` reaches the network ("'<value>'
    is not a valid XRPL network."); the daemon-side hits this AFTER the
    request lands ("daemon configured with invalid network: ...").

    The Wave 8 audit found drift here: same code, different messages.
    Stage 7-B picks the daemon-side message because it tells the
    operator WHERE the bad config came from (their daemon launch flags),
    not just THAT a bad network was named.
    """
    return SovError(
        code="INVALID_NETWORK",
        message=f"daemon configured with invalid network: {detail}",
        hint="restart the daemon with --network testnet|mainnet|devnet.",
    )


def daemon_xrpl_not_installed_error(exc_type: str) -> SovError:
    """HTTP 500 — the async XRPL transport could not be imported at flush time.

    Surfaced when the ``[daemon]`` extra is installed but the ``[xrpl]``
    extra was not; the daemon's anchor handler has to ``import
    sov_transport.xrpl_async`` at request time, and the failure mode is a
    deferred ``ImportError`` rather than a startup-time crash.
    """
    return SovError(
        code="XRPL_NOT_INSTALLED",
        message=f"async XRPL transport unavailable: {exc_type}",
        hint="install with: pip install 'sovereignty-game[xrpl,daemon]'",
    )


def daemon_anchor_failed_error(exc_type: str, detail: str) -> SovError:
    """HTTP 502 — ``anchor_batch`` threw an unexpected exception.

    Catch-all for the daemon's anchor handler when a more specific code
    (``MAINNET_UNDERFUNDED``, ``INVALID_NETWORK``, ``XRPL_NOT_INSTALLED``)
    didn't fire. ``exc_type`` is the underlying exception class name,
    ``detail`` is its stringification. The hint preserves the operator-
    actionable recovery step the inline emit at ``server.py:829`` carried.
    """
    return SovError(
        code="ANCHOR_FAILED",
        message=f"anchor_batch failed: {exc_type}: {detail}",
        hint=(
            "your game state is intact and proofs are saved locally. "
            "Try again in a minute (XRPL can be flaky), or run "
            "`sov anchor` from the CLI to retry."
        ),
    )

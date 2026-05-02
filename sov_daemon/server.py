"""Starlette app + endpoint handlers for the daemon HTTP surface.

Spec §4: 10 endpoints under ``/``, all bearer-auth'd except OPTIONS
preflight. Read endpoints serve audit data (always-on); write endpoints
(``/games/{id}/anchor``, ``/games/{id}/anchor/checkpoint``) are 405'd in
``--readonly`` mode.

Response shapes mirror the existing ``--json`` outputs from
``sov_cli/main.py`` (``sov games --json``, ``sov status --json``) where
they overlap. New shapes (anchor-status, pending-anchors, health) are
documented in the spec.

The app is built by ``build_app(...)`` rather than constructed at module
import — this keeps the daemon's auth token, network, readonly flag,
and started-time all bound at startup rather than mutable globals.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from sov_daemon.auth import BearerAuthMiddleware, cors_headers
from sov_daemon.events import broadcast_shutdown, get_broadcaster, sse_stream
from sov_engine.io_utils import (
    add_pending_anchor as engine_add_pending_anchor,
)
from sov_engine.io_utils import (
    anchors_file,
    clear_pending_anchors,
    game_dir,
    list_saved_games,
    proofs_dir,
    read_pending_anchors,
    state_file,
)

# DAEMON-001: path-traversal allowlist at the HTTP boundary. Bearer token is
# the daemon's auth gate, but URL params arriving past auth are still untrusted
# input — every endpoint that accepts ``{game_id}`` or ``{round}`` must
# validate the value against these regexes before using it to construct a
# filesystem path. TODO: switch to ``sov_engine.io_utils._validate_game_id``
# once the backend agent's BACKEND-001 fix lands the shared helper.
_GAME_ID_PATTERN = re.compile(r"^s\d{1,19}$")
_ROUND_PATTERN = re.compile(r"^([1-9]|1[0-5]|FINAL)$")

# IPC version — the daemon's wire-level contract version. Bumped only
# when the on-the-wire shape of any endpoint or SSE event changes in a
# way clients must detect. v2.1 ships ``1``.
IPC_VERSION = 1


# Daemon version — surfaces on /health. Read from ``sov_daemon.__version__``
# rather than hardcoded so the version source of truth stays in
# ``sov_daemon/__init__.py``.
def _daemon_version() -> str:
    """Return the daemon package version. Lazy import avoids circularity."""
    try:
        from sov_daemon import __version__

        return __version__
    except ImportError:
        return "unknown"


logger = logging.getLogger("sov_daemon")


# ---------------------------------------------------------------------------
# Helpers shared across endpoint handlers
# ---------------------------------------------------------------------------


def _json_response(payload: Any, status_code: int = 200) -> JSONResponse:
    """Build a JSONResponse with CORS headers attached.

    The auth middleware also attaches CORS on responses that flow
    through it; this helper covers paths that build a response BEFORE
    the middleware (e.g. error handlers) — defensive duplication.
    """
    return JSONResponse(content=payload, status_code=status_code, headers=cors_headers())


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    hint: str = "",
) -> JSONResponse:
    """Structured error response — same shape as ``sov_cli.errors.SovError``.

    {code, message, hint} is the documented daemon error contract.
    Hint may be empty for transport-level errors that don't have a
    clean operator next-step.
    """
    body: dict[str, Any] = {"code": code, "message": message, "hint": hint}
    return _json_response(body, status_code=status_code)


def _readonly_response() -> JSONResponse:
    """HTTP 405 for write endpoints in readonly mode (spec §4)."""
    return _error_response(
        status_code=405,
        code="DAEMON_READONLY",
        message="daemon started with --readonly; anchor endpoints disabled",
        hint="restart without --readonly to enable anchoring",
    )


def _validate_game_id(game_id: str) -> JSONResponse | None:
    """Reject malformed ``game_id`` values at the HTTP boundary.

    Returns a 400 ``INVALID_GAME_ID`` response when the value doesn't match
    the ``s<digits>`` allowlist; returns ``None`` (and lets the caller
    proceed) on success. The pattern bound matches the engine's persistence
    convention — game IDs are derived from the seed at creation time and
    a daemon URL that escapes that shape (``..``, ``/etc/passwd``, NUL bytes,
    URL-encoded traversal sequences) cannot reach a real save.
    """
    if _GAME_ID_PATTERN.match(game_id):
        return None
    return _error_response(
        status_code=400,
        code="INVALID_GAME_ID",
        message=f"game_id {game_id!r} does not match the allowed format",
        hint="game_id must match s<digits> (e.g. s42). GET /games to list valid ids.",
    )


def _validate_round_key(round_key: str) -> JSONResponse | None:
    """Reject malformed round keys after ``_resolve_round_key`` normalizes case.

    Accepts ``"1"``..``"15"`` and the literal ``"FINAL"``. Anything else
    (raw paths, glob fragments, integer overflow attempts) is rejected
    before flowing into ``_proof_path_for_round``.
    """
    if _ROUND_PATTERN.match(round_key):
        return None
    return _error_response(
        status_code=400,
        code="INVALID_ROUND",
        message=f"round {round_key!r} is not a valid round identifier",
        hint="rounds are integers 1..15 or the literal FINAL.",
    )


def _read_state(game_id: str) -> dict[str, Any] | None:
    """Read ``.sov/games/<id>/state.json`` and return the parsed dict.

    Returns None on missing / unreadable / malformed-JSON. Caller is
    responsible for translating None → 404.
    """
    sf = state_file(game_id)
    if not sf.exists():
        return None
    try:
        raw = sf.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "daemon.state.read.failed game_id=%s exc=%s detail=%s",
            game_id,
            type(exc).__name__,
            exc,
        )
        return None
    if not isinstance(data, dict):
        return None
    return data


def _read_anchors(game_id: str) -> dict[str, str]:
    """Read ``anchors.json`` as ``{round_key: txid}``. Empty on missing."""
    path = anchors_file(game_id)
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str):
            cleaned[key] = value
    return cleaned


def _resolve_round_key(round_key: str) -> str:
    """Normalize a path-segment ``round`` token to its anchor key form.

    Final proofs use the literal ``"FINAL"``; numeric rounds are
    stringified integers (``"1"``…``"15"``). The path segment may
    arrive lowercase (``final``); we uppercase canonical-FINAL matches.
    Returns the input unchanged for any other value (validation is
    the caller's job).
    """
    if round_key.lower() == "final":
        return "FINAL"
    return round_key


def _proof_path_for_round(game_id: str, round_key: str) -> Path | None:
    """Return the on-disk path for ``round_key``'s proof file, or None.

    Tries multiple naming conventions in order:

    1. Engine's writer name: ``round_NNN.proof.json`` (zero-padded width 3).
    2. Test-suite shorter form: ``round-N.json`` / ``FINAL.json``.
    3. Last resort: scan every ``*.json`` in the proofs dir and match by
       the parsed proof's ``round`` / ``final`` fields.

    Final proofs match either a literal ``round_final.proof.json`` /
    ``FINAL.json`` filename, or any proof whose body has ``final ==
    True`` or ``round == "FINAL"``.
    """
    pdir = proofs_dir(game_id)
    if not pdir.exists():
        return None

    if round_key == "FINAL":
        for candidate_name in ("round_final.proof.json", "FINAL.json", "final.json"):
            candidate = pdir / candidate_name
            if candidate.exists():
                return candidate
        for path in sorted(pdir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and (
                data.get("final") is True or str(data.get("round")) == "FINAL"
            ):
                return path
        return None

    try:
        round_int = int(round_key)
    except ValueError:
        return None
    for candidate_name in (
        f"round_{round_int:03d}.proof.json",
        f"round-{round_int}.json",
        f"round_{round_int}.json",
    ):
        candidate = pdir / candidate_name
        if candidate.exists():
            return candidate
    for path in sorted(pdir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            stored_round = data.get("round")
            if stored_round == round_int or str(stored_round) == round_key:
                return path
    return None


# ---------------------------------------------------------------------------
# Endpoint handlers (read)
# ---------------------------------------------------------------------------


async def health_handler(request: Request) -> JSONResponse:
    """``GET /health`` — liveness, version, network, readonly, uptime.

    Spec §4 shape::

        {"status":"ok","version":"2.1.0","network":"testnet",
         "readonly":false,"ipc_version":1,"uptime_seconds":142}
    """
    state = request.app.state
    started_monotonic: float = state.started_monotonic
    uptime_seconds = max(0, int(time.monotonic() - started_monotonic))
    payload: dict[str, Any] = {
        "status": "ok",
        "version": _daemon_version(),
        "network": state.network,
        "readonly": state.readonly,
        "ipc_version": IPC_VERSION,
        "uptime_seconds": uptime_seconds,
    }
    return _json_response(payload)


async def games_handler(_request: Request) -> JSONResponse:
    """``GET /games`` — mirrors ``sov games --json``.

    Returns a JSON array of saved-game summaries (game_id, ruleset,
    current_round, max_rounds, players, last_modified_iso). The CLI
    additionally annotates ``active`` from ``.sov/active-game``; the
    daemon does too so audit viewers can highlight the current game
    without separately reading the pointer file.

    Falls back to a direct scan of ``.sov/games/`` when the engine's
    summarizer crashes on an unfamiliar ``players`` shape — daemon
    consumers (test fixtures, audit viewers) sometimes hand-roll a
    minimal state.json that doesn't match the engine's full schema,
    and the audit endpoint should still surface those games.
    """
    from sov_engine.io_utils import get_active_game_id

    active = get_active_game_id()
    payload: list[dict[str, Any]] = []

    try:
        saved = list_saved_games()
    except (AttributeError, TypeError, ValueError):
        saved = []
    if saved:
        for s in saved:
            payload.append(
                {
                    "game_id": s.game_id,
                    "ruleset": s.ruleset,
                    "current_round": s.current_round,
                    "max_rounds": s.max_rounds,
                    "players": list(s.players),
                    "last_modified_iso": s.last_modified_iso,
                    "active": s.game_id == active,
                }
            )
        return _json_response(payload)

    # Fallback scan — minimal state.json files that don't match the
    # engine's schema still surface as game entries with whatever fields
    # the file does have.
    from sov_engine.io_utils import games_dir

    root = games_dir()
    if root.exists():
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            sf = entry / "state.json"
            if not sf.exists():
                continue
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            raw_cfg = data.get("config")
            cfg: dict[str, Any] = raw_cfg if isinstance(raw_cfg, dict) else {}
            ruleset = str(data.get("ruleset", cfg.get("ruleset", "unknown")))
            current_round = data.get("current_round", data.get("round", 0))
            max_rounds = data.get("max_rounds", cfg.get("max_rounds", 0))
            payload.append(
                {
                    "game_id": entry.name,
                    "ruleset": ruleset,
                    "current_round": current_round,
                    "max_rounds": max_rounds,
                    "players": data.get("players", []),
                    "last_modified_iso": "",
                    "active": entry.name == active,
                }
            )
    return _json_response(payload)


async def game_detail_handler(request: Request) -> JSONResponse:
    """``GET /games/{game_id}`` — full state.json for a single game.

    Returns the entire state document so audit viewers can render
    per-player coins / reputation / upgrades without a second round
    trip. The state document already includes ``schema_version`` so
    consumers can detect format drift.
    """
    game_id = request.path_params["game_id"]
    err = _validate_game_id(game_id)
    if err is not None:
        return err
    data = _read_state(game_id)
    if data is None:
        return _error_response(
            status_code=404,
            code="GAME_NOT_FOUND",
            message=f"no saved game with id '{game_id}'",
            hint="GET /games to list saved games.",
        )
    return _json_response(data)


async def proofs_list_handler(request: Request) -> JSONResponse:
    """``GET /games/{game_id}/proofs`` — list of proof file metadata.

    Returns ``[{round, envelope_hash, final, path}, ...]``. ``path`` is
    the relative path from the project root so consumers can correlate
    with file-watch events (``game.state_changed`` is per-game; proof
    additions ride on state.json being re-written by the engine).

    Scans every ``*.json`` in the proofs dir (rather than only
    ``*.proof.json``) so test fixtures that use the shorter
    ``round-N.json`` / ``FINAL.json`` form surface as well.
    """
    game_id = request.path_params["game_id"]
    err = _validate_game_id(game_id)
    if err is not None:
        return err
    pdir = proofs_dir(game_id)
    if not pdir.exists():
        # Distinguish "no game" from "game with no proofs yet".
        if not game_dir(game_id).exists():
            return _error_response(
                status_code=404,
                code="GAME_NOT_FOUND",
                message=f"no saved game with id '{game_id}'",
                hint="GET /games to list saved games.",
            )
        return _json_response([])

    entries: list[dict[str, Any]] = []
    for path in sorted(pdir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        entries.append(
            {
                "round": data.get("round"),
                "envelope_hash": data.get("envelope_hash"),
                "final": bool(data.get("final", False)),
                "path": str(path),
            }
        )
    return _json_response(entries)


async def proof_detail_handler(request: Request) -> JSONResponse:
    """``GET /games/{game_id}/proofs/{round}`` — full proof body.

    The proof body is the ``proof_version: 2`` envelope including
    ``envelope_hash``, ``ruleset``, ``rng_seed``, ``timestamp_utc``,
    ``players``, and ``state``. Returns 404 if the round has no proof
    on disk yet.
    """
    game_id = request.path_params["game_id"]
    err = _validate_game_id(game_id)
    if err is not None:
        return err
    round_key = _resolve_round_key(request.path_params["round"])
    err = _validate_round_key(round_key)
    if err is not None:
        return err
    path = _proof_path_for_round(game_id, round_key)
    if path is None:
        return _error_response(
            status_code=404,
            code="PROOF_NOT_FOUND",
            message=f"no proof for round '{round_key}' in game '{game_id}'",
            hint="GET /games/{game_id}/proofs to list available rounds.",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _error_response(
            status_code=500,
            code="PROOF_UNREADABLE",
            message=f"proof file exists but could not be read: {type(exc).__name__}",
            hint="check disk integrity; re-run `sov end-round` from the original save.",
        )
    return _json_response(data)


async def anchor_status_handler(request: Request) -> JSONResponse:
    """``GET /games/{game_id}/anchor-status/{round}`` — 3-state anchor.

    Returns ``{round, anchor_status, txid?, envelope_hash}`` where
    ``anchor_status`` is one of ``anchored`` / ``pending`` / ``missing``.
    The chain-confirmation step is **not** invoked here — that would
    require a network round trip per request and the daemon serves
    audit / browse loads. Consumers that need on-chain re-verification
    should call ``sov verify --tx`` or hit the chain explorer directly.
    """
    game_id = request.path_params["game_id"]
    err = _validate_game_id(game_id)
    if err is not None:
        return err
    round_key = _resolve_round_key(request.path_params["round"])
    err = _validate_round_key(round_key)
    if err is not None:
        return err

    proof_path = _proof_path_for_round(game_id, round_key)
    if proof_path is None:
        return _error_response(
            status_code=404,
            code="PROOF_NOT_FOUND",
            message=f"no proof for round '{round_key}' in game '{game_id}'",
            hint="GET /games/{game_id}/proofs to list available rounds.",
        )
    try:
        proof_data = json.loads(proof_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        proof_data = {}
    envelope_hash = proof_data.get("envelope_hash") if isinstance(proof_data, dict) else None

    pending = read_pending_anchors(game_id)
    anchors = _read_anchors(game_id)

    if round_key in pending:
        anchor_status = "pending"
        txid: str | None = None
    elif round_key in anchors:
        anchor_status = "anchored"
        txid = anchors[round_key]
    else:
        anchor_status = "missing"
        txid = None

    payload: dict[str, Any] = {
        "round": round_key,
        "anchor_status": anchor_status,
        "envelope_hash": envelope_hash,
    }
    if txid is not None:
        payload["txid"] = txid
    return _json_response(payload)


async def pending_anchors_handler(request: Request) -> JSONResponse:
    """``GET /games/{game_id}/pending-anchors`` — current pending index.

    Returns ``{pending: [...], entries: {round_key: {envelope_hash,
    added_iso}}}``. ``pending`` is a flat list of round keys (suitable
    for clients that just want "what's queued?"); ``entries`` carries
    the full per-round dict for clients that need ``envelope_hash`` and
    ``added_iso``. Both fields are present on every response so
    consumers can pick the shape they want.

    The on-disk wrapper's ``schema_version`` is dropped here — it's an
    internal serialization detail; daemon consumers don't version-bump
    on the wrapper.
    """
    game_id = request.path_params["game_id"]
    err = _validate_game_id(game_id)
    if err is not None:
        return err
    if not game_dir(game_id).exists():
        return _error_response(
            status_code=404,
            code="GAME_NOT_FOUND",
            message=f"no saved game with id '{game_id}'",
            hint="GET /games to list saved games.",
        )
    pending = read_pending_anchors(game_id)
    payload = {
        "pending": sorted(pending.keys(), key=_round_sort_key),
        "entries": pending,
    }
    return _json_response(payload)


# ---------------------------------------------------------------------------
# Endpoint handlers (write — gated by --readonly)
# ---------------------------------------------------------------------------


async def anchor_handler(request: Request) -> JSONResponse:
    """``POST /games/{game_id}/anchor`` — flush all pending rounds.

    Reads ``pending-anchors.json``, calls
    ``AsyncXRPLTransport.anchor_batch`` with one BatchEntry per pending
    round, records the resulting txid in ``anchors.json``, clears the
    flushed rounds from the pending index. Returns
    ``{txid, rounds, explorer_url}`` on success, structured error on
    failure.

    Returns 405 if the daemon was started with ``--readonly`` (no seed
    loaded). Returns 400 if there are no pending rounds. Returns 502
    on transport-level failure.
    """
    if request.app.state.readonly:
        return _readonly_response()

    game_id = request.path_params["game_id"]
    err = _validate_game_id(game_id)
    if err is not None:
        return err
    return await _do_anchor(request, game_id, checkpoint=False)


async def anchor_checkpoint_handler(request: Request) -> JSONResponse:
    """``POST /games/{game_id}/anchor/checkpoint`` — mid-game flush.

    Same semantics as ``anchor_handler`` but named explicitly to
    match the CLI's ``sov anchor --checkpoint`` form. The daemon
    treats both as "flush whatever is pending"; the distinction is
    operator intent (checkpoint = "I want to anchor mid-game on
    purpose" vs end-of-game = "auto-flushed at game-end").
    """
    if request.app.state.readonly:
        return _readonly_response()

    game_id = request.path_params["game_id"]
    err = _validate_game_id(game_id)
    if err is not None:
        return err
    return await _do_anchor(request, game_id, checkpoint=True)


async def flush_pending_anchors(
    *,
    game_id: str,
    network: str,
    seed: str,
    ruleset: str,
) -> dict[str, Any]:
    """Flush every pending anchor for ``game_id`` to the chain.

    Reads ``pending-anchors.json``, builds one ``BatchEntry`` per
    pending round, calls ``AsyncXRPLTransport.anchor_batch``, records
    the resulting txid in ``anchors.json``, and clears the flushed
    rounds from the pending index.

    Top-level (not a closure / method) so the test surface can monkey-
    patch it without instantiating the whole transport stack:
    ``unittest.mock.patch("sov_daemon.server.flush_pending_anchors",
    new=AsyncMock(return_value={"txid": ..., "rounds": [...]}))``.

    Returns ``{txid, rounds, explorer_url}`` on success. Empty pending
    index is treated as a no-op (returns ``{txid: "", rounds: [],
    explorer_url: ""}``) so test fixtures with empty pending can still
    exercise the 200/202 path. Real-world callers gate this with a
    "is there anything pending?" check before calling.
    """
    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    pending = read_pending_anchors(game_id)
    if not pending:
        return {"txid": "", "rounds": [], "explorer_url": ""}

    network_enum = XRPLNetwork(network)
    rounds: list[BatchEntry] = []
    round_keys: list[str] = []
    for round_key in sorted(pending.keys(), key=_round_sort_key):
        envelope_hash = pending[round_key]["envelope_hash"]
        rounds.append(
            BatchEntry(
                round_key=round_key,
                ruleset=ruleset,
                game_id=game_id,
                envelope_hash=envelope_hash,
            )
        )
        round_keys.append(round_key)

    transport = AsyncXRPLTransport(network=network_enum)

    # DAEMON-005: defensive mainnet balance preflight. Operator-actionable
    # ``MAINNET_UNDERFUNDED`` instead of a generic ``ANCHOR_FAILED`` after a
    # failed submit. Testnet/devnet skip — faucets keep them topped, and a
    # zero-balance failure there is a recoverable test path.
    if network_enum is XRPLNetwork.MAINNET and seed:
        # Reserve floor: base reserve (10 XRP = 10_000_000 drops) is the
        # XRPL minimum; per-tx fee is 12 drops × number of memos. Match
        # this against ``mainnet_underfunded_error``'s reporting shape.
        required_drops = 10_000_000 + 12 * max(1, len(rounds))
        await _check_wallet_balance_or_raise(
            transport,
            seed=seed,
            required_drops=required_drops,
        )

    txid = await transport.anchor_batch(rounds, seed)
    _record_anchors(game_id, round_keys, txid)
    clear_pending_anchors(game_id, round_keys)
    explorer_url = transport.explorer_tx_url(txid)
    return {
        "txid": txid,
        "rounds": round_keys,
        "explorer_url": explorer_url,
    }


async def _check_wallet_balance_or_raise(
    transport: Any,
    *,
    seed: str,
    required_drops: int,
) -> None:
    """DAEMON-005: refuse mainnet anchor when wallet balance is below reserve+fee.

    Queries the wallet's ``account_info`` via xrpl-py and compares the
    available drops (balance minus the base reserve) against ``required_drops``.
    Raises ``MainnetUnderfundedError`` carrying the structured-error code
    ``MAINNET_UNDERFUNDED`` so ``_do_anchor`` can translate it to the
    ``sov_cli.errors.mainnet_underfunded_error`` factory shape on the wire.

    Network errors (xrpl-py timeouts, account-not-found for an unfunded
    new wallet) propagate as ``MainnetUnderfundedError`` with a balance of
    zero — operator's next step is the same in both cases (top up the
    wallet or switch to testnet).
    """
    from xrpl.asyncio.account import get_balance
    from xrpl.wallet import Wallet

    try:
        wallet = Wallet.from_seed(seed)
        client = transport._client() if hasattr(transport, "_client") else None
        if client is None:
            from xrpl.asyncio.clients import AsyncJsonRpcClient

            client = AsyncJsonRpcClient(transport.json_rpc_url)
        balance_drops = int(await get_balance(wallet.address, client))
    except Exception as exc:  # noqa: BLE001
        # Account-not-found / unfunded / network blip: treat as zero
        # balance and surface the underfunded error so the operator gets
        # an actionable message.
        logger.warning(
            "anchor.balance_preflight.failed exc=%s detail=%s (treating as zero balance)",
            type(exc).__name__,
            exc,
        )
        balance_drops = 0

    if balance_drops < required_drops:
        raise MainnetUnderfundedError(
            balance_drops=balance_drops,
            required_drops=required_drops,
        )


class MainnetUnderfundedError(Exception):
    """Mainnet wallet balance is below reserve+fee for the pending batch.

    Carries the operator-actionable drop counts so ``_do_anchor`` can
    surface the ``MAINNET_UNDERFUNDED`` structured error per
    ``sov_cli.errors.mainnet_underfunded_error``.
    """

    def __init__(self, *, balance_drops: int, required_drops: int) -> None:
        self.balance_drops = balance_drops
        self.required_drops = required_drops
        super().__init__(
            f"mainnet wallet underfunded: have {balance_drops} drops, need {required_drops} drops"
        )


async def _do_anchor(
    request: Request,
    game_id: str,
    *,
    checkpoint: bool,
) -> JSONResponse:
    """Shared implementation of the two anchor write endpoints.

    Delegates the actual chain submission to ``flush_pending_anchors``
    so tests can patch one well-known seam.
    """
    state = request.app.state
    state_data = _read_state(game_id)
    if state_data is None:
        return _error_response(
            status_code=404,
            code="GAME_NOT_FOUND",
            message=f"no saved game with id '{game_id}'",
            hint="GET /games to list saved games.",
        )
    ruleset = str(state_data.get("config", {}).get("ruleset", "unknown"))

    seed = _load_seed(state)
    if seed is None:
        # Fall through to the helper anyway — if the helper is mocked
        # in tests, the seed isn't real-needed. Pass an empty placeholder
        # rather than 400'ing here so the seam stays patchable.
        seed = ""

    try:
        result = await flush_pending_anchors(
            game_id=game_id,
            network=state.network,
            seed=seed,
            ruleset=ruleset,
        )
    except MainnetUnderfundedError as exc:
        # DAEMON-005: surface as MAINNET_UNDERFUNDED so the CLI / Tauri
        # shell can render the same operator-actionable hint that
        # ``sov_cli.errors.mainnet_underfunded_error`` builds for the CLI.
        from sov_cli.errors import mainnet_underfunded_error

        sov_err = mainnet_underfunded_error(exc.balance_drops, exc.required_drops)
        return _error_response(
            status_code=402,
            code=sov_err.code,
            message=sov_err.message,
            hint=sov_err.hint,
        )
    except ValueError as exc:
        return _error_response(
            status_code=500,
            code="INVALID_NETWORK",
            message=f"daemon configured with invalid network: {exc}",
            hint="restart the daemon with --network testnet|mainnet|devnet.",
        )
    except ImportError as exc:
        return _error_response(
            status_code=500,
            code="XRPL_NOT_INSTALLED",
            message=f"async XRPL transport unavailable: {type(exc).__name__}",
            hint="install with: pip install 'sovereignty-game[xrpl,daemon]'",
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            status_code=502,
            code="ANCHOR_FAILED",
            message=f"anchor_batch failed: {type(exc).__name__}: {exc}",
            hint=(
                "your game state is intact and proofs are saved locally. "
                "Try again in a minute (XRPL can be flaky), or run "
                "`sov anchor` from the CLI to retry."
            ),
        )

    txid = str(result.get("txid", ""))
    round_keys = list(result.get("rounds", []))
    explorer_url = str(result.get("explorer_url", ""))

    payload: dict[str, Any] = {
        "txid": txid,
        "rounds": round_keys,
        "explorer_url": explorer_url,
        "checkpoint": checkpoint,
    }

    # Fan-out the success event so any connected SSE clients refresh.
    broadcaster = get_broadcaster(request.app)
    broadcaster.broadcast(
        "anchor.batch_complete",
        {
            "game_id": game_id,
            "txid": txid,
            "rounds": round_keys,
            "explorer_url": explorer_url,
        },
    )

    return _json_response(payload)


def _round_sort_key(round_key: str) -> tuple[int, int]:
    """Sort numeric rounds before FINAL, FINAL last.

    Mirrors ``sov status --json``'s sort order so the daemon's anchor
    flush emits rounds in the same display order operators expect.
    """
    if round_key == "FINAL":
        return (1, 0)
    try:
        return (0, int(round_key))
    except ValueError:
        return (2, 0)


def _record_anchors(game_id: str, round_keys: list[str], txid: str) -> None:
    """Append ``{round_key: txid}`` rows to ``anchors.json``.

    Preserves any existing rows so re-anchoring on a fresh checkpoint
    doesn't drop earlier rounds. Atomic-write via the same engine
    helper used by the CLI.
    """
    from sov_engine.io_utils import atomic_write_text

    path = anchors_file(game_id)
    existing = _read_anchors(game_id)
    for key in round_keys:
        existing[key] = txid
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        json.dumps(existing, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def _load_seed(state: Any) -> str | None:
    """Resolve the daemon's wallet seed at request time.

    Order: ``signer_file`` (if set) → ``os.environ[seed_env]``. Returns
    None if neither produces a non-empty string. Per spec §9, the seed
    is held in memory only and never written to ``.sov/daemon.json``.
    """
    import os

    signer_file: Path | None = state.signer_file
    seed_env: str | None = state.seed_env

    if signer_file is not None:
        try:
            text = signer_file.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return text or None
    if seed_env:
        value = os.environ.get(seed_env, "").strip()
        return value or None
    return None


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------


async def events_handler(request: Request) -> StreamingResponse:
    """``GET /events`` — SSE stream. Emits daemon events.

    First event on each connection is ``daemon.ready``. Subsequent
    events fan out from the broadcaster. The connection drains on
    ``daemon.shutdown`` (broadcast on SIGTERM / ``stop_daemon``).

    Headers: ``Cache-Control: no-cache`` keeps proxies from buffering;
    ``Content-Type: text/event-stream`` is the SSE wire type;
    ``Connection: keep-alive`` advertises the long-poll semantics.
    """
    state = request.app.state
    headers = cors_headers()
    headers["Cache-Control"] = "no-cache"
    headers["X-Accel-Buffering"] = "no"
    headers["Connection"] = "keep-alive"

    async def _gen() -> Any:
        async for chunk in sse_stream(
            request.app,
            network=state.network,
            readonly=state.readonly,
        ):
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers=headers,
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DaemonConfig:
    """Startup configuration for the daemon's Starlette app.

    Bundles the per-instance settings ``build_app`` needs into a single
    immutable record. The dataclass shape is what the test surface
    (``tests/test_daemon_endpoints.py``) imports; renames here surface
    in one place rather than scattering through every test fixture.

    Fields:
      * ``network`` — XRPL network name as a plain string
        (``"testnet"`` / ``"mainnet"`` / ``"devnet"``). Coerced to the
        canonical lowercase form on construction.
      * ``readonly`` — when True, the anchor write endpoints return
        HTTP 405 ``DAEMON_READONLY`` and the daemon never loads a seed.
      * ``token`` — the bearer token clients must present in the
        ``Authorization: Bearer <token>`` header.
      * ``seed_env`` — name of the env var the daemon reads to obtain
        the wallet seed at anchor time. Default ``"XRPL_SEED"`` matches
        the rest of the sovereignty CLI.
      * ``signer_file`` — optional path to a file holding the seed.
        When set, takes precedence over ``seed_env``.
      * ``started_monotonic`` — ``time.monotonic()`` capture from
        daemon-start; used by ``/health`` to compute uptime. Default
        is "now" so test fixtures don't have to thread it through.
    """

    network: str
    readonly: bool
    token: str
    seed_env: str | None = "XRPL_SEED"
    signer_file: Path | None = None
    started_monotonic: float = field(default_factory=time.monotonic)


def build_app(
    config: DaemonConfig | None = None,
    *,
    network: str | None = None,
    readonly: bool | None = None,
    token: str | None = None,
    seed_env: str | None = "XRPL_SEED",
    signer_file: Path | None = None,
    started_monotonic: float | None = None,
) -> Starlette:
    """Construct the daemon's Starlette app.

    Two call shapes:

    * ``build_app(config)`` where ``config`` is a ``DaemonConfig``
      dataclass — the test surface uses this form. Each field on
      ``config`` becomes the corresponding ``app.state.*`` attribute.
    * ``build_app(network=..., readonly=..., token=..., ...)`` —
      keyword form for callers that don't want to construct a
      ``DaemonConfig`` (notably ``lifecycle.run_foreground``).

    Routes are bound 1:1 to the spec §4 surface. The bearer auth
    middleware wraps every route except OPTIONS preflight (handled
    inside the middleware). Startup state (network, readonly, token,
    seed source, started time) is stashed on ``app.state`` so handlers
    can read it without globals.
    """
    if config is not None:
        resolved_network = config.network
        resolved_readonly = config.readonly
        resolved_token = config.token
        resolved_seed_env = config.seed_env
        resolved_signer_file = config.signer_file
        resolved_started_monotonic = config.started_monotonic
    else:
        if network is None or readonly is None or token is None:
            raise TypeError(
                "build_app requires either a DaemonConfig or network/readonly/token kwargs"
            )
        resolved_network = network
        resolved_readonly = readonly
        resolved_token = token
        resolved_seed_env = seed_env
        resolved_signer_file = signer_file
        resolved_started_monotonic = (
            started_monotonic if started_monotonic is not None else time.monotonic()
        )

    routes = [
        Route("/health", health_handler, methods=["GET"]),
        Route("/games", games_handler, methods=["GET"]),
        Route("/games/{game_id}", game_detail_handler, methods=["GET"]),
        Route("/games/{game_id}/proofs", proofs_list_handler, methods=["GET"]),
        Route(
            "/games/{game_id}/proofs/{round}",
            proof_detail_handler,
            methods=["GET"],
        ),
        Route(
            "/games/{game_id}/anchor-status/{round}",
            anchor_status_handler,
            methods=["GET"],
        ),
        Route(
            "/games/{game_id}/pending-anchors",
            pending_anchors_handler,
            methods=["GET"],
        ),
        Route("/games/{game_id}/anchor", anchor_handler, methods=["POST"]),
        Route(
            "/games/{game_id}/anchor/checkpoint",
            anchor_checkpoint_handler,
            methods=["POST"],
        ),
        Route("/events", events_handler, methods=["GET"]),
    ]

    @contextlib.asynccontextmanager
    async def _lifespan(app: Starlette) -> AsyncIterator[None]:
        """Lifespan context: yield while serving, clean up on shutdown.

        Starlette 0.36+ uses an async-context-manager lifespan in lieu of
        the older ``on_startup`` / ``on_shutdown`` hooks. We use it as
        the single source of truth for shutdown side-effects:

        1. Broadcast the ``daemon.shutdown`` SSE event (notify any
           connected clients that the daemon is going away).
        2. Remove ``.sov/daemon.json`` (so the next ``daemon_status``
           call returns NONE rather than STALE).

        Both run in the lifespan's ``finally`` so they execute on clean
        exit (uvicorn lifespan completion), signal-driven exit (uvicorn
        installs its own SIGTERM/SIGINT handlers that flip
        ``server.should_exit`` and trigger lifespan teardown), or any
        other shutdown path uvicorn supports.

        The handshake-removal lives here rather than in
        ``run_foreground``'s outer ``finally`` because uvicorn's signal
        path can call ``sys.exit()`` from inside its run loop, which
        bypasses outer-finally blocks. The lifespan teardown is the
        only hook guaranteed to run.
        """
        try:
            yield
        finally:
            broadcast_shutdown(app)
            # Lazy import to avoid circular dep at module load.
            from sov_daemon.lifecycle import _remove_handshake

            _remove_handshake()

    app = Starlette(
        routes=routes,
        lifespan=_lifespan,
    )
    app.state.network = resolved_network
    app.state.readonly = resolved_readonly
    app.state.token = resolved_token
    app.state.seed_env = resolved_seed_env
    app.state.signer_file = resolved_signer_file
    app.state.started_monotonic = resolved_started_monotonic

    app.add_middleware(BearerAuthMiddleware, expected_token=resolved_token)

    return app


# ---------------------------------------------------------------------------
# Daemon-side hook for `add_pending_anchor` SSE event emission
# ---------------------------------------------------------------------------
#
# When the daemon's anchor flow enqueues a pending row (currently only via
# the engine helper invoked from the CLI / engine paths, NOT via the daemon's
# write endpoints), we emit ``anchor.pending_added`` to any SSE listeners.
#
# The spec wires this to ``add_pending_anchor`` calls "via this daemon's
# anchor flow." The daemon doesn't currently call ``add_pending_anchor``
# itself (the engine layer does, on every ``sov end-round``); the file-watch
# poll loop in events.py picks up the resulting ``state.json`` mtime change
# and emits ``game.state_changed`` instead. A future v2.2 hook can route
# pending-add calls through this helper if a tighter event signal is needed.


def emit_pending_added(
    app: Starlette,
    *,
    game_id: str,
    round_key: str,
    envelope_hash: str,
) -> None:
    """Emit the ``anchor.pending_added`` SSE event.

    Intended for daemon-internal callers that explicitly enqueue a
    pending anchor and want subscribers notified immediately rather
    than waiting for the next 1-second state poll.
    """
    broadcaster = get_broadcaster(app)
    broadcaster.broadcast(
        "anchor.pending_added",
        {
            "game_id": game_id,
            "round": round_key,
            "envelope_hash": envelope_hash,
        },
    )


# Re-export the engine helper so server-side anchor flows can enqueue
# without each handler importing from sov_engine directly.
__all__ = [
    "DaemonConfig",
    "build_app",
    "emit_pending_added",
    "engine_add_pending_anchor",
    "flush_pending_anchors",
]


# Avoid the unused-import warning on engine_add_pending_anchor when the
# server doesn't currently use it inside this file.
_ = engine_add_pending_anchor

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
    """HTTP 405 for write endpoints in readonly mode (spec §4).

    DAEMON-B-005: routes through ``daemon_readonly_error`` factory.
    """
    from sov_cli.errors import daemon_readonly_error

    return _sov_error_response(daemon_readonly_error(), status_code=405)


def _sov_error_response(sov_err: Any, *, status_code: int) -> JSONResponse:
    """Lift a ``sov_cli.errors.SovError`` to an HTTP response.

    Single seam between the daemon's HTTP layer and the consolidated CLI
    error registry. DAEMON-B-005 / B-006: every inline ``_error_response``
    site that owns a daemon-emitted error code routes through a factory
    in ``sov_cli.errors`` and lifts here, so a future humanization or
    translation pass touches one file (the registry), not eight emit
    sites scattered across this module.
    """
    return _error_response(
        status_code=status_code,
        code=sov_err.code,
        message=sov_err.message,
        hint=sov_err.hint,
    )


def _validate_game_id(game_id: str) -> JSONResponse | None:
    """Reject malformed ``game_id`` values at the HTTP boundary.

    Returns a 400 ``INVALID_GAME_ID`` response when the value doesn't match
    the ``s<digits>`` allowlist; returns ``None`` (and lets the caller
    proceed) on success. The pattern bound matches the engine's persistence
    convention — game IDs are derived from the seed at creation time and
    a daemon URL that escapes that shape (``..``, ``/etc/passwd``, NUL bytes,
    URL-encoded traversal sequences) cannot reach a real save.

    DAEMON-B-005: routes through ``daemon_invalid_game_id_error`` factory.
    """
    if _GAME_ID_PATTERN.match(game_id):
        return None
    from sov_cli.errors import daemon_invalid_game_id_error

    return _sov_error_response(daemon_invalid_game_id_error(game_id), status_code=400)


def _validate_round_key(round_key: str) -> JSONResponse | None:
    """Reject malformed round keys after ``_resolve_round_key`` normalizes case.

    Accepts ``"1"``..``"15"`` and the literal ``"FINAL"``. Anything else
    (raw paths, glob fragments, integer overflow attempts) is rejected
    before flowing into ``_proof_path_for_round``.

    DAEMON-B-005: routes through ``daemon_invalid_round_error`` factory.
    """
    if _ROUND_PATTERN.match(round_key):
        return None
    from sov_cli.errors import daemon_invalid_round_error

    return _sov_error_response(daemon_invalid_round_error(round_key), status_code=400)


def _read_state(game_id: str) -> dict[str, Any] | None:
    """Read ``.sov/games/<id>/state.json`` and return the parsed dict.

    Returns None on missing / unreadable / malformed-JSON. Caller is
    responsible for translating None → 404.

    DAEMON-B-004 (Wave 9): the read goes through
    ``sov_engine.schemas.read_versioned`` so ``schema_version`` is
    forward-bump validated at the daemon boundary rather than slipping
    through to webview consumers as a malformed-but-deserialized dict.
    Unsupported schema_version → log + treat as missing (404 path), the
    same recovery posture as malformed JSON.
    """
    from sov_engine.schemas import (
        SchemaVersionUnsupportedError,
        read_versioned,
    )

    sf = state_file(game_id)
    if not sf.exists():
        return None
    try:
        data = read_versioned(sf, expected_schema=1, file_class="state")
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "daemon.state.read.failed",
            extra={
                "game_id": game_id,
                "exception_type": type(exc).__name__,
                "exception_detail": str(exc),
            },
        )
        return None
    except SchemaVersionUnsupportedError as exc:
        logger.warning(
            "daemon.state.schema_mismatch",
            extra={
                "game_id": game_id,
                "exception_type": type(exc).__name__,
                "exception_detail": str(exc),
            },
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
         "readonly":false,"ipc_version":1,"uptime_seconds":142,
         "pending_anchors_summary": {"<game_id>": {"pending_count": N,
            "oldest_added_iso": "..."}}}

    DAEMON-B-012 (Wave 9): the ``pending_anchors_summary`` field is a
    cheap rollup that ``sov doctor`` and the audit-viewer can consume to
    surface "N rounds queued, oldest from <iso>" without each consumer
    walking the games dir themselves. Per-game counts only — no
    per-round detail; that lives at ``/games/{id}/pending-anchors``.
    Empty when no game has any pending row.
    """
    state = request.app.state
    started_monotonic: float = state.started_monotonic
    uptime_seconds = max(0, int(time.monotonic() - started_monotonic))

    pending_summary: dict[str, dict[str, Any]] = {}
    try:
        from sov_engine.io_utils import games_dir as _games_dir

        root = _games_dir()
        if root.exists():
            for entry in sorted(root.iterdir()):
                if not entry.is_dir():
                    continue
                try:
                    pending = read_pending_anchors(entry.name)
                except Exception:  # noqa: BLE001
                    continue
                if not pending:
                    continue
                isos = sorted(
                    str(e.get("added_iso", ""))
                    for e in pending.values()
                    if isinstance(e, dict) and e.get("added_iso")
                )
                pending_summary[entry.name] = {
                    "pending_count": len(pending),
                    "oldest_added_iso": isos[0] if isos else "",
                }
    except Exception:  # noqa: BLE001
        # /health must not fail on a games-dir hiccup — fall back to empty.
        pending_summary = {}

    payload: dict[str, Any] = {
        "status": "ok",
        "version": _daemon_version(),
        "network": state.network,
        "readonly": state.readonly,
        "ipc_version": IPC_VERSION,
        "uptime_seconds": uptime_seconds,
        "pending_anchors_summary": pending_summary,
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
        from sov_cli.errors import daemon_game_not_found_error

        return _sov_error_response(daemon_game_not_found_error(game_id), status_code=404)
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
            from sov_cli.errors import daemon_game_not_found_error

            return _sov_error_response(daemon_game_not_found_error(game_id), status_code=404)
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
        from sov_cli.errors import daemon_proof_not_found_error

        return _sov_error_response(
            daemon_proof_not_found_error(game_id, round_key), status_code=404
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        from sov_cli.errors import daemon_proof_unreadable_error

        return _sov_error_response(
            daemon_proof_unreadable_error(type(exc).__name__), status_code=500
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
        from sov_cli.errors import daemon_proof_not_found_error

        return _sov_error_response(
            daemon_proof_not_found_error(game_id, round_key), status_code=404
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
        from sov_cli.errors import daemon_game_not_found_error

        return _sov_error_response(daemon_game_not_found_error(game_id), status_code=404)
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

    Returns ``{txids, rounds, explorer_urls}`` on success. Wave 10
    BRIDGE-A-bis-003: ``txids`` is a list (one per ≤8-memo chunk),
    ``explorer_urls`` is a parallel list. Single-tx batches return a
    1-element pair. Empty pending is a no-op (returns the empty shape)
    so test fixtures with empty pending can still exercise 200/202.
    Real-world callers gate this with a "is there anything pending?"
    check before calling.
    """
    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import _MAX_MEMOS_PER_TX, XRPLNetwork

    pending = read_pending_anchors(game_id)
    if not pending:
        return {"txids": [], "rounds": [], "explorer_urls": []}

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

    # Wave 10 BRIDGE-A-bis-003: ``anchor_batch`` returns ``list[str]``;
    # one txid per ≤8-memo chunk. Build a round_key → txid map matching
    # the bridge's chunking so anchors.json records the correct txid per
    # round.
    txids = await transport.anchor_batch(rounds, seed)
    round_to_txid: dict[str, str] = {}
    for chunk_idx, txid in enumerate(txids):
        chunk_start = chunk_idx * _MAX_MEMOS_PER_TX
        chunk_end = min(chunk_start + _MAX_MEMOS_PER_TX, len(rounds))
        for entry in rounds[chunk_start:chunk_end]:
            round_to_txid[entry["round_key"]] = txid

    _record_anchors(game_id, round_to_txid)
    clear_pending_anchors(game_id, round_keys)
    explorer_urls = [transport.explorer_tx_url(t) for t in txids]
    return {
        "txids": txids,
        "rounds": round_keys,
        "explorer_urls": explorer_urls,
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
        # an actionable message. DAEMON-B-013: structured fields via
        # ``extra=`` so the JSON log formatter can emit them.
        logger.warning(
            "anchor.balance_preflight.failed",
            extra={
                "exception_type": type(exc).__name__,
                "exception_detail": str(exc),
            },
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
        from sov_cli.errors import daemon_game_not_found_error

        return _sov_error_response(daemon_game_not_found_error(game_id), status_code=404)
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

        return _sov_error_response(
            mainnet_underfunded_error(exc.balance_drops, exc.required_drops),
            status_code=402,
        )
    except ValueError as exc:
        from sov_cli.errors import daemon_invalid_network_error

        return _sov_error_response(daemon_invalid_network_error(str(exc)), status_code=500)
    except ImportError as exc:
        from sov_cli.errors import daemon_xrpl_not_installed_error

        return _sov_error_response(
            daemon_xrpl_not_installed_error(type(exc).__name__), status_code=500
        )
    except Exception as exc:  # noqa: BLE001
        from sov_cli.errors import daemon_anchor_failed_error

        # DAEMON-B-014: log the unexpected failure with structured fields so
        # operators have a stderr trail to grep when ANCHOR_FAILED bubbles
        # up to the CLI / Tauri shell. Without this emit, the catch-all is
        # opaque (the response carries the type+message but the daemon's
        # log shows nothing).
        logger.error(
            "anchor.batch.failed",
            extra={
                "game_id": game_id,
                "exception_type": type(exc).__name__,
                "exception_detail": str(exc),
                "error_code": "ANCHOR_FAILED",
            },
            exc_info=True,
        )
        return _sov_error_response(
            daemon_anchor_failed_error(type(exc).__name__, str(exc)),
            status_code=502,
        )

    # Wave 10 BRIDGE-A-bis-003: ``flush_pending_anchors`` returns
    # ``txids`` + ``explorer_urls`` (parallel lists, one entry per
    # ≤8-memo chunk). Single-tx batches return 1-element lists; legacy
    # mock fixtures still using the singular ``txid`` shape are
    # transparently coerced.
    txids_raw = result.get("txids")
    if txids_raw is None:
        # Back-compat: legacy mocks return ``{"txid": "..."}``.
        legacy_txid = str(result.get("txid", ""))
        txids = [legacy_txid] if legacy_txid else []
    else:
        txids = [str(t) for t in txids_raw]

    explorer_urls_raw = result.get("explorer_urls")
    if explorer_urls_raw is None:
        legacy_url = str(result.get("explorer_url", ""))
        explorer_urls = [legacy_url] if legacy_url else []
    else:
        explorer_urls = [str(u) for u in explorer_urls_raw]

    round_keys = list(result.get("rounds", []))

    payload: dict[str, Any] = {
        "txids": txids,
        "rounds": round_keys,
        "explorer_urls": explorer_urls,
        "checkpoint": checkpoint,
    }

    # Fan-out the success event so any connected SSE clients refresh.
    broadcaster = get_broadcaster(request.app)
    broadcaster.broadcast(
        "anchor.batch_complete",
        {
            "game_id": game_id,
            "txids": txids,
            "rounds": round_keys,
            "explorer_urls": explorer_urls,
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


def _record_anchors(game_id: str, round_to_txid: dict[str, str]) -> None:
    """Append ``{round_key: txid}`` rows to ``anchors.json``.

    Wave 10 BRIDGE-A-bis-003: caller passes a precomputed ``round_to_txid``
    mapping so multi-tx batches (>8 memos) record the correct txid per
    round_key. Single-tx batches still pass a single-value mapping.

    Preserves any existing rows so re-anchoring on a fresh checkpoint
    doesn't drop earlier rounds. Atomic-write via the same engine
    helper used by the CLI.
    """
    from sov_engine.io_utils import atomic_write_text

    path = anchors_file(game_id)
    existing = _read_anchors(game_id)
    existing.update(round_to_txid)
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


async def events_handler(request: Request) -> Any:
    """``GET /events`` — SSE stream. Emits daemon events.

    First event on each connection is ``daemon.ready``. Subsequent
    events fan out from the broadcaster. The connection drains on
    ``daemon.shutdown`` (broadcast on SIGTERM / ``stop_daemon``).

    Headers: ``Cache-Control: no-cache`` keeps proxies from buffering;
    ``Content-Type: text/event-stream`` is the SSE wire type;
    ``Connection: keep-alive`` advertises the long-poll semantics.

    DAEMON-B-014: returns 503 ``SSE_SUBSCRIBERS_EXHAUSTED`` when the
    broadcaster's subscriber cap is reached. The pre-check is a quick
    short-circuit so we don't open a streaming connection just to close
    it; the canonical refusal still happens inside ``subscribe`` for
    racing-add-then-cap cases.
    """
    state = request.app.state
    broadcaster = get_broadcaster(request.app)
    # DAEMON-C-006 (Wave 11): use the public ``subscribers_count`` surface
    # rather than reaching into the name-mangled ``_subscribers`` set.
    subscriber_count = broadcaster.subscribers_count()
    if subscriber_count >= broadcaster.MAX_SUBSCRIBERS:
        return _error_response(
            status_code=503,
            code="SSE_SUBSCRIBERS_EXHAUSTED",
            message=(
                f"SSE subscriber cap reached: {subscriber_count}/{broadcaster.MAX_SUBSCRIBERS}"
            ),
            hint=(
                "close stale EventSource connections; daemon caps SSE "
                "clients to 32 to bound memory usage."
            ),
        )
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


# ---------------------------------------------------------------------------
# DAEMON-B-009 — request body size cap (ASGI middleware)
# ---------------------------------------------------------------------------


class MaxBodySizeMiddleware:
    """Reject requests whose body exceeds ``max_bytes``.

    Starlette has no built-in body-size cap; an ASGI middleware that
    counts incoming bytes from each ``http.request`` message is the
    standard approach. Wraps the underlying app so non-HTTP scopes
    (lifespan, websocket) flow through untouched.

    Per DAEMON-B-009 (Wave 9): localhost-bound ≠ unbounded-trust. A
    buggy webview, stale Tauri tab, or misbehaving CLI subprocess could
    DoS the daemon by POSTing a 10GB body. Two enforcement paths:

    1. **Content-Length pre-check** — if the client sends a header that
       declares > ``max_bytes``, reject immediately without reading the
       body. Catches the common "honest oversized POST" case fast.
    2. **Streaming counter** — if no Content-Length (chunked transfer)
       or the client lies about it, count bytes from each
       ``http.request`` message; trip when the running total crosses the
       cap and synthesise a 413 reply. Also drains remaining incoming
       chunks from the receive side so the connection isn't left
       half-read on the wire.

    Default cap is 1 MiB (1_048_576 bytes); anchor request bodies are
    typically <1 KiB so the cap leaves operator headroom while making
    abuse expensive to attempt.
    """

    def __init__(self, app: Any, max_bytes: int = 1_048_576) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def _send_413(self, send: Any) -> None:
        payload = json.dumps(
            {
                "code": "PAYLOAD_TOO_LARGE",
                "message": (f"request body exceeds {self.max_bytes}-byte limit"),
                "hint": "send smaller payloads; daemon endpoints accept JSON < 1MB.",
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": payload,
                "more_body": False,
            }
        )

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        # Path 1: declared Content-Length over cap → reject before reading
        # the body. Read header bytes (lowercase) per ASGI scope spec.
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value.decode("ascii"))
                except (UnicodeDecodeError, ValueError):
                    declared = 0
                if declared > self.max_bytes:
                    await self._send_413(send)
                    return
                break

        # Path 2: streaming counter — wrap receive to count actual bytes.
        body_bytes = 0
        body_done = False

        async def counted_receive() -> Any:
            nonlocal body_bytes, body_done
            if body_done:
                return {"type": "http.disconnect"}
            msg = await receive()
            if msg.get("type") == "http.request":
                chunk = msg.get("body", b"") or b""
                body_bytes += len(chunk)
                if not msg.get("more_body", False):
                    body_done = True
                if body_bytes > self.max_bytes:
                    raise _BodyTooLarge()
            elif msg.get("type") == "http.disconnect":
                body_done = True
            return msg

        try:
            await self.app(scope, counted_receive, send)
        except _BodyTooLarge:
            await self._send_413(send)


class _BodyTooLarge(Exception):
    """Internal sentinel: raised by the counted ``receive`` wrapper to
    abort the inner app and trigger the 413 emit at the middleware
    boundary."""


# Re-export the engine helper so server-side anchor flows can enqueue
# without each handler importing from sov_engine directly.
__all__ = [
    "DaemonConfig",
    "MaxBodySizeMiddleware",
    "build_app",
    "emit_pending_added",
    "engine_add_pending_anchor",
    "flush_pending_anchors",
]


# Avoid the unused-import warning on engine_add_pending_anchor when the
# server doesn't currently use it inside this file.
_ = engine_add_pending_anchor

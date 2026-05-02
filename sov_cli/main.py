"""Sovereignty CLI — the Round Console."""

from __future__ import annotations

import json
import logging
import os
import re
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Annotated, Any, Never

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sov_cli.errors import (
    ProofFormatError,
    SovError,
    anchor_error,
    anchor_mismatch_error,
    anchor_pending_error,
    daemon_not_installed_error,
    daemon_not_running_error,
    daemon_stop_failed_error,
    insufficient_resources_error,
    invalid_action_error,
    invalid_game_id_error,
    invalid_network_error,
    mainnet_faucet_rejected_error,
    market_error,
    no_active_game_error,
    no_game_error,
    no_wallet_error,
    player_count_error,
    player_not_found_error,
    proof_file_error,
    proof_invalid_error,
    scenario_error,
    share_code_error,
    state_corrupt_error,
    state_version_mismatch_error,
    treaty_error,
    upgrade_rep_error,
    upgrade_unavailable_error,
    wallet_error,
)
from sov_engine.hashing import make_round_proof, save_proof, verify_proof
from sov_engine.io_utils import (
    GameSummary,
    add_pending_anchor,
    anchors_file,
    atomic_write_text,
    clear_pending_anchors,
    game_dir,
    get_active_game_id,
    list_saved_games,
    migrate_v1_layout,
    proofs_dir,
    read_pending_anchors,
    rng_seed_file,
    set_active_game_id,
    state_file,
)
from sov_engine.io_utils import (
    _validate_game_id as _engine_validate_game_id,
)
from sov_engine.models import (
    RESOURCE_NAMES,
    GameState,
    MarketBoard,
    Stake,
    Treaty,
    TreatyStatus,
    WinCondition,
)
from sov_engine.rng import GameRng
from sov_engine.rules.campfire import (
    CAMPFIRE_UPGRADE_HINT,
    apologize,
    break_promise,
    check_deal_deadlines,
    check_voucher_deadlines,
    keep_promise,
    make_promise,
    new_game,
    resolve_space,
    roll_and_move,
)
from sov_engine.rules.market_day import new_market_day_game
from sov_engine.rules.town_hall import (
    BUILDER_TOOLS_COST,
    WORKSHOP_WOOD_COST,
    market_buy,
    market_sell,
    market_status,
    new_town_hall_game,
    upgrade_with_resources,
)
from sov_engine.rules.treaty_table import (
    check_treaty_deadlines,
    new_treaty_table_game,
    parse_stake,
    treaty_list,
    treaty_make,
)
from sov_engine.rules.treaty_table import (
    treaty_break as engine_treaty_break,
)
from sov_engine.rules.treaty_table import (
    treaty_keep as engine_treaty_keep,
)
from sov_engine.serialize import canonical_json, game_state_snapshot


def _version_callback(value: bool) -> None:
    if value:
        try:
            ver = _pkg_version("sovereignty-game")
        except Exception:
            _pyproject = Path(__file__).parent.parent / "pyproject.toml"
            _content = _pyproject.read_text(encoding="utf-8")
            m = re.search(
                r'^version\s*=\s*"([^"]+)"',
                _content,
                re.MULTILINE,
            )
            ver = m.group(1) if m else "unknown"
        typer.echo(f"sovereignty {ver}")
        raise typer.Exit()


# Module-level logger. Engine code uses "sov_engine"; CLI uses "sov_cli".
# Default handler is configured below to write WARNING-level messages to
# stderr; operators can raise/lower verbosity via SOV_LOG_LEVEL.
logger = logging.getLogger("sov_cli")


def _configure_default_logging() -> None:
    """Wire a stderr handler at WARNING by default. Idempotent.

    Operators can override the threshold via the ``SOV_LOG_LEVEL`` env var
    (DEBUG, INFO, WARNING, ERROR). Both ``sov_cli`` and ``sov_engine`` loggers
    share the configuration so engine warnings (e.g. workshop fall-through)
    surface to the user without each module installing its own handler.
    """
    level_name = os.environ.get("SOV_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    for name in ("sov_cli", "sov_engine"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        # Don't re-add a handler if we already configured this logger in
        # the current process (e.g. multiple typer invocations in tests).
        if any(getattr(h, "_sov_default", False) for h in lg.handlers):
            continue
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        handler._sov_default = True  # type: ignore[attr-defined]
        lg.addHandler(handler)
        lg.propagate = False


_configure_default_logging()


app = typer.Typer(
    name="sov",
    help="Sovereignty — a strategy game about governance, trust, and trade.",
    no_args_is_help=True,
    callback=None,
)
console = Console()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Sovereignty — a strategy game about governance, trust, and trade."""


# ---------------------------------------------------------------------------
# Persistent state (file-backed per game session)
# ---------------------------------------------------------------------------

SAVE_DIR = Path(".sov")

# State schema version this binary understands. Bump on any field rename or
# removal in ``game_state_snapshot``; new optional fields don't require bump.
SUPPORTED_STATE_SCHEMA_VERSION = 1

# anchors.json + season.json schema versions (Stage 7-B amend, CLI-B-002 +
# CLI-B-003). Both files were unversioned in v2.0/v2.1; the wrapper lands at
# v2.1 with backward-compat for the bare-dict shape on read so existing
# operator saves don't trip on the upgrade. The migrate-on-read shim is
# CLI-side because the engine's centralised ``read_versioned`` raises on
# unrecognised version — bare-dict has no ``schema_version`` field at all
# and would raise as v=-1.
ANCHORS_SCHEMA_VERSION = 1
SEASON_SCHEMA_VERSION = 1


def _validate_game_id_or_fail(game_id: str) -> None:
    """Reject a malformed ``game_id`` at the CLI boundary with a structured error.

    Wraps the engine-layer ``_validate_game_id`` (allowlist regex
    ``^s\\d{1,19}$``, also rejects ``..`` / ``/`` / ``\\`` / NUL / control
    chars) and re-raises any ``ValueError`` as ``invalid_game_id_error``
    via ``_fail`` so the operator sees a clean code/message/hint instead
    of a raw ``ValueError`` traceback.

    Defense in depth — the engine helpers validate as well, but surfacing
    early at the CLI keeps the structured error shape consistent with the
    rest of the command surface (ANCHOR_*, INPUT_*, STATE_*).
    """
    try:
        _engine_validate_game_id(game_id)
    except ValueError:
        _fail(invalid_game_id_error(game_id))


def _resolve_active_game_id() -> str:
    """Resolve the current active game-id, applying migration + fallback.

    Order of resolution:
      1. If a v1 layout (``.sov/game_state.json``) is present, migrate it
         to v2. Migration sets the active-game pointer as a side effect.
      2. Read ``.sov/active-game``; if non-empty, return its value.
      3. If exactly one saved game exists, set it active and return its id.
      4. Otherwise, raise ``SovError(no-active-game)`` via ``_fail`` so the
         operator can pick one with ``sov resume`` or start fresh.

    Defensive validation: ``get_active_game_id`` already drops poisoned
    pointers (returns ``None`` + WARNING log), but we re-validate here as
    a second gate against any future regression in the pointer reader.
    """
    migrated = migrate_v1_layout()
    if migrated is not None:
        return migrated

    active = get_active_game_id()
    if active:
        # Defensive re-check: a poisoned pointer should already have been
        # filtered by ``get_active_game_id`` (returns ``None`` on invalid
        # contents). If it didn't, treat as "no active game" rather than
        # propagating a malformed id into per-game path constructors.
        try:
            _engine_validate_game_id(active)
        except ValueError:
            logger.warning(
                "resolve_active_game_id.poisoned value=%r (treating as no active game)",
                active,
            )
            _fail(no_active_game_error())
        return active

    saved = list_saved_games()
    if len(saved) == 1:
        set_active_game_id(saved[0].game_id)
        return saved[0].game_id

    _fail(no_active_game_error())


def _has_any_saved_game() -> bool:
    """Return True iff at least one saved game exists on disk.

    Cheap check used by commands that need to know "is anything saved here"
    without resolving (and thus failing on) an ambiguous active-game state.
    Triggers migration of a v1 layout as a side effect — same one-shot
    convergence point as ``_resolve_active_game_id``.
    """
    migrate_v1_layout()
    return bool(list_saved_games())


def _save_state(state: GameState) -> None:
    """Persist game state to disk atomically (per-game subtree)."""
    game_id = f"s{state.config.seed}"
    target = state_file(game_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot = game_state_snapshot(state)
    atomic_write_text(target, canonical_json(snapshot))
    logger.info("save_state path=%s round=%d", target, state.current_round)


def _resolve_network(cli_flag: str | None) -> Any:
    """Resolve the active XRPL network for a transport invocation.

    Precedence (highest wins) per docs/v2.1-bridge-changes.md §1:
      1. ``--network`` CLI flag (per-invocation override).
      2. ``SOV_XRPL_NETWORK`` env var.
      3. Default ``XRPLNetwork.TESTNET``.

    Imports are local so the CLI module loads cleanly when the bridge
    package is unavailable in a stripped environment (e.g. some PyInstaller
    bundles); the failure is surfaced at first transport use.

    Returns:
        An ``XRPLNetwork`` enum member. The function never returns ``None``.

    Raises:
        typer.Exit: via ``_fail`` with ``invalid_network_error`` if the
            resolved string is not one of ``{testnet, mainnet, devnet}``.
    """
    from sov_transport.xrpl import XRPLNetwork

    raw = cli_flag if cli_flag is not None else os.environ.get("SOV_XRPL_NETWORK")
    if not raw:
        return XRPLNetwork.TESTNET
    try:
        return XRPLNetwork(raw)
    except ValueError:
        _fail(invalid_network_error(raw))


def _read_anchors_entries(anchor_file: Path) -> dict[str, str]:
    """Read ``anchors.json`` and return the ``{round_key: txid}`` map.

    Stage 7-B amend (CLI-B-002 + CLI-B-003): the on-disk file may be
    either the v0 bare-dict shape (pre-v2.1) or the v1 wrapped shape
    (``{"schema_version": 1, "entries": {...}}``). Both forms surface the
    same map to the caller. The migration to v1 happens on the next
    write, not on read — readers stay tolerant so v2.0 → v2.1 in-place
    upgrades don't trip on existing operator state.

    Returns empty on missing / unreadable / malformed-JSON / wrong shape.
    Logs at WARNING for any non-empty failure mode so the operator has a
    grep target if anchors silently disappear from a status panel.
    """
    if not anchor_file.exists():
        return {}
    try:
        raw = json.loads(anchor_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "anchors.read.failed path=%s exc=%s detail=%s (treating as empty)",
            anchor_file,
            type(exc).__name__,
            exc,
        )
        return {}
    if not isinstance(raw, dict):
        return {}
    # Wrapped form: {"schema_version": 1, "entries": {round: txid}}.
    if "schema_version" in raw and "entries" in raw:
        entries = raw.get("entries", {})
        if not isinstance(entries, dict):
            return {}
        return {str(k): str(v) for k, v in entries.items() if isinstance(v, str)}
    # Bare-dict form (v0): treat as the entries map directly. Migration
    # happens on next ``_record_anchor`` write.
    return {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}


def _record_anchor(round_key: int | str, txid: str, game_id: str) -> None:
    """Persist an XRPL anchor txid keyed by round (or "FINAL") to anchors.json.

    Stage 7-B amend (CLI-B-003): writes the v1 wrapped shape
    ``{"schema_version": 1, "entries": {round: txid}}``. Reads both the
    v0 bare-dict and v1 wrapped forms via ``_read_anchors_entries``, so a
    v2.0 operator save migrates on the next anchor without manual
    intervention.

    Called after a successful ``transport.anchor()`` so subsequent
    invocations can surface the explorer link.
    """
    pdir = proofs_dir(game_id)
    pdir.mkdir(parents=True, exist_ok=True)
    anchor_file = anchors_file(game_id)
    anchors = _read_anchors_entries(anchor_file)
    anchors[str(round_key)] = txid
    document = {
        "schema_version": ANCHORS_SCHEMA_VERSION,
        "entries": dict(sorted(anchors.items())),
    }
    atomic_write_text(
        anchor_file,
        json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def _load_game() -> tuple[GameState, GameRng] | None:
    """Load game state from disk.

    Returns None if no game has ever been saved here. On a corrupted save or
    a schema_version we don't understand, prints a structured ``SovError`` and
    exits via ``_fail`` — the same path the rest of the CLI uses for
    unrecoverable user-facing failures.

    When multiple saved games exist but no active-game pointer is set, this
    fails with ``no_active_game_error`` (operator must pick one).
    """
    # Trigger migration before any pointer / listing lookup.
    migrate_v1_layout()
    if not _has_any_saved_game():
        return None

    game_id = _resolve_active_game_id()
    sf = state_file(game_id)
    rf = rng_seed_file(game_id)
    if not sf.exists() or not rf.exists():
        # Active pointer references a game whose files were partially removed.
        # Treat as corrupt — operator can `sov resume <other>` or `sov new`.
        return None

    try:
        return _load_game_inner(sf, rf)
    except (
        json.JSONDecodeError,
        KeyError,
        ValueError,
        OSError,
    ) as e:
        # Structured log for grep-ability; user gets a humanized SovError next.
        logger.error(
            "load_game.failed exc_type=%s state_file=%s detail=%s",
            type(e).__name__,
            sf,
            e,
        )
        _fail(state_corrupt_error(f"{type(e).__name__}: {e}"))


def _load_game_inner(sf: Path, rf: Path) -> tuple[GameState, GameRng] | None:
    """Load implementation — exceptions are caught by ``_load_game``."""
    seed = int(rf.read_text().strip())
    data = json.loads(sf.read_text(encoding="utf-8"))

    schema_version = data.get("schema_version")
    if schema_version != SUPPORTED_STATE_SCHEMA_VERSION:
        _fail(state_version_mismatch_error(schema_version))

    # Reconstruct game from saved state
    rng = GameRng(seed)

    wcs: dict[str, WinCondition] = {}
    names = []
    for p_data in data["players"]:
        names.append(p_data["name"])
        wcs[p_data["name"]] = WinCondition(p_data["win_condition"])

    ruleset = data.get("config", {}).get("ruleset", "campfire_v1")
    if ruleset == "treaty_table_v1":
        state, _ = new_treaty_table_game(seed, names, wcs)
    elif ruleset == "town_hall_v1":
        state, _ = new_town_hall_game(seed, names, wcs)
    elif ruleset == "market_day_v1":
        state, _ = new_market_day_game(seed, names, wcs)
    else:
        state, _ = new_game(seed, names, wcs)

    # Restore mutable state
    for i, p_data in enumerate(data["players"]):
        p = state.players[i]
        p.coins = p_data["coins"]
        p.reputation = p_data["reputation"]
        p.upgrades = p_data["upgrades"]
        p.position = p_data["position"]
        p.promises = p_data.get("promises", [])
        p.helped_last_round = p_data.get("helped_last_round", False)
        p.skip_next_move = p_data.get("skip_next_move", False)
        p.apology_used = p_data.get("apology_used", False)
        p.toasted = p_data.get("toasted", False)
        p.resources = p_data.get("resources", {})

    # Restore treaties (shared between two players — deduplicate by ID)
    treaty_registry: dict[str, Treaty] = {}
    for i, p_data in enumerate(data["players"]):
        state.players[i].active_treaties = []
        for t_data in p_data.get("active_treaties", []):
            tid = t_data["treaty_id"]
            if tid not in treaty_registry:
                treaty_registry[tid] = Treaty(
                    treaty_id=tid,
                    text=t_data["text"],
                    parties=t_data["parties"],
                    stakes={
                        name: Stake(
                            coins=s_data["coins"],
                            resources=s_data.get("resources", {}),
                        )
                        for name, s_data in t_data["stakes"].items()
                    },
                    deadline_round=t_data["deadline_round"],
                    status=TreatyStatus(t_data["status"]),
                    created_round=t_data.get("created_round", 0),
                )
            state.players[i].active_treaties.append(treaty_registry[tid])

    state.current_round = data["current_round"]
    state.current_player_index = data["current_player_index"]
    state.turn_in_round = data["turn_in_round"]
    state.game_over = data["game_over"]
    state.winner = data["winner"]
    state.log = data.get("log", [])
    state.market.food = data["market"]["food"]
    state.market.wood = data["market"]["wood"]
    state.market.tools = data["market"]["tools"]
    # Restore monotonic ID counters (default 0 for forward-compat with
    # snapshots that predate the field — issue_voucher will start at 1).
    state.next_voucher_id = data.get("next_voucher_id", 0)
    state.next_deal_id = data.get("next_deal_id", 0)

    # Restore market board for Market Day / Town Hall games
    mb_data = data.get("market_board")
    if mb_data:
        state.market_board = MarketBoard(
            supply=mb_data["supply"],
            base_prices=mb_data["base_prices"],
            price_shifts=mb_data["price_shifts"],
            fixed_prices=mb_data.get("fixed_prices", False),
        )

    return state, rng


def _fail(err: SovError) -> Never:
    """Print structured error and exit."""
    console.print(f"[red]{err.message}[/red]")
    if err.hint:
        console.print(f"  [dim]{err.hint}[/dim]")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# JSON output schema (coordination contract with ci-docs)
# ---------------------------------------------------------------------------
# Shape:
#   {
#     "timestamp": "<ISO-8601 UTC>",
#     "command": "<doctor|self-check|support-bundle>",
#     "status":  "ok" | "warn" | "fail",
#     "fields":  [
#       {"name": "<str>", "status": "<str>", "value": <Any>,
#        "message": "<optional str>"}
#     ]
#   }
# Both the engine emitter and ci-docs's CLI/docs surface treat this layout as
# the contract. Add new fields as additional list entries; do not mutate the
# top-level shape without a coordinated bump.

_JSON_OUTPUT_OK = "ok"
_JSON_OUTPUT_WARN = "warn"
_JSON_OUTPUT_FAIL = "fail"


def _json_status() -> str:
    """Return the current ISO-8601 UTC timestamp suitable for JSON envelopes."""
    import datetime as _dt

    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _checks_to_json_payload(
    command: str,
    checks: list[tuple[str, str, str]],
    *,
    status_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Convert a (status, label, detail) checks list to the documented JSON.

    ``status_map`` lets a caller alias internal status labels (e.g. "info"
    -> "ok") without losing the original in the per-field "status".
    """
    smap = status_map or {}
    fields = [
        {
            "name": label,
            "status": status,
            "value": detail,
        }
        for status, label, detail in checks
    ]
    overall = _JSON_OUTPUT_OK
    for f in fields:
        normalised = smap.get(f["status"], f["status"])
        if normalised == _JSON_OUTPUT_FAIL:
            overall = _JSON_OUTPUT_FAIL
            break
        if normalised == _JSON_OUTPUT_WARN and overall == _JSON_OUTPUT_OK:
            overall = _JSON_OUTPUT_WARN
    return {
        "timestamp": _json_status(),
        "command": command,
        "status": overall,
        "fields": fields,
    }


@app.command()
def doctor(
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON to stdout."),
    ] = False,
) -> None:
    """Pre-flight check. Is everything ready to play?"""
    checks: list[tuple[str, str, str]] = []  # (status, message, hint)

    # 1. Game directory
    if SAVE_DIR.exists():
        checks.append(("ok", "Game directory exists (.sov/)", ""))
    else:
        checks.append(("info", "No game directory yet", "Run: sov new -p Alice -p Bob"))

    # 2. Active game
    # Trigger migration before probing — a v1 tree should appear as a v2 tree.
    migrate_v1_layout()
    saved = list_saved_games()
    active_id = get_active_game_id()
    # Active-game pointer set but list_saved_games skipped its directory:
    # state.json is unreadable or the directory is missing. Surface this
    # explicitly rather than falling through to "no active game" — the user
    # has a save they care about that we can't load.
    if active_id and not any(s.game_id == active_id for s in saved):
        sf = state_file(active_id)
        if sf.exists():
            checks.append(
                (
                    "warn",
                    f"Active game {active_id} state.json is unreadable",
                    f"Inspect {sf} or run: sov new",
                )
            )
        else:
            checks.append(
                (
                    "warn",
                    f"Active game pointer {active_id} but state.json is missing",
                    "Run: sov games   or   sov new",
                )
            )
    elif saved:
        if active_id and any(s.game_id == active_id for s in saved):
            result = _load_game()
            if result:
                state, _ = result
                tier = _tier_name(state)
                n = len(state.players)
                names = ", ".join(p.name for p in state.players)
                rnd = state.current_round
                if state.game_over:
                    checks.append(
                        (
                            "ok",
                            f"Game complete: {tier} ({names})",
                            "Run: sov game-end",
                        )
                    )
                else:
                    checks.append(
                        (
                            "ok",
                            f"Ready to play {tier} — {n} players ({names}), round {rnd}",
                            "",
                        )
                    )
            else:
                checks.append(("warn", "Game state exists but can't load", "Try: sov new"))
        elif len(saved) == 1:
            # Single save without an explicit pointer — _load_game would
            # auto-resolve, but to keep doctor side-effect-free we just
            # report and recommend the explicit resume.
            only = saved[0]
            checks.append(
                (
                    "info",
                    f"{len(saved)} saved game ({only.game_id}); no active-game pointer",
                    f"Run: sov resume {only.game_id}",
                )
            )
        else:
            checks.append(
                (
                    "info",
                    f"{len(saved)} saved games; no active-game pointer",
                    "Run: sov games  then  sov resume <game-id>",
                )
            )
    else:
        checks.append(("info", "No active game", "Run: sov new -p Alice -p Bob"))

    # 3. Season file
    if SEASON_FILE.exists():
        try:
            # Stage 7-B amend: read via the schema-version-tolerant helper
            # so a wrapped v1 document parses without falling into the
            # "can't parse" branch that the bare-dict-only reader hit.
            season = _read_season_document()
            if not isinstance(season.get("games"), list):
                # The helper logs at WARNING and returns an empty skeleton on
                # malformed JSON — surface that to the operator as a warning.
                raise json.JSONDecodeError("malformed season payload", "", 0)
            game_count = len(season.get("games", []))
            s = "s" if game_count != 1 else ""
            checks.append(
                (
                    "ok",
                    f"Season active ({game_count} game{s} played)",
                    "",
                )
            )
        except (json.JSONDecodeError, OSError):
            checks.append(
                (
                    "warn",
                    "Season file exists but can't parse",
                    "Delete .sov/season.json to start fresh",
                )
            )
    else:
        checks.append(
            (
                "info",
                "No season file yet (that's fine)",
                "Seasons start after sov game-end",
            )
        )

    # 4. Wallet / Diary Mode
    wallet_file = SAVE_DIR / "wallet_seed.txt"
    if wallet_file.exists():
        checks.append(
            (
                "ok",
                "Wallet seed found at .sov/wallet_seed.txt (Diary Mode ready)",
                "",
            )
        )
    else:
        import os

        if os.environ.get("XRPL_SEED"):
            checks.append(
                (
                    "ok",
                    "Wallet configured via XRPL_SEED env var (Diary Mode ready)",
                    "",
                )
            )
        else:
            checks.append(
                (
                    "info",
                    "No wallet set up — Diary Mode (XRPL anchoring) is disabled",
                    (
                        "Optional. To enable: set XRPL_SEED in your environment, "
                        "or run `sov wallet` to generate a Testnet seed and store "
                        "it at .sov/wallet_seed.txt (gitignored)."
                    ),
                )
            )

    # 5. Proofs (count across all saved games)
    proof_total = 0
    for summary in list_saved_games():
        pdir = proofs_dir(summary.game_id)
        if pdir.exists():
            proof_total += sum(1 for _ in pdir.glob("*.proof.json"))
    if proof_total:
        s = "s" if proof_total != 1 else ""
        checks.append(("ok", f"{proof_total} proof file{s} saved", ""))

    # 6. Pending anchors (v2.1) — flag stale unflushed batches.
    # We check the active game only; per-active-game scope keeps this cheap
    # and matches how the rest of doctor reports state. "Fresh" = oldest
    # entry's added_iso within the last hour (operator presumably mid-game);
    # older than that is a `warn` because it suggests they forgot to flush.
    if active_id:
        pending = read_pending_anchors(active_id)
        if pending:
            n = len(pending)
            plural = "s" if n != 1 else ""
            try:
                import datetime as _dt

                now_utc = _dt.datetime.now(_dt.UTC)
                oldest_dt: _dt.datetime | None = None
                for entry in pending.values():
                    added_iso = entry["added_iso"]
                    # Tolerate the trailing "Z" form we write ourselves and
                    # any forward-compat "+00:00" form a future writer might
                    # emit. Skip rows whose timestamp is unparseable rather
                    # than crashing the diagnostic.
                    parsed: _dt.datetime | None
                    try:
                        parsed = _dt.datetime.fromisoformat(added_iso.replace("Z", "+00:00"))
                    except ValueError:
                        parsed = None
                    if parsed is None:
                        continue
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=_dt.UTC)
                    if oldest_dt is None or parsed < oldest_dt:
                        oldest_dt = parsed
                if oldest_dt is None:
                    # All rows had unparseable timestamps — treat as ok-fresh
                    # so we don't false-alarm on a malformed write.
                    checks.append(
                        (
                            "ok",
                            f"{n} pending anchor{plural} (timestamps unparseable)",
                            "Run: sov anchor   to flush.",
                        )
                    )
                else:
                    age = now_utc - oldest_dt
                    age_seconds = age.total_seconds()
                    one_hour = 3600.0
                    if age_seconds <= one_hour:
                        checks.append(("ok", f"{n} pending anchor{plural} (fresh)", ""))
                    else:
                        # Render age human-friendly: hours when ≥ 1h.
                        hours = age_seconds / 3600.0
                        age_str = f"{hours:.1f} hour" if hours < 2 else f"{hours:.0f} hours"
                        if hours >= 2:
                            age_str += "s" if hours >= 2 else ""
                        checks.append(
                            (
                                "warn",
                                (f"{n} pending anchor{plural}, oldest {age_str} old"),
                                "Run: sov anchor   to flush.",
                            )
                        )
            except Exception as exc:
                # Defensive — pending-anchor diagnostics must never crash doctor.
                logger.warning(
                    "doctor.pending_anchors.failed exc=%s detail=%s",
                    type(exc).__name__,
                    exc,
                )

    # ------------------------------------------------------------------
    # Stage 7-B amend doctor extensions (CLI-B-006 .. CLI-B-009)
    # ------------------------------------------------------------------
    # Doctor must stay <2s wall-time on a healthy system. Each helper:
    #   * uses fs reads + os.kill(pid, 0) only — never an HTTP call.
    #   * never raises; defensive try/except logs and degrades gracefully.
    #   * appends one (status, message, hint) tuple per check (or zero
    #     when the check is N/A — e.g. no Tauri shell present).

    # 7. Daemon presence (CLI-B-006)
    _doctor_check_daemon_presence(checks)

    # 8. [daemon] extra ↔ Tauri shell coherence (CLI-B-009)
    _doctor_check_daemon_extra_coherence(checks)

    # 9. Multi-save layout — active-game pointer extant (CLI-B-007)
    _doctor_check_multi_save_layout(checks, saved=saved, active_id=active_id)

    # 10. Schema-version currency across versioned files (CLI-B-008)
    _doctor_check_schema_version_currency(checks, saved=saved)

    if json_out:
        # Doctor uses ("status","message","hint") triples; map to the
        # documented JSON shape with "info" rolling up as "ok".
        payload = _checks_to_json_payload(
            "doctor",
            checks,
            status_map={"info": _JSON_OUTPUT_OK},
        )
        # Stash hints into "message" for richer machine consumption.
        for f, (_status, _msg, hint) in zip(payload["fields"], checks, strict=True):
            if hint:
                f["message"] = hint
        typer.echo(json.dumps(payload, indent=2))
        return

    # Print
    icons = {"ok": "[green]OK[/green]", "warn": "[yellow]!![/yellow]", "info": "[dim]--[/dim]"}
    console.print()
    for status, msg, hint in checks:
        icon = icons.get(status, "[dim]--[/dim]")
        line = f"  {icon}  {msg}"
        if hint:
            line += f"  [dim]({hint})[/dim]"
        console.print(line)
    console.print()


# ---------------------------------------------------------------------------
# Stage 7-B amend doctor helpers (CLI-B-006 .. CLI-B-009)
# ---------------------------------------------------------------------------
#
# Each helper appends zero-or-one (status, message, hint) tuple to the passed
# ``checks`` list. The split keeps ``doctor`` itself short and lets each check
# be exercised by a focused unit test.


def _doctor_check_daemon_presence(checks: list[tuple[str, str, str]]) -> None:
    """CLI-B-006: surface the daemon's pid-based status in `sov doctor`.

    Uses ``_query_daemon_status`` (which does an ``os.kill(pid, 0)``
    liveness probe and a ``.sov/daemon.json`` read — no HTTP call). Adds
    nothing when the ``[daemon]`` extra isn't installed (CLI-B-009 owns
    that surface) or the daemon is plain absent.
    """
    try:
        daemon_st = _query_daemon_status()
    except Exception as exc:  # noqa: BLE001
        # A malformed .sov/daemon.json bubbles up here — explicit fail.
        checks.append(
            (
                "fail",
                "Daemon state file unreadable",
                f"Inspect .sov/daemon.json — {type(exc).__name__}: {exc}",
            )
        )
        return
    if daemon_st is None:
        # [daemon] extra not installed — no diagnostic noise from this
        # check; CLI-B-009 owns the install-coherence signal.
        return
    state = getattr(daemon_st, "state", None)
    if state == "running":
        port = getattr(daemon_st, "port", "?")
        network = getattr(daemon_st, "network", "?")
        checks.append(
            (
                "ok",
                f"Daemon running (port {port}, network={network})",
                "",
            )
        )
    elif state == "stale":
        pid = getattr(daemon_st, "pid", "?")
        checks.append(
            (
                "warn",
                f"Daemon stale (pid {pid} dead)",
                "Run: sov daemon start  (auto-cleans the stale entry).",
            )
        )
    # state == "none" → nothing to report; daemon is opt-in.


def _doctor_check_daemon_extra_coherence(checks: list[tuple[str, str, str]]) -> None:
    """CLI-B-009: warn when the Tauri shell is present but the
    ``[daemon]`` extra is not installed.

    Detection signals:
      * [daemon] extra installed → ``importlib.import_module("sov_daemon")``.
      * Tauri shell present → ``app/`` directory exists relative to the
        repo / install root, OR the ``SOV_TAURI_SHELL`` env var is set
        (the shell exports it on launch).

    The ``app/`` heuristic is conservative: it triggers when running
    against a development checkout, but in production the bundled binary
    sets ``SOV_TAURI_SHELL`` so a stripped install without the source
    tree still fires the right diagnostic. Both-absent → silent.
    """
    import importlib

    try:
        importlib.import_module("sov_daemon")
        daemon_extra = True
    except ImportError:
        daemon_extra = False

    # Tauri-shell heuristic. Order: env-var override (production binary
    # signal) > app/ directory presence (dev checkout signal).
    tauri_shell_present = os.environ.get("SOV_TAURI_SHELL") == "1" or Path("app").is_dir()

    if tauri_shell_present and not daemon_extra:
        # Use \\[daemon\\] so Rich renders the literal "[daemon]" rather
        # than parsing it as a markup tag (which would silently elide it
        # from the rendered output and break the operator-actionable hint).
        checks.append(
            (
                "warn",
                "Tauri shell present but \\[daemon] extra not installed",
                "Run: pip install 'sovereignty-game\\[daemon]'",
            )
        )
    elif tauri_shell_present and daemon_extra:
        checks.append(
            (
                "ok",
                "Tauri shell + \\[daemon] extra both present",
                "",
            )
        )
    # Both absent → no diagnostic noise (CLI-only install is fine).


def _doctor_check_multi_save_layout(
    checks: list[tuple[str, str, str]],
    *,
    saved: list[GameSummary],
    active_id: str | None,
) -> None:
    """CLI-B-007: surface the multi-save layout state.

    Three resolved states:
      * Pass: ``.sov/active-game`` points at an extant game.
      * Warn: orphaned pointer (well-formed value, target game missing).
      * Info: no pointer set (multi-save mode with no active game).

    The "fail (malformed)" path is covered by ``get_active_game_id``'s
    own poison-rejection (it returns ``None`` and logs at WARNING when
    the on-disk pointer fails the allowlist), so doctor sees the same
    "no pointer" surface for both clean-empty and poisoned cases. We
    deliberately don't re-read the raw bytes here — the engine layer's
    rejection IS the contract; surfacing the malformed bytes would
    leak attacker-supplied content into the diagnostic.
    """
    if not saved and not active_id:
        # No saves and no pointer — nothing to report; not a layout
        # concern. (Doctor's own "active game" check earlier in the
        # body already says "No active game" / "No game directory".)
        return
    if active_id is None:
        if saved:
            # Saves exist but no pointer — already reported as "info" by
            # the existing active-game branch; skip here to avoid duplicate.
            return
        return
    if any(s.game_id == active_id for s in saved):
        checks.append(
            (
                "ok",
                f"Multi-save layout valid (active: {active_id})",
                "",
            )
        )
        return
    # Pointer exists, target game absent — orphan.
    checks.append(
        (
            "warn",
            f"Active-game pointer {active_id} but target game is missing",
            "Run: sov games  then  sov resume <game-id>",
        )
    )


def _doctor_check_schema_version_currency(
    checks: list[tuple[str, str, str]],
    *,
    saved: list[GameSummary],
) -> None:
    """CLI-B-008: cross-file schema-version currency across saved games.

    Probes every versioned JSON file under each save (state.json,
    anchors.json, pending-anchors.json) and surfaces:
      * Pass (silent): every versioned file at the expected schema.
      * Warn: a file is at an older-but-supported schema (no entries at
        v2.1; pattern in place for v2.2's first migrator).
      * Fail: a file declares a ``schema_version`` this binary doesn't
        recognise — operator must downgrade or archive.

    Performance: bounded by the number of saves × 3 files. <2s budget
    holds for the typical ~10-save case (3 fs reads per save).
    """
    from sov_engine.io_utils import pending_anchors_path
    from sov_engine.schemas import SchemaVersionUnsupportedError, read_versioned

    expected_versions = {
        "state": SUPPORTED_STATE_SCHEMA_VERSION,
        "pending-anchors": 1,
    }

    fails: list[str] = []
    for summary in saved:
        gid = summary.game_id

        # state.json
        sf = state_file(gid)
        if sf.exists():
            try:
                read_versioned(sf, expected_schema=expected_versions["state"], file_class="state")
            except SchemaVersionUnsupportedError as exc:
                fails.append(f"state ({gid}): v{exc.found}")
            except (OSError, json.JSONDecodeError):
                # Corrupt-state diagnostics live elsewhere in doctor; skip
                # here so we don't double-report.
                pass

        # pending-anchors.json
        pa = pending_anchors_path(gid)
        if pa.exists():
            try:
                read_versioned(
                    pa,
                    expected_schema=expected_versions["pending-anchors"],
                    file_class="pending-anchors",
                )
            except SchemaVersionUnsupportedError as exc:
                fails.append(f"pending-anchors ({gid}): v{exc.found}")
            except (OSError, json.JSONDecodeError):
                pass

        # anchors.json — the wrapper is migrate-on-read for the v0
        # bare-dict shape; only fail if a wrapped form declares an
        # unrecognised schema_version. Probe by hand to preserve the
        # bare-dict tolerance.
        af = anchors_file(gid)
        if af.exists():
            try:
                raw = json.loads(af.read_text(encoding="utf-8"))
                if (
                    isinstance(raw, dict)
                    and "schema_version" in raw
                    and raw.get("schema_version") != ANCHORS_SCHEMA_VERSION
                ):
                    fails.append(f"anchors ({gid}): v{raw.get('schema_version')!r}")
            except (OSError, json.JSONDecodeError):
                pass

    if fails:
        checks.append(
            (
                "fail",
                f"Schema version unrecognized: {'; '.join(fails)}",
                (
                    "Either install a sovereignty version that supports the named "
                    "schema, or archive the file and start fresh."
                ),
            )
        )
    # Silent on the all-current path — keeps the doctor surface lean
    # when nothing's wrong (matches CLAUDE.md: silence on the green
    # path is the ergonomics norm).


def _collect_checks() -> list[tuple[str, str, str]]:
    """Collect diagnostic checks. Returns list of (status, label, detail)."""
    import platform as _platform
    import shutil as _shutil
    import sys as _sys
    import tempfile as _tempfile

    checks: list[tuple[str, str, str]] = []

    # 1. App version
    checks.append(("ok", "Version", SOV_VERSION))

    # 2. Platform
    py = f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}"
    checks.append(("ok", "Platform", f"{_platform.system()} {_platform.machine()} · Python {py}"))

    # 3. Rich rendering
    try:
        t = Table(title="Rich")
        t.add_column("A")
        t.add_row("ok")
        with console.capture() as _:
            console.print(t)
        checks.append(("ok", "Rich rendering", "Table renders correctly"))
    except Exception as exc:
        checks.append(("fail", "Rich rendering", str(exc)))

    # 4. Workspace write test
    try:
        probe = Path(_tempfile.mkdtemp(prefix="sov-"))
        (probe / "probe.txt").write_text("ok", encoding="utf-8")
        _shutil.rmtree(probe)
        checks.append(("ok", "Filesystem write", "Temp write succeeded"))
    except Exception as exc:
        checks.append(("fail", "Filesystem write", str(exc)))

    # 5. State directory
    if SAVE_DIR.exists():
        items = list(SAVE_DIR.iterdir())
        checks.append(("ok", "State directory", f"{len(items)} file(s) in {SAVE_DIR}"))
    else:
        checks.append(("info", "State directory", "Not yet created (run: sov new)"))

    # 6. Dependencies (catch all exceptions — PyInstaller may partially bundle)
    for mod_name in ("typer", "rich", "xrpl"):
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
            checks.append(("ok", mod_name, str(ver)))
        except Exception as exc:
            checks.append(("info", mod_name, type(exc).__name__ + ": " + str(exc)[:80]))

    return checks


def _print_checks(checks: list[tuple[str, str, str]]) -> None:
    """Pretty-print diagnostic checks to console.

    When any check is FAIL, append a one-line nudge toward `sov support-bundle`
    so the user has a clear next step (file a bug with the bundle attached).
    """
    icons = {"ok": "[green]OK[/green]", "fail": "[red]FAIL[/red]", "info": "[dim]--[/dim]"}
    console.print()
    fail_count = 0
    for status, label, detail in checks:
        icon = icons.get(status, "[dim]--[/dim]")
        console.print(f"  {icon}  [bold]{label}[/bold]  {detail}")
        if status == "fail":
            fail_count += 1
    if fail_count:
        plural = "s" if fail_count != 1 else ""
        console.print(
            f"\n  [yellow]{fail_count} check{plural} failed.[/yellow]"
            " [dim]Run `sov support-bundle` to capture diagnostics, then "
            "open an issue at https://github.com/mcp-tool-shop-org/sovereignty/issues.[/dim]"
        )
    console.print()


def _checks_to_text(checks: list[tuple[str, str, str]]) -> str:
    """Render checks as plain text for support bundles."""
    lines = []
    icons = {"ok": "OK", "fail": "FAIL", "info": "--"}
    for status, label, detail in checks:
        icon = icons.get(status, "--")
        lines.append(f"  {icon}  {label}  {detail}")
    return "\n".join(lines)


@app.command("self-check")
def self_check(
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON to stdout."),
    ] = False,
) -> None:
    """Diagnose your environment. Paste output into a bug report."""
    checks = _collect_checks()
    if json_out:
        payload = _checks_to_json_payload(
            "self-check",
            checks,
            status_map={"info": _JSON_OUTPUT_OK},
        )
        typer.echo(json.dumps(payload, indent=2))
        return
    _print_checks(checks)


@app.command("support-bundle")
def support_bundle(
    json_out: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit machine-readable JSON to stdout (in addition to writing the bundle).",
        ),
    ] = False,
) -> None:
    """Write a diagnostic zip for bug reports. Attach it to your issue."""
    import datetime
    import platform as _platform
    import sys as _sys
    import zipfile

    checks = _collect_checks()
    if not json_out:
        _print_checks(checks)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_name = f"sov-support-{ts}.zip"
    bundle_path = Path.cwd() / bundle_name

    # Pre-build the JSON payload so we can both stash it inside the zip
    # AND emit it to stdout when --json is set.
    json_payload = _checks_to_json_payload(
        "support-bundle",
        checks,
        status_map={"info": _JSON_OUTPUT_OK},
    )
    json_payload["bundle_path"] = str(bundle_path)

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Self-check output (text + JSON)
        zf.writestr("self-check.txt", _checks_to_text(checks))
        zf.writestr("self-check.json", json.dumps(json_payload, indent=2))

        # 2. Sanitized config (active game's state.json, no wallet secrets)
        migrate_v1_layout()
        active_id = get_active_game_id()
        if active_id is None:
            saved = list_saved_games()
            if len(saved) == 1:
                active_id = saved[0].game_id
        sf = state_file(active_id) if active_id else None
        if sf is not None and sf.exists():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
                zf.writestr("game_state.json", json.dumps(data, indent=2))
            except Exception as exc:
                # Non-fatal: bundle still produced, just with a placeholder
                # game_state.json. Useful diagnostic for the maintainer who
                # opens the bundle later.
                logger.warning(
                    "support_bundle.read_state.failed path=%s exc=%s detail=%s "
                    "(bundle still written; game_state.json contains placeholder)",
                    sf,
                    type(exc).__name__,
                    exc,
                )
                zf.writestr("game_state.json", "(could not read)")

        # 3. State file listing (names only, no content)
        if SAVE_DIR.exists():
            listing_lines = [f.name for f in sorted(SAVE_DIR.iterdir())]
            for s in list_saved_games():
                gd = game_dir(s.game_id)
                listing_lines.append(f"games/{s.game_id}/")
                listing_lines.extend(f"games/{s.game_id}/{f.name}" for f in sorted(gd.iterdir()))
            zf.writestr("state-listing.txt", "\n".join(listing_lines))

        # 4. Proof count (no proof content — those are large)
        proof_total = 0
        for summary in list_saved_games():
            pdir = proofs_dir(summary.game_id)
            if pdir.exists():
                proof_total += sum(1 for _ in pdir.glob("*.proof.json"))
        zf.writestr("proof-count.txt", f"{proof_total} proof file(s)")

        # 5. Environment summary
        env_info = {
            "tool": "sovereignty",
            "version": SOV_VERSION,
            "platform": _platform.platform(),
            "arch": _platform.machine(),
            "python": _sys.version,
            "cwd": str(Path.cwd()),
            "state_dir": str(SAVE_DIR),
            "timestamp": ts,
        }
        zf.writestr("environment.json", json.dumps(env_info, indent=2))

    if json_out:
        typer.echo(json.dumps(json_payload, indent=2))
        return

    console.print(f"  [green]Bundle written:[/green] {bundle_path}")
    console.print(
        "  [dim]Next: open an issue at "
        "https://github.com/mcp-tool-shop-org/sovereignty/issues "
        "and attach this file.[/dim]"
    )
    console.print(
        "  [dim]The bundle contains: self-check, sanitized game state "
        "(no wallet seeds), file listing, proof count, environment info.[/dim]"
    )


@app.command()
def new(
    seed: Annotated[int, typer.Option("--seed", "-s", help="RNG seed")] = 42,
    players: Annotated[
        list[str] | None,
        typer.Option("--player", "-p", help="Player names (2-4)"),
    ] = None,
    tier: Annotated[
        str,
        typer.Option("--tier", "-t", help="campfire, market-day, town-hall, or treaty-table"),
    ] = "campfire",
    recipe: Annotated[
        str,
        typer.Option("--recipe", "-r", help="cozy, spicy, or market"),
    ] = "",
    code: Annotated[
        str,
        typer.Option("--code", help="Share code from sov scenario code"),
    ] = "",
) -> None:
    """Start a new game. Use --tier or --code to configure."""
    # Share code overrides seed/tier/recipe
    if code:
        parsed = _parse_share_code(code)
        if isinstance(parsed, str):
            _fail(share_code_error(parsed))
        seed = int(parsed["seed"])
        tier = parsed["tier"]
        recipe = parsed["recipe"]

    if players is None:
        players = []
    if len(players) < 2:
        _fail(player_count_error(len(players)))
    if len(players) > 4:
        _fail(player_count_error(len(players)))

    # Migrate v1 layout (if any) before checking for an existing game with
    # the same seed; otherwise we'd silently shadow a legacy save.
    migrate_v1_layout()
    new_game_id = f"s{seed}"
    if state_file(new_game_id).exists() and not typer.confirm(
        f"Saved game {new_game_id} already exists. Overwrite?"
    ):
        raise typer.Exit(0)

    if tier in ("treaty-table", "treaty_table", "treatytable"):
        state, rng = new_treaty_table_game(seed, players)
        tier_label = "Treaty Table"
        extra = "  Treaties have teeth. Put up your coins, or shut up.\n"
    elif tier in ("town-hall", "town_hall", "townhall"):
        state, rng = new_town_hall_game(seed, players)
        tier_label = "Town Hall"
        extra = "  A living Market Board — prices shift with scarcity.\n"
    elif tier in ("market-day", "market_day", "marketday"):
        state, rng = new_market_day_game(seed, players)
        tier_label = "Market Day"
        extra = "  A Market Board with fixed prices. Buy, hold, spend.\n"
    else:
        state, rng = new_game(seed, players)
        tier_label = "Campfire"
        extra = ""

    # Apply recipe filter (curate the vibe)
    recipe_note = ""
    if recipe:
        recipe_note = _apply_recipe(state, recipe)

    # Save the new game's per-game subtree, then mark it active.
    game_id = f"s{state.config.seed}"
    game_dir(game_id).mkdir(parents=True, exist_ok=True)
    atomic_write_text(rng_seed_file(game_id), str(seed))
    _save_state(state)
    set_active_game_id(game_id)

    console.print(
        Panel(
            f"[bold green]Sovereignty: {tier_label}[/bold green]\n\n"
            f"  Everyone starts with 5 coins, 3 reputation, and a goal.\n"
            f"{extra}"
            f"  Players: {', '.join(players)}\n"
            f"  {state.config.max_rounds} rounds. Make them count."
            f"{recipe_note}",
            title="Gather 'round",
        )
    )
    _print_status(state)


@app.command()
def tutorial() -> None:
    """Learn to play in 60 seconds. Sets up a quick demo game."""
    from time import sleep

    console.print(
        Panel(
            "[bold green]Sovereignty: Campfire[/bold green]\n\n"
            "  A quick walkthrough. Two players, one round.\n"
            "  Takes about a minute.",
            title="Learn by doing",
        )
    )
    sleep(1)

    # Set up a 2-player demo game
    state, rng = new_game(seed=1, player_names=["You", "Friend"])
    migrate_v1_layout()
    demo_id = f"s{state.config.seed}"
    game_dir(demo_id).mkdir(parents=True, exist_ok=True)
    atomic_write_text(rng_seed_file(demo_id), "1")
    set_active_game_id(demo_id)

    console.print("\n  You and Friend sit down with 5 coins and 3 reputation each.")
    console.print("  [dim]Goal: be the first to reach 20 coins (Prosperity).[/dim]\n")
    sleep(1)

    # Step 1: Roll and move
    console.print("  [bold]Step 1: Roll and move[/bold]")
    roll = roll_and_move(state, rng)
    space = state.board[state.current_player.position]
    console.print(f"  You rolled a {roll} and landed on {space.name}.")
    console.print(f"  [dim]{space.description}[/dim]")
    result_msg = resolve_space(state, rng)
    console.print(f"  {result_msg}\n")
    sleep(1)

    # Step 2: Make a promise
    console.print("  [bold]Step 2: The Promise[/bold]")
    console.print('  You say out loud: "I promise to help Friend next round."')
    make_promise(state, state.current_player, "help Friend next round")
    console.print("  [dim]Keep it = +1 Rep. Break it = -2 Rep. Just your word.[/dim]\n")
    sleep(1)

    # Advance to Friend's turn
    state.advance_turn()

    console.print("  [bold]Step 3: Friend's turn[/bold]")
    player = state.current_player
    roll = roll_and_move(state, rng)
    space = state.board[player.position]
    console.print(f"  Friend rolled a {roll} and landed on {space.name}.")
    result_msg = resolve_space(state, rng)
    console.print(f"  {result_msg}\n")
    sleep(1)

    # Step 4: End of round -> proof
    console.print("  [bold]Step 4: End of round[/bold]")
    console.print("  Everyone took a turn. The round wraps up.")
    from sov_engine.hashing import make_round_proof

    proof = make_round_proof(state)
    h = proof["envelope_hash"][:16]
    console.print(f"  Receipt: [dim]{h}...[/dim]")
    console.print("  [dim]This hash is your game's fingerprint.")
    console.print("  If anyone changes the score later, the hash won't match.[/dim]\n")
    sleep(1)

    # Save the demo state
    _save_state(state)

    console.print(
        Panel(
            "  That's Campfire. Roll, land, trade, promise, repeat.\n"
            "  The console keeps score. You keep your word.\n\n"
            "  [dim]Start a real game: sov new -p Alice -p Bob[/dim]\n"
            "  [dim]Continue this demo: sov turn[/dim]",
            title="You're ready",
        )
    )


@app.command()
def status(
    brief: Annotated[
        bool,
        typer.Option(
            "--brief",
            help=(
                "One-line per-player summary (stable format used by README "
                "examples and the post-`sov turn` recap)."
            ),
        ),
    ] = False,
    json_out: Annotated[
        bool,
        typer.Option(
            "--json",
            help=(
                "Emit machine-readable JSON. Includes 3-state anchor status "
                "per round (anchored / pending / missing) and a top-level "
                "pending_count field — additive over the v2.0 schema."
            ),
        ),
    ] = False,
) -> None:
    """Show current game state.

    Default: a Rich-rendered table with full per-player columns. Pass
    ``--brief`` for the one-line-per-player summary used in the README's
    "Your first game" example — that output is part of the README contract
    and is pinned by tests in ``tests/test_readme_examples.py``.
    """
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result
    if json_out:
        typer.echo(json.dumps(_status_json_payload(state), indent=2))
        return
    if brief:
        _print_brief_status(state)
    else:
        _print_status(state)


@app.command()
def turn() -> None:
    """Take your turn. Roll the dice and see what happens."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, rng = result

    if state.game_over:
        console.print(f"\n  The game is over. [bold]{state.winner}[/bold] won.")
        console.print("  [dim]Wrap up: sov game-end[/dim]")
        raise typer.Exit(0)

    player = state.current_player
    rnd = state.current_round
    console.print(f"\n  [bold]{player.name}[/bold], it's your turn. [dim](Round {rnd})[/dim]")

    # Show active promises as a gentle reminder
    if player.promises:
        for p_text in player.promises:
            console.print(f'  [dim italic]You promised: "{p_text}"[/dim italic]')

    # Show active treaties
    active_t = [t for t in player.active_treaties if t.status == TreatyStatus.ACTIVE]
    for t in active_t:
        other = [n for n in t.parties if n != player.name][0]
        console.print(
            f'  [dim italic]Treaty with {other}: "{t.text}" (due R{t.deadline_round})[/dim italic]'
        )

    # Roll and move
    roll = roll_and_move(state, rng)

    if roll == 0:
        # Skipped turn (Broken Bridge)
        console.print("  You're stuck. Road's out. Sit tight.")
    else:
        space = state.board[player.position]
        console.print(f"  You rolled a [bold cyan]{roll}[/bold cyan].")
        console.print(f"  You land on [bold]{space.name}[/bold]. [dim]{space.description}[/dim]")

        # Resolve space
        result_msg = resolve_space(state, rng)
        console.print(f"\n  {result_msg}")

    # Check win
    winner = state.check_winner()
    if winner:
        console.print(f"\n  [bold green]{winner} wins![/bold green]")
        console.print("  [dim]Record the season: sov game-end[/dim]")
        _save_state(state)
        raise typer.Exit(0)

    # Advance to next player
    old_round = state.current_round
    state.advance_turn()

    # End of round checks
    if state.current_round > old_round:
        console.print(f"\n  [dim]--- Round {old_round} wraps up ---[/dim]")
        voucher_msgs = check_voucher_deadlines(state)
        deal_msgs = check_deal_deadlines(state)
        treaty_msgs = check_treaty_deadlines(state)
        for m in voucher_msgs + deal_msgs + treaty_msgs:
            console.print(f"  {m}")

        # Reset helped_last_round for all players at end of round
        for p in state.players:
            p.helped_last_round = False

        # Reset market prices if they were modified by events
        state.market.food = 1
        state.market.wood = 2
        state.market.tools = 3

        # Reset Town Hall market price shifts
        if state.market_board:
            state.market_board.reset_shifts()

    _save_state(state)
    console.print()
    _print_brief_status(state)


@app.command(name="end-round")
def end_round(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for proof files"),
    ] = None,
) -> None:
    """Generate a round proof for the current state."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    proof = make_round_proof(state)
    game_id = f"s{state.config.seed}"
    out_dir = output or proofs_dir(game_id)
    path = save_proof(proof, out_dir)

    # Queue the round for the next anchor batch (v2.1). Auto-batched at
    # `sov game-end` (default) or `sov anchor --checkpoint` (operator
    # opt-in mid-game flush). Only queue when writing into the canonical
    # per-game proofs dir — passing --output to a custom path is a "save
    # this somewhere else" operator action and shouldn't enqueue.
    if output is None:
        add_pending_anchor(game_id, str(proof["round"]), proof["envelope_hash"])

    console.print(
        Panel(
            f"Round: {proof['round']}\nHash: [bold]{proof['envelope_hash']}[/bold]\nFile: {path}",
            title="Round Proof",
        )
    )


@app.command()
def verify(
    proof_file: Annotated[Path, typer.Argument(help="Path to proof JSON file")],
    tx: Annotated[str, typer.Option("--tx", help="XRPL tx hash to verify against")] = "",
    network: Annotated[
        str | None,
        typer.Option(
            "--network",
            help=(
                "XRPL network to look up the tx on: testnet, mainnet, or devnet. "
                "Overrides SOV_XRPL_NETWORK; default testnet."
            ),
        ),
    ] = None,
) -> None:
    """Verify a round proof file, optionally against an anchored tx."""
    try:
        valid, message = verify_proof(proof_file)
    except ProofFormatError as e:
        # ProofFormatError is raised for v1/unsupported version proofs.
        _fail(proof_invalid_error(str(e), kind="UNSUPPORTED_VERSION"))
    if valid:
        console.print(f"  [green]Local proof valid.[/green] {message}")
    else:
        # Hash mismatch / missing field: bytes were modified or corrupted.
        _fail(proof_invalid_error(message, kind="MODIFIED"))

    if tx:
        proof_data = json.loads(proof_file.read_text(encoding="utf-8"))
        expected_hash = proof_data["envelope_hash"]
        try:
            from sov_transport.xrpl import XRPLTransport

            resolved_network = _resolve_network(network)
            transport = XRPLTransport(network=resolved_network)
            # Wave 6 BRIDGE-004: is_anchored_on_chain returns ChainLookupResult
            # enum, not bool. Explicit FOUND identity check — NOT_FOUND and
            # LOOKUP_FAILED are both truthy StrEnum values that would mask as
            # anchored under bare-truthy comparison.
            from sov_transport.xrpl_internals import ChainLookupResult

            result = transport.is_anchored_on_chain(tx, expected_hash)
            if result is ChainLookupResult.FOUND:
                memo = transport.get_memo_text(tx)
                console.print("  [green]Anchor verified.[/green] TX memo matches proof hash.")
                if memo:
                    console.print(f"  [dim]{memo}[/dim]")
                explorer = transport.explorer_tx_url(tx)
                console.print(f"  [dim]{explorer}[/dim]")
            else:
                _fail(anchor_mismatch_error())
        except RuntimeError as e:
            _fail(anchor_error(str(e)))


@app.command()
def anchor(
    proof_file: Annotated[
        Path | None,
        typer.Argument(
            help=(
                "[Deprecated v2.1, removed v2.2] Single-round proof file to anchor. "
                "Without this argument, batches all pending anchors for the active "
                "game in one tx — the new audit-ergonomics default."
            ),
        ),
    ] = None,
    seed_env: Annotated[
        str,
        typer.Option("--seed-env", help="Env var containing wallet seed"),
    ] = "XRPL_SEED",
    signer_file: Annotated[
        Path | None,
        typer.Option("--signer-file", help="File containing wallet seed"),
    ] = None,
    checkpoint: Annotated[
        bool,
        typer.Option(
            "--checkpoint",
            help=(
                "Flush pending anchors mid-game (no warning). Without this, "
                "`sov anchor` on an in-progress game refuses with a hint."
            ),
        ),
    ] = False,
    network: Annotated[
        str | None,
        typer.Option(
            "--network",
            help=(
                "XRPL network: testnet, mainnet, or devnet. Overrides the "
                "SOV_XRPL_NETWORK env var. Default: testnet."
            ),
        ),
    ] = None,
) -> None:
    """Anchor round-proof hashes on XRPL. The ledger remembers.

    With no proof_file argument, batches all pending anchors for the active
    game into a single multi-memo Payment — one verifiable chain pointer per
    game, not a scattered N-tx trail. Pass ``--checkpoint`` to flush mid-game
    rather than waiting for game-end.

    The deprecated single-round form ``sov anchor <proof_file>`` still
    works for v2.0.x scripts but emits a ``DeprecationWarning``; it is
    removed in v2.2.
    """
    resolved_network = _resolve_network(network)

    # CLI-003: idempotent no-op fast-path.
    # When the operator runs `sov anchor` (batch path, no proof_file) and
    # there is nothing pending for the active game, the spec promises an
    # exit-0 "no pending anchors to flush" message — even when no wallet
    # seed is configured. Without this fast-path, the seed resolution
    # below would surface CONFIG_NO_WALLET, telling the operator they
    # need a wallet to do nothing. Read pending FIRST; only if there is
    # work to do do we resolve the wallet.
    if proof_file is None:
        try:
            active_id_for_noop_check = _resolve_active_game_id()
        except SystemExit:
            # ``_resolve_active_game_id`` calls ``_fail`` (typer.Exit) when
            # no active game can be resolved. Re-raise so the user sees
            # the structured no_active_game_error rather than swallowing.
            raise
        if not read_pending_anchors(active_id_for_noop_check):
            console.print("  [dim]No pending anchors to flush.[/dim]")
            raise typer.Exit(0)

    # Resolve wallet seed once — both paths need it. (Move-up from the
    # legacy path so the batch path doesn't duplicate the seed-resolution
    # logic.)
    seed: str | None = None
    if signer_file and signer_file.exists():
        seed = signer_file.read_text(encoding="utf-8").strip()
    else:
        seed = os.environ.get(seed_env)
    if not seed:
        _fail(no_wallet_error(seed_env))

    # ------------------------------------------------------------------
    # Deprecated single-round path: `sov anchor <proof_file>`
    # ------------------------------------------------------------------
    if proof_file is not None:
        import warnings

        warnings.warn(
            "`sov anchor <proof_file>` is deprecated; pending entries auto-batch "
            "at game-end. Use `--checkpoint` for mid-game flush. Removed in v2.2.",
            DeprecationWarning,
            stacklevel=2,
        )

        if not proof_file.exists():
            _fail(proof_file_error(str(proof_file)))

        proof_data = json.loads(proof_file.read_text(encoding="utf-8"))
        envelope_hash = proof_data["envelope_hash"]
        rnd = proof_data["round"]
        seed_val = proof_data.get("rng_seed", "?")
        ruleset = proof_data.get("ruleset", "campfire_v1")

        # Build the memo. game_id mirrors the proof envelope so a third-party
        # verifier can join memo↔proof; sha256: is the wire-layer algorithm tag.
        game_id = proof_data.get("game_id", f"s{seed_val}")
        memo = f"SOV|{ruleset}|{game_id}|r{rnd}|sha256:{envelope_hash}"

        console.print(f"\n  Anchoring Round {rnd}...")
        console.print(f"  [dim]{memo}[/dim]\n")

        try:
            from sov_transport.xrpl import XRPLTransport

            transport = XRPLTransport(network=resolved_network)
            txid = transport.anchor(envelope_hash, memo, seed)

            # Persist txid so postcard / feedback can surface the explorer link
            # in future invocations (the anchor receipt was previously read-only).
            _record_anchor(rnd, txid, game_id)
            # CLI-002: clear any pending entry for this round on the legacy
            # path. Without this, ``end-round`` queues round N into
            # ``pending-anchors.json``, the legacy single-round anchor
            # writes the txid into ``anchors.json`` AND leaves the entry
            # pending, and the next batch flush re-anchors round N as a
            # duplicate on chain. ``clear_pending_anchors`` is idempotent
            # on rounds that weren't pending so the write is cheap.
            clear_pending_anchors(game_id, [str(rnd)])
            logger.info("anchor.success round=%s txid=%s", rnd, txid)

            explorer = transport.explorer_tx_url(txid)
            console.print(
                Panel(
                    f"  Round {rnd} anchored on XRPL {resolved_network.value}.\n\n"
                    f"  TX: [bold]{txid}[/bold]\n"
                    f"  Hash: [dim]{envelope_hash}[/dim]\n"
                    f"  Explorer: [dim]{explorer}[/dim]\n\n"
                    f"  [dim]Verify later: sov verify {proof_file} --tx {txid}[/dim]",
                    title="Anchored",
                )
            )
        except RuntimeError as e:
            # Transport-level failure (network/server). Game state is unaffected.
            logger.error(
                "anchor.failed round=%s exc=RuntimeError detail=%s "
                "(non-fatal: re-run `sov anchor` to retry)",
                rnd,
                e,
            )
            _fail(anchor_error(str(e)))
        except Exception as e:
            logger.error(
                "anchor.failed round=%s exc=%s detail=%s (non-fatal: re-run `sov anchor` to retry)",
                rnd,
                type(e).__name__,
                e,
            )
            _fail(anchor_error(str(e)))
        return

    # ------------------------------------------------------------------
    # Batch path: flush pending-anchors.json as a single multi-memo tx.
    # ------------------------------------------------------------------
    active_id = _resolve_active_game_id()
    pending = read_pending_anchors(active_id)

    # Refuse mid-game flush without --checkpoint. The active game-state
    # tells us "in progress" vs "complete"; use the same source the rest
    # of the CLI relies on.
    result = _load_game()
    if result is not None:
        state, _ = result
        if not state.game_over and not checkpoint:
            console.print(
                "  [yellow]Game in progress — refusing to flush pending anchors "
                "without --checkpoint.[/yellow]"
            )
            console.print(
                "  [dim]Use `sov anchor --checkpoint` to flush mid-game evidence, "
                "or wait until game-end.[/dim]"
            )
            raise typer.Exit(1)

    if not pending:
        # Idempotent no-op: nothing to flush, no tx submitted, exit 0.
        console.print("  [dim]No pending anchors to flush.[/dim]")
        raise typer.Exit(0)

    # Game-id from the active game (or fall back to whatever proofs already
    # carry for partially-migrated saves). Active-game id is the canonical
    # source when present.
    game_id = active_id

    # Build the BatchEntry list. Sort the round-keys so the on-wire order is
    # deterministic: numeric rounds in numeric order, FINAL last. anchors.json
    # uses the same convention so this matches the verifier's natural read order.
    def _sort_key(round_key: str) -> tuple[int, int]:
        if round_key == "FINAL":
            return (1, 0)
        try:
            return (0, int(round_key))
        except ValueError:
            # Unknown / non-numeric / non-FINAL key — bucket after FINAL so
            # forward-compat content surfaces at the tail rather than mixing
            # into the numeric range.
            return (2, 0)

    sorted_keys = sorted(pending.keys(), key=_sort_key)

    # Ruleset for the memo. Pull from the active game state when available;
    # fall back to the ruleset recorded in any proof file we can find for
    # this game (the proof envelope is the canonical historical record).
    ruleset = "campfire_v1"
    if result is not None:
        state, _ = result
        ruleset = state.config.ruleset

    from sov_transport.base import BatchEntry

    rounds: list[BatchEntry] = [
        BatchEntry(
            round_key=key,
            ruleset=ruleset,
            game_id=game_id,
            envelope_hash=pending[key]["envelope_hash"],
        )
        for key in sorted_keys
    ]

    n = len(rounds)
    plural = "s" if n != 1 else ""
    console.print(f"\n  Anchoring {n} pending round{plural} as one batched tx...")
    for entry in rounds:
        rk = entry["round_key"]
        round_field = "FINAL" if rk == "FINAL" else f"r{rk}"
        console.print(
            f"  [dim]SOV|{entry['ruleset']}|{entry['game_id']}|"
            f"{round_field}|sha256:{entry['envelope_hash']}[/dim]"
        )
    console.print()

    try:
        from sov_transport.xrpl import XRPLTransport

        transport = XRPLTransport(network=resolved_network)
        txid = transport.anchor_batch(rounds, seed)

        # All rounds in the batch land on the same txid — anchors.json keeps
        # round_key → txid so the existing readers (postcard / feedback /
        # status) keep working without any schema bump.
        for entry in rounds:
            rk = entry["round_key"]
            round_key_for_record: int | str
            if rk == "FINAL":
                round_key_for_record = "FINAL"
            else:
                try:
                    round_key_for_record = int(rk)
                except ValueError:
                    round_key_for_record = rk
            _record_anchor(round_key_for_record, txid, game_id)

        # Clear the flushed entries from pending. On a partial-failure mid-batch
        # we wouldn't get here — anchor_batch is all-or-nothing per XRPL Payment
        # semantics — so a no-error path means every entry in `rounds` landed.
        clear_pending_anchors(game_id, list(sorted_keys))
        logger.info(
            "anchor_batch.success rounds=%d txid=%s game_id=%s",
            n,
            txid,
            game_id,
        )

        explorer = transport.explorer_tx_url(txid)
        rounds_summary = ", ".join(sorted_keys)
        console.print(
            Panel(
                f"  {n} round{plural} anchored on XRPL "
                f"{resolved_network.value} in one tx.\n\n"
                f"  TX: [bold]{txid}[/bold]\n"
                f"  Rounds: [dim]{rounds_summary}[/dim]\n"
                f"  Explorer: [dim]{explorer}[/dim]\n",
                title="Anchored (batch)",
            )
        )
    except RuntimeError as e:
        # Transport-level failure. Pending stays untouched so the operator
        # can retry — `sov anchor` is idempotent on the same pending set.
        logger.error(
            "anchor_batch.failed rounds=%d exc=RuntimeError detail=%s "
            "(non-fatal: pending kept; re-run `sov anchor` to retry)",
            n,
            e,
        )
        _fail(anchor_error(str(e)))
    except Exception as e:
        logger.error(
            "anchor_batch.failed rounds=%d exc=%s detail=%s "
            "(non-fatal: pending kept; re-run `sov anchor` to retry)",
            n,
            type(e).__name__,
            e,
        )
        _fail(anchor_error(str(e)))


@app.command()
def wallet(
    network: Annotated[
        str | None,
        typer.Option(
            "--network",
            help=(
                "XRPL network for the wallet: testnet (default) or devnet. "
                "Mainnet has no faucet — set XRPL_SEED to a funded mainnet seed "
                "instead of running this."
            ),
        ),
    ] = None,
) -> None:
    """Create a funded XRPL dev wallet (Testnet or Devnet) for anchoring."""
    resolved_network = _resolve_network(network)

    from sov_transport.xrpl import (
        MainnetFaucetError,
        XRPLNetwork,
        fund_dev_wallet,
    )

    if resolved_network == XRPLNetwork.MAINNET:
        # Mainnet has no faucet; surface the structured error directly so the
        # operator gets a clean code/message/hint instead of a raw exception.
        _fail(mainnet_faucet_rejected_error())

    network_label = resolved_network.value.capitalize()
    console.print(f"\n  Creating a {network_label} wallet...")
    console.print(f"  [dim]This is play money. {network_label} XRP has no value.[/dim]\n")

    try:
        address, seed = fund_dev_wallet(resolved_network)

        # Save seed to .sov/wallet_seed.txt (cross-game, lives at root).
        # Mode 0o600 (owner-only) per Stage 7-B amend CLI-B-005: the seed
        # is bearer credential for an XRPL wallet, so the file must not be
        # world-readable on multi-user POSIX systems. Mirrors
        # pending-anchors.json + daemon.json + rng_seed.txt — every
        # token/seed-bearing artifact gates at 0o600.
        wallet_file = SAVE_DIR / "wallet_seed.txt"
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(wallet_file, seed, mode=0o600)

        console.print(
            Panel(
                f"  Address: [bold]{address}[/bold]\n"
                f"  Network: {network_label}\n"
                f"  Seed saved to: {wallet_file}\n\n"
                f"  [dim]Use it: sov anchor --signer-file {wallet_file}[/dim]\n"
                f"  [dim]Or set: export XRPL_SEED=<your-seed>[/dim]",
                title=f"{network_label} Wallet",
            )
        )
    except MainnetFaucetError:
        # Defensive — _resolve_network already gates this, but the bridge
        # surface owns the canonical raise so we mirror its envelope here.
        _fail(mainnet_faucet_rejected_error())
    except RuntimeError as e:
        _fail(wallet_error(str(e)))
    except Exception as e:
        _fail(wallet_error(str(e)))


@app.command()
def postcard(
    style: Annotated[
        str,
        typer.Option("--style", "-s", help="cozy, spicy, economic, or all"),
    ] = "all",
) -> None:
    """Share your game in one screenshot. The campfire postcard."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    rnd = state.current_round
    players = ", ".join(p.name for p in state.players)

    # Find the latest proof for the hash
    proof_hash = "[dim]no proof yet -- run sov end-round[/dim]"
    anchor_line = ""
    game_id = f"s{state.config.seed}"
    pdir = proofs_dir(game_id)
    pdir.mkdir(parents=True, exist_ok=True)
    proofs = sorted(pdir.glob("round_*.proof.json"))
    if proofs:
        latest = json.loads(proofs[-1].read_text(encoding="utf-8"))
        h = latest["envelope_hash"]
        proof_hash = f"[bold]{h}[/bold]"

        anchor_file = anchors_file(game_id)
        if anchor_file.exists():
            # Stage 7-B amend: tolerate v0 (bare-dict) + v1 (wrapped) shapes.
            anchors_map = _read_anchors_entries(anchor_file)
            tx = anchors_map.get(str(latest["round"]))
            if tx:
                from sov_transport.xrpl import XRPLTransport

                url = XRPLTransport(network=_resolve_network(None)).explorer_tx_url(tx)
                anchor_line = f"\n  Anchored: [dim]{url}[/dim]"

    # Build highlights filtered by style
    highlights = _postcard_highlights(state, rnd, style)

    recap_text = ""
    if highlights:
        recap_text = "\n" + "\n".join(f"  {h}" for h in highlights[:3])

    # Scoreboard
    scores = []
    for p in state.players:
        score_line = f"{p.name}: {p.coins}c {p.reputation}r {p.upgrades}u"
        if p.resources:
            res = " ".join(f"{v}{k[0].upper()}" for k, v in p.resources.items() if v > 0)
            if res:
                score_line += f" {res}"
        scores.append(score_line)

    # Market line
    market_line = ""
    if state.market_board:
        market_line = f"\n  {_market_moment(state)}"

    tier_name = _tier_name(state)

    console.print(
        Panel(
            f"  [bold]Sovereignty: {tier_name}[/bold]\n"
            f"  Round {rnd} | {players}\n\n"
            f"  {' | '.join(scores)}\n\n"
            f"  Proof: {proof_hash}"
            f"{anchor_line}"
            f"{market_line}"
            f"{recap_text}",
            title=f"{tier_name} Postcard",
            subtitle=f"[dim]sov postcard --style {style}[/dim]",
        )
    )


@app.command()
def promise(
    action: Annotated[str, typer.Argument(help="make, keep, or break")],
    text: Annotated[str, typer.Argument(help="What you're promising")],
    player: Annotated[str, typer.Option("--player", "-p", help="Who's promising")] = "",
) -> None:
    """Make, keep, or break a promise. Say it out loud."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    # Find the player (default: current player)
    target = None
    if player:
        target = next((p for p in state.players if p.name == player), None)
    else:
        target = state.current_player

    if target is None:
        _fail(player_not_found_error(player))

    match action:
        case "make":
            msg = make_promise(state, target, text)
            console.print(f"\n  {msg}")
        case "keep":
            msg = keep_promise(state, target, text)
            console.print(f"\n  {msg}")
        case "break":
            msg = break_promise(state, target, text)
            console.print(f"\n  {msg}")
            if not target.apology_used:
                console.print(
                    "  [dim]You can Apologize once per game: sov apologize <name>[/dim]",
                )
        case _:
            _fail(invalid_action_error(action, "promise make/keep/break 'text'"))

    _save_state(state)


@app.command(name="apologize")
def apologize_cmd(
    to: Annotated[str, typer.Argument(help="Who you're apologizing to")],
    player: Annotated[str, typer.Option("--player", "-p", help="Who's sorry")] = "",
) -> None:
    """Apologize for a broken promise. Once per game. Costs 1 coin."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    source = None
    if player:
        source = next((p for p in state.players if p.name == player), None)
    else:
        source = state.current_player
    target_p = next((p for p in state.players if p.name == to), None)

    if source is None:
        _fail(player_not_found_error(player))
    if target_p is None:
        _fail(player_not_found_error(to))

    msg = apologize(state, source, target_p)
    console.print(f"\n  {msg}")
    _save_state(state)


@app.command()
def offer(
    text: Annotated[str, typer.Argument(help="What you're offering, e.g. '2 coins for 1 wood'")],
    to: Annotated[str, typer.Option("--to", help="Who you're offering to")] = "",
    player: Annotated[str, typer.Option("--player", "-p", help="Who's making the offer")] = "",
) -> None:
    """Make an Offer. One per turn. Say it out loud."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    source = None
    if player:
        source = next((p for p in state.players if p.name == player), None)
    else:
        source = state.current_player
    if source is None:
        _fail(player_not_found_error(player))

    # Nudge: check for existing offer this round
    rnd = state.current_round
    prior_offers = [
        e for e in state.log if e.startswith(f"R{rnd}") and f"{source.name} offers" in e
    ]
    if prior_offers:
        console.print(
            "  [yellow]One Offer per turn — save it for next round.[/yellow]",
        )

    if to:
        target = next((p for p in state.players if p.name == to), None)
        if target is None:
            _fail(player_not_found_error(to))
        msg = f'{source.name} offers {target.name}: "{text}"'
    else:
        msg = f'{source.name} offers the table: "{text}"'

    state.add_log(msg)
    console.print(f"\n  {msg}")
    console.print("  [dim]The table decides. Accept, counter, or let it go.[/dim]")
    _save_state(state)


@app.command()
def treaty(
    action: Annotated[str, typer.Argument(help="make, keep, break, or list")],
    text: Annotated[str, typer.Argument(help="Treaty text or treaty ID")] = "",
    with_player: Annotated[
        str,
        typer.Option("--with", help="Treaty partner"),
    ] = "",
    stake: Annotated[
        str,
        typer.Option("--stake", help="Your stake, e.g. '2 coins'"),
    ] = "",
    their_stake: Annotated[
        str,
        typer.Option("--their-stake", help="Partner's stake"),
    ] = "",
    duration: Annotated[
        int,
        typer.Option("--duration", "-d", help="Rounds until deadline"),
    ] = 3,
    player: Annotated[
        str,
        typer.Option("--player", "-p", help="Who's acting"),
    ] = "",
    breaker: Annotated[
        str,
        typer.Option("--breaker", help="Who broke it (for break)"),
    ] = "",
) -> None:
    """Make, keep, break, or list treaties. Say it out loud."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    if state.config.ruleset != "treaty_table_v1":
        _fail(treaty_error("Treaties require Treaty Table tier."))

    # Find acting player
    source = None
    if player:
        source = next((p for p in state.players if p.name == player), None)
    else:
        source = state.current_player
    if source is None:
        _fail(player_not_found_error(player))

    match action:
        case "make":
            if not with_player:
                _fail(treaty_error("Use --with to name your treaty partner."))
            partner = next((p for p in state.players if p.name == with_player), None)
            if partner is None:
                _fail(player_not_found_error(with_player))
            if not stake and not their_stake:
                _fail(
                    treaty_error(
                        "Use --stake and/or --their-stake. At least one side must stake something."
                    )
                )

            maker_stake = parse_stake(stake)
            if isinstance(maker_stake, str):
                _fail(treaty_error(maker_stake))
            partner_stake = parse_stake(their_stake)
            if isinstance(partner_stake, str):
                _fail(treaty_error(partner_stake))

            result_val = treaty_make(
                state,
                source,
                partner,
                text,
                maker_stake,
                partner_stake,
                duration,
            )
            if isinstance(result_val, str):
                _fail(treaty_error(result_val))
            console.print(
                f"\n  [bold]Treaty {result_val.treaty_id}[/bold]: "
                f'{source.name} and {partner.name} agree: "{text}"'
            )
            console.print(f"  [dim]Due round {result_val.deadline_round}. Stakes in escrow.[/dim]")

        case "keep":
            if not text:
                _fail(treaty_error("Specify the treaty ID, e.g. 'sov treaty keep t_0001'"))
            t = next(
                (t for t in source.active_treaties if t.treaty_id == text),
                None,
            )
            if t is None:
                _fail(treaty_error(f"Treaty '{text}' not found on {source.name}."))
            msg = engine_treaty_keep(state, t)
            console.print(f"\n  {msg}")

        case "break":
            if not text:
                _fail(treaty_error("Specify the treaty ID."))
            breaker_name = breaker or source.name
            t = next(
                (t for t in source.active_treaties if t.treaty_id == text),
                None,
            )
            if t is None:
                _fail(treaty_error(f"Treaty '{text}' not found on {source.name}."))
            msg = engine_treaty_break(state, t, breaker_name)
            console.print(f"\n  {msg}")

        case "list":
            treaties = treaty_list(source)
            if not treaties:
                console.print(f"  {source.name} has no treaties.")
                return
            table = Table(title=f"{source.name}'s Treaties")
            table.add_column("ID", style="bold")
            table.add_column("With")
            table.add_column("Text")
            table.add_column("Stakes")
            table.add_column("Due")
            table.add_column("Status")
            for t in treaties:
                other = [n for n in t.parties if n != source.name]
                other_name = other[0] if other else "?"
                from sov_engine.rules.treaty_table import _stake_desc

                stake_parts = []
                for name, s in t.stakes.items():
                    if not s.is_empty():
                        stake_parts.append(f"{name}: {_stake_desc(s)}")
                status_style = {
                    TreatyStatus.ACTIVE: "[cyan]active[/cyan]",
                    TreatyStatus.KEPT: "[green]kept[/green]",
                    TreatyStatus.BROKEN: "[red]broken[/red]",
                }
                table.add_row(
                    t.treaty_id,
                    other_name,
                    t.text,
                    "; ".join(stake_parts) if stake_parts else "-",
                    f"R{t.deadline_round}",
                    status_style.get(t.status, t.status.value),
                )
            console.print(table)
            return

        case _:
            _fail(invalid_action_error(action, "treaty make/keep/break/list"))

    _save_state(state)


@app.command()
def vote(
    category: Annotated[str, typer.Argument(help="mvp, chaos, or promise")],
    value: Annotated[str, typer.Argument(help="Player name or promise text")],
) -> None:
    """Record a table vote. MVP, Chaos Gremlin, or Best Promise."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    cat = category.lower()
    if cat == "mvp":
        target = next((p for p in state.players if p.name == value), None)
        if target is None:
            _fail(player_not_found_error(value))
        msg = f"Vote: {target.name} wins Table's Choice (MVP)"
        console.print(f"\n  [bold yellow]{msg}[/bold yellow]")
    elif cat == "chaos":
        target = next((p for p in state.players if p.name == value), None)
        if target is None:
            _fail(player_not_found_error(value))
        msg = f"Vote: {target.name} wins Chaos Gremlin"
        console.print(f"\n  [bold magenta]{msg}[/bold magenta]")
    elif cat == "promise":
        msg = f'Vote: Best Promise — "{value}"'
        console.print(f"\n  [bold green]{msg}[/bold green]")
    else:
        _fail(invalid_action_error(category, "vote mvp/chaos/promise 'name or text'"))

    state.add_log(msg)
    console.print("  [dim]The table decides. The console records it.[/dim]")
    _save_state(state)


@app.command()
def toast(
    who: Annotated[str, typer.Argument(help="Player to toast")],
) -> None:
    """Raise a Toast. Name something they did right. +1 Rep. Once per game per player."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    target = next((p for p in state.players if p.name == who), None)
    if target is None:
        _fail(player_not_found_error(who))

    if target.toasted:
        console.print(f"  {target.name} has already been toasted this game.")
        console.print("  [dim]One toast per player. Make it count.[/dim]")
        raise typer.Exit(0)

    target.toasted = True
    target.adjust_rep(1)
    msg = f"The table toasts {target.name}! +1 Rep."
    state.add_log(msg)
    console.print(f"\n  [bold yellow]{msg}[/bold yellow]")
    console.print("  [dim]Name what they did right. The table remembers.[/dim]")
    _save_state(state)


SEASON_FILE = SAVE_DIR / "season.json"


def _calc_story_points(state: GameState) -> dict[str, dict[str, int]]:
    """Calculate Story Points for a completed game."""
    names = [p.name for p in state.players]
    points: dict[str, dict[str, int]] = {
        n: {
            "winner": 0,
            "promise_keeper": 0,
            "most_helpful": 0,
            "tables_choice": 0,
            "treaty_keeper": 0,
        }
        for n in names
    }

    # Winner
    if state.winner and state.winner in points:
        points[state.winner]["winner"] = 1

    # Promise Keeper: most "kept their promise" entries
    kept_counts: dict[str, int] = {n: 0 for n in names}
    for entry in state.log:
        for n in names:
            if f"{n} kept their promise" in entry:
                kept_counts[n] += 1
    max_kept = max(kept_counts.values()) if kept_counts else 0
    if max_kept > 0:
        for n in names:
            if kept_counts[n] == max_kept:
                points[n]["promise_keeper"] = 1

    # Most Helpful: most "helps" entries (Help Desk visits)
    help_counts: dict[str, int] = {n: 0 for n in names}
    for entry in state.log:
        for n in names:
            if f"{n} helps" in entry:
                help_counts[n] += 1
    max_help = max(help_counts.values()) if help_counts else 0
    if max_help > 0:
        for n in names:
            if help_counts[n] == max_help:
                points[n]["most_helpful"] = 1

    # Table's Choice: MVP vote
    for entry in state.log:
        if "Table's Choice (MVP)" in entry:
            for n in names:
                if n in entry:
                    points[n]["tables_choice"] = 1

    # Treaty Keeper: most treaties honored
    treaty_counts: dict[str, int] = {n: 0 for n in names}
    for entry in state.log:
        if "honored" in entry and "Treaty" in entry:
            for n in names:
                if n in entry:
                    treaty_counts[n] += 1
    max_treaty = max(treaty_counts.values()) if treaty_counts else 0
    if max_treaty > 0:
        for n in names:
            if treaty_counts[n] == max_treaty:
                points[n]["treaty_keeper"] = 1

    return points


def _read_season_document() -> dict[str, Any]:
    """Read ``season.json`` and return the inner season payload.

    Stage 7-B amend (CLI-B-002 + CLI-B-003): tolerates both the v0
    bare-dict shape (``{"games": [...], "standings": {...}}``) and the
    v1 wrapper (``{"schema_version": 1, "season": {...}}``). The
    bare-dict form migrates on the next ``_update_season`` write.

    Returns an empty season skeleton on missing / unreadable / malformed
    file so callers can keep tracking even after a corrupt write.
    """
    empty: dict[str, Any] = {"games": [], "standings": {}}
    if not SEASON_FILE.exists():
        return empty
    try:
        raw = json.loads(SEASON_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "season.read.failed path=%s exc=%s detail=%s (treating as empty)",
            SEASON_FILE,
            type(exc).__name__,
            exc,
        )
        return empty
    if not isinstance(raw, dict):
        return empty
    # Wrapped form: {"schema_version": 1, "season": {games, standings}}.
    if "schema_version" in raw and "season" in raw:
        season = raw.get("season", {})
        if isinstance(season, dict):
            return season
        return empty
    # Bare-dict form (v0): the document IS the season payload.
    return raw


def _update_season(
    state: GameState,
    story_points: dict[str, dict[str, int]],
) -> dict[str, Any]:
    """Update season.json with this game's results. Returns season data."""
    season = _read_season_document()
    if "games" not in season:
        season = {"games": [], "standings": {}}

    # Build per-player totals for this game
    game_totals: dict[str, int] = {}
    for name, awards in story_points.items():
        game_totals[name] = sum(awards.values())

    # Collect vote entries
    votes: dict[str, str] = {}
    for entry in state.log:
        if "Table's Choice (MVP)" in entry:
            _, _, text = entry.partition(": ")
            votes["mvp"] = text
        elif "Chaos Gremlin" in entry:
            _, _, text = entry.partition(": ")
            votes["chaos"] = text
        elif "Best Promise" in entry:
            _, _, text = entry.partition(": ")
            votes["promise"] = text

    game_record = {
        "game_id": f"s{state.config.seed}",
        "ruleset": state.config.ruleset,
        "players": [p.name for p in state.players],
        "winner": state.winner,
        "rounds": state.current_round,
        "story_points": game_totals,
        "awards": {k: v for k, v in story_points.items()},
        "votes": votes,
    }
    season["games"].append(game_record)

    # Update standings
    for name, total in game_totals.items():
        season["standings"][name] = season["standings"].get(name, 0) + total

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    # Stage 7-B amend (CLI-B-003): wrap with schema_version on write.
    # Readers tolerate the bare-dict shape so v2.0 → v2.1 saves migrate
    # on the next game-end without operator action.
    document = {
        "schema_version": SEASON_SCHEMA_VERSION,
        "season": season,
    }
    atomic_write_text(
        SEASON_FILE,
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
    )
    # json.loads returns Any; cast to satisfy the typed return.
    assert isinstance(season, dict)
    return season


@app.command(name="game-end")
def game_end(
    do_anchor: Annotated[
        bool,
        typer.Option("--anchor", help="Stamp the final hash on XRPL Testnet"),
    ] = False,
) -> None:
    """End the game. Final recap, Story Points, season standings, FINAL proof."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    # If game isn't over yet, mark it
    if not state.game_over:
        winner = state.check_winner()
        if not winner:
            # Force end — tiebreak
            state._resolve_tiebreak()

    tier_name = _tier_name(state)

    # Calculate Story Points
    story_points = _calc_story_points(state)

    # Print final scoreboard
    score_table = Table(title=f"Final Scores — {tier_name}")
    score_table.add_column("Player", style="bold")
    score_table.add_column("Coins", justify="right")
    score_table.add_column("Rep", justify="right")
    score_table.add_column("Upgrades", justify="right")
    if state.market_board:
        score_table.add_column("Resources", justify="right")
    score_table.add_column("Score", justify="right")
    for p in state.players:
        combined = (p.coins / 2) + p.reputation + (p.upgrades * 3)
        row: list[str] = [p.name, str(p.coins), str(p.reputation), str(p.upgrades)]
        if state.market_board:
            res_parts = []
            for r in RESOURCE_NAMES:
                count = p.resources.get(r, 0)
                if count > 0:
                    res_parts.append(f"{count}{r[0].upper()}")
            row.append(" ".join(res_parts) if res_parts else "-")
        row.append(f"{combined:.1f}")
        score_table.add_row(*row)
    console.print(score_table)

    # Print winner
    if state.winner:
        console.print(f"\n  [bold green]{state.winner} wins![/bold green]")

    # Print Story Points awards
    console.print()
    awards_table = Table(title="Story Points")
    awards_table.add_column("Award", style="bold")
    awards_table.add_column("Player(s)")
    awards_table.add_column("Points", justify="right")

    award_names = {
        "winner": "Winner",
        "promise_keeper": "Promise Keeper",
        "most_helpful": "Most Helpful",
        "tables_choice": "Table's Choice",
        "treaty_keeper": "Treaty Keeper",
    }
    for key, label in award_names.items():
        winners = [n for n, a in story_points.items() if a[key] > 0]
        if winners:
            awards_table.add_row(label, ", ".join(winners), "+1")
        else:
            awards_table.add_row(label, "[dim]—[/dim]", "[dim]—[/dim]")
    console.print(awards_table)

    # Totals
    console.print()
    for name, awards in story_points.items():
        total = sum(awards.values())
        if total > 0:
            console.print(f"  {name}: [bold]{total}[/bold] Story Points")

    # Update season
    season = _update_season(state, story_points)

    # Show season standings
    if len(season["games"]) > 1:
        console.print()
        standing_table = Table(title=f"Season Standings (Game {len(season['games'])})")
        standing_table.add_column("Player", style="bold")
        standing_table.add_column("Story Points", justify="right")
        for name, total in sorted(
            season["standings"].items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            standing_table.add_row(name, str(total))
        console.print(standing_table)

    # Show votes
    for entry in state.log:
        _, _, text = entry.partition(": ")
        if "Vote:" in text:
            console.print(f"  [dim]{text}[/dim]")

    # Generate FINAL proof
    proof = make_round_proof(state)
    proof["final"] = True
    active_id = f"s{state.config.seed}"
    out_dir = proofs_dir(active_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    proof_path = out_dir / "final.proof.json"
    proof_content = canonical_json(proof)
    atomic_write_text(proof_path, proof_content)
    h = proof["envelope_hash"]
    console.print(f"\n  Final proof: [dim]{h}[/dim]")
    console.print(f"  Saved to: [dim]{proof_path}[/dim]")

    # Queue the FINAL hash for the next anchor batch (v2.1).
    add_pending_anchor(active_id, "FINAL", proof["envelope_hash"])

    _save_state(state)

    # Optional anchor — flush all pending entries (per-round + FINAL) as one
    # multi-memo Payment. v2.1 audit-ergonomics path replaces the v2.0.x
    # single-memo FINAL anchor.
    if do_anchor:
        seed_val = state.config.seed
        game_id = proof.get("game_id", f"s{seed_val}")

        wallet_file = SAVE_DIR / "wallet_seed.txt"
        wallet_seed: str | None = None
        if wallet_file.exists():
            wallet_seed = wallet_file.read_text(encoding="utf-8").strip()
        else:
            wallet_seed = os.environ.get("XRPL_SEED")

        if not wallet_seed:
            console.print(
                "\n  [yellow]No wallet seed found for anchoring.[/yellow]"
                "\n  [dim]Pick one of:[/dim]"
                "\n  [dim]  - Generate a Testnet wallet:  sov wallet[/dim]"
                "\n  [dim]  - Set XRPL_SEED in your environment[/dim]"
                "\n  [dim]  - Save a seed at .sov/wallet_seed.txt[/dim]"
                "\n  [dim]The final proof is already saved locally — anchoring is optional.[/dim]"
            )
        else:
            pending = read_pending_anchors(active_id)
            if not pending:
                console.print("\n  [dim]No pending anchors to flush.[/dim]")
            else:
                resolved_network = _resolve_network(None)

                def _sort_key(round_key: str) -> tuple[int, int]:
                    if round_key == "FINAL":
                        return (1, 0)
                    try:
                        return (0, int(round_key))
                    except ValueError:
                        return (2, 0)

                sorted_keys = sorted(pending.keys(), key=_sort_key)

                from sov_transport.base import BatchEntry

                rounds: list[BatchEntry] = [
                    BatchEntry(
                        round_key=key,
                        ruleset=state.config.ruleset,
                        game_id=game_id,
                        envelope_hash=pending[key]["envelope_hash"],
                    )
                    for key in sorted_keys
                ]

                n = len(rounds)
                plural = "s" if n != 1 else ""
                console.print(f"\n  Anchoring {n} pending round{plural} as one batched tx...")
                try:
                    from sov_transport.xrpl import XRPLTransport

                    transport = XRPLTransport(network=resolved_network)
                    txid = transport.anchor_batch(rounds, wallet_seed)

                    for batch_entry in rounds:
                        rk = batch_entry["round_key"]
                        round_key_for_record: int | str
                        if rk == "FINAL":
                            round_key_for_record = "FINAL"
                        else:
                            try:
                                round_key_for_record = int(rk)
                            except ValueError:
                                round_key_for_record = rk
                        _record_anchor(round_key_for_record, txid, game_id)

                    clear_pending_anchors(active_id, list(sorted_keys))
                    logger.info(
                        "anchor_batch.success rounds=%d txid=%s game_id=%s",
                        n,
                        txid,
                        game_id,
                    )
                    explorer = transport.explorer_tx_url(txid)
                    console.print(f"  [green]Anchored.[/green] TX: [dim]{txid}[/dim]")
                    console.print(f"  [dim]{explorer}[/dim]")
                except Exception as e:
                    # Batch anchor failed; the proof files are still saved
                    # locally and pending-anchors.json is intact. Operator
                    # retries with `sov anchor` (idempotent on the same set).
                    logger.error(
                        "anchor_batch.failed rounds=%d exc=%s detail=%s "
                        "(non-fatal: pending kept; retry with `sov anchor`)",
                        len(rounds),
                        type(e).__name__,
                        e,
                    )
                    _fail(anchor_error(str(e)))

    console.print(
        Panel(
            "  Game over. Story Points recorded.\n"
            "  Share a screenshot of this recap with your group.\n\n"
            "  [dim]Start the next game: sov new -p ...[/dim]\n"
            "  [dim]Season standings: cat .sov/season.json[/dim]",
            title="That's a wrap",
        )
    )


@app.command(name="season-postcard")
def season_postcard() -> None:
    """Share your season in one screenshot."""
    if not SEASON_FILE.exists():
        console.print("  [yellow]No season yet.[/yellow]")
        console.print("  [dim]Finish a game with sov game-end to start tracking.[/dim]")
        raise typer.Exit(0)

    # Stage 7-B amend: read via the schema-version-tolerant helper so this
    # surface picks up both the v0 bare-dict and v1 wrapped forms.
    season = _read_season_document()
    games = season.get("games", [])
    standings = season.get("standings", {})

    if not games:
        console.print("  [yellow]No games recorded yet.[/yellow]")
        raise typer.Exit(0)

    # Standings table
    s = "s" if len(games) != 1 else ""
    standing_table = Table(title=f"Season Standings ({len(games)} game{s})")
    standing_table.add_column("Player", style="bold")
    standing_table.add_column("Story Points", justify="right")
    sorted_standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)
    for name, total in sorted_standings:
        standing_table.add_row(name, str(total))
    console.print(standing_table)

    # Champion (if 3+ games)
    if len(games) >= 3 and sorted_standings:
        champ = sorted_standings[0]
        # Check for tie
        tied = [n for n, t in sorted_standings if t == champ[1]]
        if len(tied) > 1:
            names = ", ".join(tied)
            console.print(
                f"\n  [bold yellow]Tied for Season Champion: {names}[/bold yellow]",
            )
        else:
            console.print(f"\n  [bold yellow]Season Champion: {champ[0]}[/bold yellow]")

    # Award totals across the season
    award_totals: dict[str, dict[str, int]] = {}
    for game in games:
        for name, awards in game.get("awards", {}).items():
            if name not in award_totals:
                award_totals[name] = {
                    "winner": 0,
                    "promise_keeper": 0,
                    "most_helpful": 0,
                    "tables_choice": 0,
                }
            for key, val in awards.items():
                award_totals[name][key] = award_totals[name].get(key, 0) + val

    if award_totals:
        console.print()
        award_table = Table(title="Award Totals")
        award_table.add_column("Player", style="bold")
        award_table.add_column("Wins", justify="right")
        award_table.add_column("Promise", justify="right")
        award_table.add_column("Helpful", justify="right")
        award_table.add_column("MVP", justify="right")
        for name in [n for n, _ in sorted_standings]:
            a = award_totals.get(name, {})
            award_table.add_row(
                name,
                str(a.get("winner", 0)),
                str(a.get("promise_keeper", 0)),
                str(a.get("most_helpful", 0)),
                str(a.get("tables_choice", 0)),
            )
        console.print(award_table)

    # Game history
    console.print()
    for i, game in enumerate(games, 1):
        w = game.get("winner", "?")
        r = game.get("ruleset", "?").replace("_v1", "").replace("_", " ").title()
        rnds = game.get("rounds", "?")
        console.print(f"  Game {i}: {r} — {w} won (round {rnds})")

    # Votes highlight
    all_votes = []
    for game in games:
        for _key, text in game.get("votes", {}).items():
            all_votes.append(text)
    if all_votes:
        console.print()
        for v in all_votes:
            console.print(f"  [dim]{v}[/dim]")

    console.print(
        Panel(
            "  Share this screenshot with your group.\n  [dim]sov season-postcard[/dim]",
            title="Season Postcard",
        )
    )


@app.command()
def recap() -> None:
    """Show a human-readable summary of what happened recently."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    if not state.log:
        console.print("  Nothing has happened yet.")
        return

    # Show log entries from the current round (and previous if we just started)
    rnd = state.current_round
    prev_rnd = rnd - 1 if rnd > 1 else rnd

    console.print(f"\n  [bold]What happened lately[/bold] [dim](Round {rnd})[/dim]\n")
    for entry in state.log:
        # Show entries from current and previous round
        if entry.startswith(f"R{rnd}") or entry.startswith(f"R{prev_rnd}"):
            # Strip the round/turn prefix for readability
            _, _, text = entry.partition(": ")
            if text:
                console.print(f"  - {text}")

    # Highlight interesting moments
    broken = [e for e in state.log if "broke their promise" in e]
    helped = [e for e in state.log if "helps" in e and "Help" not in e[:5]]
    apologized = [e for e in state.log if "apologizes" in e]

    if broken or helped or apologized:
        console.print()
    for b in broken:
        _, _, text = b.partition(": ")
        console.print(f"  [red]Ouch:[/red] {text}")
    for h in helped:
        _, _, text = h.partition(": ")
        console.print(f"  [green]Kind:[/green] {text}")
    for a in apologized:
        _, _, text = a.partition(": ")
        console.print(f"  [yellow]Brave:[/yellow] {text}")

    # Market Moments (Town Hall only)
    if state.market_board:
        console.print()
        console.print(f"  {_market_moment(state)}")

    console.print()


@app.command()
def board() -> None:
    """Show the game board with player positions."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    table = Table(title="Board")
    table.add_column("#", style="dim", width=3)
    table.add_column("Space", width=14)
    table.add_column("Players Here", width=30)
    table.add_column("Effect", width=40)

    for space in state.board:
        players_here = [p.name for p in state.players if p.position == space.index]
        names = (f"[bold cyan]{n}[/bold cyan]" for n in players_here)
        marker = ", ".join(names) if players_here else ""
        table.add_row(str(space.index), space.name, marker, space.description)

    console.print(table)


@app.command()
def market(
    action: Annotated[
        str,
        typer.Argument(help="show, buy, or sell"),
    ] = "show",
    resource: Annotated[
        str,
        typer.Argument(help="food, wood, or tools"),
    ] = "",
    player: Annotated[
        str,
        typer.Option("--player", "-p", help="Who's trading"),
    ] = "",
) -> None:
    """Show the Market Board, or buy/sell a resource (Town Hall only)."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    if state.market_board is None:
        _fail(market_error("Market Board requires Market Day or Town Hall."))

    if action == "show":
        _print_market(state)
        return

    # Find the player
    target = None
    if player:
        target = next((p for p in state.players if p.name == player), None)
    else:
        target = state.current_player
    if target is None:
        _fail(player_not_found_error(player))

    if not resource:
        _fail(market_error("Specify a resource: food, wood, or tools"))

    if action == "buy":
        msg = market_buy(state, target, resource)
    elif action == "sell":
        msg = market_sell(state, target, resource)
    else:
        _fail(invalid_action_error(action, "market show/buy/sell"))

    console.print(f"\n  {msg}")
    _save_state(state)
    console.print()
    _print_market(state)


# ---------------------------------------------------------------------------
# Upgrades — Town Hall / Treaty Table / Market Day
# ---------------------------------------------------------------------------

# Resource-cost rulesets that expose ``upgrade_with_resources``. Kept here
# (and not imported from campfire._RESOURCE_UPGRADE_RULESETS, which is a
# private symbol) so the CLI's allow-list is independently auditable. The
# string set must stay in sync with the engine's set; tests pin both.
_UPGRADE_RULESETS = frozenset(
    {"town_hall_v1", "treaty_table_v1", "market_day_v1"},
)


def _upgrade_cost_table(target: str) -> tuple[int, str, int]:
    """Return (coin_cost, resource_name, resource_cost) for the upgrade.

    Mirrors the constants the engine uses (WORKSHOP_WOOD_COST,
    BUILDER_TOOLS_COST) so the CLI can render dry-run output without
    re-implementing pricing. Engine remains the source of truth for the
    resource amounts.
    """
    if target == "workshop":
        return (2, "wood", WORKSHOP_WOOD_COST)
    return (3, "tools", BUILDER_TOOLS_COST)


@app.command()
def upgrade(
    target: Annotated[
        str,
        typer.Argument(help="workshop or builder"),
    ],
    player: Annotated[
        str,
        typer.Option("--player", "-p", help="Who's upgrading (defaults to active player)"),
    ] = "",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show the cost and target tier without spending resources.",
        ),
    ] = False,
) -> None:
    """Spend coins + a resource to gain an upgrade (Town Hall / Treaty Table / Market Day).

    Costs:
      workshop — 2 coins + 1 wood
      builder  — 3 coins + 1 tools, requires Rep >= 3

    Campfire uses the coinless workshop (``sov build``) and does not expose
    this command. Defaulting and ergonomics mirror ``sov market buy|sell``.
    """
    target_norm = target.lower().strip()
    if target_norm not in ("workshop", "builder"):
        _fail(invalid_action_error(target, "upgrade workshop|builder"))

    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    ruleset = state.config.ruleset
    if ruleset not in _UPGRADE_RULESETS:
        # Campfire (the documented coinless ruleset) — emit the locked
        # coordination INFO and refuse the command. Tests pin this string
        # via caplog (Wave 9 contract).
        logger.info(CAMPFIRE_UPGRADE_HINT)
        _fail(upgrade_unavailable_error(_tier_name(state)))

    # Resolve player (mirror ``sov market`` defaulting).
    if player:
        target_player = next((p for p in state.players if p.name == player), None)
    else:
        target_player = state.current_player
    if target_player is None:
        _fail(player_not_found_error(player))

    coin_cost, res_name, res_cost = _upgrade_cost_table(target_norm)

    # --dry-run: describe the cost + tier without dispatching to engine.
    if dry_run:
        tier = _tier_name(state)
        console.print(
            f"\n  [bold]Dry run:[/bold] upgrade {target_norm} ({tier})\n"
            f"  Cost: {coin_cost} coins + {res_cost} {res_name}"
            + (" (requires Rep >= 3)" if target_norm == "builder" else "")
        )
        held_coins = target_player.coins
        held_res = target_player.resources.get(res_name, 0)
        console.print(
            f"  {target_player.name} has: {held_coins} coins, {held_res} {res_name}, "
            f"Rep {target_player.reputation}"
        )
        return

    # Pre-validate so we can emit the actionable structured error rather
    # than the engine's terse string. Engine remains authoritative for the
    # actual mutation; we just front it with a humane error surface.
    if target_norm == "builder" and target_player.reputation < 3:
        _fail(
            upgrade_rep_error(
                target_norm,
                3,
                target_player.reputation,
                "Earn Rep by keeping promises ('sov promise keep ...') "
                "or apologizing ('sov apologize ...').",
            )
        )

    held_coins = target_player.coins
    held_res = target_player.resources.get(res_name, 0)
    coins_short = max(0, coin_cost - held_coins)
    res_short = max(0, res_cost - held_res)

    if coins_short > 0 or res_short > 0:
        # Pick the most actionable hint: the missing resource is usually the
        # bigger blocker, so name it first when both are short. Mirror the
        # patterns the rest of the CLI uses for "earn 1 more X via Y".
        coin_unit = "coin" if coins_short == 1 else "coins"
        if res_short > 0 and coins_short > 0:
            hint = (
                f"Earn {coins_short} more {coin_unit} via 'sov market sell', "
                f"then pick up {res_short} {res_name} via 'sov market buy {res_name}'."
            )
        elif res_short > 0:
            hint = f"Pick up {res_short} {res_name} via 'sov market buy {res_name}'."
        else:
            hint = f"Earn {coins_short} more {coin_unit} via 'sov market sell'."
        _fail(
            insufficient_resources_error(
                target_norm,
                {"coins": coin_cost, res_name: res_cost},
                {"coins": held_coins, res_name: held_res},
                hint,
            )
        )

    # All gates passed — dispatch to the engine.
    msg = upgrade_with_resources(state, target_player, target_norm)
    console.print(f"\n  {msg}")
    _save_state(state)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _apply_recipe(state: GameState, recipe: str) -> str:
    """Filter event/deal decks to cards matching a recipe tag. Returns a note string."""
    from sov_engine.models import Deck

    tag = recipe.lower()
    valid_tags = ("cozy", "spicy", "market", "promise")
    if tag not in valid_tags:
        opts = "cozy, spicy, market, or promise"
        return f"\n  [yellow]Unknown recipe '{recipe}'. Try: {opts}.[/yellow]"

    # Filter events
    all_events = state.event_deck.draw_pile
    filtered_events = [c for c in all_events if tag in c.tags]
    if len(filtered_events) >= 5:
        state.event_deck = Deck(draw_pile=filtered_events)
        evt_note = f"{len(filtered_events)} events"
    else:
        evt_note = f"all {len(all_events)} events (too few '{tag}' events to filter)"

    # Filter deals
    all_deals = state.deal_deck.draw_pile
    filtered_deals = [c for c in all_deals if tag in c.tags]
    if len(filtered_deals) >= 3:
        state.deal_deck = Deck(draw_pile=filtered_deals)
        deal_note = f"{len(filtered_deals)} deals"
    else:
        deal_note = f"all {len(all_deals)} deals (too few '{tag}' deals to filter)"

    state.add_log(f"Recipe: {tag} ({evt_note}, {deal_note})")
    return f"\n  [dim]Recipe: {tag} — {evt_note}, {deal_note}[/dim]"


def _postcard_highlights(
    state: GameState,
    rnd: int,
    style: str,
) -> list[str]:
    """Build postcard highlights filtered by story style."""
    # Define which log patterns each style cares about
    matchers: dict[str, list[tuple[str, str]]] = {
        "cozy": [
            ("helps", "[green]Kind:[/green]"),
            ("apologizes", "[yellow]Brave:[/yellow]"),
            ("toasts", "[yellow]Toast:[/yellow]"),
            ("kept their promise", "[green]Kept:[/green]"),
        ],
        "spicy": [
            ("broke their promise", "[red]Ouch:[/red]"),
            ("BROKEN", "[red]Treaty broken:[/red]"),
            ("offers", "[cyan]Trade:[/cyan]"),
            ("defaults", "[red]Default:[/red]"),
        ],
        "economic": [
            ("buys", "[cyan]Buy:[/cyan]"),
            ("sells", "[cyan]Sell:[/cyan]"),
            ("Market", "[dim]Market:[/dim]"),
        ],
    }
    # "all" uses every matcher
    if style == "all":
        active = [
            ("broke their promise", "[red]Ouch:[/red]"),
            ("apologizes", "[yellow]Brave:[/yellow]"),
            ("helps", "[green]Kind:[/green]"),
            ("offers", "[cyan]Trade:[/cyan]"),
            ("toasts", "[yellow]Toast:[/yellow]"),
            ("Treaty.*honored", "[green]Treaty kept:[/green]"),
            ("BROKEN", "[red]Treaty broken:[/red]"),
            ("wins", "[bold green]"),
        ]
    else:
        active = matchers.get(style, matchers["cozy"])

    highlights: list[str] = []
    for entry in state.log:
        if not (entry.startswith(f"R{rnd}") or (rnd > 1 and entry.startswith(f"R{rnd - 1}"))):
            continue
        _, _, text = entry.partition(": ")
        for pattern, label in active:
            if pattern in text:
                highlights.append(f"{label} {text}")
                break
    return highlights


def _tier_name(state: GameState) -> str:
    """Human-readable tier name from game state."""
    ruleset = state.config.ruleset
    if ruleset == "treaty_table_v1":
        return "Treaty Table"
    if ruleset == "town_hall_v1":
        return "Town Hall"
    if ruleset == "market_day_v1":
        return "Market Day"
    return "Campfire"


def _market_moment(state: GameState) -> str:
    """One human-readable line about the market's mood."""
    mb = state.market_board
    if mb is None:
        return ""

    # Market Day: fixed prices, always open
    if mb.fixed_prices:
        return "[green]Market's open.[/green] Fixed prices — always 2 coins."

    # Town Hall: dynamic mood
    empty = [r for r in RESOURCE_NAMES if mb.supply[r] == 0]
    scarce = [r for r in RESOURCE_NAMES if 0 < mb.supply[r] <= 2]
    cheap = [r for r in RESOURCE_NAMES if mb.price(r) <= 1]

    if empty:
        names = " and ".join(r.title() for r in empty)
        return f"[red]Market's dry:[/red] {names} unavailable."
    if scarce:
        r = scarce[0]
        p = mb.price(r)
        return f"[yellow]Market's tight:[/yellow] {r.title()} is scarce (price {p})."
    if cheap:
        r = cheap[0]
        return f"[green]Market's kind:[/green] {r.title()} is cheap (price 1)."
    return "[dim]Market's steady. Nothing scarce, nothing cheap.[/dim]"


def _print_market(state: GameState) -> None:
    """Print the market board."""
    mb = state.market_board
    if mb is None:
        return
    info = market_status(state)
    title = "Market Board" if not mb.fixed_prices else "Market Board (fixed prices)"
    table = Table(title=title)
    table.add_column("Resource", style="bold")
    table.add_column("Buy", justify="right")
    table.add_column("Sell", justify="right")
    if not mb.fixed_prices:
        table.add_column("Supply", justify="right")
        table.add_column("Status")
    for r in RESOURCE_NAMES:
        d = info[r]
        sell = max(1, d["price"] - 1)
        row: list[str] = [r.title(), str(d["price"]), str(sell)]
        if not mb.fixed_prices:
            if d["supply"] == 0:
                status = "[red]EMPTY[/red]"
            elif d["supply"] <= 2:
                status = "[yellow]scarce (+1 price)[/yellow]"
            else:
                status = "[green]available[/green]"
            row.extend([str(d["supply"]), status])
        table.add_row(*row)
    console.print(table)
    if mb.fixed_prices:
        console.print("  [dim]A shop, not a casino. Buy what you need.[/dim]")


def _print_status(state: GameState) -> None:
    is_town_hall = state.market_board is not None
    table = Table(title=f"Round {state.current_round}")
    table.add_column("Player", style="bold")
    table.add_column("Coins", justify="right")
    table.add_column("Rep", justify="right")
    table.add_column("Upgrades", justify="right")
    if is_town_hall:
        table.add_column("Resources", justify="right")
    table.add_column("Position")
    table.add_column("Goal")

    for i, p in enumerate(state.players):
        marker = " *" if i == state.current_player_index else ""
        pos_name = state.board[p.position].name if state.board else str(p.position)
        row: list[str] = [
            p.name + marker,
            str(p.coins),
            str(p.reputation),
            str(p.upgrades),
        ]
        if is_town_hall:
            res_parts = []
            for r in RESOURCE_NAMES:
                count = p.resources.get(r, 0)
                if count > 0:
                    res_parts.append(f"{count}{r[0].upper()}")
            row.append(" ".join(res_parts) if res_parts else "-")
        row.extend([pos_name, p.win_condition.value])
        table.add_row(*row)

    console.print(table)
    if state.game_over:
        console.print(f"  [bold green]{state.winner} wins the game.[/bold green]")
    else:
        console.print(f"  [dim]{state.current_player.name}'s turn next.[/dim]")
    if is_town_hall:
        console.print()
        _print_market(state)
    # v2.1: daemon presence line under the player table.
    try:
        daemon_st = _query_daemon_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "status.daemon_probe.failed exc=%s detail=%s",
            type(exc).__name__,
            exc,
        )
    else:
        if daemon_st is not None:
            console.print(f"  [dim]{_daemon_status_human_line(daemon_st)}[/dim]")


def _query_daemon_status() -> Any:
    """Probe the daemon's pid-based status without crashing on missing extras.

    Returns the daemon ``DaemonStatus`` object on success, or ``None`` if the
    ``[daemon]`` opt-in extra isn't installed (so daemon-aware surfaces in
    the CLI degrade gracefully on stripped installs). Any other exception is
    re-raised — a malformed ``.sov/daemon.json`` is a real diagnostic, not
    a "daemon not installed" signal.

    The import goes through ``importlib`` (rather than a ``from sov_daemon
    import …`` statement) so that the wave-3 split between the cli and
    daemon agents stays clean: the daemon-domain agent owns the public
    surface, and the CLI binds to it at runtime, not at type-check time.
    """
    import importlib

    try:
        daemon_mod = importlib.import_module("sov_daemon")
    except ImportError:
        return None
    return daemon_mod.daemon_status()


def _daemon_status_human_line(status: Any) -> str:
    """Render a daemon-status object for `sov status` human output.

    Shape examples (per docs/v2.1-daemon-ipc.md §13):
        daemon: running (port 47823, network=testnet, readonly=false)
        daemon: stale (last pid 12345 — run `sov daemon start` to start a fresh one)
        daemon: none
    """
    state = getattr(status, "state", None)
    if state == "running":
        port = getattr(status, "port", "?")
        network = getattr(status, "network", "?")
        readonly = getattr(status, "readonly", False)
        return (
            f"daemon: running (port {port}, network={network}, "
            f"readonly={'true' if readonly else 'false'})"
        )
    if state == "stale":
        pid = getattr(status, "pid", "?")
        return f"daemon: stale (last pid {pid} — run `sov daemon start` to start a fresh one)"
    return "daemon: none"


def _daemon_status_json_field(status: Any) -> dict[str, Any]:
    """Render a daemon-status object as the ``daemon`` field for `sov status --json`."""
    if status is None:
        return {"state": "none"}
    state = getattr(status, "state", "none")
    field: dict[str, Any] = {"state": state}
    for attr in ("port", "pid", "network", "readonly", "started_iso"):
        val = getattr(status, attr, None)
        if val is not None:
            field[attr] = val
    return field


def _print_brief_status(state: GameState) -> None:
    parts = []
    for i, p in enumerate(state.players):
        marker = ">" if i == state.current_player_index else " "
        parts.append(f"{marker}{p.name}: {p.coins}c {p.reputation}r {p.upgrades}u")
    console.print(f"[dim]R{state.current_round} | {' | '.join(parts)}[/dim]")
    # Stage 7-B amend (CLI-B-011): pending-anchors count visible in --brief
    # so operators see queued rounds without invoking full status or --json.
    # Single-line additive output; deterministic format for README pinning.
    game_id = f"s{state.config.seed}"
    try:
        pending = read_pending_anchors(game_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "status.pending_probe.failed exc=%s detail=%s",
            type(exc).__name__,
            exc,
        )
        pending = {}
    if pending:
        n = len(pending)
        plural = "s" if n != 1 else ""
        console.print(f"[dim]  {n} pending anchor{plural} — run sov anchor to flush.[/dim]")
    # v2.1: daemon presence line — surfaced in both --brief and full modes
    # so audit-tier consumers know whether a daemon is up without grepping
    # `sov daemon status` separately.
    try:
        daemon_st = _query_daemon_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "status.daemon_probe.failed exc=%s detail=%s",
            type(exc).__name__,
            exc,
        )
        return
    if daemon_st is None:
        return
    console.print(f"[dim]{_daemon_status_human_line(daemon_st)}[/dim]")


def _status_json_payload(state: GameState) -> dict[str, Any]:
    """Build the ``sov status --json`` payload.

    v2.1 surfaces the 3-state anchor status per round (``anchored``,
    ``pending``, ``missing``) by composing the local ``anchors.json`` history
    with ``pending-anchors.json``. Pure-local (no chain hit) — the chain
    lookup variant lives behind ``sov verify --tx``. Adding the
    ``rounds`` and ``pending_count`` fields is additive over v2.0; the
    top-level shape is unchanged so we don't bump ``schema_version``.
    """
    game_id = f"s{state.config.seed}"

    pending = read_pending_anchors(game_id)

    # Read anchors.json defensively — same recovery posture as `_record_anchor`.
    # Stage 7-B amend (CLI-B-002 + CLI-B-003): tolerates both the v0 bare-dict
    # shape and the v1 ``{"schema_version": 1, "entries": ...}`` wrapper.
    anchor_file = anchors_file(game_id)
    anchored = _read_anchors_entries(anchor_file)

    rounds_payload: list[dict[str, Any]] = []
    # Surface every round we have local evidence for — proof file present,
    # anchor recorded, or pending entry queued. Union of the three sources
    # so a round in any one of them shows up in the JSON.
    pdir = proofs_dir(game_id)
    seen: set[str] = set()
    if pdir.exists():
        for proof_path in sorted(pdir.glob("*.proof.json")):
            try:
                proof_data = json.loads(proof_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rnd_value = proof_data.get("round")
            if rnd_value is None:
                continue
            seen.add(str(rnd_value))
    seen.update(anchored.keys())
    seen.update(pending.keys())

    def _sort_key(round_key: str) -> tuple[int, int]:
        if round_key == "FINAL":
            return (1, 0)
        try:
            return (0, int(round_key))
        except ValueError:
            return (2, 0)

    for round_key in sorted(seen, key=_sort_key):
        if round_key in anchored:
            anchor_state = "anchored"
        elif round_key in pending:
            anchor_state = "pending"
        else:
            anchor_state = "missing"
        entry: dict[str, Any] = {
            "round": round_key,
            "anchor_status": anchor_state,
        }
        if round_key in anchored:
            entry["txid"] = anchored[round_key]
        rounds_payload.append(entry)

    # v2.1: daemon presence as an additive field. Probe is best-effort —
    # a stripped install without the [daemon] extra renders ``state: none``
    # so JSON consumers don't have to special-case the optional dependency.
    try:
        daemon_st = _query_daemon_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "status.daemon_probe.failed exc=%s detail=%s",
            type(exc).__name__,
            exc,
        )
        daemon_field: dict[str, Any] = {"state": "none"}
    else:
        daemon_field = _daemon_status_json_field(daemon_st)

    payload: dict[str, Any] = {
        "timestamp": _json_status(),
        "command": "status",
        "status": _JSON_OUTPUT_OK,
        "game_id": game_id,
        "current_round": state.current_round,
        "game_over": state.game_over,
        "winner": state.winner,
        "players": [
            {
                "name": p.name,
                "coins": p.coins,
                "reputation": p.reputation,
                "upgrades": p.upgrades,
                "is_current": i == state.current_player_index,
            }
            for i, p in enumerate(state.players)
        ],
        "rounds": rounds_payload,
        "pending_count": len(pending),
        "daemon": daemon_field,
    }

    # CLI-004: surface the structured ``ANCHOR_PENDING`` shape when at least
    # one round is queued in pending-anchors.json. The diagnostic JSON
    # consumer (`sov status --json`) is a discovery surface, not a failure
    # gate — but the v2.1 spec promises the structured code so external
    # tooling can reason about it. Embed the error envelope alongside the
    # existing ``rounds`` / ``pending_count`` fields rather than replacing
    # them; humans still see the per-round breakdown.
    if pending:
        # Sort by the same numeric / FINAL key the rounds list uses so the
        # message is deterministic across runs.
        pending_round_keys = sorted(pending.keys(), key=_sort_key)
        anchor_pending = anchor_pending_error(pending_round_keys)
        payload["anchor_pending"] = {
            "code": anchor_pending.code,
            "message": anchor_pending.message,
            "hint": anchor_pending.hint,
            "rounds": pending_round_keys,
        }

    return payload


# ---------------------------------------------------------------------------
# Scenario metadata (pure content — no engine logic)
# ---------------------------------------------------------------------------

_SCENARIOS = [
    {
        "name": "Cozy Night",
        "slug": "cozy-night",
        "tier": "Campfire / Market Day",
        "tier_value": "campfire",
        "recipe": "cozy",
        "recipe_value": "cozy",
        "players": "2-4",
        "time": "30-45 min",
    },
    {
        "name": "Market Panic",
        "slug": "market-panic",
        "tier": "Town Hall",
        "tier_value": "town-hall",
        "recipe": "market",
        "recipe_value": "market",
        "players": "3-4",
        "time": "45-60 min",
    },
    {
        "name": "Promises Matter",
        "slug": "promises-matter",
        "tier": "Campfire",
        "tier_value": "campfire",
        "recipe": "promise",
        "recipe_value": "promise",
        "players": "2-3",
        "time": "30 min",
    },
    {
        "name": "Treaty Night",
        "slug": "treaty-night",
        "tier": "Treaty Table",
        "tier_value": "treaty-table",
        "recipe": "—",
        "recipe_value": "",
        "players": "3-4",
        "time": "75-90 min",
    },
]

_SCENARIO_BY_SLUG = {s["slug"]: s for s in _SCENARIOS}

SOV_VERSION = "1.4.7"


# ---------------------------------------------------------------------------
# Scenario lint
# ---------------------------------------------------------------------------

_VALID_TIERS = {
    "campfire",
    "market-day",
    "town-hall",
    "treaty-table",
    "Campfire",
    "Market Day",
    "Town Hall",
    "Treaty Table",
    "Campfire / Market Day",
    "Campfire or Market Day",
}

_VALID_RECIPES = {"cozy", "spicy", "market", "promise", "\u2014", "-", ""}


def _lint_scenario(filepath: str) -> list[tuple[str, str]]:
    """Lint a scenario markdown file. Returns list of (level, message)."""
    import re

    results: list[tuple[str, str]] = []
    path = Path(filepath)

    if not path.exists():
        results.append(("error", f"File not found: {filepath}"))
        return results

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # --- Structure checks (errors) ---

    # H1 heading present
    has_h1 = any(line.startswith("# ") for line in lines)
    if not has_h1:
        results.append(("error", "Missing: H1 heading (scenario name)"))

    # Block quote present (vibe intro)
    has_blockquote = any(line.startswith("> ") for line in lines)
    if not has_blockquote:
        results.append(("error", "Missing: Block quote (vibe intro)"))

    # Settings table with required rows
    table_rows: dict[str, str] = {}
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| Setting") or stripped.startswith("| ----"):
            in_table = True
            continue
        if in_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")]
            # cells[0] is empty (before first |), cells[1] key, cells[2] value
            if len(cells) >= 3:
                table_rows[cells[1].lower()] = cells[2]
        elif in_table and not stripped.startswith("|"):
            in_table = False

    required_rows = {"tier", "recipe", "players", "rounds", "time"}
    found_rows = set(table_rows.keys())
    missing_rows = required_rows - found_rows
    if missing_rows:
        results.append(("error", "Settings table missing rows: " + ", ".join(sorted(missing_rows))))
    elif not table_rows:
        results.append(("error", "Missing: Settings table"))

    # "What to expect" section
    has_expect = any(line.strip().lower().startswith("## what to expect") for line in lines)
    if not has_expect:
        results.append(("error", "Missing: ## What to expect"))

    # "Start command" section with a code block
    has_start = any(line.strip().lower().startswith("## start command") for line in lines)
    if not has_start:
        results.append(("error", "Missing: ## Start command"))
    else:
        in_start = False
        has_code_block = False
        for line in lines:
            if line.strip().lower().startswith("## start command"):
                in_start = True
                continue
            if in_start and line.strip().startswith("## "):
                break
            if in_start and line.strip().startswith("```"):
                has_code_block = True
                break
        if not has_code_block:
            results.append(
                ("error", "Start command section has no code block"),
            )

    # --- Field checks (errors) ---

    tier_value = table_rows.get("tier", "")
    if tier_value and tier_value not in _VALID_TIERS:
        results.append(("error", f'Invalid tier: "{tier_value}"'))

    recipe_value = table_rows.get("recipe", "")
    recipe_clean = recipe_value.split("(")[0].strip()
    if recipe_clean and recipe_clean not in _VALID_RECIPES:
        results.append(("error", f'Invalid recipe: "{recipe_value}"'))

    players_value = table_rows.get("players", "")
    if players_value and not re.match(r"^\d+(-\d+)?$", players_value):
        results.append(
            ("error", f'Invalid players format: "{players_value}"'),
        )

    time_value = table_rows.get("time", "")
    if time_value and "min" not in time_value.lower():
        results.append(
            ("error", f"Invalid time: \"{time_value}\" (should contain 'min')"),
        )

    # --- Content checks (warnings) ---

    has_success = any(
        line.strip().lower().startswith("## what success feels like") for line in lines
    )
    if not has_success:
        results.append(("warn", "Missing: ## What success feels like"))

    has_after = any(line.strip().lower().startswith("## after the game") for line in lines)
    if not has_after:
        results.append(("warn", "Missing: ## After the game"))

    has_norms = any(line.strip().lower().startswith("## table norms") for line in lines)
    if not has_norms:
        results.append(("warn", "Missing: ## Table norms"))

    # Vibe intro length check
    if has_blockquote:
        bq_lines = [line[2:] for line in lines if line.startswith("> ")]
        vibe_text = " ".join(bq_lines).strip()
        if len(vibe_text) < 20:
            results.append(
                ("warn", f"Vibe intro too short ({len(vibe_text)} chars)"),
            )
        elif len(vibe_text) > 500:
            results.append(
                ("warn", f"Vibe intro too long ({len(vibe_text)} chars)"),
            )

    # --- Deck checks (warnings) ---

    valid_recipe_tags = ("cozy", "spicy", "market", "promise")
    if recipe_clean.lower() in valid_recipe_tags:
        from sov_engine.content import build_deal_deck, build_event_deck

        tag = recipe_clean.lower()
        events = build_event_deck()
        deals = build_deal_deck()
        event_count = sum(1 for e in events if tag in e.tags)
        deal_count = sum(1 for d in deals if tag in d.tags)

        if event_count < 5:
            results.append(
                (
                    "warn",
                    f"Recipe '{tag}': only {event_count} matching events "
                    f"(< 5, full deck will be used)",
                )
            )
        if deal_count < 3:
            results.append(
                (
                    "warn",
                    f"Recipe '{tag}': only {deal_count} matching deals "
                    f"(< 3, full deck will be used)",
                )
            )

    return results


def _parse_share_code(code: str) -> dict[str, str] | str:
    """Parse a SOV share code. Returns dict or error string."""
    parts = code.strip().split("|")
    if len(parts) != 5 or parts[0] != "SOV":
        return "Invalid share code. Expected: SOV|<scenario>|<tier>|<recipe>|s<seed>"
    slug, tier, recipe, seed_part = parts[1], parts[2], parts[3], parts[4]
    if not seed_part.startswith("s") or not seed_part[1:].isdigit():
        return f"Invalid seed in share code: '{seed_part}'. Expected s<number>."
    return {
        "slug": slug,
        "tier": tier,
        "recipe": recipe if recipe != "-" else "",
        "seed": seed_part[1:],
    }


def _build_share_code(slug: str, tier: str, recipe: str, seed: int) -> str:
    """Build a SOV share code string."""
    recipe_part = recipe if recipe else "-"
    return f"SOV|{slug}|{tier}|{recipe_part}|s{seed}"


@app.command()
def scenario(
    action: Annotated[str, typer.Argument(help="Action: list, code, or lint")],
    name: Annotated[str, typer.Argument(help="Scenario name or file path")] = "",
    seed: Annotated[int, typer.Option("--seed", "-s", help="RNG seed")] = 42,
    tier_opt: Annotated[
        str,
        typer.Option("--tier", "-t", help="Tier override (for custom)"),
    ] = "",
    recipe_opt: Annotated[
        str,
        typer.Option("--recipe", "-r", help="Recipe override (for custom)"),
    ] = "",
) -> None:
    """Browse scenario packs, generate share codes, or lint scenario files."""
    if action == "list":
        table = Table(title="Scenario Packs")
        table.add_column("Scenario", style="bold")
        table.add_column("Tier")
        table.add_column("Recipe")
        table.add_column("Players", justify="center")
        table.add_column("Time", justify="right")

        for s in _SCENARIOS:
            table.add_row(
                s["name"],
                s["tier"],
                s["recipe"],
                s["players"],
                s["time"],
            )

        console.print(table)
        console.print("\n  [dim]Details: docs/scenarios/<name>.md[/dim]")

    elif action == "code":
        if not name:
            _fail(scenario_error("Usage: sov scenario code <name> --seed N"))

        if name == "custom":
            if not tier_opt:
                _fail(scenario_error("Custom codes need --tier."))
            code = _build_share_code("custom", tier_opt, recipe_opt, seed)
        elif name in _SCENARIO_BY_SLUG:
            sc = _SCENARIO_BY_SLUG[name]
            code = _build_share_code(
                name,
                sc["tier_value"],
                sc["recipe_value"],
                seed,
            )
        else:
            known = ", ".join(s["slug"] for s in _SCENARIOS) + ", custom"
            _fail(scenario_error(f"Unknown scenario '{name}'. Known: {known}"))

        console.print(f"\n  [bold]{code}[/bold]\n")
        console.print("  [dim]Share this code. Others run:[/dim]")
        console.print(f'  [dim]sov new --code "{code}" -p Name1 -p Name2[/dim]')

    elif action == "lint":
        # Determine which files to lint
        if name:
            files_to_lint = [name]
        else:
            scenario_dir = Path("docs/scenarios")
            if not scenario_dir.exists():
                _fail(scenario_error("docs/scenarios/ not found."))
            files_to_lint = sorted(
                str(f)
                for f in scenario_dir.glob("*.md")
                if f.name not in ("README.md", "CANON.md", "_TEMPLATE.md")
            )
            if not files_to_lint:
                _fail(scenario_error("No scenario files found."))

        total = len(files_to_lint)
        passed = 0
        failed = 0

        for fpath in files_to_lint:
            console.print(f"\n[bold]{fpath}[/bold]")
            issues = _lint_scenario(fpath)

            errors = [msg for lvl, msg in issues if lvl == "error"]
            warns = [msg for lvl, msg in issues if lvl == "warn"]

            if not errors:
                console.print("  [green]OK[/green] Structure OK")
                passed += 1
            else:
                for msg in errors:
                    safe = msg.replace("[", "\\[")
                    console.print(f"  [red]FAIL[/red] {safe}")
                failed += 1

            for msg in warns:
                safe = msg.replace("[", "\\[")
                console.print(f"  [yellow]WARN[/yellow] {safe}")

        console.print(
            f"\n{total} file(s) checked, {passed} passed, {failed} failed.",
        )
        if failed:
            raise typer.Exit(1)

    else:
        _fail(invalid_action_error(action, "scenario list/code/lint"))


# ---------------------------------------------------------------------------
# Feedback artifact
# ---------------------------------------------------------------------------

_NOTABLE_PATTERNS = (
    "promises:",
    "kept their promise",
    "broke their promise",
    "apologizes",
    "Treaty",
    "BROKEN",
    "honored",
    "wins the game",
    "toasts",
    "helps",
)


# ---------------------------------------------------------------------------
# Multi-save: list + resume
# ---------------------------------------------------------------------------


def _summary_to_dict(s: GameSummary) -> dict[str, Any]:
    """Render a ``GameSummary`` as a JSON-serializable dict.

    The shape is the public schema for ``sov games --json`` consumers
    (audit viewer, game shell). Add new fields at the end; do not rename.
    """
    return {
        "game_id": s.game_id,
        "ruleset": s.ruleset,
        "current_round": s.current_round,
        "max_rounds": s.max_rounds,
        "players": list(s.players),
        "last_modified_iso": s.last_modified_iso,
    }


def _format_last_played(iso: str) -> str:
    """Render an ISO-8601 UTC timestamp as ``YYYY-MM-DD HH:MM UTC`` for the table.

    Falls back to the raw string when parsing fails so we never crash a
    listing on an unexpected format.
    """
    try:
        from datetime import datetime as _dt

        dt = _dt.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return iso


@app.command(name="games")
def games_cmd(
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON to stdout."),
    ] = False,
) -> None:
    """List saved games. Pick one with `sov resume <game-id>`."""
    # v1 layouts auto-migrate before listing — stays consistent with other
    # commands that funnel through _resolve_active_game_id / _load_game.
    migrate_v1_layout()
    saved = list_saved_games()
    active = get_active_game_id()

    if json_out:
        payload = [_summary_to_dict(s) for s in saved]
        # Annotate the active row so consumers can highlight it without
        # cross-referencing .sov/active-game themselves.
        for entry in payload:
            entry["active"] = entry["game_id"] == active
        typer.echo(json.dumps(payload, indent=2))
        return

    if not saved:
        console.print("  No saved games. Run `sov new` to start one.")
        return

    table = Table(title="Saved Games")
    table.add_column("GAME-ID", style="bold")
    table.add_column("RULESET")
    table.add_column("ROUND", justify="right")
    table.add_column("PLAYERS")
    table.add_column("LAST PLAYED")
    table.add_column("ACTIVE", justify="center")
    for s in saved:
        round_col = f"{s.current_round}/{s.max_rounds}" if s.max_rounds else str(s.current_round)
        active_marker = "[bold green]*[/bold green]" if s.game_id == active else ""
        table.add_row(
            s.game_id,
            s.ruleset,
            round_col,
            ", ".join(s.players),
            _format_last_played(s.last_modified_iso),
            active_marker,
        )
    console.print(table)
    if active is None:
        console.print(
            "\n  [dim]No active game pointer. Run `sov resume <game-id>` to pick one.[/dim]"
        )


@app.command(name="resume")
def resume_cmd(
    game_id: Annotated[
        str,
        typer.Argument(help="Game id to resume (e.g. s42)."),
    ],
) -> None:
    """Switch the active game. Game must already exist on disk."""
    # Reject path-traversal payloads (``..``, ``/``, ``\\``, control chars,
    # newlines) before touching the filesystem. Without this gate, a value
    # like ``s17/../s42`` would resolve to a sibling save's state.json AND
    # poison ``.sov/active-game`` on subsequent set, breaking every helper
    # that consumes the pointer downstream (state_file, rng_seed_file,
    # proofs_dir, anchors_file, game_dir, pending_anchors_path).
    _validate_game_id_or_fail(game_id)

    migrate_v1_layout()
    sf = state_file(game_id)
    if not sf.exists():
        console.print(f"  [red]No saved game with id '{game_id}'.[/red]")
        console.print("  [dim]Run `sov games` to list saved games.[/dim]")
        raise typer.Exit(1)

    set_active_game_id(game_id)

    # Read enough state to print a confirmation matching the spec example.
    try:
        data = json.loads(sf.read_text(encoding="utf-8"))
        cfg = data.get("config", {})
        ruleset = cfg.get("ruleset", "unknown")
        rnd = data.get("current_round", "?")
        max_rounds = cfg.get("max_rounds", "?")
        console.print(
            f"  Switched to game [bold]{game_id}[/bold] "
            f"(round {rnd}/{max_rounds}, ruleset {ruleset})."
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        # Pointer was set even if the read failed — operator can still
        # dig into the per-game directory by hand. Keep the surface honest.
        console.print(f"  Switched to game [bold]{game_id}[/bold].")


@app.command()
def feedback() -> None:
    """Print an issue-ready play report. Paste into GitHub Issues."""
    result = _load_game()
    if result is None:
        _fail(no_game_error())
    state, _ = result

    tier = _tier_name(state)
    game_id = f"s{state.config.seed}"
    rf = rng_seed_file(game_id)
    seed_str = rf.read_text().strip() if rf.exists() else "?"
    winner = state.winner or "(in progress)"
    rnd = state.current_round
    player_count = len(state.players)

    # Extract recipe from log
    recipe_used = "—"
    for entry in state.log:
        if "Recipe:" in entry:
            # Format: "R1T0: Recipe: cozy (12 events, 5 deals)"
            part = entry.split("Recipe: ", 1)[1]
            recipe_used = part.split(" ")[0]
            break

    # Awards
    awards = _calc_story_points(state)
    award_names = {
        "winner": "Winner",
        "promise_keeper": "Promise Keeper",
        "most_helpful": "Most Helpful",
        "tables_choice": "Table's Choice",
        "treaty_keeper": "Treaty Keeper",
    }
    award_lines: list[str] = []
    for award_key, label in award_names.items():
        winners = [name for name, pts in awards.items() if pts.get(award_key, 0) > 0]
        if winners:
            award_lines.append(f"- {label}: {', '.join(winners)}")

    # Notable moments
    notable: list[str] = []
    for entry in state.log:
        for pattern in _NOTABLE_PATTERNS:
            if pattern in entry:
                notable.append(f"- {entry}")
                break
    # Keep last 10 if there are many
    if len(notable) > 10:
        notable = notable[-10:]

    # Proof
    proof_line = "No proof generated."
    anchor_line = ""
    pdir = proofs_dir(game_id)
    pdir.mkdir(parents=True, exist_ok=True)
    proofs = sorted(pdir.glob("*.proof.json"))
    if proofs:
        latest = json.loads(proofs[-1].read_text(encoding="utf-8"))
        proof_line = f"`{latest['envelope_hash']}`"

        anchor_file = anchors_file(game_id)
        if anchor_file.exists():
            # Stage 7-B amend: read via the schema-version-tolerant helper
            # so this surface picks up both the v0 bare-dict and v1 wrapped
            # forms without diverging from `_record_anchor`'s write shape.
            anchors_map = _read_anchors_entries(anchor_file)
            tx = anchors_map.get(str(latest["round"]))
            if tx:
                from sov_transport.xrpl import XRPLTransport

                url = XRPLTransport(network=_resolve_network(None)).explorer_tx_url(tx)
                anchor_line = f" | [XRPL TX]({url})"

    # Build markdown output (plain text, no Rich)
    lines = [
        "## Sovereignty Play Report",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Version | {SOV_VERSION} |",
        f"| Tier | {tier} |",
        f"| Recipe | {recipe_used} |",
        f"| Seed | {seed_str} |",
        f"| Players | {player_count} |",
        f"| Rounds | {rnd} |",
        f"| Winner | {winner} |",
        "",
    ]

    if award_lines:
        lines.append("### Awards")
        lines.extend(award_lines)
        lines.append("")

    if notable:
        lines.append("### Notable moments")
        lines.extend(notable)
        lines.append("")

    lines.append("### Proof")
    lines.append(f"{proof_line}{anchor_line}")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by `sov feedback` v{SOV_VERSION}*")

    output = "\n".join(lines)
    console.print(output, highlight=False)


# ---------------------------------------------------------------------------
# v2.1 daemon Typer sub-app (per docs/v2.1-daemon-ipc.md §13)
# ---------------------------------------------------------------------------
#
# `sov daemon`           foreground HTTP server — blocks on SIGINT
# `sov daemon start`     detached background server (writes .sov/daemon.json)
# `sov daemon stop`      stop running daemon for active project root
# `sov daemon status`    report running / stale / none
#
# The daemon package itself (`sov_daemon`) lives behind the optional
# `[daemon]` extra and is owned by the daemon-domain agent in this wave.
# Imports are deferred until each subcommand actually needs them so the
# CLI loads cleanly on stripped installs that didn't pip-install the extra.

daemon_app = typer.Typer(
    name="daemon",
    help=(
        "Local HTTP/JSON daemon for Tauri shell + audit viewer (v2.1). "
        "With no subcommand, runs the server in the foreground; "
        "use `start` / `stop` / `status` for the detached lifecycle."
    ),
    invoke_without_command=True,
    no_args_is_help=False,
)


def _import_daemon_api() -> Any:
    """Import the daemon's public API or fail with an actionable hint.

    The daemon module isn't installed by default — `pip install
    'sovereignty-game[daemon]'` opts in. ``ImportError`` here is a missing
    extra, not a programming error, so we render a structured CLI message.

    Uses ``importlib`` so the typecheck / runtime split between the cli and
    daemon-domain agents stays clean — the CLI does not hard-import any
    sov_daemon symbol at module load time.
    """
    import importlib

    try:
        return importlib.import_module("sov_daemon")
    except ImportError as exc:
        _fail(daemon_not_installed_error(str(exc)))


@daemon_app.callback()
def _daemon_root(
    ctx: typer.Context,
    readonly: Annotated[
        bool,
        typer.Option("--readonly", help="Run without seed; anchor endpoints disabled."),
    ] = False,
    network: Annotated[
        str | None,
        typer.Option(
            "--network",
            help=(
                "XRPL network: testnet, mainnet, or devnet. "
                "Per-invocation override (precedence #1)."
            ),
        ),
    ] = None,
    seed_env: Annotated[
        str,
        typer.Option("--seed-env", help="Env var containing wallet seed."),
    ] = "XRPL_SEED",
    signer_file: Annotated[
        Path | None,
        typer.Option("--signer-file", help="File containing wallet seed."),
    ] = None,
) -> None:
    """Run the local daemon in the foreground (test/dev mode).

    With a subcommand (`start` / `stop` / `status`), this callback only
    parses the global daemon options and dispatches. Without a subcommand,
    runs uvicorn in the current process and blocks until SIGINT.
    """
    if ctx.invoked_subcommand is not None:
        # Subcommand path — let the dedicated handlers do the work.
        return
    daemon_mod = _import_daemon_api()
    resolved_network = _resolve_network(network)
    daemon_mod.run_foreground(
        network=resolved_network,
        readonly=readonly,
        seed_env=seed_env,
        signer_file=signer_file,
    )


@daemon_app.command("start")
def daemon_start(
    readonly: Annotated[
        bool,
        typer.Option("--readonly", help="Run without seed; anchor endpoints disabled."),
    ] = False,
    network: Annotated[
        str | None,
        typer.Option(
            "--network",
            help=(
                "XRPL network: testnet, mainnet, or devnet. "
                "Per-invocation override (precedence #1)."
            ),
        ),
    ] = None,
    seed_env: Annotated[
        str,
        typer.Option("--seed-env", help="Env var containing wallet seed."),
    ] = "XRPL_SEED",
    signer_file: Annotated[
        Path | None,
        typer.Option("--signer-file", help="File containing wallet seed."),
    ] = None,
) -> None:
    """Start the daemon as a detached background process.

    Writes ``.sov/daemon.json`` (port + bearer token + pid) and returns
    immediately. Subsequent ``sov daemon status`` / ``sov daemon stop``
    operate on the recorded pid.
    """
    daemon_mod = _import_daemon_api()
    resolved_network = _resolve_network(network)
    info = daemon_mod.start_daemon(
        network=resolved_network,
        readonly=readonly,
        seed_env=seed_env,
        signer_file=signer_file,
    )
    # `info` is the daemon-side handle exposing port / pid / token plus the
    # network + readonly echo. We accept attribute or dict shape so a
    # daemon-side schema tweak doesn't immediately break the CLI.
    port = _daemon_field(info, "port")
    pid = _daemon_field(info, "pid")
    token = _daemon_field(info, "token")
    panel_lines = [
        f"port:    {port}",
        f"pid:     {pid}",
        f"network: {resolved_network}",
        f"readonly: {'true' if readonly else 'false'}",
        f"token:   {token}",
    ]
    console.print(
        Panel(
            "\n".join(panel_lines),
            title="sov daemon started",
            border_style="green",
        )
    )
    console.print(
        "  [dim]Connection details persist in `.sov/daemon.json`. "
        "Stop with `sov daemon stop`.[/dim]"
    )


@daemon_app.command("stop")
def daemon_stop() -> None:
    """Stop the running daemon for the current project root."""
    daemon_mod = _import_daemon_api()
    console.print("  Stopping daemon...")
    try:
        result = daemon_mod.stop_daemon()
    except FileNotFoundError:
        _fail(daemon_not_running_error())
    except Exception as exc:  # noqa: BLE001
        _fail(daemon_stop_failed_error(str(exc)))
    # Most daemon impls return None on success. Tolerate either shape.
    pid = _daemon_field(result, "pid", default=None) if result is not None else None
    if pid is not None:
        console.print(f"  [green]Daemon stopped (pid {pid}).[/green]")
    else:
        console.print("  [green]Daemon stopped.[/green]")


@daemon_app.command("status")
def daemon_status_cmd(
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON to stdout."),
    ] = False,
) -> None:
    """Report whether a daemon is running, stale, or absent."""
    daemon_mod = _import_daemon_api()
    status = daemon_mod.daemon_status()
    state_val = _daemon_field(status, "state", default="none")

    if json_out:
        # Mirror the `sov doctor --json` envelope shape from
        # docs/cli-json-output.md (timestamp / command / status / fields[]).
        # The per-field "status" axis is local-evidence-derived: a running
        # daemon is "ok"; stale recovery state is "warn"; absent is "ok"
        # (not a failure — daemon is opt-in).
        if state_val == "running":
            field_status = _JSON_OUTPUT_OK
            overall = _JSON_OUTPUT_OK
            state_msg = "Daemon process is alive."
        elif state_val == "stale":
            field_status = _JSON_OUTPUT_WARN
            overall = _JSON_OUTPUT_WARN
            state_msg = "Recorded daemon pid is dead — `sov daemon start` auto-cleans + proceeds."
        else:
            field_status = _JSON_OUTPUT_OK
            overall = _JSON_OUTPUT_OK
            state_msg = "No daemon recorded for this project root."
        fields: list[dict[str, Any]] = [
            {
                "name": "state",
                "status": field_status,
                "value": state_val,
                "message": state_msg,
            },
        ]
        for attr in ("port", "pid", "network", "readonly", "started_iso"):
            val = _daemon_field(status, attr, default=None)
            if val is None:
                continue
            fields.append(
                {
                    "name": attr,
                    "status": _JSON_OUTPUT_OK,
                    "value": val,
                }
            )
        payload = {
            "timestamp": _json_status(),
            "command": "daemon status",
            "status": overall,
            "fields": fields,
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    if state_val == "running":
        port = _daemon_field(status, "port", default="?")
        pid = _daemon_field(status, "pid", default="?")
        network = _daemon_field(status, "network", default="?")
        readonly = _daemon_field(status, "readonly", default=False)
        started = _daemon_field(status, "started_iso", default="?")
        rows = [
            ("state", "running"),
            ("port", str(port)),
            ("pid", str(pid)),
            ("network", str(network)),
            ("readonly", "true" if readonly else "false"),
            ("started_iso", str(started)),
        ]
        table = Table(title="sov daemon status", show_header=False)
        table.add_column("field", style="dim")
        table.add_column("value")
        for k, v in rows:
            table.add_row(k, v)
        console.print(table)
    elif state_val == "stale":
        pid = _daemon_field(status, "pid", default="?")
        console.print(
            f"  [yellow]daemon: stale[/yellow] (last pid {pid} — recorded process is dead)"
        )
        console.print(
            "  [dim]Run `sov daemon start` to start a fresh one "
            "(auto-cleans the stale entry).[/dim]"
        )
    else:
        console.print("  [dim]daemon: none[/dim]")
        console.print("  [dim]Start one with `sov daemon start`.[/dim]")


def _daemon_field(obj: Any, name: str, *, default: Any = "?") -> Any:
    """Pull ``name`` off either an attribute-style or mapping-style object.

    The daemon-side public API is owned by the daemon-domain agent in this
    wave. Tolerating both shapes here keeps the CLI/daemon contract tight at
    the call sites (positional args + named return field) without locking
    the return type to a specific dataclass-vs-dict choice.
    """
    if obj is None:
        return default
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


app.add_typer(daemon_app, name="daemon")


if __name__ == "__main__":
    app()

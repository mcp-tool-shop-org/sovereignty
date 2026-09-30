"""Coverage for the operator-facing CLI commands and load helpers.

Owns: the ``main`` callback + logging bootstrap, the active-game / load-game
helpers, ``doctor`` (and every ``_doctor_check_*`` helper), ``self-check``,
``support-bundle``, ``verify``, ``anchor``, ``wallet``, the ``daemon`` sub-app
and ``_resolve_version``.

Everything is offline: the XRPL transport and faucet are replaced at the
``sov_transport.xrpl`` import boundary, the OS keychain is never touched, and
the daemon lifecycle API is monkeypatched so no daemon is ever spawned.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json
import logging
import sys
import tempfile
import tomllib
import warnings
import zipfile
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

import sov_cli.main as cli_main
from sov_cli.main import app
from sov_engine.io_utils import (
    GameSummary,
    add_pending_anchor,
    anchors_file,
    get_active_game_id,
    list_saved_games,
    pending_anchors_path,
    proofs_dir,
    read_pending_anchors,
    rng_seed_file,
    state_file,
)
from sov_engine.rules.campfire import new_game
from sov_transport.base import ChainLookupResult
from sov_transport.xrpl import MainnetFaucetError, XRPLNetwork

runner = CliRunner()

_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_FINAL = "f" * 64
_SEED = "sEdTESTSEEDXXXXXXXXXXXXXXXX"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flat(text: str) -> str:
    """Collapse whitespace so Rich's 80-column wrapping can't split a match."""
    return " ".join(text.split())


@pytest.fixture
def cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fresh project root with the env vars the CLI reads scrubbed."""
    monkeypatch.chdir(tmp_path)
    for var in ("XRPL_SEED", "SOV_XRPL_NETWORK", "SOV_TAURI_SHELL"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _new_game(seed: int = 42, *extra: str) -> str:
    result = runner.invoke(app, ["new", "-s", str(seed), "-p", "Alice", "-p", "Bob", *extra])
    assert result.exit_code == 0, result.output
    return f"s{seed}"


def _rewrite_state(game_id: str, **changes: Any) -> None:
    sf = state_file(game_id)
    data = json.loads(sf.read_text(encoding="utf-8"))
    data.update(changes)
    sf.write_text(json.dumps(data), encoding="utf-8")


def _write_pending(game_id: str, rows: dict[str, str]) -> None:
    """Write pending-anchors.json with explicit ``added_iso`` per round key."""
    doc = {
        "schema_version": 1,
        "entries": {k: {"envelope_hash": _HASH_A, "added_iso": ts} for k, ts in rows.items()},
    }
    path = pending_anchors_path(game_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _iso_ago(**delta: float) -> str:
    when = dt.datetime.now(dt.UTC) - dt.timedelta(**delta)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _doctor_payload() -> dict[str, Any]:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0, result.output
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


def _field(payload: dict[str, Any], needle: str) -> dict[str, Any]:
    matches = [f for f in payload["fields"] if needle in f["name"]]
    assert matches, f"no field containing {needle!r} in {[f['name'] for f in payload['fields']]}"
    return matches[0]


def _has_field(payload: dict[str, Any], needle: str) -> bool:
    return any(needle in f["name"] for f in payload["fields"])


def _block_sov_daemon_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``importlib.import_module('sov_daemon')`` raise ImportError only."""
    real = importlib.import_module

    def fake(name: str, package: str | None = None) -> Any:
        if name == "sov_daemon":
            raise ImportError("No module named 'sov_daemon'")
        return real(name, package)

    monkeypatch.setattr(importlib, "import_module", fake)


# ---------------------------------------------------------------------------
# main callback + logging bootstrap
# ---------------------------------------------------------------------------


def test_version_flag_prints_resolved_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"sovereignty {cli_main._resolve_version()}"


def test_configure_default_logging_is_idempotent_and_honours_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = ("sov_cli", "sov_engine")
    saved_levels = {n: logging.getLogger(n).level for n in names}
    try:
        monkeypatch.setenv("SOV_LOG_LEVEL", "debug")
        cli_main._configure_default_logging()
        cli_main._configure_default_logging()  # second call takes the `continue` path
        for n in names:
            lg = logging.getLogger(n)
            assert lg.level == logging.DEBUG
            defaults = [h for h in lg.handlers if getattr(h, "_sov_default", False)]
            assert len(defaults) == 1, "handler must not be re-added"
            assert lg.propagate is False

        monkeypatch.setenv("SOV_LOG_LEVEL", "not-a-level")
        cli_main._configure_default_logging()
        assert logging.getLogger("sov_cli").level == logging.WARNING
    finally:
        for n, level in saved_levels.items():
            logging.getLogger(n).setLevel(level)


def test_configure_default_logging_installs_handler_when_missing() -> None:
    lg = logging.getLogger("sov_engine")
    original = list(lg.handlers)
    level = lg.level
    try:
        for h in original:
            lg.removeHandler(h)
        cli_main._configure_default_logging()
        added = [h for h in lg.handlers if getattr(h, "_sov_default", False)]
        assert len(added) == 1
        assert added[0].formatter is not None
        assert "%(levelname)s" in (added[0].formatter._fmt or "")
    finally:
        for h in list(lg.handlers):
            lg.removeHandler(h)
        for h in original:
            lg.addHandler(h)
        lg.setLevel(level)


# ---------------------------------------------------------------------------
# _resolve_active_game_id
# ---------------------------------------------------------------------------


def test_resolve_active_returns_migrated_v1_game(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_main, "migrate_v1_layout", lambda: "s7")
    assert cli_main._resolve_active_game_id() == "s7"


def test_resolve_active_rejects_poisoned_pointer(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pointer that slips past the reader is re-validated and refused."""
    monkeypatch.setattr(cli_main, "get_active_game_id", lambda: "../evil")
    with pytest.raises(typer.Exit) as exc:
        cli_main._resolve_active_game_id()
    assert exc.value.exit_code == 1
    out = _flat(capsys.readouterr().out)
    assert "No active game." in out
    assert "sov games" in out


def test_resolve_active_adopts_only_saved_game(cwd: Path) -> None:
    gid = _new_game()
    (cwd / ".sov" / "active-game").unlink()
    assert cli_main._resolve_active_game_id() == gid
    assert get_active_game_id() == gid


def test_resolve_active_refuses_when_ambiguous(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _new_game(42)
    _new_game(43)
    (cwd / ".sov" / "active-game").unlink()
    with pytest.raises(typer.Exit):
        cli_main._resolve_active_game_id()
    assert "No active game." in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Snapshot / restore helpers
# ---------------------------------------------------------------------------


def test_disk_snapshot_records_rng_and_decks() -> None:
    state, _ = new_game(42, ["Alice", "Bob"])
    rng = cli_main.GameRng(42)
    snap = cli_main._disk_snapshot(state, rng)
    assert snap["rng_state"] == rng.getstate()
    assert snap["event_deck"]["draw"] == [c.id for c in state.event_deck.draw_pile]
    assert snap["deal_deck"]["discard"] == [c.id for c in state.deal_deck.discard_pile]


@pytest.mark.parametrize(
    "raw",
    [
        "not-a-dict",
        None,
        {"draw": "AB", "discard": []},
        {"draw": [], "discard": "AB"},
    ],
)
def test_deck_from_ids_rejects_malformed_shapes(raw: object) -> None:
    assert cli_main._deck_from_ids(raw, {}) is None


def test_deck_from_ids_drops_unknown_and_non_string_ids() -> None:
    state, _ = new_game(42, ["Alice", "Bob"])
    catalog = {c.id: c for c in state.event_deck.draw_pile}
    known = next(iter(catalog))
    deck = cli_main._deck_from_ids({"draw": [known, "nope", 5], "discard": [known]}, catalog)
    assert deck is not None
    assert [c.id for c in deck.draw_pile] == [known]
    assert [c.id for c in deck.discard_pile] == [known]


def test_restore_decks_skips_saves_that_predate_deck_fields() -> None:
    state, _ = new_game(42, ["Alice", "Bob"])
    before = [c.id for c in state.event_deck.draw_pile]
    cli_main._restore_decks(state, {})
    assert [c.id for c in state.event_deck.draw_pile] == before


def test_restore_decks_leaves_deck_alone_when_shape_is_bad() -> None:
    state, _ = new_game(42, ["Alice", "Bob"])
    before = [c.id for c in state.event_deck.draw_pile]
    cli_main._restore_decks(state, {"event_deck": {"draw": "bad"}, "deal_deck": {}})
    assert [c.id for c in state.event_deck.draw_pile] == before


def test_restore_vouchers_and_deals_shares_objects_and_skips_junk() -> None:
    state, _ = new_game(42, ["Alice", "Bob"])
    voucher = {
        "voucher_id": "v1",
        "template_id": "t",
        "issuer": "Alice",
        "holder": "Bob",
        "face_value": 2,
        "deadline_round": 3,
        "penalty_rep": 1,
    }
    deal = {
        "deal_id": "d1",
        "template_id": "dt",
        "player": "Alice",
        "deadline_round": 4,
        "reward_coins": 2,
        "reward_rep": 1,
        "penalty_rep": 1,
    }
    players_data = [
        {
            "vouchers_issued": [voucher, "junk", {"voucher_id": 7}],
            "vouchers_held": [],
            "active_deals": [deal, "junk", {"deal_id": 5}],
        },
        {"vouchers_issued": [], "vouchers_held": [voucher], "active_deals": [deal]},
    ]
    cli_main._restore_vouchers_and_deals(state, players_data)
    alice, bob = state.players
    assert len(alice.vouchers_issued) == 1
    assert alice.vouchers_issued[0] is bob.vouchers_held[0]
    assert alice.vouchers_issued[0].face_value == 2
    assert alice.active_deals[0] is bob.active_deals[0]
    assert alice.active_deals[0].reward_coins == 2
    assert len(alice.active_deals) == 1


def test_restore_vouchers_and_deals_tolerates_wrong_container_types() -> None:
    state, _ = new_game(42, ["Alice", "Bob"])
    cli_main._restore_vouchers_and_deals(
        state,
        ["not-a-dict", {"vouchers_issued": "x", "vouchers_held": 5, "active_deals": None}],
    )
    for p in state.players:
        assert p.vouchers_issued == []
        assert p.vouchers_held == []
        assert p.active_deals == []


# ---------------------------------------------------------------------------
# _resolve_network
# ---------------------------------------------------------------------------


def test_resolve_network_precedence_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOV_XRPL_NETWORK", raising=False)
    assert cli_main._resolve_network(None) is XRPLNetwork.TESTNET
    monkeypatch.setenv("SOV_XRPL_NETWORK", "devnet")
    assert cli_main._resolve_network(None) is XRPLNetwork.DEVNET
    assert cli_main._resolve_network("mainnet") is XRPLNetwork.MAINNET


def test_resolve_network_rejects_unknown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SOV_XRPL_NETWORK", raising=False)
    with pytest.raises(typer.Exit):
        cli_main._resolve_network("moonnet")
    assert "'moonnet' is not a valid XRPL network." in _flat(capsys.readouterr().out)


# ---------------------------------------------------------------------------
# _commit_anchor_chunks
# ---------------------------------------------------------------------------


def _batch_entries(game_id: str, keys: list[str]) -> list[Any]:
    return [
        {
            "round_key": k,
            "ruleset": "campfire_v1",
            "game_id": game_id,
            "envelope_hash": _HASH_A,
        }
        for k in keys
    ]


def test_commit_anchor_chunks_rejects_empty_txid_list(cwd: Path) -> None:
    gid = _new_game()
    add_pending_anchor(gid, "1", _HASH_A)
    transport = MagicMock()
    transport.anchor_batch.return_value = []
    with pytest.raises(RuntimeError, match="returned no txids"):
        cli_main._commit_anchor_chunks(
            transport, game_id=gid, rounds=_batch_entries(gid, ["1"]), seed=_SEED
        )
    assert set(read_pending_anchors(gid)) == {"1"}


def test_commit_anchor_chunks_keeps_succeeded_prefix_on_later_failure(cwd: Path) -> None:
    gid = _new_game()
    keys = [str(i) for i in range(1, 10)]
    for k in keys:
        add_pending_anchor(gid, k, _HASH_A)
    transport = MagicMock()
    transport.anchor_batch.side_effect = [["TX-FIRST"], RuntimeError("net down")]
    with pytest.raises(RuntimeError, match="net down"):
        cli_main._commit_anchor_chunks(
            transport, game_id=gid, rounds=_batch_entries(gid, keys), seed=_SEED
        )
    recorded = cli_main._read_anchors_entries(anchors_file(gid))
    assert recorded == {str(i): "TX-FIRST" for i in range(1, 9)}
    assert set(read_pending_anchors(gid)) == {"9"}


def test_commit_anchor_chunks_returns_one_txid_per_chunk(cwd: Path) -> None:
    gid = _new_game()
    keys = [str(i) for i in range(1, 10)]
    for k in keys:
        add_pending_anchor(gid, k, _HASH_A)
    transport = MagicMock()
    transport.anchor_batch.side_effect = [["TX-A"], ["TX-B"]]
    txids = cli_main._commit_anchor_chunks(
        transport, game_id=gid, rounds=_batch_entries(gid, keys), seed=_SEED
    )
    assert txids == ["TX-A", "TX-B"]
    assert read_pending_anchors(gid) == {}


# ---------------------------------------------------------------------------
# _load_game / _load_game_inner
# ---------------------------------------------------------------------------


def test_load_game_returns_none_when_nothing_saved(cwd: Path) -> None:
    assert cli_main._load_game() is None


def test_load_game_returns_none_when_active_game_lost_its_rng_file(cwd: Path) -> None:
    gid = _new_game()
    rng_seed_file(gid).unlink()
    assert cli_main._load_game() is None


@pytest.mark.parametrize(
    ("tier", "ruleset"),
    [
        ("campfire", "campfire_v1"),
        ("market-day", "market_day_v1"),
        ("town-hall", "town_hall_v1"),
        ("treaty-table", "treaty_table_v1"),
    ],
)
def test_load_game_rebuilds_each_tier(cwd: Path, tier: str, ruleset: str) -> None:
    _new_game(42, "--tier", tier)
    loaded = cli_main._load_game()
    assert loaded is not None
    state, rng = loaded
    assert state.config.ruleset == ruleset
    assert [p.name for p in state.players] == ["Alice", "Bob"]
    assert rng is cli_main._loaded_rng


def test_load_game_reports_schema_mismatch(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    gid = _new_game()
    _rewrite_state(gid, schema_version=99)
    with pytest.raises(typer.Exit) as exc:
        cli_main._load_game()
    assert exc.value.exit_code == 1
    out = _flat(capsys.readouterr().out)
    assert "schema_version=99" in out
    assert "not supported" in out


def test_load_game_reports_missing_field_as_corrupt(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gid = _new_game()
    sf = state_file(gid)
    sf.write_text(
        json.dumps({"schema_version": 1, "config": {}, "players": [{"name": "A"}]}),
        encoding="utf-8",
    )
    with pytest.raises(typer.Exit) as exc:
        cli_main._load_game()
    assert exc.value.exit_code == 1
    out = _flat(capsys.readouterr().out)
    assert "Saved game state is unreadable." in out
    assert "KeyError" in out


def test_load_game_reports_bad_rng_seed_as_corrupt(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gid = _new_game()
    rng_seed_file(gid).write_text("not-an-int", encoding="utf-8")
    with pytest.raises(typer.Exit):
        cli_main._load_game()
    out = _flat(capsys.readouterr().out)
    assert "Saved game state is unreadable." in out
    assert "ValueError" in out


# ---------------------------------------------------------------------------
# JSON envelope
# ---------------------------------------------------------------------------


def test_checks_to_json_payload_rolls_up_worst_status() -> None:
    fail = cli_main._checks_to_json_payload(
        "x", [("ok", "a", ""), ("warn", "b", ""), ("fail", "c", "")]
    )
    assert fail["status"] == "fail"
    warn = cli_main._checks_to_json_payload("x", [("ok", "a", ""), ("warn", "b", "")])
    assert warn["status"] == "warn"
    ok = cli_main._checks_to_json_payload("x", [("info", "a", "")], status_map={"info": "ok"})
    assert ok["status"] == "ok"
    aliased = cli_main._checks_to_json_payload(
        "x", [("info", "a", "")], status_map={"info": "warn"}
    )
    assert aliased["status"] == "warn"
    assert [f["name"] for f in fail["fields"]] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# doctor: game / season / wallet / proofs / pending
# ---------------------------------------------------------------------------


def test_doctor_empty_directory_reports_info_only(cwd: Path) -> None:
    payload = _doctor_payload()
    assert payload["command"] == "doctor"
    assert payload["status"] == "ok"
    assert _field(payload, "No game directory yet")["message"] == "Run `sov new -p Alice -p Bob`."
    assert _has_field(payload, "No active game")
    assert _has_field(payload, "No season file yet")
    assert _has_field(payload, "No wallet set up")


def test_doctor_completed_game_points_at_game_end(cwd: Path) -> None:
    gid = _new_game()
    _rewrite_state(gid, game_over=True)
    payload = _doctor_payload()
    field = _field(payload, "Game complete: Campfire (Alice, Bob)")
    assert field["status"] == "ok"
    assert field["message"] == "Run `sov game-end` to wrap up."


def test_doctor_reports_unloadable_active_game(cwd: Path) -> None:
    gid = _new_game()
    rng_seed_file(gid).unlink()
    payload = _doctor_payload()
    field = _field(payload, "Game state exists but can't load")
    assert field["status"] == "warn"
    assert payload["status"] == "warn"


def test_doctor_single_save_without_pointer_recommends_resume(cwd: Path) -> None:
    gid = _new_game()
    (cwd / ".sov" / "active-game").unlink()
    payload = _doctor_payload()
    field = _field(payload, "1 saved game (s42); no active-game pointer")
    assert field["message"] == f"Run `sov resume {gid}`."
    assert not _has_field(payload, "Multi-save layout")


def test_doctor_many_saves_without_pointer_recommends_games(cwd: Path) -> None:
    _new_game(42)
    _new_game(43)
    (cwd / ".sov" / "active-game").unlink()
    payload = _doctor_payload()
    field = _field(payload, "2 saved games; no active-game pointer")
    assert "sov games" in field["message"]
    # The pointer-less state is reported once, by the branch above.
    assert not _has_field(payload, "Multi-save layout")


def test_doctor_orphaned_pointer_warns_twice_with_recovery(cwd: Path) -> None:
    (cwd / ".sov").mkdir()
    (cwd / ".sov" / "active-game").write_text("s99", encoding="utf-8")
    payload = _doctor_payload()
    assert _field(payload, "pointer s99 but state.json is missing")["status"] == "warn"
    orphan = _field(payload, "Active-game pointer s99 but target game is missing")
    assert orphan["status"] == "warn"
    assert "sov resume" in orphan["message"]


def test_doctor_multi_save_layout_ok_when_pointer_resolves(cwd: Path) -> None:
    gid = _new_game()
    payload = _doctor_payload()
    assert _field(payload, "Multi-save layout valid")["name"].endswith(f"(active: {gid})")


@pytest.mark.parametrize(
    ("season", "expected"),
    [
        ({"games": [{}, {}], "standings": {}}, "Season active (2 games played)"),
        ({"games": [{}], "standings": {}}, "Season active (1 game played)"),
        ({"schema_version": 1, "season": {"games": [], "standings": {}}}, "(0 games played)"),
    ],
)
def test_doctor_reads_bare_and_wrapped_season_files(
    cwd: Path, season: dict[str, Any], expected: str
) -> None:
    (cwd / ".sov").mkdir()
    (cwd / ".sov" / "season.json").write_text(json.dumps(season), encoding="utf-8")
    payload = _doctor_payload()
    assert expected in _field(payload, "Season active")["name"]
    assert _field(payload, "Season active")["status"] == "ok"


def test_doctor_warns_when_season_games_is_not_a_list(cwd: Path) -> None:
    (cwd / ".sov").mkdir()
    (cwd / ".sov" / "season.json").write_text(json.dumps({"games": "nope"}), encoding="utf-8")
    payload = _doctor_payload()
    field = _field(payload, "Season file exists but can't parse")
    assert field["status"] == "warn"
    assert field["message"] == "Delete `.sov/season.json` to start fresh."


@pytest.mark.parametrize(
    "raw",
    [
        "{not json",  # unparseable
        "[]",  # wrong top-level type
        '{"schema_version": 1, "season": []}',  # wrapped, season not an object
        '{"games": {}, "standings": {}}',  # games not a list
        '{"standings": {}}',  # games missing
    ],
)
def test_doctor_warns_when_season_json_is_malformed(cwd: Path, raw: str) -> None:
    # Regression: the tolerant reader turned a corrupt file into an empty
    # season, so doctor said "Season active (0 games played)" (fixed 2.3.4).
    (cwd / ".sov").mkdir()
    (cwd / ".sov" / "season.json").write_text(raw, encoding="utf-8")
    payload = _doctor_payload()
    assert _has_field(payload, "Season file exists but can't parse")
    assert not _has_field(payload, "Season active")


@pytest.mark.parametrize(
    "raw",
    [
        '{"games": [], "standings": {}}',
        '{"schema_version": 1, "season": {"games": [{"id": "s1"}], "standings": {}}}',
    ],
)
def test_doctor_accepts_valid_season_shapes(cwd: Path, raw: str) -> None:
    (cwd / ".sov").mkdir()
    (cwd / ".sov" / "season.json").write_text(raw, encoding="utf-8")
    payload = _doctor_payload()
    assert _has_field(payload, "Season active")
    assert not _has_field(payload, "Season file exists but can't parse")


def test_doctor_detects_wallet_file(cwd: Path) -> None:
    (cwd / ".sov").mkdir()
    (cwd / ".sov" / "wallet_seed.txt").write_text(_SEED, encoding="utf-8")
    payload = _doctor_payload()
    assert _field(payload, "Wallet seed found at .sov/wallet_seed.txt")["status"] == "ok"
    assert _SEED not in json.dumps(payload)


def test_doctor_detects_wallet_env_var(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XRPL_SEED", _SEED)
    payload = _doctor_payload()
    assert _field(payload, "Wallet configured via XRPL_SEED env var")["status"] == "ok"
    assert _SEED not in json.dumps(payload)


@pytest.mark.parametrize(
    ("count", "label"), [(1, "1 proof file saved"), (3, "3 proof files saved")]
)
def test_doctor_counts_proof_files(cwd: Path, count: int, label: str) -> None:
    gid = _new_game()
    pdir = proofs_dir(gid)
    pdir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (pdir / f"round_{i:02d}.proof.json").write_text("{}", encoding="utf-8")
    (pdir / "anchors.json").write_text("{}", encoding="utf-8")  # not a proof
    assert _has_field(_doctor_payload(), label)


def test_doctor_fresh_pending_anchor_is_ok(cwd: Path) -> None:
    gid = _new_game()
    add_pending_anchor(gid, "1", _HASH_A)
    field = _field(_doctor_payload(), "pending anchor")
    assert field["name"] == "1 pending anchor (fresh)"
    assert field["status"] == "ok"


@pytest.mark.parametrize(
    ("age", "label"),
    [
        ({"hours": 5}, "2 pending anchors, oldest 5 hours old"),
        ({"minutes": 90}, "2 pending anchors, oldest 1.5 hour old"),
    ],
)
def test_doctor_old_pending_anchors_warn_with_age(
    cwd: Path, age: dict[str, float], label: str
) -> None:
    gid = _new_game()
    _write_pending(gid, {"1": _iso_ago(**age), "2": _iso_ago(minutes=1)})
    payload = _doctor_payload()
    field = _field(payload, "pending anchors")
    assert field["name"] == label
    assert field["status"] == "warn"
    assert field["message"] == "Run `sov anchor` to flush pending entries."
    assert payload["status"] == "warn"


def test_doctor_pending_anchor_timestamp_forms(cwd: Path) -> None:
    """tz-naive and ``+00:00`` timestamps parse; garbage rows are skipped."""
    gid = _new_game()
    recent = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=2)
    _write_pending(
        gid,
        {
            "1": recent.replace(tzinfo=None).isoformat(timespec="seconds"),
            "2": recent.isoformat(timespec="seconds"),
            "3": "not-a-date",
        },
    )
    field = _field(_doctor_payload(), "pending anchors")
    assert field["name"] == "3 pending anchors (fresh)"


def test_doctor_pending_anchors_with_only_garbage_timestamps(cwd: Path) -> None:
    gid = _new_game()
    _write_pending(gid, {"1": "yesterday-ish"})
    field = _field(_doctor_payload(), "pending anchor")
    assert field["name"] == "1 pending anchor (timestamps unparseable)"
    assert field["status"] == "ok"
    assert field["message"] == "Run `sov anchor` to flush pending entries."


def test_doctor_survives_a_pending_row_it_cannot_read(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _new_game()
    monkeypatch.setattr(
        cli_main,
        "read_pending_anchors",
        lambda gid, heal=False: {"1": {"envelope_hash": _HASH_A}},
    )
    payload = _doctor_payload()  # exit code 0 asserted inside
    assert not _has_field(payload, "pending anchor")
    assert _has_field(payload, "Multi-save layout valid")


def test_doctor_human_output_has_icons_and_summary(cwd: Path) -> None:
    gid = _new_game()
    _write_pending(gid, {"1": _iso_ago(hours=5)})
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    out = _flat(result.output)
    assert "OK Ready to play Campfire" in out
    assert "WARN 1 pending anchor, oldest 5 hours old" in out
    assert "Summary:" in out
    assert "1 warn" in out


# ---------------------------------------------------------------------------
# doctor: daemon / extra coherence / schema currency
# ---------------------------------------------------------------------------


def test_doctor_reports_unreadable_daemon_state_as_fail(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> Any:
        raise ValueError("bad handshake json")

    monkeypatch.setattr(cli_main, "_query_daemon_status", boom)
    payload = _doctor_payload()
    field = _field(payload, "Daemon state file unreadable")
    assert field["status"] == "fail"
    assert "ValueError: bad handshake json" in field["message"]
    assert payload["status"] == "fail"


def test_doctor_stays_silent_when_daemon_extra_is_missing(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_main, "_query_daemon_status", lambda: None)
    assert not _has_field(_doctor_payload(), "Daemon")


def test_doctor_reports_stale_daemon(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sov_daemon

    monkeypatch.setattr(sov_daemon, "daemon_status", lambda: sov_daemon.DaemonStatus.STALE)
    monkeypatch.setattr(sov_daemon, "daemon_info", lambda: {"pid": 4242})
    field = _field(_doctor_payload(), "Daemon stale")
    assert field["name"] == "Daemon stale (pid 4242 dead)"
    assert field["status"] == "warn"
    assert "sov daemon start" in field["message"]


def test_doctor_reports_running_daemon_with_unknown_details(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sov_daemon

    monkeypatch.setattr(sov_daemon, "daemon_status", lambda: sov_daemon.DaemonStatus.RUNNING)
    monkeypatch.setattr(sov_daemon, "daemon_info", lambda: None)
    field = _field(_doctor_payload(), "Daemon running")
    assert field["name"] == "Daemon running (port ?, network=?)"


def test_doctor_daemon_silent_when_status_none(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sov_daemon

    monkeypatch.setattr(sov_daemon, "daemon_status", lambda: sov_daemon.DaemonStatus.NONE)
    assert not _has_field(_doctor_payload(), "Daemon")


def test_doctor_warns_when_tauri_shell_lacks_daemon_extra(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SOV_TAURI_SHELL", "1")
    _block_sov_daemon_import(monkeypatch)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    out = _flat(result.output)
    assert "WARN Tauri shell present but [daemon] extra not installed" in out
    assert "pip install 'sovereignty-game[daemon]'" in out


def test_doctor_confirms_tauri_shell_with_daemon_extra(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SOV_TAURI_SHELL", "1")
    result = runner.invoke(app, ["doctor"])
    assert "OK Tauri shell + [daemon] extra both present" in _flat(result.output)


def test_doctor_detects_tauri_shell_from_app_directory(cwd: Path) -> None:
    (cwd / "app").mkdir()
    result = runner.invoke(app, ["doctor"])
    assert "Tauri shell + [daemon] extra both present" in _flat(result.output)


def test_doctor_coherence_silent_for_cli_only_install(cwd: Path) -> None:
    result = runner.invoke(app, ["doctor"])
    assert "Tauri shell" not in result.output


def test_multi_save_check_is_silent_without_pointer() -> None:
    checks: list[tuple[str, str, str]] = []
    summary = GameSummary(
        game_id="s1",
        ruleset="campfire_v1",
        current_round=1,
        max_rounds=5,
        players=("A", "B"),
        last_modified_iso="2026-01-01T00:00:00Z",
    )
    cli_main._doctor_check_multi_save_layout(checks, saved=[summary], active_id=None)
    cli_main._doctor_check_multi_save_layout(checks, saved=[], active_id=None)
    assert checks == []


def test_schema_currency_flags_unsupported_versions_across_files(cwd: Path) -> None:
    _new_game(42)
    _new_game(43)
    _rewrite_state("s43", schema_version=99)
    _write_pending("s42", {})
    pending = pending_anchors_path("s42")
    pending.write_text(json.dumps({"schema_version": 7, "entries": {}}), encoding="utf-8")
    anchors = anchors_file("s42")
    anchors.parent.mkdir(parents=True, exist_ok=True)
    anchors.write_text(json.dumps({"schema_version": 5, "entries": {}}), encoding="utf-8")

    checks: list[tuple[str, str, str]] = []
    cli_main._doctor_check_schema_version_currency(checks, saved=list_saved_games())
    assert len(checks) == 1
    status, message, hint = checks[0]
    assert status == "fail"
    assert "state (s43): v99" in message
    assert "pending-anchors (s42): v7" in message
    assert "anchors (s42): v5" in message
    assert "archive the file and start fresh" in hint


def test_schema_currency_is_silent_on_healthy_and_legacy_files(cwd: Path) -> None:
    gid = _new_game()
    add_pending_anchor(gid, "1", _HASH_A)
    anchors = anchors_file(gid)
    anchors.parent.mkdir(parents=True, exist_ok=True)
    anchors.write_text(json.dumps({"1": "TX"}), encoding="utf-8")  # bare v0 dict
    checks: list[tuple[str, str, str]] = []
    cli_main._doctor_check_schema_version_currency(checks, saved=list_saved_games())
    assert checks == []


def test_schema_currency_skips_unreadable_and_corrupt_files(cwd: Path) -> None:
    gid = _new_game()
    summary = list_saved_games()[0]
    # state.json becomes a directory (OSError on read), the others become
    # invalid JSON. The corrupt-file reporting lives elsewhere in doctor, so
    # none of them may raise or add a duplicate diagnostic here.
    sf = state_file(gid)
    sf.unlink()
    sf.mkdir()
    pending_anchors_path(gid).write_text("{broken", encoding="utf-8")
    anchors = anchors_file(gid)
    anchors.parent.mkdir(parents=True, exist_ok=True)
    anchors.write_text("{broken", encoding="utf-8")
    checks: list[tuple[str, str, str]] = []
    cli_main._doctor_check_schema_version_currency(checks, saved=[summary])
    assert checks == []


def test_schema_currency_skips_corrupt_state_json(cwd: Path) -> None:
    gid = _new_game()
    summary = list_saved_games()[0]
    state_file(gid).write_text("{broken", encoding="utf-8")
    checks: list[tuple[str, str, str]] = []
    cli_main._doctor_check_schema_version_currency(checks, saved=[summary])
    assert checks == []


# ---------------------------------------------------------------------------
# _collect_checks / _print_checks / self-check
# ---------------------------------------------------------------------------


def _by_label(checks: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    return {label: (status, detail) for status, label, detail in checks}


def test_collect_checks_reports_state_directory(cwd: Path) -> None:
    assert _by_label(cli_main._collect_checks())["State directory"][0] == "info"
    _new_game()
    status, detail = _by_label(cli_main._collect_checks())["State directory"]
    assert status == "ok"
    assert "file(s) in .sov" in detail


def test_collect_checks_reports_rich_failure(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("table exploded")

    monkeypatch.setattr(cli_main, "Table", boom)
    assert _by_label(cli_main._collect_checks())["Rich rendering"] == ("fail", "table exploded")


def test_collect_checks_reports_filesystem_failure(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: Any, **_k: Any) -> str:
        raise OSError("disk full")

    monkeypatch.setattr(tempfile, "mkdtemp", boom)
    assert _by_label(cli_main._collect_checks())["Filesystem write"] == ("fail", "disk full")


def test_collect_checks_degrades_missing_dependency_to_info(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_import = __import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "xrpl":
            raise ImportError("no xrpl here")
        return real_import(name, *args, **kwargs)

    # Module-globals shadow builtins, so this only affects the CLI's own
    # ``__import__(mod_name)`` call and not the interpreter's import machinery.
    monkeypatch.setattr(cli_main, "__import__", fake_import, raising=False)
    checks = _by_label(cli_main._collect_checks())
    assert checks["xrpl"] == ("info", "ImportError: no xrpl here")
    assert checks["typer"][0] == "ok"


def test_print_checks_tallies_failures_and_warnings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_main._print_checks([("ok", "A", "fine"), ("warn", "B", "hmm"), ("warn", "C", "hmm")])
    out = _flat(capsys.readouterr().out)
    assert "OK A fine" in out
    assert "WARN B hmm" in out
    assert "2 checks warned." in out
    assert "sov support-bundle" in out

    cli_main._print_checks([("fail", "D", "bad"), ("warn", "E", "hmm")])
    out = _flat(capsys.readouterr().out)
    assert "FAIL D bad" in out
    assert "1 check failed." in out
    assert "issues" in out
    assert "warned" not in out


def test_checks_to_text_uses_word_glyphs() -> None:
    text = cli_main._checks_to_text(
        [("ok", "A", "1"), ("warn", "B", "2"), ("fail", "C", "3"), ("info", "D", "4")]
    )
    assert text.splitlines() == ["  OK  A  1", "  WARN  B  2", "  FAIL  C  3", "  --  D  4"]


def test_self_check_json_shape_and_failure_rollup(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = runner.invoke(app, ["self-check", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "self-check"
    assert payload["status"] == "ok"
    names = [f["name"] for f in payload["fields"]]
    assert names[:2] == ["Version", "Platform"]
    assert {"Rich rendering", "Filesystem write", "State directory"} <= set(names)

    monkeypatch.setattr(tempfile, "mkdtemp", MagicMock(side_effect=OSError("disk full")))
    failing = json.loads(runner.invoke(app, ["self-check", "--json"]).stdout)
    assert failing["status"] == "fail"
    assert _field(failing, "Filesystem write")["value"] == "disk full"


def test_self_check_human_nudges_toward_support_bundle_on_failure(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tempfile, "mkdtemp", MagicMock(side_effect=OSError("disk full")))
    result = runner.invoke(app, ["self-check"])
    assert result.exit_code == 0
    out = _flat(result.output)
    assert "FAIL Filesystem write disk full" in out
    assert "1 check failed." in out


# ---------------------------------------------------------------------------
# support-bundle
# ---------------------------------------------------------------------------


def _bundle(cwd: Path) -> Path:
    bundles = list(cwd.glob("sov-support-*.zip"))
    assert len(bundles) == 1, bundles
    return bundles[0]


def test_support_bundle_without_a_game(cwd: Path) -> None:
    result = runner.invoke(app, ["support-bundle"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "Bundle written:" in out
    with zipfile.ZipFile(_bundle(cwd)) as zf:
        names = set(zf.namelist())
        assert names == {
            "self-check.txt",
            "self-check.json",
            "proof-count.txt",
            "environment.json",
        }
        assert zf.read("proof-count.txt").decode() == "0 proof file(s)"
        env = json.loads(zf.read("environment.json"))
        assert env["tool"] == "sovereignty"
        assert env["version"] == cli_main._resolve_version()


def test_support_bundle_includes_state_listing_and_proof_count(cwd: Path) -> None:
    gid = _new_game()
    runner.invoke(app, ["end-round"])
    result = runner.invoke(app, ["support-bundle"])
    assert result.exit_code == 0, result.output
    with zipfile.ZipFile(_bundle(cwd)) as zf:
        state = json.loads(zf.read("game_state.json"))
        assert state["players"][0]["name"] == "Alice"
        listing = zf.read("state-listing.txt").decode().splitlines()
        assert "active-game" in listing
        assert f"games/{gid}/" in listing
        assert f"games/{gid}/state.json" in listing
        assert zf.read("proof-count.txt").decode() == "1 proof file(s)"
        assert "sEd" not in zf.read("game_state.json").decode()


def test_support_bundle_adopts_single_save_without_pointer(cwd: Path) -> None:
    _new_game()
    (cwd / ".sov" / "active-game").unlink()
    result = runner.invoke(app, ["support-bundle"])
    assert result.exit_code == 0
    with zipfile.ZipFile(_bundle(cwd)) as zf:
        assert "game_state.json" in zf.namelist()


def test_support_bundle_placeholder_for_unreadable_state(cwd: Path) -> None:
    gid = _new_game()
    state_file(gid).write_text("{broken", encoding="utf-8")
    result = runner.invoke(app, ["support-bundle"])
    assert result.exit_code == 0, result.output
    with zipfile.ZipFile(_bundle(cwd)) as zf:
        assert zf.read("game_state.json").decode() == "(could not read)"


def test_support_bundle_json_mode_emits_payload_only(cwd: Path) -> None:
    result = runner.invoke(app, ["support-bundle", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["command"] == "support-bundle"
    assert Path(payload["bundle_path"]) == _bundle(cwd)
    assert "Bundle written" not in result.stdout
    with zipfile.ZipFile(_bundle(cwd)) as zf:
        inner = json.loads(zf.read("self-check.json"))
    assert inner["bundle_path"] == payload["bundle_path"]
    assert inner["status"] == payload["status"]


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def _make_proof(cwd: Path) -> Path:
    gid = _new_game()
    result = runner.invoke(app, ["end-round"])
    assert result.exit_code == 0, result.output
    proofs = sorted(proofs_dir(gid).glob("round_*.proof.json"))
    assert proofs
    return proofs[-1]


def _transport_factory() -> MagicMock:
    transport = MagicMock()
    transport.explorer_tx_url.side_effect = lambda t: f"https://explorer.example/{t}"
    return MagicMock(return_value=transport)


def test_verify_local_only_accepts_a_good_proof(cwd: Path) -> None:
    proof = _make_proof(cwd)
    result = runner.invoke(app, ["verify", str(proof)])
    assert result.exit_code == 0, result.output
    assert "Local proof valid." in result.output
    assert "Anchor verified" not in result.output


def test_verify_rejects_a_modified_proof(cwd: Path) -> None:
    proof = _make_proof(cwd)
    data = json.loads(proof.read_text(encoding="utf-8"))
    data["round"] = 99
    proof.write_text(json.dumps(data), encoding="utf-8")
    result = runner.invoke(app, ["verify", str(proof)])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "Local proof invalid." in out
    assert "Hash mismatch" in out
    assert "edited, corrupted, or truncated" in out


def test_verify_rejects_legacy_v1_proof(cwd: Path) -> None:
    proof = cwd / "old.proof.json"
    proof.write_text(json.dumps({"proof_version": 1}), encoding="utf-8")
    result = runner.invoke(app, ["verify", str(proof)])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "no longer supported" in out
    assert "install sovereignty <2.0.0" in out


def test_verify_tx_found_prints_memo_and_explorer(cwd: Path) -> None:
    proof = _make_proof(cwd)
    expected_hash = json.loads(proof.read_text(encoding="utf-8"))["envelope_hash"]
    factory = _transport_factory()
    transport = factory.return_value
    transport.is_anchored_on_chain.return_value = ChainLookupResult.FOUND
    transport.get_memo_text.return_value = "SOV|campfire_v1|s42|r1|sha256:abc"
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXID1", "--network", "devnet"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "Local proof valid." in out
    assert "Anchor verified. TX memo matches proof hash." in out
    assert "SOV|campfire_v1|s42|r1|sha256:abc" in out
    assert "https://explorer.example/TXID1" in out
    assert factory.call_args.kwargs["network"] is XRPLNetwork.DEVNET
    transport.is_anchored_on_chain.assert_called_once_with("TXID1", expected_hash)


def test_verify_tx_found_without_memo_still_prints_explorer(cwd: Path) -> None:
    proof = _make_proof(cwd)
    factory = _transport_factory()
    transport = factory.return_value
    transport.is_anchored_on_chain.return_value = ChainLookupResult.FOUND
    transport.get_memo_text.return_value = None
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXID2"])
    assert result.exit_code == 0, result.output
    assert "Anchor verified." in result.output
    assert "https://explorer.example/TXID2" in result.output
    assert factory.call_args.kwargs["network"] is XRPLNetwork.TESTNET


def test_verify_tx_not_found_is_a_mismatch(cwd: Path) -> None:
    proof = _make_proof(cwd)
    factory = _transport_factory()
    factory.return_value.is_anchored_on_chain.return_value = ChainLookupResult.NOT_FOUND
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXID3"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "Anchor mismatch" in out
    assert "Anchor verified" not in out


def test_verify_tx_lookup_failure_is_not_reported_as_mismatch(cwd: Path) -> None:
    proof = _make_proof(cwd)
    factory = _transport_factory()
    factory.return_value.is_anchored_on_chain.return_value = ChainLookupResult.LOOKUP_FAILED
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXID4"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "Chain lookup failed" in out
    assert "Anchor mismatch" not in out


def test_verify_tx_transport_error_surfaces_anchor_error(cwd: Path) -> None:
    proof = _make_proof(cwd)
    factory = _transport_factory()
    factory.return_value.is_anchored_on_chain.side_effect = RuntimeError("rpc exploded")
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXID5"])
    assert result.exit_code == 1
    assert "Anchor submission failed: rpc exploded" in _flat(result.output)


def test_verify_tx_rejects_unknown_network(cwd: Path) -> None:
    proof = _make_proof(cwd)
    factory = _transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "T", "--network", "bogus"])
    assert result.exit_code == 1
    assert "'bogus' is not a valid XRPL network." in _flat(result.output)
    factory.assert_not_called()


# ---------------------------------------------------------------------------
# anchor
# ---------------------------------------------------------------------------


def _factory(txids: list[list[str]] | None = None) -> MagicMock:
    transport = MagicMock()
    transport.anchor_batch.side_effect = txids or [["BATCHTX"]]
    transport.anchor.return_value = "SINGLETX"
    transport.explorer_tx_url.side_effect = lambda t: f"https://explorer.example/{t}"
    return MagicMock(return_value=transport)


def test_anchor_without_any_game_refuses(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XRPL_SEED", _SEED)
    result = runner.invoke(app, ["anchor"])
    assert result.exit_code == 1
    assert "No active game." in _flat(result.output)


def test_anchor_reraises_systemexit_from_active_game_resolution(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> str:
        raise SystemExit(3)

    monkeypatch.setattr(cli_main, "_resolve_active_game_id", boom)
    result = runner.invoke(app, ["anchor"])
    assert result.exit_code == 3


def test_anchor_requires_a_wallet_when_work_is_pending(cwd: Path) -> None:
    gid = _new_game()
    add_pending_anchor(gid, "1", _HASH_A)
    factory = _factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--checkpoint"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "No wallet seed found" in out
    assert "sov wallet" in out
    factory.assert_not_called()
    assert set(read_pending_anchors(gid)) == {"1"}


def test_anchor_no_pending_needs_no_wallet(cwd: Path) -> None:
    _new_game()
    result = runner.invoke(app, ["anchor"])
    assert result.exit_code == 0
    out = _flat(result.output)
    assert "No pending anchors." in out
    assert "sov end-round" in out


def test_anchor_batch_reads_seed_from_signer_file_and_reads_wallet_file(cwd: Path) -> None:
    gid = _new_game()
    add_pending_anchor(gid, "1", _HASH_A)
    signer = cwd / "signer.seed"
    signer.write_text(_SEED + "\n", encoding="utf-8")
    factory = _factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--checkpoint", "--signer-file", str(signer)])
    assert result.exit_code == 0, result.output
    call = factory.return_value.anchor_batch.call_args
    assert call.args[1] == _SEED
    out = _flat(result.output)
    assert "Anchored (batch)" in out
    assert "TX: BATCHTX" in out
    assert "https://explorer.example/BATCHTX" in out
    assert "Rounds: 1" in out


def test_anchor_second_empty_check_after_a_racing_flush(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pending drains between the fast-path read and the batch read: no-op, exit 0."""
    gid = _new_game()
    _rewrite_state(gid, game_over=True)
    monkeypatch.setenv("XRPL_SEED", _SEED)
    rows = iter([{"1": {"envelope_hash": _HASH_A, "added_iso": "x"}}, {}])
    monkeypatch.setattr(cli_main, "read_pending_anchors", lambda _gid, heal=False: next(rows))
    factory = _factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor"])
    assert result.exit_code == 0, result.output
    assert "No pending anchors to flush." in _flat(result.output)
    factory.return_value.anchor_batch.assert_not_called()


def test_anchor_batch_orders_numeric_then_final_then_unknown_keys(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gid = _new_game()
    monkeypatch.setenv("XRPL_SEED", _SEED)
    for key in ("FINAL", "10", "weird", "2"):
        add_pending_anchor(gid, key, _HASH_A)
    factory = _factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--checkpoint"])
    assert result.exit_code == 0, result.output
    sent = factory.return_value.anchor_batch.call_args.args[0]
    assert [e["round_key"] for e in sent] == ["2", "10", "FINAL", "weird"]
    assert {e["game_id"] for e in sent} == {gid}
    assert {e["ruleset"] for e in sent} == {"campfire_v1"}


def test_anchor_batch_splits_into_chunks_and_lists_each_txid(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gid = _new_game()
    monkeypatch.setenv("XRPL_SEED", _SEED)
    for i in range(1, 10):
        add_pending_anchor(gid, str(i), _HASH_A)
    factory = _factory([["TX-ONE"], ["TX-TWO"]])
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--checkpoint"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "Anchored (batch — 2 txs)" in out
    assert "TX 1/2: TX-ONE" in out
    assert "Rounds: 1, 2, 3, 4, 5, 6, 7, 8" in out
    assert "TX 2/2: TX-TWO" in out
    assert "Rounds: 9" in out
    assert "https://explorer.example/TX-TWO" in out
    recorded = cli_main._read_anchors_entries(anchors_file(gid))
    assert recorded["8"] == "TX-ONE"
    assert recorded["9"] == "TX-TWO"
    assert read_pending_anchors(gid) == {}


@pytest.mark.parametrize("failure", [RuntimeError("net down"), ValueError("weird failure")])
def test_anchor_batch_failure_keeps_succeeded_prefix(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    gid = _new_game()
    monkeypatch.setenv("XRPL_SEED", _SEED)
    for i in range(1, 10):
        add_pending_anchor(gid, str(i), _HASH_A)
    transport = MagicMock()
    transport.anchor_batch.side_effect = [["TX-ONE"], failure]
    with patch("sov_transport.xrpl.XRPLTransport", MagicMock(return_value=transport)):
        result = runner.invoke(app, ["anchor", "--checkpoint"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert f"Anchor submission failed: {failure}" in out
    assert "Retry with sov anchor in a minute" in out
    assert set(read_pending_anchors(gid)) == {"9"}
    assert cli_main._read_anchors_entries(anchors_file(gid))["1"] == "TX-ONE"


def _legacy_anchor(args: list[str], factory: MagicMock) -> Any:
    """Run the deprecated ``sov anchor <proof>`` form.

    CI promotes DeprecationWarning to an error; the command deliberately emits
    one, so record it instead of letting it abort the invocation.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with patch("sov_transport.xrpl.XRPLTransport", factory):
            result = runner.invoke(app, ["anchor", *args])
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    return result


def test_anchor_legacy_single_round_records_txid_and_clears_pending(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proof = _make_proof(cwd)
    gid = "s42"
    monkeypatch.setenv("XRPL_SEED", _SEED)
    assert set(read_pending_anchors(gid)) == {"1"}
    factory = _factory()
    result = _legacy_anchor([str(proof)], factory)
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "Anchoring Round 1..." in out
    assert "SOV|campfire_v1|s42|r1|sha256:" in out
    assert "Round 1 anchored on XRPL testnet." in out
    assert "TX: SINGLETX" in out
    envelope_hash = json.loads(proof.read_text(encoding="utf-8"))["envelope_hash"]
    factory.return_value.anchor.assert_called_once()
    assert factory.return_value.anchor.call_args.args[0] == envelope_hash
    assert cli_main._read_anchors_entries(anchors_file(gid)) == {"1": "SINGLETX"}
    assert read_pending_anchors(gid) == {}


def test_anchor_legacy_final_proof_uses_final_slot(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gid = _new_game()
    monkeypatch.setenv("XRPL_SEED", _SEED)
    final = cwd / "final.proof.json"
    final.write_text(
        json.dumps(
            {
                "proof_version": 2,
                "game_id": gid,
                "round": 15,
                "final": True,
                "ruleset": "campfire_v1",
                "rng_seed": 42,
                "envelope_hash": _HASH_FINAL,
            }
        ),
        encoding="utf-8",
    )
    factory = _factory()
    result = _legacy_anchor([str(final)], factory)
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "Anchoring FINAL..." in out
    # The 64-char hash wraps at 80 columns; compare with all whitespace removed.
    assert f"SOV|campfire_v1|{gid}|FINAL|sha256:{_HASH_FINAL}" in out.replace(" ", "")
    assert cli_main._read_anchors_entries(anchors_file(gid)) == {"FINAL": "SINGLETX"}


def test_anchor_legacy_missing_proof_file(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _new_game()
    monkeypatch.setenv("XRPL_SEED", _SEED)
    factory = _factory()
    result = _legacy_anchor([str(cwd / "ghost.proof.json")], factory)
    assert result.exit_code == 1
    assert "Proof file not found" in _flat(result.output)
    factory.return_value.anchor.assert_not_called()


@pytest.mark.parametrize("failure", [RuntimeError("rpc down"), KeyError("odd")])
def test_anchor_legacy_transport_failure_is_reported(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    proof = _make_proof(cwd)
    monkeypatch.setenv("XRPL_SEED", _SEED)
    factory = _factory()
    factory.return_value.anchor.side_effect = failure
    result = _legacy_anchor([str(proof)], factory)
    assert result.exit_code == 1
    assert "Anchor submission failed:" in _flat(result.output)
    # Nothing was recorded; the round is still queued for a retry.
    assert set(read_pending_anchors("s42")) == {"1"}


# ---------------------------------------------------------------------------
# wallet
# ---------------------------------------------------------------------------


def test_wallet_testnet_writes_seed_file_and_hides_nothing_but_the_seed(cwd: Path) -> None:
    fund = MagicMock(return_value=("rTESTADDRESS", "sTestSeedValue"))
    with patch("sov_transport.xrpl.fund_dev_wallet", fund):
        result = runner.invoke(app, ["wallet"])
    assert result.exit_code == 0, result.output
    fund.assert_called_once_with(XRPLNetwork.TESTNET)
    out = _flat(result.output)
    assert "Creating a Testnet wallet..." in out
    assert "This is play money." in out
    assert "Address: rTESTADDRESS" in out
    assert "Testnet Wallet" in out
    wallet_file = cwd / ".sov" / "wallet_seed.txt"
    assert wallet_file.read_text(encoding="utf-8") == "sTestSeedValue"
    assert "sTestSeedValue" not in result.output
    if sys.platform != "win32":
        assert wallet_file.stat().st_mode & 0o777 == 0o600


def test_wallet_devnet_uses_devnet_faucet(cwd: Path) -> None:
    fund = MagicMock(return_value=("rDEV", "sDevSeed"))
    with patch("sov_transport.xrpl.fund_dev_wallet", fund):
        result = runner.invoke(app, ["wallet", "--network", "devnet"])
    assert result.exit_code == 0, result.output
    fund.assert_called_once_with(XRPLNetwork.DEVNET)
    assert "Creating a Devnet wallet..." in _flat(result.output)


def test_wallet_rejects_unknown_network(cwd: Path) -> None:
    fund = MagicMock()
    with patch("sov_transport.xrpl.fund_dev_wallet", fund):
        result = runner.invoke(app, ["wallet", "--network", "bogus"])
    assert result.exit_code == 1
    assert "'bogus' is not a valid XRPL network." in _flat(result.output)
    fund.assert_not_called()


@pytest.mark.parametrize(
    ("error", "needle"),
    [
        (RuntimeError("faucet busy"), "Wallet operation failed: faucet busy"),
        (ValueError("bad payload"), "Wallet operation failed: bad payload"),
    ],
)
def test_wallet_faucet_failures_are_structured(cwd: Path, error: Exception, needle: str) -> None:
    fund = MagicMock(side_effect=error)
    with patch("sov_transport.xrpl.fund_dev_wallet", fund):
        result = runner.invoke(app, ["wallet"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert needle in out
    assert "sov wallet" in out
    assert not (cwd / ".sov" / "wallet_seed.txt").exists()


def test_wallet_faucet_mainnet_error_maps_to_faucet_rejected(cwd: Path) -> None:
    fund = MagicMock(side_effect=MainnetFaucetError("no faucet"))
    with patch("sov_transport.xrpl.fund_dev_wallet", fund):
        result = runner.invoke(app, ["wallet"])
    assert result.exit_code == 1
    assert "Mainnet has no faucet." in _flat(result.output)


@pytest.mark.parametrize("env", [None, "", "   "])
def test_wallet_mainnet_without_seed_is_rejected(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, env: str | None
) -> None:
    if env is not None:
        monkeypatch.setenv("XRPL_SEED", env)
    store = MagicMock()
    monkeypatch.setattr(cli_main, "set_mainnet_seed", store)
    result = runner.invoke(app, ["wallet", "--network", "mainnet"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "Mainnet has no faucet." in out
    assert "sov wallet --network mainnet" in out
    store.assert_not_called()


def test_wallet_mainnet_stores_stripped_seed_in_keychain(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XRPL_SEED", f"  {_SEED}  ")
    store = MagicMock()
    monkeypatch.setattr(cli_main, "set_mainnet_seed", store)
    result = runner.invoke(app, ["wallet", "--network", "mainnet"])
    assert result.exit_code == 0, result.output
    store.assert_called_once_with(_SEED)
    assert _SEED not in result.output
    assert not (cwd / ".sov" / "wallet_seed.txt").exists()


def test_wallet_mainnet_reports_unavailable_keychain(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_engine.wallet_seed import KeyringUnavailableError

    monkeypatch.setenv("XRPL_SEED", _SEED)
    monkeypatch.setattr(
        cli_main,
        "set_mainnet_seed",
        MagicMock(side_effect=KeyringUnavailableError("no backend")),
    )
    result = runner.invoke(app, ["wallet", "--network", "mainnet"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "OS keychain unavailable: no backend." in out
    assert "Do not write the mainnet seed" in out
    assert _SEED not in result.output
    assert not (cwd / ".sov" / "wallet_seed.txt").exists()


# ---------------------------------------------------------------------------
# daemon sub-app (lifecycle API is faked; no daemon is ever spawned)
# ---------------------------------------------------------------------------


@pytest.fixture
def daemon_api(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    import sov_daemon

    api = SimpleNamespace(
        run_foreground=MagicMock(),
        start_daemon=MagicMock(),
        stop_daemon=MagicMock(return_value=None),
        daemon_status=MagicMock(return_value=sov_daemon.DaemonStatus.NONE),
        daemon_info=MagicMock(return_value=None),
    )
    for name in ("run_foreground", "start_daemon", "stop_daemon", "daemon_status", "daemon_info"):
        monkeypatch.setattr(sov_daemon, name, getattr(api, name))
    return api


def test_daemon_without_subcommand_runs_in_foreground(
    cwd: Path, daemon_api: SimpleNamespace
) -> None:
    signer = cwd / "seed.txt"
    result = runner.invoke(
        app,
        [
            "daemon",
            "--readonly",
            "--network",
            "devnet",
            "--seed-env",
            "MY_SEED",
            "--signer-file",
            str(signer),
        ],
    )
    assert result.exit_code == 0, result.output
    daemon_api.run_foreground.assert_called_once_with(
        network=XRPLNetwork.DEVNET, readonly=True, seed_env="MY_SEED", signer_file=signer
    )


def test_daemon_root_options_do_not_start_foreground_for_subcommands(
    cwd: Path, daemon_api: SimpleNamespace
) -> None:
    result = runner.invoke(app, ["daemon", "--readonly", "status"])
    assert result.exit_code == 0, result.output
    daemon_api.run_foreground.assert_not_called()


def test_daemon_foreground_rejects_unknown_network(cwd: Path, daemon_api: SimpleNamespace) -> None:
    result = runner.invoke(app, ["daemon", "--network", "bogus"])
    assert result.exit_code == 1
    assert "'bogus' is not a valid XRPL network." in _flat(result.output)
    daemon_api.run_foreground.assert_not_called()


@pytest.mark.parametrize("argv", [["daemon"], ["daemon", "start"], ["daemon", "stop"]])
def test_daemon_commands_explain_missing_extra(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    _block_sov_daemon_import(monkeypatch)
    result = runner.invoke(app, argv)
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "Daemon support is not installed: No module named 'sov_daemon'" in out
    assert "Install the daemon extra:" in out


# Regression: Rich read `[daemon]` as a markup tag and dropped it from the
# hint; _fail now escapes factory text (fixed 2.3.3).
def test_daemon_missing_extra_hint_shows_the_extra_name(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_sov_daemon_import(monkeypatch)
    result = runner.invoke(app, ["daemon", "start"])
    assert "pip install 'sovereignty-game[daemon]'" in _flat(result.output)


def test_daemon_status_explains_missing_extra(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _block_sov_daemon_import(monkeypatch)
    result = runner.invoke(app, ["daemon", "status", "--json"])
    assert result.exit_code == 1
    assert "Daemon support is not installed" in _flat(result.output)


def test_daemon_start_prints_connection_panel(cwd: Path, daemon_api: SimpleNamespace) -> None:
    daemon_api.start_daemon.return_value = {"port": 47823, "pid": 999, "token": "tok-abc"}
    result = runner.invoke(app, ["daemon", "start", "--network", "mainnet"])
    assert result.exit_code == 0, result.output
    daemon_api.start_daemon.assert_called_once_with(
        network=XRPLNetwork.MAINNET, readonly=False, seed_env="XRPL_SEED", signer_file=None
    )
    out = _flat(result.output)
    assert "sov daemon started" in out
    assert "port: 47823" in out
    assert "pid: 999" in out
    assert "network: mainnet" in out
    assert "readonly: false" in out
    assert "token: tok-abc" in out
    assert "sov daemon stop" in out


def test_daemon_start_accepts_attribute_style_handle_and_readonly(
    cwd: Path, daemon_api: SimpleNamespace
) -> None:
    daemon_api.start_daemon.return_value = SimpleNamespace(port=1234, pid=5, token="t0k")
    result = runner.invoke(app, ["daemon", "start", "--readonly"])
    assert result.exit_code == 0, result.output
    assert daemon_api.start_daemon.call_args.kwargs["readonly"] is True
    out = _flat(result.output)
    assert "port: 1234" in out
    assert "readonly: true" in out


def test_daemon_start_rejects_unknown_network(cwd: Path, daemon_api: SimpleNamespace) -> None:
    result = runner.invoke(app, ["daemon", "start", "--network", "bogus"])
    assert result.exit_code == 1
    daemon_api.start_daemon.assert_not_called()


def test_daemon_stop_reports_success_without_pid(cwd: Path, daemon_api: SimpleNamespace) -> None:
    daemon_api.stop_daemon.return_value = True
    result = runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "Stopping daemon..." in out
    assert "Daemon stopped." in out
    assert "pid" not in out


def test_daemon_stop_reports_pid_when_handle_carries_one(
    cwd: Path, daemon_api: SimpleNamespace
) -> None:
    daemon_api.stop_daemon.return_value = {"pid": 321}
    result = runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 0, result.output
    assert "Daemon stopped (pid 321)." in _flat(result.output)


def test_daemon_stop_with_no_daemon_recorded(cwd: Path, daemon_api: SimpleNamespace) -> None:
    daemon_api.stop_daemon.side_effect = FileNotFoundError()
    result = runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "No daemon is recorded for this project root." in out
    assert "sov daemon start" in out


def test_daemon_stop_failure_is_structured(cwd: Path, daemon_api: SimpleNamespace) -> None:
    daemon_api.stop_daemon.side_effect = PermissionError("access denied")
    result = runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "Daemon stop failed: access denied" in out
    assert "kill <pid>" in out


def test_daemon_status_running_table(cwd: Path, daemon_api: SimpleNamespace) -> None:
    import sov_daemon

    daemon_api.daemon_status.return_value = sov_daemon.DaemonStatus.RUNNING
    daemon_api.daemon_info.return_value = {
        "port": 47823,
        "pid": 77,
        "network": "testnet",
        "readonly": True,
        "started_iso": "2026-09-29T10:00:00Z",
    }
    result = runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    for needle in (
        "sov daemon status",
        "state │ running",
        "port │ 47823",
        "pid │ 77",
        "network │ testnet",
        "readonly │ true",
        "started_iso │ 2026-09-29T10:00:00Z",
    ):
        assert needle in out


def test_daemon_status_running_without_details_uses_placeholders(
    cwd: Path, daemon_api: SimpleNamespace
) -> None:
    daemon_api.daemon_status.return_value = "running"  # plain str: no ``.value``
    result = runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "state │ running" in out
    assert "port │ ?" in out
    assert "readonly │ false" in out


def test_daemon_status_stale_human_output(cwd: Path, daemon_api: SimpleNamespace) -> None:
    import sov_daemon

    daemon_api.daemon_status.return_value = sov_daemon.DaemonStatus.STALE
    daemon_api.daemon_info.return_value = {"pid": 555}
    result = runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "daemon: stale (last pid 555 — recorded process is dead)" in out
    assert "sov daemon start" in out


def test_daemon_status_none_human_output(cwd: Path, daemon_api: SimpleNamespace) -> None:
    result = runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "daemon: none" in out
    assert "Start one with `sov daemon start`." in out


def test_daemon_status_json_running(cwd: Path, daemon_api: SimpleNamespace) -> None:
    import sov_daemon

    daemon_api.daemon_status.return_value = sov_daemon.DaemonStatus.RUNNING
    daemon_api.daemon_info.return_value = {"port": 1, "pid": 2, "network": "devnet"}
    payload = json.loads(runner.invoke(app, ["daemon", "status", "--json"]).stdout)
    assert payload["command"] == "daemon status"
    assert payload["status"] == "ok"
    fields = {f["name"]: f for f in payload["fields"]}
    assert fields["state"]["value"] == "running"
    assert fields["state"]["message"] == "Daemon process is alive."
    assert (fields["port"]["value"], fields["pid"]["value"]) == (1, 2)
    assert fields["network"]["value"] == "devnet"
    assert "readonly" not in fields and "started_iso" not in fields


def test_daemon_status_json_stale_is_a_warning(cwd: Path, daemon_api: SimpleNamespace) -> None:
    import sov_daemon

    daemon_api.daemon_status.return_value = sov_daemon.DaemonStatus.STALE
    daemon_api.daemon_info.return_value = {"pid": 9}
    payload = json.loads(runner.invoke(app, ["daemon", "status", "--json"]).stdout)
    assert payload["status"] == "warn"
    state = payload["fields"][0]
    assert state["status"] == "warn"
    assert state["value"] == "stale"
    assert "auto-cleans" in state["message"]


def test_daemon_status_json_none_is_ok(cwd: Path, daemon_api: SimpleNamespace) -> None:
    payload = json.loads(runner.invoke(app, ["daemon", "status", "--json"]).stdout)
    assert payload["status"] == "ok"
    assert [f["name"] for f in payload["fields"]] == ["state"]
    assert payload["fields"][0]["value"] == "none"
    assert payload["fields"][0]["message"] == "No daemon recorded for this project root."


def test_daemon_field_reads_attributes_mappings_and_defaults() -> None:
    assert cli_main._daemon_field(None, "port") == "?"
    assert cli_main._daemon_field(None, "port", default=0) == 0
    assert cli_main._daemon_field(SimpleNamespace(port=7), "port") == 7
    assert cli_main._daemon_field({"port": 8}, "port") == 8
    assert cli_main._daemon_field({}, "port", default=None) is None
    assert cli_main._daemon_field(42, "port") == "?"


# ---------------------------------------------------------------------------
# _resolve_version
# ---------------------------------------------------------------------------


def _pyproject_version() -> str:
    pyproject = Path(cli_main.__file__).parent.parent / "pyproject.toml"
    return str(tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"])


def test_resolve_version_falls_back_to_pyproject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli_main, "_pkg_version", MagicMock(side_effect=PackageNotFoundError("sovereignty-game"))
    )
    assert cli_main._resolve_version() == _pyproject_version()


def test_resolve_version_unknown_when_pyproject_has_no_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_main, "_pkg_version", MagicMock(side_effect=RuntimeError("no dist")))
    real_read_text = Path.read_text

    def fake_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "pyproject.toml":
            return '[project]\nname = "x"\n'
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    assert cli_main._resolve_version() == "unknown"


def test_resolve_version_unknown_when_pyproject_is_unreadable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_main, "_pkg_version", MagicMock(side_effect=RuntimeError("no dist")))
    real_read_text = Path.read_text

    def fake_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "pyproject.toml":
            raise FileNotFoundError(self)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    assert cli_main._resolve_version() == "unknown"

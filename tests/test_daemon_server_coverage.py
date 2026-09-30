"""Coverage for ``sov_daemon.server`` and ``sov_daemon.events`` edge paths.

Phase 3 of the coverage-90 handoff. Everything here runs offline: the XRPL
transport, ``get_balance`` and the JSON-RPC client are fakes, and the daemon
is exercised in-process through ``httpx.ASGITransport`` or by calling the
module-level helpers directly.

Groups:

* ``_read_state`` / ``_proof_path_for_round`` / ``_round_sort_key`` helpers.
* HTTP error branches: games, proofs list/detail, anchor-status, verify,
  pending-anchors, health.
* The anchor path: ``flush_pending_anchors`` (chunking, partial failure),
  ``_do_anchor`` (every mapped HTTP status), the mainnet balance preflight,
  reserve lookup and the async client factory.
* ``MaxBodySizeMiddleware`` streaming-counter path (raw ASGI).
* ``sov_daemon.events``: ``_poll_once``, the poll loop, queue overflow,
  chain-cache accessor, module-level emitters, SSE shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")
pytest.importorskip("xrpl", reason="xrpl extra not installed")

from xrpl.asyncio.clients import XRPLRequestFailureException  # noqa: E402

_TOKEN = "test-server-coverage-token"
_AUTH = {"Authorization": f"Bearer {_TOKEN}"}
_HASH = "a" * 64


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_game(root: Path, game_id: str = "s42") -> Path:
    """Minimal multi-save layout (string players => games_handler fallback)."""
    gd = root / ".sov" / "games" / game_id
    (gd / "proofs").mkdir(parents=True, exist_ok=True)
    (gd / "state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "game_id": game_id,
                "round": 0,
                "ruleset": "campfire_v1",
                "config": {"ruleset": "campfire_v1", "max_rounds": 5},
                "players": ["A", "B"],
                "rng_seed": "42",
            }
        ),
        encoding="utf-8",
    )
    return gd


def _write_proof(gd: Path, name: str, body: dict[str, Any] | str) -> Path:
    path = gd / "proofs" / name
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return path


def _make_app(
    *,
    network: str = "testnet",
    readonly: bool = False,
    signer_file: Path | None = None,
) -> Any:
    from sov_daemon.server import DaemonConfig, build_app

    return build_app(
        DaemonConfig(
            network=network,
            readonly=readonly,
            token=_TOKEN,
            signer_file=signer_file,
        )
    )


def _client(app: Any) -> Any:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _write_seed_file(tmp_path: Path) -> Path:
    from xrpl.wallet import Wallet

    path = tmp_path / "signer.txt"
    path.write_text(Wallet.create().seed, encoding="utf-8")
    return path


def _same(found: Path | None, expected: Path) -> bool:
    """The daemon returns cwd-relative paths; compare on resolved form."""
    return found is not None and found.resolve() == expected.resolve()


def _add_pending(game_id: str, keys: list[str]) -> None:
    from sov_engine.io_utils import add_pending_anchor

    for key in keys:
        add_pending_anchor(game_id, key, _HASH)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Run in an empty project root with no ambient seed or broadcaster."""
    from sov_daemon.events import reset_default_broadcaster

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    reset_default_broadcaster()
    yield
    reset_default_broadcaster()


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def test_build_app_requires_config_or_kwargs() -> None:
    from sov_daemon.server import build_app

    with pytest.raises(TypeError, match="DaemonConfig"):
        build_app()


def test_daemon_version_falls_back_when_package_has_no_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sov_daemon
    from sov_daemon.server import _daemon_version

    assert _daemon_version() == sov_daemon.__version__
    monkeypatch.delattr(sov_daemon, "__version__")
    assert _daemon_version() == "unknown"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("1", (0, 1)),
        ("15", (0, 15)),
        ("FINAL", (1, 0)),
        ("bogus", (2, 0)),
    ],
)
def test_round_sort_key_orders_numeric_then_final_then_junk(
    key: str, expected: tuple[int, int]
) -> None:
    from sov_daemon.server import _round_sort_key

    assert _round_sort_key(key) == expected
    assert sorted(["FINAL", "bogus", "10", "2"], key=_round_sort_key) == [
        "2",
        "10",
        "FINAL",
        "bogus",
    ]


# ---------------------------------------------------------------------------
# _read_state
# ---------------------------------------------------------------------------


def test_read_state_returns_dict_for_valid_state(tmp_path: Path) -> None:
    from sov_daemon.server import _read_state

    _seed_game(tmp_path)
    data = _read_state("s42")
    assert data is not None
    assert data["game_id"] == "s42"


def test_read_state_missing_file_is_none() -> None:
    from sov_daemon.server import _read_state

    assert _read_state("s42") is None


def test_read_state_malformed_json_is_none_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from sov_daemon.server import _read_state

    gd = _seed_game(tmp_path)
    (gd / "state.json").write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_daemon"):
        assert _read_state("s42") is None
    assert any(r.getMessage() == "daemon.state.read.failed" for r in caplog.records)


def test_read_state_unsupported_schema_version_is_none_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from sov_daemon.server import _read_state

    gd = _seed_game(tmp_path)
    (gd / "state.json").write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="sov_daemon"):
        assert _read_state("s42") is None
    assert any(r.getMessage() == "daemon.state.schema_mismatch" for r in caplog.records)


def test_read_state_non_dict_payload_is_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defensive: a versioned reader that returns a non-dict is treated as missing."""
    import sov_engine.schemas as schemas
    from sov_daemon.server import _read_state

    _seed_game(tmp_path)
    monkeypatch.setattr(schemas, "read_versioned", lambda *a, **k: ["not", "a", "dict"])
    assert _read_state("s42") is None


async def test_game_detail_returns_404_for_unreadable_state(tmp_path: Path) -> None:
    gd = _seed_game(tmp_path)
    (gd / "state.json").write_text("{nope", encoding="utf-8")
    async with _client(_make_app()) as c:
        r = await c.get("/games/s42", headers=_AUTH)
    assert r.status_code == 404
    assert r.json()["code"] == "GAME_NOT_FOUND"


# ---------------------------------------------------------------------------
# _proof_path_for_round
# ---------------------------------------------------------------------------


def test_proof_path_none_when_proofs_dir_missing() -> None:
    from sov_daemon.server import _proof_path_for_round

    assert _proof_path_for_round("s42", "1") is None
    assert _proof_path_for_round("s42", "FINAL") is None


@pytest.mark.parametrize(
    "name",
    ["round_007.proof.json", "round-7.json", "round_7.json"],
)
def test_proof_path_numeric_round_matches_each_naming_convention(tmp_path: Path, name: str) -> None:
    from sov_daemon.server import _proof_path_for_round

    gd = _seed_game(tmp_path)
    expected = _write_proof(gd, name, {"round": 7})
    assert _same(_proof_path_for_round("s42", "7"), expected)


def test_proof_path_numeric_round_falls_back_to_content_scan(tmp_path: Path) -> None:
    from sov_daemon.server import _proof_path_for_round

    gd = _seed_game(tmp_path)
    _write_proof(gd, "0-broken.json", "{not json")
    _write_proof(gd, "1-list.json", "[1, 2]")
    _write_proof(gd, "2-other.json", {"round": 3})
    by_int = _write_proof(gd, "3-int.json", {"round": 4})
    by_str = _write_proof(gd, "4-str.json", {"round": "5"})
    assert _same(_proof_path_for_round("s42", "4"), by_int)
    assert _same(_proof_path_for_round("s42", "5"), by_str)
    assert _proof_path_for_round("s42", "6") is None


@pytest.mark.parametrize(
    "name",
    ["round_final.proof.json", "FINAL.json", "final.json"],
)
def test_proof_path_final_matches_literal_names(tmp_path: Path, name: str) -> None:
    from sov_daemon.server import _proof_path_for_round

    gd = _seed_game(tmp_path)
    expected = _write_proof(gd, name, {"final": True})
    assert _same(_proof_path_for_round("s42", "FINAL"), expected)


@pytest.mark.parametrize(
    "body",
    [{"final": True, "round": 15}, {"round": "FINAL"}],
)
def test_proof_path_final_falls_back_to_content_scan(tmp_path: Path, body: dict[str, Any]) -> None:
    from sov_daemon.server import _proof_path_for_round

    gd = _seed_game(tmp_path)
    _write_proof(gd, "a-broken.json", "{not json")
    _write_proof(gd, "b-list.json", "[]")
    _write_proof(gd, "c-normal.json", {"round": 2})
    expected = _write_proof(gd, "d-final.json", body)
    assert _same(_proof_path_for_round("s42", "FINAL"), expected)


def test_proof_path_final_none_when_no_final_proof(tmp_path: Path) -> None:
    from sov_daemon.server import _proof_path_for_round

    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_001.proof.json", {"round": 1})
    assert _proof_path_for_round("s42", "FINAL") is None


@pytest.mark.parametrize(
    "hostile",
    ["../../etc/passwd", "..", "1/../../x", "abc", "", "1e1", "0x1"],
)
def test_proof_path_never_escapes_for_non_numeric_round_keys(tmp_path: Path, hostile: str) -> None:
    """A non-integer round key can never name a file: the helper answers None."""
    from sov_daemon.server import _proof_path_for_round

    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_001.proof.json", {"round": 1})
    (tmp_path / "secret.json").write_text(json.dumps({"round": 1}), encoding="utf-8")
    assert _proof_path_for_round("s42", hostile) is None


@pytest.mark.parametrize(
    "hostile",
    ["%2e%2e", "0", "16", "01", "final%00", "999999999999"],
)
async def test_proof_routes_reject_hostile_round_tokens(tmp_path: Path, hostile: str) -> None:
    _seed_game(tmp_path)
    async with _client(_make_app()) as c:
        for suffix in ("proofs", "anchor-status", "verify"):
            r = await c.get(f"/games/s42/{suffix}/{hostile}", headers=_AUTH)
            assert r.status_code == 400, (suffix, hostile)
            assert r.json()["code"] == "INVALID_ROUND"


@pytest.mark.parametrize("hostile", ["..%2F..%2Fsecret", "1%2F..%2F.."])
async def test_proof_routes_never_route_encoded_slash_round_tokens(
    tmp_path: Path, hostile: str
) -> None:
    """An encoded ``/`` splits the path segment, so no handler ever sees it."""
    _seed_game(tmp_path)
    async with _client(_make_app()) as c:
        for suffix in ("proofs", "anchor-status", "verify"):
            r = await c.get(f"/games/s42/{suffix}/{hostile}", headers=_AUTH)
            assert r.status_code == 404, (suffix, hostile)
            assert r.text == "Not Found"


# ---------------------------------------------------------------------------
# Read endpoints: error branches
# ---------------------------------------------------------------------------


async def test_games_handler_lists_engine_summaries(tmp_path: Path) -> None:
    gd = tmp_path / ".sov" / "games" / "s7"
    gd.mkdir(parents=True)
    (gd / "state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "current_round": 3,
                "config": {"ruleset": "campfire_v1", "max_rounds": 10},
                "players": [{"name": "Ada"}, {"name": "Bo"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".sov" / "active-game").write_text("s7\n", encoding="utf-8")
    async with _client(_make_app()) as c:
        r = await c.get("/games", headers=_AUTH)
    assert r.status_code == 200
    (entry,) = r.json()
    assert entry["game_id"] == "s7"
    assert entry["ruleset"] == "campfire_v1"
    assert entry["current_round"] == 3
    assert entry["max_rounds"] == 10
    assert entry["players"] == ["Ada", "Bo"]
    assert entry["active"] is True
    assert entry["last_modified_iso"].endswith("Z")


async def test_games_handler_fallback_scan_surfaces_hand_rolled_states(
    tmp_path: Path,
) -> None:
    games = tmp_path / ".sov" / "games"
    _seed_game(tmp_path, "s1")  # string players: engine summarizer raises AttributeError
    (games / "afile.txt").write_text("not a dir", encoding="utf-8")
    (games / "nostate").mkdir()
    (games / "s2").mkdir()
    (games / "s2" / "state.json").write_text("{broken", encoding="utf-8")
    (games / "s3").mkdir()
    (games / "s3" / "state.json").write_text("[1, 2]", encoding="utf-8")
    (games / "s4").mkdir()
    (games / "s4" / "state.json").write_text(
        json.dumps({"ruleset": "town_hall_v1", "round": 2, "max_rounds": 9, "players": ["X"]}),
        encoding="utf-8",
    )
    (tmp_path / ".sov" / "active-game").write_text("s4\n", encoding="utf-8")

    async with _client(_make_app()) as c:
        r = await c.get("/games", headers=_AUTH)
    assert r.status_code == 200
    by_id = {g["game_id"]: g for g in r.json()}
    assert set(by_id) == {"s1", "s4"}
    assert by_id["s1"]["ruleset"] == "campfire_v1"  # from config.ruleset
    assert by_id["s1"]["max_rounds"] == 5
    assert by_id["s1"]["active"] is False
    assert by_id["s4"] == {
        "game_id": "s4",
        "ruleset": "town_hall_v1",
        "current_round": 2,
        "max_rounds": 9,
        "players": ["X"],
        "last_modified_iso": "",
        "active": True,
    }


async def test_games_handler_empty_when_no_games_dir() -> None:
    async with _client(_make_app()) as c:
        r = await c.get("/games", headers=_AUTH)
    assert r.status_code == 200
    assert r.json() == []


async def test_proofs_list_unknown_game_is_404_and_empty_game_is_empty_list(
    tmp_path: Path,
) -> None:
    gd = tmp_path / ".sov" / "games" / "s9"
    gd.mkdir(parents=True)
    async with _client(_make_app()) as c:
        missing = await c.get("/games/s1/proofs", headers=_AUTH)
        empty = await c.get("/games/s9/proofs", headers=_AUTH)
    assert missing.status_code == 404
    assert missing.json()["code"] == "GAME_NOT_FOUND"
    assert empty.status_code == 200
    assert empty.json() == []


async def test_proofs_list_skips_anchors_malformed_and_non_dict_files(tmp_path: Path) -> None:
    gd = _seed_game(tmp_path)
    _write_proof(gd, "anchors.json", {"schema_version": 1, "entries": {}})
    _write_proof(gd, "bad.json", "{oops")
    _write_proof(gd, "list.json", "[1]")
    good = _write_proof(gd, "round-1.json", {"round": 1, "envelope_hash": _HASH})
    fin = _write_proof(
        gd, "FINAL.json", {"round": "FINAL", "envelope_hash": "b" * 64, "final": True}
    )
    async with _client(_make_app()) as c:
        r = await c.get("/games/s42/proofs", headers=_AUTH)
    assert r.status_code == 200
    rows = {Path(row["path"]).name: row for row in r.json()}
    assert set(rows) == {good.name, fin.name}
    assert rows[good.name] == {
        "round": 1,
        "envelope_hash": _HASH,
        "final": False,
        "path": rows[good.name]["path"],
    }
    assert _same(Path(rows[good.name]["path"]), good)
    assert rows[fin.name]["final"] is True


async def test_proof_detail_not_found_and_unreadable(tmp_path: Path) -> None:
    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_002.proof.json", "{corrupt")
    good = {"round": 3, "envelope_hash": _HASH}
    _write_proof(gd, "round_003.proof.json", good)
    async with _client(_make_app()) as c:
        missing = await c.get("/games/s42/proofs/1", headers=_AUTH)
        corrupt = await c.get("/games/s42/proofs/2", headers=_AUTH)
        ok = await c.get("/games/s42/proofs/3", headers=_AUTH)
        bad_game = await c.get("/games/nope/proofs/1", headers=_AUTH)
    assert missing.status_code == 404
    assert missing.json()["code"] == "PROOF_NOT_FOUND"
    assert corrupt.status_code == 500
    assert corrupt.json()["code"] == "PROOF_UNREADABLE"
    assert ok.status_code == 200
    assert ok.json() == good
    assert bad_game.status_code == 400
    assert bad_game.json()["code"] == "INVALID_GAME_ID"


async def test_anchor_status_errors_and_unreadable_proof_degrades(tmp_path: Path) -> None:
    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_001.proof.json", "{corrupt")
    async with _client(_make_app()) as c:
        bad_game = await c.get("/games/nope/anchor-status/1", headers=_AUTH)
        missing = await c.get("/games/s42/anchor-status/2", headers=_AUTH)
        degraded = await c.get("/games/s42/anchor-status/1", headers=_AUTH)
    assert bad_game.status_code == 400
    assert bad_game.json()["code"] == "INVALID_GAME_ID"
    assert missing.status_code == 404
    assert missing.json()["code"] == "PROOF_NOT_FOUND"
    assert degraded.status_code == 200
    assert degraded.json() == {"round": "1", "anchor_status": "missing", "envelope_hash": None}


async def test_anchor_status_recorded_txid_wins_over_pending_and_heals(tmp_path: Path) -> None:
    from sov_engine.io_utils import read_pending_anchors
    from sov_engine.proof import record_anchors

    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_001.proof.json", {"round": 1, "envelope_hash": _HASH})
    _add_pending("s42", ["1"])
    record_anchors("s42", {"1": "TXID1"})
    async with _client(_make_app()) as c:
        r = await c.get("/games/s42/anchor-status/1", headers=_AUTH)
    assert r.json() == {
        "round": "1",
        "anchor_status": "anchored",
        "envelope_hash": _HASH,
        "txid": "TXID1",
    }
    assert read_pending_anchors("s42") == {}  # stale pending row was healed away


async def test_heal_survives_clear_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sov_daemon import server as srv
    from sov_engine.proof import record_anchors

    _seed_game(tmp_path)
    _add_pending("s42", ["1", "2"])
    record_anchors("s42", {"1": "TXID1"})

    def _boom(*_a: Any, **_k: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(srv, "clear_pending_anchors", _boom)
    pending, anchors = srv._heal_stale_pending_against_anchors("s42")
    assert set(pending) == {"2"}  # in-memory view is healed even if the clear failed
    assert anchors["1"] == "TXID1"


class _Found:
    value = "found"


async def test_verify_round_error_branches(tmp_path: Path) -> None:
    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_001.proof.json", "{corrupt")
    async with _client(_make_app()) as c:
        bad_game = await c.get("/games/nope/verify/1", headers=_AUTH)
        bad_round = await c.get("/games/s42/verify/99", headers=_AUTH)
        missing = await c.get("/games/s42/verify/2", headers=_AUTH)
        corrupt = await c.get("/games/s42/verify/1", headers=_AUTH)
    assert bad_game.status_code == 400
    assert bad_game.json()["code"] == "INVALID_GAME_ID"
    assert bad_round.status_code == 400
    assert bad_round.json()["code"] == "INVALID_ROUND"
    assert missing.status_code == 404
    assert missing.json()["code"] == "PROOF_NOT_FOUND"
    assert corrupt.status_code == 200
    assert corrupt.json() == {"round": "1", "anchor_status": "missing", "envelope_hash": None}


@pytest.mark.parametrize(
    ("transport_result", "expected"),
    [
        (_Found(), "found"),
        ("not_found", "not_found"),
        ("lookup_failed", "lookup_failed"),
        ("banana", "lookup_failed"),  # unknown verdicts fail open, never "missing"
        (True, "lookup_failed"),
    ],
)
async def test_verify_round_normalises_transport_verdicts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    transport_result: Any,
    expected: str,
) -> None:
    from sov_daemon import server as srv
    from sov_engine.proof import record_anchors

    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_001.proof.json", {"round": 1, "envelope_hash": _HASH})
    record_anchors("s42", {"1": "TXID1"})
    seen: list[tuple[str, str]] = []

    class _T:
        def is_anchored_on_chain(self, txid: str, envelope_hash: str) -> Any:
            seen.append((txid, envelope_hash))
            return transport_result

    monkeypatch.setattr(srv, "get_verify_transport", lambda network: _T())
    async with _client(_make_app()) as c:
        r = await c.get("/games/s42/verify/1", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["anchor_status"] == "anchored"
    assert body["chain_lookup"] == expected
    assert seen == [("TXID1", _HASH)]


async def test_verify_round_transport_exception_becomes_lookup_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon import server as srv
    from sov_engine.proof import record_anchors

    gd = _seed_game(tmp_path)
    _write_proof(gd, "round_001.proof.json", {"round": 1, "envelope_hash": _HASH})
    record_anchors("s42", {"1": "TXID1"})

    def _explode(_network: str) -> Any:
        raise ConnectionError("no route")

    monkeypatch.setattr(srv, "get_verify_transport", _explode)
    async with _client(_make_app()) as c:
        r = await c.get("/games/s42/verify/1", headers=_AUTH)
    assert r.status_code == 200
    assert r.json()["chain_lookup"] == "lookup_failed"
    assert r.json()["anchor_status"] == "anchored"


def test_get_verify_transport_builds_xrpl_transport_for_network() -> None:
    from sov_daemon.server import get_verify_transport
    from sov_transport.xrpl import XRPLTransport

    transport = get_verify_transport("testnet")
    assert isinstance(transport, XRPLTransport)
    with pytest.raises(ValueError, match="bogus"):
        get_verify_transport("bogus")


async def test_pending_anchors_unknown_game_404_and_sorted_entries(tmp_path: Path) -> None:
    _seed_game(tmp_path)
    _add_pending("s42", ["10", "FINAL", "2"])
    async with _client(_make_app()) as c:
        missing = await c.get("/games/s8/pending-anchors", headers=_AUTH)
        ok = await c.get("/games/s42/pending-anchors", headers=_AUTH)
    assert missing.status_code == 404
    assert missing.json()["code"] == "GAME_NOT_FOUND"
    assert ok.status_code == 200
    body = ok.json()
    assert body["pending"] == ["2", "10", "FINAL"]
    assert set(body["entries"]) == {"2", "10", "FINAL"}
    assert body["entries"]["2"]["envelope_hash"] == _HASH


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


async def test_health_reports_pending_summary_and_skips_noise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon import server as srv

    games = tmp_path / ".sov" / "games"
    _seed_game(tmp_path, "s1")
    _seed_game(tmp_path, "s2")
    _seed_game(tmp_path, "s3")
    (games / "stray.txt").write_text("x", encoding="utf-8")
    _add_pending("s1", ["1", "2"])
    _add_pending("s3", ["FINAL"])

    real = srv.read_pending_anchors

    def _flaky(game_id: str) -> Any:
        if game_id == "s3":
            raise RuntimeError("corrupt index")
        return real(game_id)

    monkeypatch.setattr(srv, "read_pending_anchors", _flaky)
    async with _client(_make_app(network="devnet")) as c:
        r = await c.get("/health", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["network"] == "devnet"
    assert body["readonly"] is False
    assert body["ipc_version"] == 1
    assert set(body["pending_anchors_summary"]) == {"s1"}  # s2 empty, s3 raised, file skipped
    row = body["pending_anchors_summary"]["s1"]
    assert row["pending_count"] == 2
    assert row["oldest_added_iso"].endswith("Z")


async def test_health_survives_games_dir_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import sov_engine.io_utils as io_utils

    def _boom() -> Path:
        raise PermissionError("locked")

    monkeypatch.setattr(io_utils, "games_dir", _boom)
    async with _client(_make_app()) as c:
        r = await c.get("/health", headers=_AUTH)
    assert r.status_code == 200
    assert r.json()["pending_anchors_summary"] == {}


# ---------------------------------------------------------------------------
# Anchor path: fakes
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, result: Any, ok: bool = True) -> None:
        self.result = result
        self._ok = ok

    def is_successful(self) -> bool:
        return self._ok


class _FakeClient:
    """Stands in for ``AsyncJsonRpcClient``: only ``request`` is used."""

    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.requests: list[Any] = []

    async def request(self, req: Any) -> Any:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        return self.response


def _server_state(reserve: Any = 1_000_000, key: str = "validated_ledger") -> dict[str, Any]:
    ledger: dict[str, Any] = {} if reserve is None else {"reserve_base": reserve}
    return {"state": {key: ledger}}


class _Recorder:
    """Shared record of what the fake transport was asked to do."""

    def __init__(self) -> None:
        self.batches: list[list[str]] = []
        self.seeds: list[str] = []
        self.networks: list[Any] = []


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    *,
    results: list[Any] | None = None,
    client: Any = None,
) -> _Recorder:
    """Replace ``AsyncXRPLTransport``. ``results`` is consumed one per ``anchor_batch``.

    Each item is a ``list[str]`` of txids or an ``Exception`` to raise. Default:
    one deterministic txid per call (``TX<n>``).
    """
    import sov_transport.xrpl_async as xa

    recorder = _Recorder()
    queue = list(results) if results is not None else None

    class _FakeTransport:
        def __init__(self, network: Any = None, **_kw: Any) -> None:
            recorder.networks.append(network)

        def _client(self) -> Any:
            return client

        async def anchor_batch(self, rounds: list[dict[str, Any]], signer: str) -> list[str]:
            recorder.batches.append([r["round_key"] for r in rounds])
            recorder.seeds.append(signer)
            if queue is None:
                return [f"TX{len(recorder.batches)}"]
            item = queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return list(item)

        def explorer_tx_url(self, txid: str) -> str:
            return f"https://explorer.test/{txid}"

    monkeypatch.setattr(xa, "AsyncXRPLTransport", _FakeTransport)
    return recorder


def _install_balance(
    monkeypatch: pytest.MonkeyPatch, value: int | Exception
) -> list[tuple[str, Any]]:
    """Patch ``xrpl.asyncio.account.get_balance``; returns the (address, client) calls."""
    import xrpl.asyncio.account as account

    calls: list[tuple[str, Any]] = []

    async def _get_balance(address: str, client: Any) -> int:
        calls.append((address, client))
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(account, "get_balance", _get_balance)
    return calls


# ---------------------------------------------------------------------------
# _reserve_base_drops_from_server_state / _async_xrpl_client / _fetch_reserve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (None, None),
        ("nope", None),
        ({}, None),
        ({"state": "nope"}, None),
        ({"state": {}}, None),
        ({"state": {"validated_ledger": "nope"}}, None),
        ({"state": {"validated_ledger": {}}}, None),
        (_server_state("10000000"), 10_000_000),
        (_server_state(2_000_000), 2_000_000),
        (_server_state(0), None),
        (_server_state(-5), None),
        (_server_state("garbage"), None),
        (_server_state([1]), None),
        (_server_state(1_000_000, key="closed_ledger"), 1_000_000),
        (
            {
                "state": {
                    "validated_ledger": {"reserve_base": "garbage"},
                    "closed_ledger": {"reserve_base": 1_500_000},
                }
            },
            1_500_000,
        ),
    ],
)
def test_reserve_base_parser(result: Any, expected: int | None) -> None:
    from sov_daemon.server import _reserve_base_drops_from_server_state

    assert _reserve_base_drops_from_server_state(result) == expected


def test_required_drops_for_batch_is_reserve_plus_per_memo_fee() -> None:
    from sov_daemon.server import _required_drops_for_batch

    assert _required_drops_for_batch(9, 1_000_000) == 1_000_108
    assert _required_drops_for_batch(0, 1_000_000) == 1_000_012  # floor of one memo


def test_async_xrpl_client_prefers_transport_client() -> None:
    from sov_daemon.server import _async_xrpl_client

    sentinel = object()

    class _T:
        def _client(self) -> Any:
            return sentinel

    assert _async_xrpl_client(_T()) is sentinel


@pytest.mark.parametrize("attr", ["url", "json_rpc_url"])
def test_async_xrpl_client_builds_json_rpc_client_from_url(attr: str) -> None:
    from xrpl.asyncio.clients import AsyncJsonRpcClient

    from sov_daemon.server import _async_xrpl_client

    class _T:
        def _client(self) -> Any:
            return None

    transport = _T()
    setattr(transport, attr, "https://rpc.example.test:51234")
    client = _async_xrpl_client(transport)
    assert isinstance(client, AsyncJsonRpcClient)
    assert client.url == "https://rpc.example.test:51234"


def test_async_xrpl_client_uses_real_transport_url() -> None:
    from xrpl.asyncio.clients import AsyncJsonRpcClient

    from sov_daemon.server import _async_xrpl_client
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    transport = AsyncXRPLTransport(network=XRPLNetwork.TESTNET)
    client = _async_xrpl_client(transport)
    assert isinstance(client, AsyncJsonRpcClient)
    assert client.url == transport.url


def test_async_xrpl_client_without_url_raises() -> None:
    from sov_daemon.server import _async_xrpl_client

    with pytest.raises(RuntimeError, match="no JSON-RPC URL"):
        _async_xrpl_client(object())


async def test_fetch_reserve_base_reads_server_state() -> None:
    from xrpl.models.requests import ServerState

    from sov_daemon.server import _fetch_reserve_base_drops

    client = _FakeClient(_FakeResponse(_server_state("10000000")))

    class _T:
        def _client(self) -> Any:
            return client

    assert await _fetch_reserve_base_drops(_T()) == 10_000_000
    assert len(client.requests) == 1
    assert isinstance(client.requests[0], ServerState)


async def test_fetch_reserve_base_falls_back_when_field_missing() -> None:
    from sov_daemon.server import _MAINNET_RESERVE_BASE_DROPS_FALLBACK, _fetch_reserve_base_drops

    client = _FakeClient(_FakeResponse(_server_state(None)))

    class _T:
        def _client(self) -> Any:
            return client

    assert (
        await _fetch_reserve_base_drops(_T()) == _MAINNET_RESERVE_BASE_DROPS_FALLBACK == 1_000_000
    )


async def test_fetch_reserve_base_accepts_response_without_is_successful() -> None:
    from sov_daemon.server import _fetch_reserve_base_drops

    class _Bare:
        result = _server_state(3_000_000)

    client = _FakeClient(_Bare())

    class _T:
        def _client(self) -> Any:
            return client

    assert await _fetch_reserve_base_drops(_T()) == 3_000_000


async def test_fetch_reserve_base_unsuccessful_response_raises() -> None:
    from sov_daemon.server import _fetch_reserve_base_drops

    client = _FakeClient(_FakeResponse({"error": "slowDown"}, ok=False))

    class _T:
        def _client(self) -> Any:
            return client

    with pytest.raises(RuntimeError, match="server_state lookup failed"):
        await _fetch_reserve_base_drops(_T())


# ---------------------------------------------------------------------------
# _check_wallet_balance_or_raise (direct)
# ---------------------------------------------------------------------------


class _ClientTransport:
    def __init__(self, client: Any) -> None:
        self._c = client

    def _client(self) -> Any:
        return self._c


async def test_balance_check_passes_at_exact_requirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from xrpl.wallet import Wallet

    from sov_daemon.server import _check_wallet_balance_or_raise

    wallet = Wallet.create()
    calls = _install_balance(monkeypatch, 1_000_108)
    client = _FakeClient()
    await _check_wallet_balance_or_raise(
        _ClientTransport(client),
        seed=wallet.seed,
        n_memos=9,
        reserve_base_drops=1_000_000,
    )
    assert calls == [(wallet.address, client)]
    assert client.requests == []  # reserve given, so no server_state lookup


async def test_balance_check_underfunded_carries_drop_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xrpl.wallet import Wallet

    from sov_daemon.server import MainnetUnderfundedError, _check_wallet_balance_or_raise

    _install_balance(monkeypatch, 5)
    with pytest.raises(MainnetUnderfundedError) as excinfo:
        await _check_wallet_balance_or_raise(
            _ClientTransport(_FakeClient()),
            seed=Wallet.create().seed,
            required_drops=100,
        )
    assert excinfo.value.balance_drops == 5
    assert excinfo.value.required_drops == 100
    assert "have 5 drops, need 100 drops" in str(excinfo.value)


async def test_balance_check_fetches_reserve_when_not_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xrpl.wallet import Wallet

    from sov_daemon.server import MainnetUnderfundedError, _check_wallet_balance_or_raise

    _install_balance(monkeypatch, 10_000_000)
    client = _FakeClient(_FakeResponse(_server_state("10000000")))
    with pytest.raises(MainnetUnderfundedError) as excinfo:
        await _check_wallet_balance_or_raise(
            _ClientTransport(client), seed=Wallet.create().seed, n_memos=2
        )
    assert excinfo.value.required_drops == 10_000_024  # live reserve + 2 * 12 fee
    assert len(client.requests) == 1


async def test_balance_check_account_not_found_is_underfunded_zero(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from xrpl.wallet import Wallet

    from sov_daemon.server import MainnetUnderfundedError, _check_wallet_balance_or_raise

    _install_balance(monkeypatch, XRPLRequestFailureException({"error": "actNotFound"}))
    with (
        caplog.at_level(logging.WARNING, logger="sov_daemon"),
        pytest.raises(MainnetUnderfundedError) as excinfo,
    ):
        await _check_wallet_balance_or_raise(
            _ClientTransport(_FakeClient()),
            seed=Wallet.create().seed,
            required_drops=1_000_012,
        )
    assert excinfo.value.balance_drops == 0
    assert excinfo.value.required_drops == 1_000_012
    assert any(r.getMessage() == "anchor.balance_preflight.failed" for r in caplog.records)


@pytest.mark.parametrize(
    "exc",
    [
        XRPLRequestFailureException({"error": "slowDown"}),
        TimeoutError("rpc timed out"),
        ConnectionError("refused"),
    ],
)
async def test_balance_check_other_failures_propagate_not_insolvency(
    monkeypatch: pytest.MonkeyPatch, exc: Exception
) -> None:
    from xrpl.wallet import Wallet

    from sov_daemon.server import MainnetUnderfundedError, _check_wallet_balance_or_raise

    _install_balance(monkeypatch, exc)
    with pytest.raises(type(exc)) as excinfo:
        await _check_wallet_balance_or_raise(
            _ClientTransport(_FakeClient()),
            seed=Wallet.create().seed,
            required_drops=1_000_012,
        )
    assert not isinstance(excinfo.value, MainnetUnderfundedError)


async def test_balance_check_invalid_seed_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    from sov_daemon.server import _check_wallet_balance_or_raise

    _install_balance(monkeypatch, 10**9)
    with pytest.raises(Exception, match=r"(?i)seed|decode|checksum|invalid"):
        await _check_wallet_balance_or_raise(
            _ClientTransport(_FakeClient()), seed="not-a-seed", required_drops=1
        )


# ---------------------------------------------------------------------------
# flush_pending_anchors (direct)
# ---------------------------------------------------------------------------


async def test_flush_with_nothing_pending_is_empty_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon.server import flush_pending_anchors

    _seed_game(tmp_path)
    recorder = _install_transport(monkeypatch)
    out = await flush_pending_anchors(
        game_id="s42", network="testnet", seed="", ruleset="campfire_v1"
    )
    assert out == {"txids": [], "rounds": [], "explorer_urls": []}
    assert recorder.batches == []


async def test_flush_chunks_at_eight_memos_and_commits_each_chunk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon.server import flush_pending_anchors
    from sov_engine.io_utils import read_pending_anchors
    from sov_engine.proof import _read_anchors

    _seed_game(tmp_path)
    _add_pending("s42", [*(str(i) for i in range(1, 10)), "FINAL"])
    recorder = _install_transport(monkeypatch)
    out = await flush_pending_anchors(
        game_id="s42", network="testnet", seed="sEdSEED", ruleset="campfire_v1"
    )
    assert recorder.batches == [
        ["1", "2", "3", "4", "5", "6", "7", "8"],
        ["9", "FINAL"],
    ]
    assert recorder.seeds == ["sEdSEED", "sEdSEED"]
    assert out["txids"] == ["TX1", "TX2"]
    assert out["rounds"] == ["1", "2", "3", "4", "5", "6", "7", "8", "9", "FINAL"]
    assert out["explorer_urls"] == [
        "https://explorer.test/TX1",
        "https://explorer.test/TX2",
    ]
    anchors = _read_anchors("s42")
    assert anchors["1"] == "TX1" and anchors["8"] == "TX1"
    assert anchors["9"] == "TX2" and anchors["FINAL"] == "TX2"
    assert read_pending_anchors("s42") == {}


async def test_flush_partial_failure_keeps_committed_prefix_and_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from sov_daemon.server import flush_pending_anchors
    from sov_engine.io_utils import read_pending_anchors
    from sov_engine.proof import _read_anchors

    _seed_game(tmp_path)
    _add_pending("s42", [str(i) for i in range(1, 10)])
    _install_transport(monkeypatch, results=[["TXA"], RuntimeError("ledger busy")])
    with (
        caplog.at_level(logging.WARNING, logger="sov_daemon"),
        pytest.raises(RuntimeError, match="ledger busy"),
    ):
        await flush_pending_anchors(
            game_id="s42", network="testnet", seed="sEdSEED", ruleset="campfire_v1"
        )
    anchors = _read_anchors("s42")
    assert {k: anchors[k] for k in map(str, range(1, 9))} == {str(i): "TXA" for i in range(1, 9)}
    assert "9" not in anchors
    assert set(read_pending_anchors("s42")) == {"9"}  # retry resubmits only what's left
    partial = [r for r in caplog.records if r.getMessage() == "anchor.batch.partial"]
    assert len(partial) == 1
    assert partial[0].txid == "TXA"  # type: ignore[attr-defined]


async def test_flush_first_chunk_failure_does_not_log_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from sov_daemon.server import flush_pending_anchors
    from sov_engine.io_utils import read_pending_anchors

    _seed_game(tmp_path)
    _add_pending("s42", ["1"])
    _install_transport(monkeypatch, results=[ConnectionError("down")])
    with (
        caplog.at_level(logging.WARNING, logger="sov_daemon"),
        pytest.raises(ConnectionError),
    ):
        await flush_pending_anchors(
            game_id="s42", network="testnet", seed="sEdSEED", ruleset="campfire_v1"
        )
    assert set(read_pending_anchors("s42")) == {"1"}
    assert not [r for r in caplog.records if r.getMessage() == "anchor.batch.partial"]


async def test_flush_empty_txid_list_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon.server import flush_pending_anchors
    from sov_engine.io_utils import read_pending_anchors

    _seed_game(tmp_path)
    _add_pending("s42", ["1"])
    _install_transport(monkeypatch, results=[[]])
    with pytest.raises(RuntimeError, match="no txids"):
        await flush_pending_anchors(
            game_id="s42", network="testnet", seed="sEdSEED", ruleset="campfire_v1"
        )
    assert set(read_pending_anchors("s42")) == {"1"}


async def test_flush_testnet_skips_balance_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon.server import flush_pending_anchors

    _seed_game(tmp_path)
    _add_pending("s42", ["1"])
    _install_transport(monkeypatch)
    calls = _install_balance(monkeypatch, RuntimeError("must not be called"))
    await flush_pending_anchors(
        game_id="s42", network="devnet", seed="sEdSEED", ruleset="campfire_v1"
    )
    assert calls == []


# ---------------------------------------------------------------------------
# Anchor endpoints over HTTP
# ---------------------------------------------------------------------------


async def test_anchor_endpoint_success_records_broadcasts_and_flags_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon.events import get_broadcaster
    from sov_engine.io_utils import read_pending_anchors
    from sov_engine.proof import _read_anchors

    _seed_game(tmp_path)
    _add_pending("s42", [str(i) for i in range(1, 10)])
    _install_transport(monkeypatch)
    app = _make_app(signer_file=_write_seed_file(tmp_path))
    broadcaster = get_broadcaster(app)
    queue = await broadcaster.subscribe()
    try:
        async with _client(app) as c:
            r = await c.post("/games/s42/anchor", headers=_AUTH)
        event_type, payload = queue.get_nowait()
    finally:
        await broadcaster.unsubscribe(queue)
    assert r.status_code == 200
    body = r.json()
    assert body["txids"] == ["TX1", "TX2"]
    assert body["rounds"] == [str(i) for i in range(1, 10)]
    assert body["explorer_urls"] == ["https://explorer.test/TX1", "https://explorer.test/TX2"]
    assert body["checkpoint"] is False
    assert event_type == "anchor.batch_complete"
    assert payload["game_id"] == "s42"
    assert payload["txids"] == ["TX1", "TX2"]
    assert _read_anchors("s42")["9"] == "TX2"
    assert read_pending_anchors("s42") == {}


async def test_anchor_checkpoint_endpoint_sets_checkpoint_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_game(tmp_path)
    _add_pending("s42", ["1", "2"])
    _install_transport(monkeypatch)
    app = _make_app(signer_file=_write_seed_file(tmp_path))
    async with _client(app) as c:
        r = await c.post("/games/s42/anchor/checkpoint", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["checkpoint"] is True
    assert body["txids"] == ["TX1"]
    assert body["rounds"] == ["1", "2"]


async def test_anchor_endpoints_with_nothing_pending_return_empty_success(
    tmp_path: Path,
) -> None:
    _seed_game(tmp_path)
    app = _make_app(signer_file=_write_seed_file(tmp_path))
    async with _client(app) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 200
    assert r.json() == {"txids": [], "rounds": [], "explorer_urls": [], "checkpoint": False}


@pytest.mark.parametrize("path", ["anchor", "anchor/checkpoint"])
async def test_anchor_endpoints_reject_bad_game_id_unknown_game_and_readonly(
    tmp_path: Path, path: str
) -> None:
    _seed_game(tmp_path)
    seed = _write_seed_file(tmp_path)
    async with _client(_make_app(signer_file=seed)) as c:
        bad = await c.post(f"/games/sNOPE/{path}", headers=_AUTH)
        unknown = await c.post(f"/games/s99/{path}", headers=_AUTH)
    async with _client(_make_app(readonly=True)) as c:
        ro = await c.post(f"/games/s42/{path}", headers=_AUTH)
    assert bad.status_code == 400
    assert bad.json()["code"] == "INVALID_GAME_ID"
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "GAME_NOT_FOUND"
    assert ro.status_code == 405
    assert ro.json()["code"] == "DAEMON_READONLY"


async def test_anchor_endpoint_no_seed_is_400_config_no_wallet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_game(tmp_path)
    _add_pending("s42", ["1"])
    recorder = _install_transport(monkeypatch)
    async with _client(_make_app()) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 400
    assert r.json()["code"] == "CONFIG_NO_WALLET"
    assert "XRPL_SEED" in r.json()["message"] + r.json()["hint"]
    assert recorder.batches == []


async def test_anchor_endpoint_submit_failure_is_502_anchor_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from sov_engine.io_utils import read_pending_anchors

    _seed_game(tmp_path)
    _add_pending("s42", ["1"])
    _install_transport(monkeypatch, results=[ConnectionError("rippled unreachable")])
    app = _make_app(signer_file=_write_seed_file(tmp_path))
    with caplog.at_level(logging.ERROR, logger="sov_daemon"):
        async with _client(app) as c:
            r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 502
    body = r.json()
    assert body["code"] == "ANCHOR_FAILED"
    assert "ConnectionError" in body["message"]
    assert "rippled unreachable" in body["message"]
    assert "`sov anchor`" in body["hint"]
    assert set(read_pending_anchors("s42")) == {"1"}
    assert any(r.getMessage() == "anchor.batch.failed" for r in caplog.records)


async def test_anchor_endpoint_invalid_network_is_500(tmp_path: Path) -> None:
    _seed_game(tmp_path)
    _add_pending("s42", ["1"])
    app = _make_app(network="bogusnet", signer_file=_write_seed_file(tmp_path))
    async with _client(app) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "INVALID_NETWORK"
    assert "bogusnet" in body["message"]


async def test_anchor_endpoint_missing_xrpl_is_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon import server as srv

    _seed_game(tmp_path)

    async def _no_xrpl(**_kw: Any) -> dict[str, Any]:
        raise ImportError("No module named 'xrpl'")

    monkeypatch.setattr(srv, "flush_pending_anchors", _no_xrpl)
    async with _client(_make_app(signer_file=_write_seed_file(tmp_path))) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 500
    assert r.json()["code"] == "XRPL_NOT_INSTALLED"
    assert "ImportError" in r.json()["message"]


async def test_anchor_endpoint_coerces_legacy_singular_result_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_daemon import server as srv

    _seed_game(tmp_path)
    shapes: list[dict[str, Any]] = [
        {"txid": "LEGACY", "explorer_url": "https://x.test/LEGACY", "rounds": ["1"]},
        {},
    ]

    async def _legacy(**_kw: Any) -> dict[str, Any]:
        return shapes.pop(0)

    monkeypatch.setattr(srv, "flush_pending_anchors", _legacy)
    async with _client(_make_app(signer_file=_write_seed_file(tmp_path))) as c:
        first = await c.post("/games/s42/anchor", headers=_AUTH)
        second = await c.post("/games/s42/anchor", headers=_AUTH)
    assert first.json() == {
        "txids": ["LEGACY"],
        "rounds": ["1"],
        "explorer_urls": ["https://x.test/LEGACY"],
        "checkpoint": False,
    }
    assert second.json() == {"txids": [], "rounds": [], "explorer_urls": [], "checkpoint": False}


# ---------------------------------------------------------------------------
# Mainnet balance preflight through the endpoint
# ---------------------------------------------------------------------------


def _mainnet_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    client: Any,
    balance: int | Exception,
) -> tuple[Any, _Recorder]:
    _seed_game(tmp_path)
    _add_pending("s42", [str(i) for i in range(1, 10)])
    recorder = _install_transport(monkeypatch, client=client)
    _install_balance(monkeypatch, balance)
    return _make_app(network="mainnet", signer_file=_write_seed_file(tmp_path)), recorder


async def test_mainnet_anchor_underfunded_is_402_and_never_submits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _FakeClient(_FakeResponse(_server_state(1_000_000)))
    app, recorder = _mainnet_setup(tmp_path, monkeypatch, client=client, balance=1_000_107)
    async with _client(app) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 402
    body = r.json()
    assert body["code"] == "MAINNET_UNDERFUNDED"
    assert "1000107 drops" in body["message"]
    assert "1000108 drops" in body["message"]  # 1 XRP reserve + 9 memos * 12 drops
    assert recorder.batches == []


async def test_mainnet_anchor_funded_wallet_submits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _FakeClient(_FakeResponse(_server_state(1_000_000)))
    app, recorder = _mainnet_setup(tmp_path, monkeypatch, client=client, balance=1_000_108)
    async with _client(app) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 200
    assert r.json()["txids"] == ["TX1", "TX2"]
    assert len(recorder.batches) == 2


async def test_mainnet_anchor_unknown_account_is_402_with_zero_balance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    client = _FakeClient(_FakeResponse(_server_state(None)))  # fallback reserve
    app, recorder = _mainnet_setup(
        tmp_path,
        monkeypatch,
        client=client,
        balance=XRPLRequestFailureException({"error": "actNotFound"}),
    )
    async with _client(app) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 402
    assert r.json()["code"] == "MAINNET_UNDERFUNDED"
    assert "have 0 XRP (0 drops)" in r.json()["message"]
    assert recorder.batches == []


@pytest.mark.parametrize(
    ("client", "balance", "needle"),
    [
        # server_state RPC itself raises: a network blip is not insolvency.
        (_FakeClient(error=TimeoutError("server_state timed out")), 10**9, "TimeoutError"),
        # server_state answers but reports failure.
        (_FakeClient(_FakeResponse({"error": "slowDown"}, ok=False)), 10**9, "server_state lookup"),
        # balance RPC raises a non-actNotFound failure.
        (
            _FakeClient(_FakeResponse(_server_state(1_000_000))),
            ConnectionError("balance rpc down"),
            "balance rpc down",
        ),
    ],
)
async def test_mainnet_preflight_infrastructure_failures_are_502_not_402(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: Any,
    balance: int | Exception,
    needle: str,
) -> None:
    app, recorder = _mainnet_setup(tmp_path, monkeypatch, client=client, balance=balance)
    async with _client(app) as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 502
    body = r.json()
    assert body["code"] == "ANCHOR_FAILED"
    assert needle in body["message"]
    assert recorder.batches == []


# ---------------------------------------------------------------------------
# emit_pending_added / MaxBodySizeMiddleware
# ---------------------------------------------------------------------------


async def test_emit_pending_added_reaches_subscribers() -> None:
    from sov_daemon.events import get_broadcaster
    from sov_daemon.server import emit_pending_added

    app = _make_app()
    broadcaster = get_broadcaster(app)
    queue = await broadcaster.subscribe()
    try:
        emit_pending_added(app, game_id="s42", round_key="3", envelope_hash=_HASH)
        event = queue.get_nowait()
    finally:
        await broadcaster.unsubscribe(queue)
    assert event == (
        "anchor.pending_added",
        {"game_id": "s42", "round": "3", "envelope_hash": _HASH},
    )


def _http_scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict[str, Any]:
    return {
        "type": "http",
        "method": "POST",
        "path": "/x",
        "headers": headers or [],
    }


class _Wire:
    """Captures ASGI ``send`` calls and feeds scripted ``receive`` messages."""

    def __init__(self, incoming: list[dict[str, Any]]) -> None:
        self.incoming = list(incoming)
        self.sent: list[dict[str, Any]] = []

    async def receive(self) -> dict[str, Any]:
        if self.incoming:
            return self.incoming.pop(0)
        return {"type": "http.disconnect"}

    async def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)

    @property
    def status(self) -> int | None:
        for m in self.sent:
            if m["type"] == "http.response.start":
                return int(m["status"])
        return None

    @property
    def body(self) -> bytes:
        return b"".join(m.get("body", b"") for m in self.sent if m["type"] == "http.response.body")


def _consumer(seen: dict[str, Any]) -> Any:
    """Inner ASGI app that drains the request body, then answers 200."""

    async def app(scope: Any, receive: Any, send: Any) -> None:
        total = 0
        while True:
            msg = await receive()
            if msg["type"] != "http.request":
                seen["terminal"] = msg["type"]
                break
            total += len(msg.get("body", b""))
            if not msg.get("more_body", False):
                break
        seen["total"] = total
        seen["after"] = (await receive())["type"]  # a second read after the body ended
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return app


async def test_middleware_streaming_over_cap_returns_413() -> None:
    from sov_daemon.server import MaxBodySizeMiddleware

    seen: dict[str, Any] = {}
    wire = _Wire(
        [
            {"type": "http.request", "body": b"x" * 600, "more_body": True},
            {"type": "http.request", "body": b"y" * 600, "more_body": False},
        ]
    )
    mw = MaxBodySizeMiddleware(_consumer(seen), max_bytes=1000)
    await mw(_http_scope(), wire.receive, wire.send)
    assert wire.status == 413
    payload = json.loads(wire.body)
    assert payload["code"] == "PAYLOAD_TOO_LARGE"
    assert "1000-byte limit" in payload["message"]
    assert "total" not in seen  # the handler never finished reading


async def test_middleware_streaming_exactly_at_cap_passes_through() -> None:
    from sov_daemon.server import MaxBodySizeMiddleware

    seen: dict[str, Any] = {}
    wire = _Wire(
        [
            {"type": "http.request", "body": b"x" * 500, "more_body": True},
            {"type": "http.request", "body": b"y" * 500, "more_body": False},
        ]
    )
    mw = MaxBodySizeMiddleware(_consumer(seen), max_bytes=1000)
    await mw(_http_scope(), wire.receive, wire.send)
    assert wire.status == 200
    assert wire.body == b"ok"
    assert seen["total"] == 1000
    assert seen["after"] == "http.disconnect"  # body already complete


async def test_middleware_passes_disconnect_through() -> None:
    from sov_daemon.server import MaxBodySizeMiddleware

    seen: dict[str, Any] = {}
    wire = _Wire([{"type": "http.disconnect"}])
    mw = MaxBodySizeMiddleware(_consumer(seen), max_bytes=10)
    await mw(_http_scope(), wire.receive, wire.send)
    assert seen["terminal"] == "http.disconnect"
    assert wire.status == 200


async def test_middleware_ignores_non_http_scopes() -> None:
    from sov_daemon.server import MaxBodySizeMiddleware

    calls: list[str] = []

    async def inner(scope: Any, receive: Any, send: Any) -> None:
        calls.append(scope["type"])

    mw = MaxBodySizeMiddleware(inner, max_bytes=1)
    wire = _Wire([])
    await mw({"type": "lifespan"}, wire.receive, wire.send)
    assert calls == ["lifespan"]
    assert wire.sent == []


@pytest.mark.parametrize(
    ("declared", "expected_status"),
    [(b"2000", 413), (b"1000", 200), (b"not-a-number", 200), (b"\xff\xfe", 200)],
)
async def test_middleware_content_length_precheck(declared: bytes, expected_status: int) -> None:
    from sov_daemon.server import MaxBodySizeMiddleware

    seen: dict[str, Any] = {}
    wire = _Wire([{"type": "http.request", "body": b"z" * 10, "more_body": False}])
    mw = MaxBodySizeMiddleware(_consumer(seen), max_bytes=1000)
    await mw(_http_scope([(b"content-length", declared)]), wire.receive, wire.send)
    assert wire.status == expected_status
    if expected_status == 413:
        assert "total" not in seen  # rejected before the body was read


async def test_middleware_streaming_413_through_a_real_starlette_route() -> None:
    """A chunked body with no Content-Length, read by a real Starlette handler.

    The 413 must be the response the client sees. Regression (fixed 2.3.5):
    Starlette's outer error middleware sent a 500 for the escaping
    _BodyTooLarge before our handler ran, so the 413 was a second
    http.response.start and the client saw the 500.
    """
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    from sov_daemon.server import MaxBodySizeMiddleware

    async def sink(request: Any) -> Any:
        data = await request.body()
        return PlainTextResponse(str(len(data)))

    async def chunks() -> Any:
        for _ in range(4):
            yield b"x" * 600

    app = MaxBodySizeMiddleware(Starlette(routes=[Route("/x", sink, methods=["POST"])]), 1000)
    async with _client(app) as c:
        r = await c.post("/x", content=chunks())
    assert r.status_code == 413
    assert r.json()["code"] == "PAYLOAD_TOO_LARGE"


def _oversized_wire() -> _Wire:
    return _Wire(
        [
            {"type": "http.request", "body": b"x" * 600, "more_body": True},
            {"type": "http.request", "body": b"x" * 600, "more_body": False},
        ]
    )


async def test_middleware_streaming_413_when_inner_app_swallows_the_error() -> None:
    """An inner app that catches the trip and answers 200 still yields one 413."""
    from sov_daemon.server import MaxBodySizeMiddleware

    async def forgiving(scope: Any, receive: Any, send: Any) -> None:
        try:
            while (await receive()).get("more_body", False):
                pass
        except Exception:
            pass
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    wire = _oversized_wire()
    await MaxBodySizeMiddleware(forgiving, max_bytes=1000)(_http_scope(), wire.receive, wire.send)
    starts = [m for m in wire.sent if m["type"] == "http.response.start"]
    assert [m["status"] for m in starts] == [413]
    assert json.loads(wire.body)["code"] == "PAYLOAD_TOO_LARGE"


async def test_middleware_streaming_trip_after_response_started_sends_no_second_start() -> None:
    """If the inner app already began its reply, the cap cannot replace it.

    The status line is on the wire, so a 413 would be a second
    http.response.start (an ASGI protocol error). The exchange just ends.
    """
    from sov_daemon.server import MaxBodySizeMiddleware

    async def eager(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        while (await receive()).get("more_body", False):
            pass

    wire = _oversized_wire()
    await MaxBodySizeMiddleware(eager, max_bytes=1000)(_http_scope(), wire.receive, wire.send)
    starts = [m for m in wire.sent if m["type"] == "http.response.start"]
    assert [m["status"] for m in starts] == [200]


# ---------------------------------------------------------------------------
# events.py
# ---------------------------------------------------------------------------


class _FakeEntry:
    """Minimal ``Path``-like games-dir entry for ``_poll_once``."""

    def __init__(
        self,
        name: str,
        *,
        is_dir: bool = True,
        has_state: bool = True,
        mtime: float | Exception = 1.0,
    ) -> None:
        self.name = name
        self._is_dir = is_dir
        self._has_state = has_state
        self.mtime = mtime

    def is_dir(self) -> bool:
        return self._is_dir

    def __truediv__(self, _other: str) -> _FakeEntry:
        return self

    def exists(self) -> bool:
        return self._has_state

    def stat(self) -> Any:
        if isinstance(self.mtime, Exception):
            raise self.mtime

        class _Stat:
            st_mtime = self.mtime

        return _Stat()


class _FakeRoot:
    def __init__(self, entries: list[_FakeEntry], exists: bool = True) -> None:
        self.entries = entries
        self._exists = exists

    def exists(self) -> bool:
        return self._exists

    def iterdir(self) -> Any:
        return iter(self.entries)


def _drain(queue: asyncio.Queue[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


async def test_poll_once_seeds_then_reports_changes_and_new_games(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sov_daemon.events as events

    broadcaster = events.EventBroadcaster()
    queue = await broadcaster.subscribe()
    try:
        broken = _FakeEntry("s5", mtime=OSError("vanished"))
        root = _FakeRoot(
            [
                _FakeEntry("afile", is_dir=False),
                _FakeEntry("nostate", has_state=False),
                _FakeEntry("s1", mtime=1.0),
                _FakeEntry("s2", mtime=2.0),
                broken,
            ]
        )
        monkeypatch.setattr(events, "games_dir", lambda: root)

        broadcaster._poll_once()
        assert _drain(queue) == []  # first poll only seeds
        assert broadcaster._last_mtimes == {"s1": 1.0, "s2": 2.0}  # unstat-able game dropped

        root.entries = [
            _FakeEntry("s1", mtime=1.0),  # unchanged
            _FakeEntry("s2", mtime=9.0),  # changed
            _FakeEntry("s3", mtime=3.0),  # new save
        ]
        broadcaster._poll_once()
        assert _drain(queue) == [
            ("game.state_changed", {"game_id": "s2"}),
            ("game.state_changed", {"game_id": "s3"}),
        ]

        root._exists = False
        broadcaster._poll_once()  # games dir vanished: quiet no-op, state retained
        assert _drain(queue) == []
        assert set(broadcaster._last_mtimes) == {"s1", "s2", "s3"}
    finally:
        await broadcaster.unsubscribe(queue)


async def test_poll_loop_survives_iteration_failure_and_cancels_cleanly(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import sov_daemon.events as events

    monkeypatch.setattr(events, "_STATE_POLL_INTERVAL_SECONDS", 0)
    broadcaster = events.EventBroadcaster()
    calls = 0
    second_call = asyncio.Event()

    def _poll() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("game dir deleted mid-scan")
        second_call.set()

    monkeypatch.setattr(broadcaster, "_poll_once", _poll)
    with caplog.at_level(logging.WARNING, logger="sov_daemon"):
        task = asyncio.create_task(broadcaster._poll_state_changes())
        await asyncio.wait_for(second_call.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert task.cancelled()
    failed = [r for r in caplog.records if r.getMessage() == "events.poll.failed"]
    assert len(failed) == 1
    assert failed[0].exception_type == "RuntimeError"  # type: ignore[attr-defined]


async def test_broadcast_drops_and_logs_when_a_queue_is_full(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from sov_daemon.events import EventBroadcaster

    broadcaster = EventBroadcaster()
    slow = await broadcaster.subscribe()
    fast = await broadcaster.subscribe()
    try:
        for i in range(broadcaster.QUEUE_MAXSIZE):
            slow.put_nowait(("filler", {"i": i}))
        with caplog.at_level(logging.WARNING, logger="sov_daemon"):
            broadcaster.broadcast("game.state_changed", {"game_id": "s1"})
        assert slow.qsize() == broadcaster.QUEUE_MAXSIZE  # the new event was dropped
        assert fast.get_nowait() == ("game.state_changed", {"game_id": "s1"})
        dropped = [r for r in caplog.records if r.getMessage() == "events.broadcast.dropped"]
        assert len(dropped) == 1
        assert dropped[0].endpoint == "game.state_changed"  # type: ignore[attr-defined]
    finally:
        await broadcaster.unsubscribe(slow)
        await broadcaster.unsubscribe(fast)


def test_get_chain_cache_is_created_once_per_app() -> None:
    from sov_daemon.events import ChainLookupCache, get_chain_cache

    app = _make_app()
    first = get_chain_cache(app)
    assert isinstance(first, ChainLookupCache)
    assert get_chain_cache(app) is first
    assert get_chain_cache(_make_app()) is not first


async def test_chain_cache_refetches_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    import sov_daemon.events as events

    now = [1000.0]
    monkeypatch.setattr(events._time, "monotonic", lambda: now[0])
    cache = events.ChainLookupCache()
    calls = 0

    async def _fetch() -> bool:
        nonlocal calls
        calls += 1
        return calls == 1

    assert await cache.get("T", _fetch) is True
    now[0] += 1.0
    assert await cache.get("T", _fetch) is True  # within TTL: cached
    now[0] += 10.0
    assert await cache.get("T", _fetch) is False  # expired: re-fetched
    assert calls == 2


async def test_module_level_emitters_are_noops_without_an_app_then_deliver() -> None:
    from sov_daemon.events import (
        emit_anchor_batch_complete,
        emit_anchor_pending_added,
        get_broadcaster,
    )

    # No default broadcaster yet (autouse fixture reset it): must not raise.
    emit_anchor_pending_added(game_id="s1", round_key="1", envelope_hash=_HASH)
    emit_anchor_batch_complete(game_id="s1", txid="T", rounds=["1"], explorer_url="u")

    broadcaster = get_broadcaster(_make_app())
    queue = await broadcaster.subscribe()
    try:
        emit_anchor_pending_added(game_id="s1", round_key="1", envelope_hash=_HASH)
        emit_anchor_batch_complete(game_id="s1", txid="T", rounds=["1"], explorer_url="u")
        events = _drain(queue)
    finally:
        await broadcaster.unsubscribe(queue)
    assert events == [
        ("anchor.pending_added", {"game_id": "s1", "round": "1", "envelope_hash": _HASH}),
        (
            "anchor.batch_complete",
            {"game_id": "s1", "txid": "T", "rounds": ["1"], "explorer_url": "u"},
        ),
    ]


async def test_sse_stream_emits_ready_then_ends_after_shutdown_frame() -> None:
    from sov_daemon.events import broadcast_shutdown, get_broadcaster, sse_stream

    app = _make_app()
    stream = sse_stream(app, network="testnet", readonly=True)
    ready = await stream.__anext__()
    assert ready == (
        b'event: daemon.ready\ndata: {"network":"testnet","readonly":true,"ipc_version":1}\n\n'
    )
    assert get_broadcaster(app).subscribers_count() == 1
    broadcast_shutdown(app)
    shutdown = await stream.__anext__()
    assert shutdown == b'event: daemon.shutdown\ndata: {"reason":"stop_command"}\n\n'
    with pytest.raises(StopAsyncIteration):
        await stream.__anext__()
    assert get_broadcaster(app).subscribers_count() == 0  # unsubscribed in finally


# ---------------------------------------------------------------------------
# log_fields
# ---------------------------------------------------------------------------


def test_json_formatter_surfaces_exception_type_and_detail_from_exc_info() -> None:
    from sov_daemon.log_fields import JsonLineFormatter

    try:
        raise KeyError("boom")
    except KeyError:
        import sys

        record = logging.LogRecord(
            "sov_daemon", logging.ERROR, __file__, 1, "daemon.failed detail", (), sys.exc_info()
        )
    payload = json.loads(JsonLineFormatter().format(record))
    assert payload["event"] == "daemon.failed"
    assert payload["level"] == "ERROR"
    assert payload["exception_type"] == "KeyError"
    assert payload["exception_detail"] == "'boom'"


def test_json_formatter_keeps_explicit_exception_fields() -> None:
    from sov_daemon.log_fields import JsonLineFormatter

    try:
        raise KeyError("boom")
    except KeyError:
        import sys

        record = logging.LogRecord(
            "sov_daemon", logging.ERROR, __file__, 1, "daemon.failed", (), sys.exc_info()
        )
    record.exception_type = "Custom"
    payload = json.loads(JsonLineFormatter().format(record))
    assert payload["exception_type"] == "Custom"
    assert "exception_detail" not in payload

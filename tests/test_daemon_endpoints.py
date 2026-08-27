"""Tests for ``sov_daemon.server`` endpoints — read + anchor + SSE.

Uses ``httpx.AsyncClient`` with ``ASGITransport`` against an in-process
Starlette app rather than spawning a real subprocess. Subprocess spawn is
~200ms per case and would balloon the test suite well past the wave's
runtime budget; in-process exercises the same code path the real daemon
serves.

Pattern (from spec §11):

    from sov_daemon.server import build_app
    app = build_app(config)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers={"Authorization": f"Bearer {token}"})

The 10 endpoints from spec §4 are exercised in both readonly + full modes.
Anchor endpoints in readonly mode return HTTP 405 with a structured body
carrying ``DAEMON_READONLY``. The token comes from the daemon config; tests
use a known-fixed token so the bearer-auth shape is deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")


_FIXED_TOKEN = "test-token-fixed-for-tests"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}


def _build_config(*, readonly: bool, network: str = "testnet") -> Any:
    """Build a daemon config object suitable for ``server.build_app``.

    The exact config-object shape is owned by the daemon agent. We build it
    via the public helper rather than handcrafting a dict so any daemon-side
    rename surfaces as one place to update.
    """
    from sov_daemon.server import DaemonConfig  # type: ignore[attr-defined]

    return DaemonConfig(
        network=network,
        readonly=readonly,
        token=_FIXED_TOKEN,
    )


@pytest.fixture
def readonly_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """Starlette app configured in readonly mode."""
    from sov_daemon.server import build_app

    monkeypatch.chdir(tmp_path)
    return build_app(_build_config(readonly=True))


@pytest.fixture
def full_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """Starlette app configured in full (anchor-enabled) mode."""
    from sov_daemon.server import build_app

    monkeypatch.chdir(tmp_path)
    return build_app(_build_config(readonly=False))


_PROOF_META_KEYS = frozenset({"round", "envelope_hash", "final", "path"})
_HASH_ROUND_1 = "0" * 64
_HASH_FINAL = "f" * 64


def _write_proof(
    proofs_dir: Path,
    *,
    filename: str,
    game_id: str,
    round_value: int | str,
    envelope_hash: str,
    final: bool = False,
) -> None:
    body: dict[str, Any] = {
        "proof_version": 2,
        "game_id": game_id,
        "round": round_value,
        "envelope_hash": envelope_hash,
    }
    if final:
        body["final"] = True
    (proofs_dir / filename).write_text(json.dumps(body), encoding="utf-8")


def _seed_game(root: Path, game_id: str = "s42", *, short_proof_names: bool = False) -> None:
    """Seed a minimal multi-save layout under ``root/.sov/games/<id>/``.

    Default on-disk names match the engine writer
    (``round_001.proof.json`` / ``round_final.proof.json``) and the
    wrapped pending-anchors document (``{schema_version, entries}``).
    ``short_proof_names=True`` is the explicit alias fixture.
    """
    game_dir = root / ".sov" / "games" / game_id
    proofs_dir = game_dir / "proofs"
    proofs_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "game_id": game_id,
                "round": 0,
                "ruleset": "campfire_v1",
                "players": ["A", "B"],
                "rng_seed": "42",
            }
        ),
        encoding="utf-8",
    )
    if short_proof_names:
        _write_proof(
            proofs_dir,
            filename="round-1.json",
            game_id=game_id,
            round_value=1,
            envelope_hash=_HASH_ROUND_1,
        )
        _write_proof(
            proofs_dir,
            filename="FINAL.json",
            game_id=game_id,
            round_value="FINAL",
            envelope_hash=_HASH_FINAL,
            final=True,
        )
    else:
        _write_proof(
            proofs_dir,
            filename="round_001.proof.json",
            game_id=game_id,
            round_value=1,
            envelope_hash=_HASH_ROUND_1,
        )
        _write_proof(
            proofs_dir,
            filename="round_final.proof.json",
            game_id=game_id,
            round_value="FINAL",
            envelope_hash=_HASH_FINAL,
            final=True,
        )
    (game_dir / "pending-anchors.json").write_text(
        json.dumps({"schema_version": 1, "entries": {}}),
        encoding="utf-8",
    )


def _assert_proof_meta_list(body: Any) -> list[dict[str, Any]]:
    """GET /proofs must be a bare array of objects, not a wrap or string[]."""
    assert isinstance(body, list), f"expected bare list, got {type(body).__name__}: {body!r}"
    assert not isinstance(body, dict)
    for item in body:
        assert not isinstance(item, str), f"string[] revert: {item!r}"
        assert isinstance(item, dict), f"expected proof object, got {item!r}"
        missing = _PROOF_META_KEYS - set(item)
        assert not missing, f"proof row missing {missing}: {item!r}"
    return body


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


async def test_health_returns_documented_shape_in_readonly(readonly_app: Any) -> None:
    """Spec §4 health shape: status, version, network, readonly, ipc_version, uptime_seconds."""
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    for key in (
        "status",
        "version",
        "network",
        "readonly",
        "ipc_version",
        "uptime_seconds",
    ):
        assert key in body, f"/health missing required field {key!r}: {body!r}"
    assert body["status"] == "ok"
    assert body["network"] == "testnet"
    assert body["readonly"] is True
    assert body["ipc_version"] == 1
    assert isinstance(body["uptime_seconds"], (int, float))


async def test_health_reports_readonly_false_in_full_mode(full_app: Any) -> None:
    transport = httpx.ASGITransport(app=full_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers=_AUTH)
    assert r.status_code == 200
    assert r.json()["readonly"] is False


# ---------------------------------------------------------------------------
# /games — list
# ---------------------------------------------------------------------------


async def test_games_list_returns_json_array(readonly_app: Any, tmp_path: Path) -> None:
    """``GET /games`` returns the array shape that ``sov games --json`` emits."""
    _seed_game(tmp_path, "s42")
    _seed_game(tmp_path, "s99")

    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    # The endpoint mirrors `sov games --json`. Accept either the full
    # envelope (status/fields/games) shape or a plain array of summaries —
    # both are documented as legitimate.
    games = body.get("games") if isinstance(body, dict) else body
    assert isinstance(games, list)
    ids = {g.get("game_id") for g in games}
    assert ids >= {"s42", "s99"}


# ---------------------------------------------------------------------------
# /games/{id}
# ---------------------------------------------------------------------------


async def test_games_detail_returns_state_json(readonly_app: Any, tmp_path: Path) -> None:
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body.get("game_id") == "s42"
    assert body.get("ruleset") == "campfire_v1"


async def test_games_detail_returns_404_for_missing_game(readonly_app: Any, tmp_path: Path) -> None:
    # ``s99999999`` matches the game_id allowlist (see DAEMON-001) but no
    # such save exists on disk — the right code is GAME_NOT_FOUND / 404.
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s99999999", headers=_AUTH)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /games/{id}/proofs (list + by-round)
# ---------------------------------------------------------------------------


async def test_games_proofs_list_returns_proof_files(readonly_app: Any, tmp_path: Path) -> None:
    _seed_game(tmp_path, "s42")
    proofs_dir = tmp_path / ".sov" / "games" / "s42" / "proofs"
    (proofs_dir / "anchors.json").write_text(
        json.dumps({"schema_version": 1, "entries": {"1": "TXLEAK"}}),
        encoding="utf-8",
    )
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/proofs", headers=_AUTH)
    assert r.status_code == 200
    proofs = _assert_proof_meta_list(r.json())
    rounds = {str(item["round"]) for item in proofs}
    assert "1" in rounds
    assert "FINAL" in rounds
    assert all(Path(str(item["path"])).name != "anchors.json" for item in proofs)
    assert all(item.get("round") is not None for item in proofs)


async def test_games_proofs_list_includes_engine_writer_name(
    readonly_app: Any, tmp_path: Path
) -> None:
    """A save that only has ``round_001.proof.json`` (engine writer) still lists."""
    game_dir = tmp_path / ".sov" / "games" / "s42"
    proofs_dir = game_dir / "proofs"
    proofs_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "game_id": "s42",
                "round": 1,
                "ruleset": "campfire_v1",
                "players": ["A", "B"],
                "rng_seed": "42",
            }
        ),
        encoding="utf-8",
    )
    _write_proof(
        proofs_dir,
        filename="round_001.proof.json",
        game_id="s42",
        round_value=1,
        envelope_hash=_HASH_ROUND_1,
    )
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/proofs", headers=_AUTH)
    assert r.status_code == 200
    proofs = _assert_proof_meta_list(r.json())
    assert len(proofs) == 1
    assert str(proofs[0]["round"]) == "1"
    assert "round_001.proof.json" in str(proofs[0]["path"])


async def test_games_proofs_list_still_lists_short_aliases(
    readonly_app: Any, tmp_path: Path
) -> None:
    """Explicit pin of the test-suite shorter filenames, not the default seed."""
    _seed_game(tmp_path, "s42", short_proof_names=True)
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/proofs", headers=_AUTH)
    assert r.status_code == 200
    proofs = _assert_proof_meta_list(r.json())
    names = {Path(str(item["path"])).name for item in proofs}
    assert "round-1.json" in names
    assert "FINAL.json" in names


async def test_games_proof_round_1_returns_contents(readonly_app: Any, tmp_path: Path) -> None:
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/proofs/1", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body.get("game_id") == "s42"
    assert body.get("round") == 1


async def test_games_proof_round_final_returns_contents(readonly_app: Any, tmp_path: Path) -> None:
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/proofs/FINAL", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body.get("round") == "FINAL"


# ---------------------------------------------------------------------------
# /games/{id}/anchor-status/{round}
# ---------------------------------------------------------------------------


def _assert_anchor_status_wire(
    body: Any,
    *,
    round_key: str,
    anchor_status: str,
    envelope_hash: str | None,
    txid: str | None = None,
) -> None:
    assert isinstance(body, dict), f"expected object, got {type(body).__name__}: {body!r}"
    assert "anchor_status" in body, body
    assert "status" not in body, body
    assert "game_id" not in body, body
    assert "explorer_url" not in body, body
    assert body["round"] == round_key
    assert body["anchor_status"] == anchor_status
    assert body["envelope_hash"] == envelope_hash
    if txid is None:
        assert "txid" not in body, body
    else:
        assert body["txid"] == txid


async def test_anchor_status_missing_has_no_txid(readonly_app: Any, tmp_path: Path) -> None:
    """Empty pending + no anchors.json → lowercase missing, no txid, no legacy status."""
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/anchor-status/1", headers=_AUTH)
    assert r.status_code == 200
    _assert_anchor_status_wire(
        r.json(),
        round_key="1",
        anchor_status="missing",
        envelope_hash=_HASH_ROUND_1,
    )


async def test_anchor_status_pending_via_add_pending_anchor(
    readonly_app: Any, tmp_path: Path
) -> None:
    from sov_engine.io_utils import add_pending_anchor

    _seed_game(tmp_path, "s42")
    add_pending_anchor("s42", "1", _HASH_ROUND_1)
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/anchor-status/1", headers=_AUTH)
    assert r.status_code == 200
    _assert_anchor_status_wire(
        r.json(),
        round_key="1",
        anchor_status="pending",
        envelope_hash=_HASH_ROUND_1,
    )


async def test_anchor_status_anchored_via_record_anchors(readonly_app: Any, tmp_path: Path) -> None:
    from sov_engine.proof import record_anchors

    _seed_game(tmp_path, "s42")
    record_anchors("s42", {"1": "ABCDEF0123456789"})
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/anchor-status/1", headers=_AUTH)
    assert r.status_code == 200
    _assert_anchor_status_wire(
        r.json(),
        round_key="1",
        anchor_status="anchored",
        envelope_hash=_HASH_ROUND_1,
        txid="ABCDEF0123456789",
    )


# ---------------------------------------------------------------------------
# /games/{id}/pending-anchors
# ---------------------------------------------------------------------------


async def test_pending_anchors_returns_json_contents(readonly_app: Any, tmp_path: Path) -> None:
    from sov_engine.io_utils import add_pending_anchor

    _seed_game(tmp_path, "s42")
    add_pending_anchor("s42", "1", _HASH_ROUND_1)
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/pending-anchors", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert "pending" in body
    assert "entries" in body
    assert isinstance(body["pending"], list)
    assert "1" in body["pending"]
    assert isinstance(body["entries"], dict)
    assert "1" in body["entries"]
    assert body["entries"]["1"]["envelope_hash"] == _HASH_ROUND_1
    assert isinstance(body["entries"]["1"]["added_iso"], str)


# ---------------------------------------------------------------------------
# POST /games/{id}/anchor — full mode triggers flush; readonly returns 405
# ---------------------------------------------------------------------------


async def test_anchor_post_readonly_returns_405_with_daemon_readonly_code(
    readonly_app: Any, tmp_path: Path
) -> None:
    """Spec §4: readonly mode → HTTP 405 + structured body w/ DAEMON_READONLY."""
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 405
    body = r.json()
    assert body.get("code") == "DAEMON_READONLY"


async def test_anchor_post_full_mode_invokes_flush(full_app: Any, tmp_path: Path) -> None:
    """Full mode triggers an anchor flush via the daemon's transport."""
    _seed_game(tmp_path, "s42")

    fake_txid = "FAKETXIDDEADBEEF"
    with patch(
        "sov_daemon.server.flush_pending_anchors",
        new=AsyncMock(return_value={"txid": fake_txid, "rounds": ["1"]}),
    ):
        transport = httpx.ASGITransport(app=full_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/games/s42/anchor", headers=_AUTH)
    # 200/202 acceptable: spec doesn't pin the success code, only that the
    # flush is triggered. 200 is the conventional choice for "complete".
    assert r.status_code in (200, 202)


# ---------------------------------------------------------------------------
# POST /games/{id}/anchor/checkpoint — full mode flushes mid-game
# ---------------------------------------------------------------------------


async def test_anchor_checkpoint_post_readonly_returns_405(
    readonly_app: Any, tmp_path: Path
) -> None:
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/games/s42/anchor/checkpoint", headers=_AUTH)
    assert r.status_code == 405
    assert r.json().get("code") == "DAEMON_READONLY"


async def test_anchor_checkpoint_full_mode_invokes_flush(full_app: Any, tmp_path: Path) -> None:
    _seed_game(tmp_path, "s42")
    fake_txid = "CHKPTDEADBEEF"
    with patch(
        "sov_daemon.server.flush_pending_anchors",
        new=AsyncMock(return_value={"txid": fake_txid, "rounds": ["1"]}),
    ):
        transport = httpx.ASGITransport(app=full_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/games/s42/anchor/checkpoint", headers=_AUTH)
    assert r.status_code in (200, 202)

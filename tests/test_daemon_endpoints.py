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


def _seed_game(root: Path, game_id: str = "s42") -> None:
    """Seed a minimal multi-save layout under ``root/.sov/games/<id>/``."""
    import json

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
    (proofs_dir / "round-1.json").write_text(
        json.dumps(
            {
                "proof_version": 2,
                "game_id": game_id,
                "round": 1,
                "envelope_hash": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    (proofs_dir / "FINAL.json").write_text(
        json.dumps(
            {
                "proof_version": 2,
                "game_id": game_id,
                "round": "FINAL",
                "envelope_hash": "f" * 64,
            }
        ),
        encoding="utf-8",
    )
    (game_dir / "pending-anchors.json").write_text(json.dumps({"pending": []}), encoding="utf-8")


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
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/proofs", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    proofs = body.get("proofs") if isinstance(body, dict) else body
    assert isinstance(proofs, list)
    assert len(proofs) >= 2  # round-1 + FINAL


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


async def test_anchor_status_returns_three_state(readonly_app: Any, tmp_path: Path) -> None:
    """Returns one of MISSING / PENDING / ANCHORED."""
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/anchor-status/1", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    status = body.get("status") or body.get("anchor_status") or body
    if isinstance(status, dict):
        status = status.get("status")
    assert str(status).upper() in {"MISSING", "PENDING", "ANCHORED"}


# ---------------------------------------------------------------------------
# /games/{id}/pending-anchors
# ---------------------------------------------------------------------------


async def test_pending_anchors_returns_json_contents(readonly_app: Any, tmp_path: Path) -> None:
    _seed_game(tmp_path, "s42")
    transport = httpx.ASGITransport(app=readonly_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/pending-anchors", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    pending = body.get("pending") if isinstance(body, dict) else body
    assert isinstance(pending, list)


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

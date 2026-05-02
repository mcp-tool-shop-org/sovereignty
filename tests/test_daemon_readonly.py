"""Tests for ``sov_daemon`` readonly mode contract.

Spec §4 + §9: ``--readonly`` skips seed load and disables anchor endpoints.
Anchor endpoints return HTTP 405 with structured body
``{"code":"DAEMON_READONLY","message":"...","hint":"..."}``. Read endpoints
work in both modes.

This file is a focused complement to ``test_daemon_endpoints.py``: it
exercises the readonly switch as a single coherent contract rather than
mixing it into the per-endpoint tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")


_FIXED_TOKEN = "test-readonly-token-fixed-for-tests"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}


def _build_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, readonly: bool) -> Any:
    from sov_daemon.server import DaemonConfig, build_app  # type: ignore[attr-defined]

    monkeypatch.chdir(tmp_path)
    return build_app(DaemonConfig(network="testnet", readonly=readonly, token=_FIXED_TOKEN))


def _seed_game(root: Path, game_id: str = "s42") -> None:
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
    (game_dir / "pending-anchors.json").write_text('{"pending":[]}', encoding="utf-8")


# ---------------------------------------------------------------------------
# Readonly mode — anchor endpoints are 405
# ---------------------------------------------------------------------------


async def test_readonly_anchor_post_returns_405_with_daemon_readonly_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spec §4: anchor endpoint in readonly → 405 + ``DAEMON_READONLY``."""
    _seed_game(tmp_path, "s42")
    app = _build_app(monkeypatch, tmp_path, readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/games/s42/anchor", headers=_AUTH)
    assert r.status_code == 405
    body = r.json()
    assert body.get("code") == "DAEMON_READONLY"
    assert "readonly" in str(body.get("message", "")).lower()
    # The hint should mention restarting without --readonly so operators have
    # an actionable next step.
    hint = body.get("hint") or ""
    assert "readonly" in hint.lower() or "restart" in hint.lower()


async def test_readonly_anchor_checkpoint_post_returns_405(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seed_game(tmp_path, "s42")
    app = _build_app(monkeypatch, tmp_path, readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/games/s42/anchor/checkpoint", headers=_AUTH)
    assert r.status_code == 405
    assert r.json().get("code") == "DAEMON_READONLY"


# ---------------------------------------------------------------------------
# Read endpoints — work in both modes
# ---------------------------------------------------------------------------


async def test_readonly_health_endpoint_returns_200(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = _build_app(monkeypatch, tmp_path, readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body.get("readonly") is True


async def test_full_health_endpoint_reports_readonly_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = _build_app(monkeypatch, tmp_path, readonly=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers=_AUTH)
    assert r.status_code == 200
    assert r.json().get("readonly") is False


async def test_readonly_games_list_returns_200(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Read endpoints are unaffected by readonly mode."""
    _seed_game(tmp_path, "s42")
    app = _build_app(monkeypatch, tmp_path, readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games", headers=_AUTH)
    assert r.status_code == 200


async def test_full_games_list_returns_200(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _seed_game(tmp_path, "s42")
    app = _build_app(monkeypatch, tmp_path, readonly=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games", headers=_AUTH)
    assert r.status_code == 200


async def test_readonly_pending_anchors_returns_200(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reading the pending-anchors index is allowed in readonly."""
    _seed_game(tmp_path, "s42")
    app = _build_app(monkeypatch, tmp_path, readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/pending-anchors", headers=_AUTH)
    assert r.status_code == 200

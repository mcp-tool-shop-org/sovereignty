"""Tests for ``sov_daemon`` bearer-token auth.

Spec §6 + §7: token is ``secrets.token_urlsafe(32)`` generated fresh per
daemon start, sent in ``Authorization: Bearer <token>``. Missing → 401,
wrong → 403, correct → 200. Preflight ``OPTIONS`` is exempt because
browsers don't send auth on preflight.

Pinned behaviors:

* Missing ``Authorization`` header → HTTP 401 + ``DAEMON_AUTH_MISSING``.
* Wrong token → HTTP 403 + ``DAEMON_AUTH_INVALID``.
* Correct token → HTTP 200 + endpoint payload.
* ``OPTIONS`` preflight does NOT require auth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")


_FIXED_TOKEN = "test-auth-token-fixed-for-tests"


def _build_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    from sov_daemon.server import DaemonConfig, build_app  # type: ignore[attr-defined]

    monkeypatch.chdir(tmp_path)
    return build_app(DaemonConfig(network="testnet", readonly=True, token=_FIXED_TOKEN))


# ---------------------------------------------------------------------------
# Missing Authorization → 401 + DAEMON_AUTH_MISSING
# ---------------------------------------------------------------------------


async def test_missing_authorization_returns_401_with_auth_missing_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spec: missing ``Authorization`` → 401 + ``{"code":"DAEMON_AUTH_MISSING",...}``."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 401, f"missing auth must return 401, got {r.status_code} {r.text!r}"
    body = r.json()
    assert body.get("code") == "DAEMON_AUTH_MISSING", (
        f"missing-auth body must carry DAEMON_AUTH_MISSING, got {body!r}"
    )


async def test_empty_bearer_token_returns_401(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``Authorization: Bearer`` with no token (empty) is treated as missing."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers={"Authorization": "Bearer "})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Wrong token → 403 + DAEMON_AUTH_INVALID
# ---------------------------------------------------------------------------


async def test_wrong_token_returns_403_with_auth_invalid_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spec: wrong token → 403 + ``{"code":"DAEMON_AUTH_INVALID",...}``."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers={"Authorization": "Bearer not-the-right-token"})
    assert r.status_code == 403, f"wrong token must return 403, got {r.status_code} {r.text!r}"
    body = r.json()
    assert body.get("code") == "DAEMON_AUTH_INVALID", (
        f"wrong-token body must carry DAEMON_AUTH_INVALID, got {body!r}"
    )


async def test_malformed_authorization_header_returns_401_or_403(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``Authorization: Basic ...`` (wrong scheme) is rejected — either as
    missing (no Bearer scheme) or invalid. Both 401 and 403 acceptable;
    must not be 200."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert r.status_code in (401, 403), (
        f"malformed auth scheme must be 401/403, got {r.status_code}"
    )


# ---------------------------------------------------------------------------
# Correct token → 200
# ---------------------------------------------------------------------------


async def test_correct_token_returns_200(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(
            "/health",
            headers={"Authorization": f"Bearer {_FIXED_TOKEN}"},
        )
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---------------------------------------------------------------------------
# OPTIONS preflight exempt from auth
# ---------------------------------------------------------------------------


async def test_options_preflight_does_not_require_authorization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Browsers don't send ``Authorization`` on preflight, so the daemon
    MUST answer ``OPTIONS`` before the auth middleware runs (coordinator
    brief item #7)."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.options(
            "/health",
            headers={
                "Origin": "tauri://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert r.status_code == 204, (
        f"OPTIONS preflight must respond 204 without auth, got {r.status_code}"
    )

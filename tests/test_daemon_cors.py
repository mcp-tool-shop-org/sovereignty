"""Tests for ``sov_daemon`` CORS posture — locked at the contract level.

Spec §7: ``Access-Control-Allow-Origin: *`` on all endpoints. The bearer
token in ``Authorization`` is the actual auth gate; CORS origin restrictions
add no real security on a localhost-bound port. **This is locked at the
contract level so agents don't default-restrict and silently break Wave 4
(the Tauri shell, whose webview origin is cross-origin to ``127.0.0.1``).**

CORS preflight (``OPTIONS``) must respond ``204 No Content`` with the
documented headers BEFORE the bearer-auth middleware runs — browsers don't
send ``Authorization`` on preflight by spec.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")


_FIXED_TOKEN = "test-cors-token-fixed-for-tests"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}


def _build_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, readonly: bool = True) -> Any:
    from sov_daemon.server import DaemonConfig, build_app  # type: ignore[attr-defined]

    monkeypatch.chdir(tmp_path)
    return build_app(DaemonConfig(network="testnet", readonly=readonly, token=_FIXED_TOKEN))


# ---------------------------------------------------------------------------
# OPTIONS preflight returns 204 with the documented headers
# ---------------------------------------------------------------------------


async def test_options_preflight_health_returns_204_with_cors_headers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spec §7: ``OPTIONS /health`` → 204 with origin=*, methods, headers,
    max-age. **No Authorization header sent.** Browsers don't send auth on
    preflight, so the daemon must answer preflight before auth middleware."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.options(
            "/health",
            headers={
                "Origin": "tauri://localhost",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
    assert r.status_code == 204, (
        f"OPTIONS preflight must return 204, got {r.status_code} {r.text!r}"
    )
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    methods = r.headers.get("Access-Control-Allow-Methods", "")
    for verb in ("GET", "POST", "OPTIONS"):
        assert verb in methods, f"preflight missing method {verb}: {methods!r}"
    allow_headers = r.headers.get("Access-Control-Allow-Headers", "")
    for header in ("Authorization", "Content-Type"):
        assert header.lower() in allow_headers.lower(), (
            f"preflight missing allow-header {header}: {allow_headers!r}"
        )
    assert r.headers.get("Access-Control-Max-Age") == "600"


async def test_options_preflight_anchor_post_returns_204(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Preflight on a write endpoint also passes — auth runs only on the
    actual request, not on the preflight."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.options(
            "/games/s42/anchor",
            headers={
                "Origin": "tauri://localhost",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
    assert r.status_code == 204
    assert r.headers.get("Access-Control-Allow-Origin") == "*"


# ---------------------------------------------------------------------------
# Origin: * on actual GET responses
# ---------------------------------------------------------------------------


async def test_get_health_includes_cors_allow_origin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``GET /health`` (with auth) → response carries ``Allow-Origin: *``."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers={**_AUTH, "Origin": "tauri://localhost"})
    assert r.status_code == 200
    assert r.headers.get("Access-Control-Allow-Origin") == "*", (
        "spec §7 locks Allow-Origin: * on every endpoint"
    )


async def test_get_health_allow_origin_is_star_not_echoed_origin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``Allow-Origin`` is the literal ``*``, not an echo of the request
    Origin header. Echoing breaks Wave 4 by accident if the daemon agent
    plugged in a default-restrict middleware."""
    app = _build_app(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(
            "/health",
            headers={**_AUTH, "Origin": "https://attacker.example"},
        )
    assert r.status_code == 200
    assert r.headers.get("Access-Control-Allow-Origin") == "*"

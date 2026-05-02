"""Wave 9 Stage 7-B regression tests for ``sov_daemon`` domain amends.

Each test pins a specific finding from
``swarm-1777686810-67fd/wave-8/audit/daemon-findings.yaml`` so the next
audit can match a green test to a closed finding.

Coverage:

* DAEMON-B-009 — uvicorn explicit limits + 1 MiB body cap (HIGH).
* DAEMON-B-013 — ``--log-format=json`` flag + JSON-line formatter.
* DAEMON-B-014 — SSE max-clients cap + per-queue backpressure.
* DAEMON-B-005/006 — daemon error sites route through ``sov_cli.errors``
  factories, not inline ``SovError(code=...)`` literals.
* DAEMON-B-008 — Rust↔TS struct-parity grep-test for ``DaemonStatus``.
* DAEMON-B-012 — ``/health`` adds ``pending_anchors_summary`` field.
"""

from __future__ import annotations

import inspect
import io
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")


_FIXED_TOKEN = "test-amend-wave9-token"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}


def _build_app(*, readonly: bool = True, network: str = "testnet") -> Any:
    from sov_daemon.server import DaemonConfig, build_app

    return build_app(DaemonConfig(network=network, readonly=readonly, token=_FIXED_TOKEN))


# ---------------------------------------------------------------------------
# DAEMON-B-009 — uvicorn limits + body cap (HIGH, MANDATORY)
# ---------------------------------------------------------------------------


def test_daemon_b_009_uvicorn_config_sets_explicit_limits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-B-009 MANDATORY: uvicorn.Config kwargs at daemon startup
    must include the four resource limits explicitly. Default-everything
    config is what the audit caught (no body cap, no concurrency cap, no
    request recycle).

    We monkeypatch ``uvicorn.Config`` to capture the kwargs without
    actually starting a server (server.run would block forever). The
    test asserts each named limit reaches the constructor call.
    """
    monkeypatch.chdir(tmp_path)

    captured_kwargs: dict[str, Any] = {}

    class _StubServer:
        def __init__(self, _config: Any) -> None:
            self._config = _config

        def run(self) -> None:
            return  # don't actually serve

    def _stub_config(*args: Any, **kwargs: Any) -> Any:
        captured_kwargs.update(kwargs)
        return type("_Cfg", (), {})()

    import uvicorn

    monkeypatch.setattr(uvicorn, "Config", _stub_config)
    monkeypatch.setattr(uvicorn, "Server", _StubServer)

    from sov_daemon.lifecycle import run_foreground

    run_foreground(network="testnet", readonly=True)

    # Each explicit limit must be set; presence is the contract, not the
    # exact value (operators may tune later).
    assert "limit_concurrency" in captured_kwargs, (
        "uvicorn.Config missing limit_concurrency — DAEMON-B-009 regression"
    )
    assert "limit_max_requests" in captured_kwargs
    assert "timeout_keep_alive" in captured_kwargs
    assert "h11_max_incomplete_event_size" in captured_kwargs
    # Sanity-check the floor values match the AMEND brief (allow operator
    # tuning above but not removal).
    assert captured_kwargs["limit_concurrency"] == 64
    assert captured_kwargs["limit_max_requests"] == 10_000
    assert captured_kwargs["timeout_keep_alive"] == 5
    assert captured_kwargs["h11_max_incomplete_event_size"] == 16384


async def test_daemon_b_009_max_body_size_rejects_oversized_post(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-B-009 MANDATORY: a POST body > 1 MiB returns 413
    PAYLOAD_TOO_LARGE with the structured-error envelope shape; the
    handler never sees the bloated payload."""
    from sov_daemon.server import MaxBodySizeMiddleware

    monkeypatch.chdir(tmp_path)
    app = _build_app(readonly=False)
    wrapped = MaxBodySizeMiddleware(app, max_bytes=1024)  # tighten cap for test
    transport = httpx.ASGITransport(app=wrapped)
    payload = b"x" * 2048  # > 1024 bytes
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/games/s42/anchor", content=payload, headers=_AUTH)
    assert r.status_code == 413, f"expected 413, got {r.status_code}"
    body = r.json()
    assert body.get("code") == "PAYLOAD_TOO_LARGE"
    assert "limit" in body.get("message", "").lower()


async def test_daemon_b_009_small_body_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-B-009 MANDATORY: a POST body < 1 MiB flows through the
    middleware. We use the readonly daemon path (returns 405) so the
    body-cap layer doesn't gate on auth state — confirms the middleware
    is permissive on under-cap bodies."""
    from sov_daemon.server import MaxBodySizeMiddleware

    monkeypatch.chdir(tmp_path)
    app = _build_app(readonly=True)
    wrapped = MaxBodySizeMiddleware(app, max_bytes=1_048_576)
    transport = httpx.ASGITransport(app=wrapped)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/games/s42/anchor", content=b"{}", headers=_AUTH)
    # Readonly daemon returns 405 DAEMON_READONLY for the anchor POST —
    # what matters here is that 413 is NOT returned (middleware passed
    # the small body through).
    assert r.status_code != 413, "small body must not be rejected"


# ---------------------------------------------------------------------------
# DAEMON-B-013 — structured JSON-lines logging
# ---------------------------------------------------------------------------


def test_daemon_b_013_log_fields_registry_known_fields() -> None:
    """The registry exports CORE + CONTEXT field names. The JSON formatter
    emits ONLY whitelisted fields from extra= so a typo doesn't end up
    in the wire format."""
    from sov_daemon.log_fields import (
        CONTEXT_FIELDS,
        CORE_FIELDS,
        KNOWN_FIELDS,
    )

    # Core fields are synthesised by the formatter, always present.
    assert "timestamp_iso" in CORE_FIELDS
    assert "level" in CORE_FIELDS
    assert "logger" in CORE_FIELDS
    assert "event" in CORE_FIELDS

    # Context fields: the brief explicitly names these.
    for required in (
        "account",
        "txid",
        "network",
        "port",
        "pid",
        "round_key",
        "game_id",
        "error_code",
        "duration_ms",
        "client_ip",
        "endpoint",
        "status",
    ):
        assert required in CONTEXT_FIELDS, f"missing context field: {required}"

    assert KNOWN_FIELDS == CORE_FIELDS | CONTEXT_FIELDS


def test_daemon_b_013_json_line_formatter_emits_one_json_line() -> None:
    """The formatter produces one JSON object per record, with core
    fields synthesised and whitelisted context fields promoted from
    ``extra=``."""
    from sov_daemon.log_fields import JsonLineFormatter

    f = JsonLineFormatter()
    record = logging.LogRecord(
        name="sov_daemon",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="anchor.submit",
        args=(),
        exc_info=None,
    )
    record.__dict__["game_id"] = "s42"
    record.__dict__["txid"] = "DEADBEEF"
    record.__dict__["round_key"] = "1"
    out = f.format(record)
    payload = json.loads(out)
    assert payload["event"] == "anchor.submit"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "sov_daemon"
    assert payload["game_id"] == "s42"
    assert payload["txid"] == "DEADBEEF"
    assert payload["round_key"] == "1"
    # timestamp_iso is synthesised; existence + ISO8601 shape suffice.
    assert "timestamp_iso" in payload
    assert "T" in payload["timestamp_iso"]


def test_daemon_b_013_json_line_formatter_drops_unknown_fields() -> None:
    """Fields outside ``CONTEXT_FIELDS`` are NOT promoted to the wire —
    a typo in ``extra=`` doesn't leak into the structured log."""
    from sov_daemon.log_fields import JsonLineFormatter

    f = JsonLineFormatter()
    record = logging.LogRecord(
        name="sov_daemon",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="event.fired",
        args=(),
        exc_info=None,
    )
    record.__dict__["bogus_field"] = "should-not-appear"
    out = f.format(record)
    payload = json.loads(out)
    assert "bogus_field" not in payload


def test_daemon_b_013_argv_parsing_sets_log_format_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--log-format=json`` on argv sets ``SOV_DAEMON_LOG_FORMAT`` env
    var and removes the flag so downstream code (run_foreground_from_env)
    consumes a clean argv."""
    from sov_daemon.__main__ import _parse_log_format_arg

    monkeypatch.delenv("SOV_DAEMON_LOG_FORMAT", raising=False)
    monkeypatch.setattr(sys, "argv", ["sov_daemon", "--log-format=json"])
    _parse_log_format_arg()
    assert sys.argv == ["sov_daemon"]
    assert sys.executable  # smoke
    import os

    assert os.environ.get("SOV_DAEMON_LOG_FORMAT") == "json"


def test_daemon_b_013_argv_parsing_handles_separated_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--log-format json`` (space-separated) also works."""
    from sov_daemon.__main__ import _parse_log_format_arg

    monkeypatch.delenv("SOV_DAEMON_LOG_FORMAT", raising=False)
    monkeypatch.setattr(sys, "argv", ["sov_daemon", "--log-format", "human"])
    _parse_log_format_arg()
    import os

    assert os.environ.get("SOV_DAEMON_LOG_FORMAT") == "human"


# ---------------------------------------------------------------------------
# DAEMON-B-014 — SSE max-clients cap
# ---------------------------------------------------------------------------


async def test_daemon_b_014_subscriber_cap_refuses_overflow() -> None:
    """``EventBroadcaster`` raises ``SubscribersExhaustedError`` when the
    subscriber set reaches ``MAX_SUBSCRIBERS``. Translates to HTTP 503
    at the request boundary."""
    from sov_daemon.events import EventBroadcaster, SubscribersExhaustedError

    bcast = EventBroadcaster()
    # Fill to the cap.
    queues = []
    for _ in range(bcast.MAX_SUBSCRIBERS):
        queues.append(await bcast.subscribe())
    # Next subscribe must raise.
    with pytest.raises(SubscribersExhaustedError):
        await bcast.subscribe()


def test_daemon_b_014_per_subscriber_queue_is_bounded() -> None:
    """Per-subscriber queues use ``QUEUE_MAXSIZE`` so a slow consumer
    drops events rather than pinning unbounded RAM."""
    from sov_daemon.events import EventBroadcaster

    bcast = EventBroadcaster()
    assert bcast.QUEUE_MAXSIZE > 0
    # MAX_SUBSCRIBERS is a small finite cap — explicit floor.
    assert 1 <= bcast.MAX_SUBSCRIBERS <= 1024


async def test_daemon_b_014_events_handler_returns_503_when_full(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``GET /events`` returns 503 ``SSE_SUBSCRIBERS_EXHAUSTED`` when the
    broadcaster is at the cap. Ensures we don't open a streaming
    connection only to close it after the broadcaster refuses."""
    monkeypatch.chdir(tmp_path)
    app = _build_app(readonly=True)
    from sov_daemon.events import get_broadcaster

    broadcaster = get_broadcaster(app)
    # Saturate the broadcaster's subscriber set in-process.
    queues = []
    for _ in range(broadcaster.MAX_SUBSCRIBERS):
        queues.append(await broadcaster.subscribe())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/events", headers=_AUTH)
    assert r.status_code == 503
    body = r.json()
    assert body.get("code") == "SSE_SUBSCRIBERS_EXHAUSTED"


# ---------------------------------------------------------------------------
# DAEMON-B-005 / B-006 — registry-only error sites
# ---------------------------------------------------------------------------


def test_daemon_b_005_no_inline_sov_error_in_server_py() -> None:
    """No direct ``SovError(code=..., message=...)`` calls in
    ``sov_daemon/server.py``; every emit routes through a factory in
    ``sov_cli.errors``. Pinned via grep-test."""
    server_path = Path(__file__).resolve().parent.parent / "sov_daemon" / "server.py"
    text = server_path.read_text(encoding="utf-8")
    # Strip out the ``_error_response`` helper signature so we don't
    # match the helper's own ``code=...`` parameter declaration.
    # ``SovError(code=`` is the inline-construction smell the audit
    # called out.
    pattern = re.compile(r"SovError\s*\(\s*code\s*=", re.MULTILINE)
    matches = pattern.findall(text)
    assert not matches, (
        f"sov_daemon/server.py has inline SovError(code=...) emits "
        f"({len(matches)}); route through sov_cli.errors factories instead."
    )


def test_daemon_b_005_factories_resolve_at_import_time() -> None:
    """The factory functions the daemon depends on must exist in
    ``sov_cli.errors`` post-CLI-amend. Imported directly here so a
    rename or removal fails CI."""
    from sov_cli.errors import (
        daemon_anchor_failed_error,
        daemon_game_not_found_error,
        daemon_invalid_game_id_error,
        daemon_invalid_network_error,
        daemon_invalid_round_error,
        daemon_proof_not_found_error,
        daemon_proof_unreadable_error,
        daemon_xrpl_not_installed_error,
    )

    # Smoke: each callable returns something with a ``code`` attribute.
    for fn, args in (
        (daemon_invalid_game_id_error, ("bad",)),
        (daemon_invalid_round_error, ("bad",)),
        (daemon_game_not_found_error, ("s42",)),
        (daemon_proof_not_found_error, ("s42", "1")),
        (daemon_proof_unreadable_error, ("OSError",)),
        (daemon_invalid_network_error, ("typo",)),
        (daemon_xrpl_not_installed_error, ("ImportError",)),
        (daemon_anchor_failed_error, ("RuntimeError", "boom")),
    ):
        result = fn(*args)
        assert hasattr(result, "code")
        assert hasattr(result, "message")
        assert hasattr(result, "hint")


# ---------------------------------------------------------------------------
# DAEMON-B-008 — Rust↔TS DaemonStatus struct-parity grep-test
# ---------------------------------------------------------------------------


def _extract_rust_struct_fields(rust_src: str, struct_name: str) -> set[str]:
    """Grep ``pub struct <name> { pub field_a: ..., pub field_b: ... }``."""
    pattern = re.compile(
        rf"pub struct {re.escape(struct_name)}\s*{{(.*?)}}",
        re.DOTALL,
    )
    m = pattern.search(rust_src)
    if not m:
        return set()
    body = m.group(1)
    field_pattern = re.compile(r"pub\s+(\w+)\s*:", re.MULTILINE)
    return set(field_pattern.findall(body))


def _extract_ts_interface_fields(ts_src: str, iface_name: str) -> set[str]:
    """Grep ``export interface <name> { field_a: ...; field_b?: ... }``."""
    pattern = re.compile(
        rf"export interface {re.escape(iface_name)}\s*{{(.*?)}}",
        re.DOTALL,
    )
    m = pattern.search(ts_src)
    if not m:
        return set()
    body = m.group(1)
    field_pattern = re.compile(r"^\s*(\w+)\??\s*:", re.MULTILINE)
    return set(field_pattern.findall(body))


def test_daemon_b_008_daemon_status_rust_ts_parity() -> None:
    """``DaemonStatus`` field names must match between Rust struct and
    TS interface. A future addition that lands on one side only causes
    silent webview drift; this grep pin catches it at CI time."""
    repo_root = Path(__file__).resolve().parent.parent
    rust_src_path = repo_root / "app" / "src-tauri" / "src" / "commands.rs"
    ts_src_path = repo_root / "app" / "src" / "types" / "daemon.ts"
    if not rust_src_path.exists() or not ts_src_path.exists():
        pytest.skip("app/ not present (pre-Wave-4)")
    rust_fields = _extract_rust_struct_fields(
        rust_src_path.read_text(encoding="utf-8"), "DaemonStatus"
    )
    ts_fields = _extract_ts_interface_fields(
        ts_src_path.read_text(encoding="utf-8"), "DaemonStatus"
    )
    assert rust_fields, "Rust DaemonStatus struct fields not extracted (regex drift?)"
    assert ts_fields, "TS DaemonStatus interface fields not extracted (regex drift?)"
    # Allow Rust to carry serde-renamed fields; the assertion is on
    # the public on-the-wire field names. Currently the structs use
    # field-name parity (no #[serde(rename)] on DaemonStatus), so the
    # sets must match.
    assert rust_fields == ts_fields, (
        f"DaemonStatus drift: rust={sorted(rust_fields)} ts={sorted(ts_fields)}"
    )


# ---------------------------------------------------------------------------
# DAEMON-B-012 — /health includes pending_anchors_summary
# ---------------------------------------------------------------------------


async def test_daemon_b_012_health_includes_pending_anchors_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``GET /health`` carries the new ``pending_anchors_summary`` field
    so doctor / audit-viewer can render queued-rounds status without
    walking the games dir themselves. Empty dict when no queue exists."""
    monkeypatch.chdir(tmp_path)
    app = _build_app(readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "pending_anchors_summary" in body
    # No saved games, no pending rows — empty dict.
    assert body["pending_anchors_summary"] == {}


async def test_daemon_b_012_health_summarises_pending_per_game(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Seed one pending row, hit /health, assert it surfaces."""
    monkeypatch.chdir(tmp_path)
    # Seed game + pending entry.
    from sov_engine.io_utils import add_pending_anchor

    add_pending_anchor("s42", "1", "a" * 64)
    app = _build_app(readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health", headers=_AUTH)
    body = r.json()
    summary = body.get("pending_anchors_summary", {})
    assert "s42" in summary, f"expected s42 in summary; got {summary}"
    assert summary["s42"]["pending_count"] == 1
    assert summary["s42"]["oldest_added_iso"]


# ---------------------------------------------------------------------------
# DAEMON-B-010 — httpx not imported by daemon at runtime
# ---------------------------------------------------------------------------


def test_daemon_b_010_no_httpx_import_in_daemon_runtime() -> None:
    """``sov_daemon/`` must not import ``httpx`` at runtime; httpx is a
    test-only dep (used by tests/test_daemon_endpoints.py via
    ``ASGITransport``). ci-tooling uses this pin to safely move httpx
    out of the [daemon] runtime extra into a test extra."""
    daemon_pkg_root = Path(__file__).resolve().parent.parent / "sov_daemon"
    for py in daemon_pkg_root.rglob("*.py"):
        # Skip AppleDouble resource-fork droppings (T9-Shared bug) — they
        # carry the ._<name>.py prefix and are not real Python source.
        if py.name.startswith("._"):
            continue
        text = py.read_text(encoding="utf-8")
        # Allow ``httpx`` mentions in docstrings / comments. The
        # discriminator is whether the source has an ``import httpx`` or
        # ``from httpx`` line.
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            assert not stripped.startswith("import httpx"), (
                f"{py}: runtime import of httpx — DAEMON-B-010 violation"
            )
            assert not stripped.startswith("from httpx"), (
                f"{py}: runtime import of httpx — DAEMON-B-010 violation"
            )


# ---------------------------------------------------------------------------
# DAEMON-B-001 — handshake atomic_write_text(..., mode=0o600) consolidation
# ---------------------------------------------------------------------------


def test_daemon_b_001_handshake_uses_mode_kwarg() -> None:
    """``_write_handshake`` calls ``atomic_write_text(..., mode=0o600)``
    rather than the post-replace ``os.chmod(...)`` Stage A placeholder.
    Pinned via source inspection — the kwarg is now the contract."""
    from sov_daemon import lifecycle

    src = inspect.getsource(lifecycle._write_handshake)
    # The new contract: mode=0o600 in the atomic_write_text call.
    assert "mode=0o600" in src, (
        "_write_handshake must pass mode=0o600 to atomic_write_text "
        "(DAEMON-B-001: drop the post-rename os.chmod placeholder)."
    )
    # And the post-rename os.chmod block is gone.
    assert "os.chmod(path, 0o600)" not in src, (
        "_write_handshake still has the inline os.chmod fallback; "
        "the atomic_write_text mode= kwarg subsumes it."
    )


# Silence unused-import warnings in environments where some imports above
# are only consumed by parametrize / fixtures.
_ = io

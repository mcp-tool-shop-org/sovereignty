"""Tests for ``sov_daemon`` SSE event stream — fire-and-forget contract.

Spec §5: each event is ``event: <type>\\ndata: <json>\\n\\n``. **No ``id:``
line** — v2.1 ships without buffer/replay support, so reconnecting clients
re-fetch state via ``GET /games/{id}`` and don't expect missed events.

Pinned behaviors:

* First event on each new SSE connection is ``daemon.ready`` carrying the
  network + readonly flag + ipc_version.
* ``add_pending_anchor`` triggers an ``anchor.pending_added`` event.
* Successful ``anchor_batch`` emits ``anchor.batch_complete``.
* State.json mtime change emits ``game.state_changed`` (1s polling).
* Reconnect → fresh ``daemon.ready``, no replay of missed events.
* No ``id:`` lines anywhere in the emitted stream (no buffer support).

DAEMON-007: this file used to skip via ``httpx.ASGITransport`` because that
transport buffers SSE responses. We now bind a real uvicorn server on
``127.0.0.1:0`` and hit it with ``httpx.AsyncClient`` over a real socket
— streaming works as the spec intends.
"""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")
uvicorn = pytest.importorskip("uvicorn", reason="daemon extra not installed")


_FIXED_TOKEN = "test-sse-token-fixed-for-tests"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}


def _build_config(**overrides: Any) -> Any:
    from sov_daemon.server import DaemonConfig  # type: ignore[attr-defined]

    defaults: dict[str, Any] = {
        "network": "testnet",
        "readonly": True,
        "token": _FIXED_TOKEN,
    }
    defaults.update(overrides)
    return DaemonConfig(**defaults)


def _seed_game(root: Path, game_id: str = "s42") -> Path:
    """Seed minimal multi-save layout so state-mtime polling has a target."""
    game_dir = root / ".sov" / "games" / game_id
    game_dir.mkdir(parents=True, exist_ok=True)
    state_path = game_dir / "state.json"
    state_path.write_text(
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
    (game_dir / "pending-anchors.json").write_text(json.dumps({"pending": []}), encoding="utf-8")
    return state_path


def _claim_free_port() -> int:
    """Bind to ``127.0.0.1:0`` to claim a free port from the kernel."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _ServerFixture:
    """Live uvicorn server bound to a real socket on ``127.0.0.1:<port>``."""

    def __init__(self, app: Any, port: int) -> None:
        self.app = app
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
            access_log=False,
            lifespan="on",
        )
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())
        # Poll the started flag instead of sleeping — boot is typically
        # under 100ms but a slow CI runner can take longer.
        for _ in range(100):
            if self._server.started:
                return
            await asyncio.sleep(0.05)
        raise RuntimeError("uvicorn server did not start within 5s")

    async def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except TimeoutError:
                self._task.cancel()


@pytest.fixture
async def real_daemon(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncIterator[str]:
    """Spin up a real uvicorn-bound daemon for one test. Yields its base URL.

    The daemon is in readonly mode by default; tests that need full mode
    can override via the wrapper fixtures below. Each test gets its own
    port + ``tmp_path`` so concurrent runs don't collide.
    """
    from sov_daemon.events import reset_default_broadcaster
    from sov_daemon.server import build_app

    monkeypatch.chdir(tmp_path)
    reset_default_broadcaster()
    app = build_app(_build_config(readonly=True))
    port = _claim_free_port()
    server = _ServerFixture(app, port)
    await server.start()
    try:
        yield server.base_url
    finally:
        await server.stop()
        reset_default_broadcaster()


async def _read_first_event(
    client: httpx.AsyncClient, path: str = "/events"
) -> tuple[str, dict[str, Any]]:
    """Open SSE stream and read exactly the first event off the wire."""
    async with client.stream("GET", path, headers=_AUTH) as response:
        assert response.status_code == 200, f"/events expected 200, got {response.status_code}"
        ctype = response.headers.get("content-type", "")
        assert ctype.startswith("text/event-stream"), (
            f"/events content-type must start with text/event-stream, got {ctype!r}"
        )
        event_type = ""
        data_buf: list[str] = []
        async with asyncio.timeout(5.0):
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    data_buf.append(line[len("data:") :].strip())
                elif line == "" and (event_type or data_buf):
                    break
        payload: dict[str, Any] = {}
        if data_buf:
            payload = json.loads("".join(data_buf))
        return event_type, payload


# ---------------------------------------------------------------------------
# daemon.ready first event
# ---------------------------------------------------------------------------


async def test_sse_first_event_is_daemon_ready(real_daemon: str) -> None:
    """Spec §5: first event on each connection is ``daemon.ready``."""
    async with httpx.AsyncClient(base_url=real_daemon, timeout=10.0) as client:
        event_type, payload = await _read_first_event(client)
    assert event_type == "daemon.ready", f"first event must be daemon.ready, got {event_type!r}"
    assert payload.get("network") == "testnet"
    assert payload.get("readonly") is True
    assert payload.get("ipc_version") == 1


async def test_sse_no_id_lines_in_event_stream(real_daemon: str) -> None:
    """Spec §5: NO ``id:`` lines (no Last-Event-ID buffer in v2.1)."""
    async with (
        httpx.AsyncClient(base_url=real_daemon, timeout=10.0) as client,
        client.stream("GET", "/events", headers=_AUTH) as response,
    ):
        collected: list[str] = []
        # daemon.ready is the only event that fires unprompted. After we
        # see its terminating blank line, the contract is verified — no
        # need to wait for a second event the daemon may never emit.
        try:
            async with asyncio.timeout(3.0):
                async for line in response.aiter_lines():
                    collected.append(line)
                    if collected.count("") >= 1 and any(
                        line.startswith("event:") for line in collected
                    ):
                        break
        except TimeoutError:
            pass
    id_lines = [line for line in collected if line.startswith("id:")]
    assert not id_lines, f"v2.1 SSE must not emit id: lines, got: {id_lines!r}"
    # Sanity: we did read at least the daemon.ready frame.
    assert any("daemon.ready" in line for line in collected), (
        f"never saw daemon.ready: {collected!r}"
    )


# ---------------------------------------------------------------------------
# anchor.pending_added — emitted via add_pending_anchor hook
# ---------------------------------------------------------------------------


async def test_sse_emits_anchor_pending_added_event(real_daemon: str, tmp_path: Path) -> None:
    """Spec §5: ``anchor.pending_added`` fires when ``add_pending_anchor``
    is invoked through the daemon-side hook."""
    from sov_daemon.events import emit_anchor_pending_added

    _seed_game(tmp_path, "s42")
    async with (
        httpx.AsyncClient(base_url=real_daemon, timeout=10.0) as client,
        client.stream("GET", "/events", headers=_AUTH) as response,
    ):
        seen_types: list[str] = []
        async with asyncio.timeout(5.0):
            event_type = ""
            buf: list[str] = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    buf.append(line[len("data:") :].strip())
                elif line == "":
                    if event_type:
                        seen_types.append(event_type)
                        if event_type == "daemon.ready":
                            emit_anchor_pending_added(
                                game_id="s42",
                                round_key="3",
                                envelope_hash="abc" * 21 + "x",
                            )
                        if event_type == "anchor.pending_added":
                            payload = json.loads("".join(buf))
                            assert payload.get("game_id") == "s42"
                            assert payload.get("round") == "3" or payload.get("round_key") == "3"
                            return
                    event_type = ""
                    buf = []
    pytest.fail(f"never saw anchor.pending_added; observed: {seen_types!r}")


# ---------------------------------------------------------------------------
# anchor.batch_complete — emitted after successful anchor_batch
# ---------------------------------------------------------------------------


async def test_sse_emits_anchor_batch_complete_event(real_daemon: str, tmp_path: Path) -> None:
    """Spec §5: ``anchor.batch_complete`` fires after successful flush."""
    from sov_daemon.events import emit_anchor_batch_complete

    _seed_game(tmp_path, "s42")
    async with (
        httpx.AsyncClient(base_url=real_daemon, timeout=10.0) as client,
        client.stream("GET", "/events", headers=_AUTH) as response,
    ):
        async with asyncio.timeout(5.0):
            event_type = ""
            buf: list[str] = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    buf.append(line[len("data:") :].strip())
                elif line == "":
                    if event_type == "daemon.ready":
                        emit_anchor_batch_complete(
                            game_id="s42",
                            txid="DEADBEEF",
                            rounds=["1", "2", "FINAL"],
                            explorer_url="https://testnet.xrpl.org/transactions/DEADBEEF",
                        )
                    if event_type == "anchor.batch_complete":
                        payload = json.loads("".join(buf))
                        assert payload.get("game_id") == "s42"
                        assert payload.get("txid") == "DEADBEEF"
                        assert "FINAL" in payload.get("rounds", [])
                        return
                    event_type = ""
                    buf = []
    pytest.fail("never saw anchor.batch_complete")


# ---------------------------------------------------------------------------
# game.state_changed — fires when state.json mtime bumps
# ---------------------------------------------------------------------------


async def test_sse_emits_game_state_changed_on_mtime_bump(real_daemon: str, tmp_path: Path) -> None:
    """Spec §5: state.json mtime bump → ``game.state_changed``.

    Polling is 1s. We wait up to 8s for the change to be observed.
    """
    state_path = _seed_game(tmp_path, "s42")
    async with (
        httpx.AsyncClient(base_url=real_daemon, timeout=10.0) as client,
        client.stream("GET", "/events", headers=_AUTH) as response,
    ):
        async with asyncio.timeout(8.0):
            event_type = ""
            buf: list[str] = []
            touched = False
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    buf.append(line[len("data:") :].strip())
                elif line == "":
                    if event_type == "daemon.ready" and not touched:
                        # Bump the mtime far enough into the future that the
                        # poll's 1s granularity sees a change even on
                        # filesystems with low mtime resolution.
                        import os
                        import time

                        future = time.time() + 5.0
                        os.utime(state_path, (future, future))
                        touched = True
                    if event_type == "game.state_changed":
                        payload = json.loads("".join(buf))
                        assert payload.get("game_id") == "s42"
                        return
                    event_type = ""
                    buf = []
    pytest.fail("never saw game.state_changed event")


# ---------------------------------------------------------------------------
# Reconnect contract — fresh daemon.ready, no replay
# ---------------------------------------------------------------------------


async def test_sse_reconnect_yields_fresh_daemon_ready_no_replay(
    real_daemon: str, tmp_path: Path
) -> None:
    """Spec §5: disconnect + reconnect → new ``daemon.ready``, NO replay."""
    from sov_daemon.events import emit_anchor_pending_added

    _seed_game(tmp_path, "s42")
    async with httpx.AsyncClient(base_url=real_daemon, timeout=10.0) as client:
        event_type, _ = await _read_first_event(client)
        assert event_type == "daemon.ready"
        emit_anchor_pending_added(
            game_id="s42",
            round_key="9",
            envelope_hash="missed-while-disconnected",
        )
        event_type2, payload2 = await _read_first_event(client)
    assert event_type2 == "daemon.ready", (
        f"reconnect must replay daemon.ready, got {event_type2!r} "
        "(missed events MUST NOT be replayed in v2.1)"
    )
    assert "missed-while-disconnected" not in json.dumps(payload2), (
        "reconnect MUST NOT replay events emitted during disconnect"
    )

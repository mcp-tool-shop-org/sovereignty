"""SSE event broadcaster + state-change file watcher.

Spec §5: ``GET /events`` returns ``text/event-stream``. Each event is
``event: <type>\\ndata: <json>\\n\\n``. **No ``id:`` line, no buffer, no
Last-Event-ID.** Reconnecting clients miss any events emitted while
disconnected and re-fetch state via ``GET /games/{id}``.

The broadcaster is in-memory pub/sub: each SSE connection gets an
``asyncio.Queue``; ``broadcast(event_type, payload)`` enqueues onto every
queue. State-change polling runs every 1 second only when at least one
SSE client is connected — cost-free idle when no listeners.

Event types (per spec §5):

* ``daemon.ready`` — first event on each connection.
* ``daemon.shutdown`` — emitted on SIGTERM / ``stop_daemon``.
* ``anchor.pending_added`` — when ``add_pending_anchor`` is called via
  this daemon's anchor flow (hooked from the daemon's anchor handlers).
* ``anchor.batch_complete`` — after a successful ``anchor_batch``.
* ``game.state_changed`` — emitted when a state.json mtime changes.
* ``error`` — daemon-level errors worth surfacing.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from starlette.applications import Starlette

from sov_engine.io_utils import games_dir

logger = logging.getLogger("sov_daemon")

# Polling cadence for state.json mtime changes. Spec §5 pins 1s as the
# right granularity for human-perceptible UI updates without burning CPU
# on idle inspection. Lifted to a constant so future contracts (e.g. a
# tuneable cadence for slow filesystems) can adjust in one place.
_STATE_POLL_INTERVAL_SECONDS = 1.0


class EventBroadcaster:
    """In-memory pub/sub for SSE event distribution.

    Each connected client gets its own ``asyncio.Queue``; ``broadcast``
    fan-outs events to every queue. Slow consumers are bounded — the
    queue is unbounded by default (we expect <10 events/sec total) but
    a backpressure-aware enqueue can be added if a client falls behind.

    The broadcaster also owns the state-change polling task. The task
    is started lazily on the first SSE connection and cancelled when
    the last connection closes — cost-free when nothing's listening.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[tuple[str, dict[str, Any]]]] = set()
        self._lock = asyncio.Lock()
        self._poll_task: asyncio.Task[None] | None = None
        # Track per-game state.json mtimes so we can detect changes.
        # Empty dict means "never polled yet" — the first poll seeds
        # the dict and only emits events on subsequent changes.
        self._last_mtimes: dict[str, float] = {}

    async def subscribe(self) -> asyncio.Queue[tuple[str, dict[str, Any]]]:
        """Register a new SSE listener. Returns its event queue.

        Starts the state-change poll task on the first subscription —
        no polling happens while no clients are connected.
        """
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
            if self._poll_task is None or self._poll_task.done():
                self._poll_task = asyncio.create_task(self._poll_state_changes())
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[tuple[str, dict[str, Any]]]) -> None:
        """Drop a listener. Stops the poll task when the last one leaves."""
        async with self._lock:
            self._subscribers.discard(queue)
            if not self._subscribers and self._poll_task is not None:
                self._poll_task.cancel()
                self._poll_task = None
                # Re-seed mtimes on next subscribe — a long idle gap
                # would otherwise dump every changed state.json as a
                # single burst when polling resumes.
                self._last_mtimes = {}

    def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Enqueue an event for every connected listener.

        Sync (not async) so anchor-flow hooks can call from sync code
        without awaiting. The queue's ``put_nowait`` is non-blocking;
        if a queue is full (won't happen with the unbounded default),
        we'd log + drop here.
        """
        for queue in list(self._subscribers):
            try:
                queue.put_nowait((event_type, payload))
            except asyncio.QueueFull:
                # Unbounded queue can't hit this in practice, but the
                # branch keeps mypy strict happy and pins the policy.
                logger.warning(
                    "events.broadcast.dropped event=%s reason=queue_full",
                    event_type,
                )

    async def _poll_state_changes(self) -> None:
        """Poll ``.sov/games/*/state.json`` mtimes every 1 second.

        Initial poll seeds ``_last_mtimes`` without emitting events;
        subsequent polls emit ``game.state_changed`` for any mtime that
        moved. Newly-added games are also reported. Removed games are
        evicted from the tracking dict silently — the daemon doesn't
        emit a ``game.removed`` event in v2.1.
        """
        try:
            while True:
                try:
                    self._poll_once()
                except Exception as exc:  # noqa: BLE001
                    # Keep polling alive even if a single iteration
                    # blew up (e.g. a game dir was deleted mid-scan).
                    logger.warning(
                        "events.poll.failed exc=%s detail=%s (continuing)",
                        type(exc).__name__,
                        exc,
                    )
                await asyncio.sleep(_STATE_POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            # Clean cancellation on last-unsubscribe. Re-raise so the
            # task transitions to CANCELLED rather than DONE.
            raise

    def _poll_once(self) -> None:
        """One pass over the games dir. Emit on mtime changes."""
        root = games_dir()
        if not root.exists():
            return
        seen_now: dict[str, float] = {}
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            sf = entry / "state.json"
            if not sf.exists():
                continue
            try:
                mtime = sf.stat().st_mtime
            except OSError:
                continue
            seen_now[entry.name] = mtime
            previous = self._last_mtimes.get(entry.name)
            if previous is None:
                # Newly-tracked game on first poll: don't emit, just
                # seed. Subsequent polls report changes from here.
                # If we're in a non-initial poll AND the game wasn't
                # there before, it's a new save — emit so consumers
                # refresh their game list.
                if self._last_mtimes:
                    self.broadcast("game.state_changed", {"game_id": entry.name})
            elif mtime != previous:
                self.broadcast("game.state_changed", {"game_id": entry.name})
        self._last_mtimes = seen_now


# Module-level broadcaster registry. Most callers reach for the
# per-app broadcaster via ``get_broadcaster(app)``; the test surface
# also wants module-level emit helpers (``emit_anchor_pending_added``,
# ``emit_anchor_batch_complete``) that don't require threading an
# app reference through every call site. To support both, we keep a
# weak singleton: the most recently-built app's broadcaster is cached
# in ``_default_broadcaster`` and returned by the module-level emitters.
# In production there's exactly one app per daemon process so the
# singleton matches the per-app value.
_default_broadcaster: EventBroadcaster | None = None


def get_broadcaster(app: Starlette) -> EventBroadcaster:
    """Return the broadcaster bound to ``app.state``. Created lazily.

    The broadcaster is an app-level singleton — one per daemon process.
    Stashed on ``app.state`` so any handler / lifespan hook can reach
    it without threading the app through every call. The most recently
    built app's broadcaster is also cached as a module-level default
    so the module-level emit helpers (``emit_anchor_pending_added``
    etc.) can reach it without an explicit app argument.
    """
    global _default_broadcaster
    broadcaster = getattr(app.state, "broadcaster", None)
    if broadcaster is None:
        broadcaster = EventBroadcaster()
        app.state.broadcaster = broadcaster
    _default_broadcaster = broadcaster
    return broadcaster


def _default() -> EventBroadcaster | None:
    """Return the module-level default broadcaster, or None.

    Module-level emit helpers use this. None means "no app has been
    built yet"; the helpers degrade to no-ops in that case rather
    than constructing a broadcaster with no listeners (which would
    leak per-test state across the suite).
    """
    return _default_broadcaster


def emit_anchor_pending_added(
    *,
    game_id: str,
    round_key: str,
    envelope_hash: str,
) -> None:
    """Emit an ``anchor.pending_added`` event on the default broadcaster.

    Intended for callers that explicitly enqueue a pending anchor and
    want subscribers notified immediately rather than waiting for the
    next 1-second state poll. No-op when no daemon app has been built
    yet (e.g. unit tests that import this module in isolation).
    """
    broadcaster = _default()
    if broadcaster is None:
        return
    broadcaster.broadcast(
        "anchor.pending_added",
        {
            "game_id": game_id,
            "round": round_key,
            "envelope_hash": envelope_hash,
        },
    )


def emit_anchor_batch_complete(
    *,
    game_id: str,
    txid: str,
    rounds: list[str],
    explorer_url: str,
) -> None:
    """Emit an ``anchor.batch_complete`` event on the default broadcaster.

    Mirrors ``server._do_anchor``'s success-path event but reachable
    from outside the request handler — useful when the CLI flushes
    anchors via the engine path (rather than the daemon endpoint) and
    wants connected SSE clients to refresh.
    """
    broadcaster = _default()
    if broadcaster is None:
        return
    broadcaster.broadcast(
        "anchor.batch_complete",
        {
            "game_id": game_id,
            "txid": txid,
            "rounds": rounds,
            "explorer_url": explorer_url,
        },
    )


async def sse_stream(app: Starlette, *, network: str, readonly: bool) -> AsyncIterator[bytes]:
    """Async generator yielding SSE-framed bytes for one client connection.

    Emits ``daemon.ready`` first, then forwards every queued event until
    the client disconnects (``asyncio.CancelledError`` from the generator
    consumer). Bytes are encoded ``utf-8`` with the standard SSE framing
    ``event: <type>\\ndata: <json>\\n\\n``.
    """
    logger.debug("sse_stream: starting")
    broadcaster = get_broadcaster(app)
    queue = await broadcaster.subscribe()
    logger.debug("sse_stream: subscribed")
    try:
        ready_payload = {
            "network": network,
            "readonly": readonly,
            "ipc_version": 1,
        }
        yield _sse_frame("daemon.ready", ready_payload)

        while True:
            event_type, payload = await queue.get()
            yield _sse_frame(event_type, payload)
            if event_type == "daemon.shutdown":
                # After shutdown, drain the connection cleanly. Browser
                # EventSource will reconnect; the daemon won't be there
                # to answer.
                return
    finally:
        await broadcaster.unsubscribe(queue)


def _sse_frame(event_type: str, payload: dict[str, Any]) -> bytes:
    """Build one SSE frame. Spec §5: NO ``id:`` line, NO retry hint.

    ``data:`` is one line of JSON; multi-line JSON would require
    ``data: ...\\ndata: ...`` repetition, which we avoid by serializing
    without indents.
    """
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_type}\ndata: {body}\n\n".encode()


def broadcast_shutdown(app: Starlette) -> None:
    """Emit the ``daemon.shutdown`` event. Called on SIGTERM / SIGINT.

    Idempotent — safe to call from both the signal handler and the
    uvicorn lifespan ``on_shutdown`` hook (whichever fires first wins;
    the second call broadcasts to an empty subscriber set).
    """
    broadcaster = get_broadcaster(app)
    broadcaster.broadcast("daemon.shutdown", {"reason": "stop_command"})


__all__ = [
    "EventBroadcaster",
    "broadcast_shutdown",
    "emit_anchor_batch_complete",
    "emit_anchor_pending_added",
    "get_broadcaster",
    "sse_stream",
]

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
import threading
import time as _time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from starlette.applications import Starlette

from sov_engine.io_utils import games_dir

logger = logging.getLogger("sov_daemon")

# Polling cadence for state.json mtime changes. Spec §5 pins 1s as the
# right granularity for human-perceptible UI updates without burning CPU
# on idle inspection. Lifted to a constant so future contracts (e.g. a
# tuneable cadence for slow filesystems) can adjust in one place.
_STATE_POLL_INTERVAL_SECONDS = 1.0


class SubscribersExhaustedError(RuntimeError):
    """Raised by ``EventBroadcaster.subscribe`` when the per-broadcaster
    subscriber cap (``MAX_SUBSCRIBERS``) is already at the ceiling.

    DAEMON-B-014 (Wave 9): localhost-bound but not unbounded — a misbehaving
    consumer that doesn't drain its queue or a Tauri hot-reload that leaks
    EventSource connections would otherwise pin daemon RAM. The handler at
    ``server.py::events_handler`` translates this to HTTP 503 with code
    ``SSE_SUBSCRIBERS_EXHAUSTED`` so the client gets a structured envelope
    instead of a 500.
    """


class EventBroadcaster:
    """In-memory pub/sub for SSE event distribution.

    Each connected client gets its own ``asyncio.Queue``; ``broadcast``
    fan-outs events to every queue. Slow consumers are bounded — the
    queue is bounded at ``QUEUE_MAXSIZE`` events; a consumer that falls
    behind drops events (preferable to OOM).

    The broadcaster also owns the state-change polling task. The task
    is started lazily on the first SSE connection and cancelled when
    the last connection closes — cost-free when nothing's listening.

    DAEMON-B-014 (Wave 9):
    * ``MAX_SUBSCRIBERS = 32`` caps subscriber count to prevent a stale
      Tauri tab + dev-server hot-reload from leaking unbounded
      EventSource connections that pin RAM.
    * ``QUEUE_MAXSIZE = 256`` bounds per-subscriber queue depth so a
      slow consumer can't pin a growing chunk of memory; overflow drops
      via the existing ``QueueFull`` branch in ``broadcast``.
    """

    MAX_SUBSCRIBERS: int = 32
    QUEUE_MAXSIZE: int = 256

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[tuple[str, dict[str, Any]]]] = set()
        # DAEMON-008: ``threading.Lock`` instead of ``asyncio.Lock`` so the
        # sync ``broadcast`` API can acquire the same lock that the async
        # subscribe / unsubscribe paths hold. The single-event-loop pattern
        # makes contention vanishingly rare (the lock is only held for a
        # set add / discard / iteration), and ``threading.Lock`` works
        # under free-threaded CPython too.
        self._lock = threading.Lock()
        self._poll_task: asyncio.Task[None] | None = None
        # Track per-game state.json mtimes so we can detect changes.
        # Empty dict means "never polled yet" — the first poll seeds
        # the dict and only emits events on subsequent changes.
        self._last_mtimes: dict[str, float] = {}

    async def subscribe(self) -> asyncio.Queue[tuple[str, dict[str, Any]]]:
        """Register a new SSE listener. Returns its event queue.

        Starts the state-change poll task on the first subscription —
        no polling happens while no clients are connected.

        DAEMON-B-014: rejects with ``SubscribersExhaustedError`` when the
        subscriber count is already at ``MAX_SUBSCRIBERS``. The handler
        translates this to HTTP 503 ``SSE_SUBSCRIBERS_EXHAUSTED``.
        """
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=self.QUEUE_MAXSIZE)
        with self._lock:
            if len(self._subscribers) >= self.MAX_SUBSCRIBERS:
                raise SubscribersExhaustedError(
                    f"SSE subscriber cap reached: {len(self._subscribers)}/{self.MAX_SUBSCRIBERS}"
                )
            self._subscribers.add(queue)
            need_poll = self._poll_task is None or self._poll_task.done()
        if need_poll:
            # Spawn the polling task outside the lock so a failing
            # ``create_task`` doesn't strand the lock; ``asyncio.Lock``
            # would have made this irrelevant, but ``threading.Lock``
            # makes the discipline visible.
            with self._lock:
                if self._poll_task is None or self._poll_task.done():
                    self._poll_task = asyncio.create_task(self._poll_state_changes())
        return queue

    def subscribers_count(self) -> int:
        """Return the current number of active SSE subscribers.

        DAEMON-C-006 (Wave 11): public surface so callers (e.g.
        ``server.events_handler``'s pre-cap-check) don't need to reach
        into the name-mangled ``_subscribers`` set. The lock is held
        only for the size read — small and contention-free in practice.
        """
        with self._lock:
            return len(self._subscribers)

    async def unsubscribe(self, queue: asyncio.Queue[tuple[str, dict[str, Any]]]) -> None:
        """Drop a listener. Stops the poll task when the last one leaves."""
        task_to_cancel: asyncio.Task[None] | None = None
        with self._lock:
            self._subscribers.discard(queue)
            if not self._subscribers and self._poll_task is not None:
                task_to_cancel = self._poll_task
                self._poll_task = None
                # Re-seed mtimes on next subscribe — a long idle gap
                # would otherwise dump every changed state.json as a
                # single burst when polling resumes.
                self._last_mtimes = {}
        if task_to_cancel is not None:
            task_to_cancel.cancel()

    def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Enqueue an event for every connected listener.

        Sync (not async) so anchor-flow hooks can call from sync code
        without awaiting. The queue's ``put_nowait`` is non-blocking;
        if a queue is full (won't happen with the unbounded default),
        we'd log + drop here.

        DAEMON-008: snapshot the subscriber set under the lock before
        iterating so a concurrent ``unsubscribe`` can't drop the queue
        we're about to enqueue onto. The snapshot is small (typically
        one or two clients) and the lock window is correspondingly tiny.
        """
        with self._lock:
            queues = list(self._subscribers)
        for queue in queues:
            try:
                queue.put_nowait((event_type, payload))
            except asyncio.QueueFull:
                # Bounded queue (Wave 9 DAEMON-B-014): a slow consumer
                # that fell ``QUEUE_MAXSIZE`` events behind drops events
                # rather than pinning unbounded RAM. DAEMON-B-013:
                # structured fields via ``extra=`` for the JSON log
                # formatter.
                logger.warning(
                    "events.broadcast.dropped",
                    extra={
                        "endpoint": event_type,
                    },
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
                    # DAEMON-B-013: structured fields via ``extra=``.
                    logger.warning(
                        "events.poll.failed",
                        extra={
                            "exception_type": type(exc).__name__,
                            "exception_detail": str(exc),
                        },
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


class ChainLookupCache:
    """DAEMON-006: single-flight + 5s TTL cache for ``is_anchored_on_chain``.

    Two SSE clients concurrently hitting the same txid would otherwise
    each spawn an upstream xrpl-py request. xrpl-py's testnet rate limit
    (~120 req/min/IP) starts to bite under multi-client audit-viewer
    fan-out. The cache:

    * coalesces concurrent ``get(txid, fetch)`` calls into a single
      upstream invocation (single-flight); waiters share the future.
    * caches the result for ``_TTL_SECONDS`` so SSE refresh storms don't
      re-query the chain for an already-known txid.

    Build the infrastructure now even though the v2.1 endpoints don't
    call ``is_anchored_on_chain`` from the request path — the next
    endpoint that adds chain re-verification (audit viewer "anchor
    confirmed" badges, etc.) inherits the protection rather than
    retrofitting it after a rate-limit incident.
    """

    _TTL_SECONDS: float = 5.0

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, bool]] = {}
        self._inflight: dict[str, asyncio.Future[bool]] = {}
        self._lock = asyncio.Lock()

    async def get(
        self,
        txid: str,
        fetch: Callable[[], Awaitable[bool]],
    ) -> bool:
        """Return ``fetch()``'s result, coalesced + cached.

        ``fetch`` is the upstream lookup (e.g. ``transport.is_anchored_on_chain``
        bound to a particular envelope hash). Two concurrent ``get`` calls
        for the same ``txid`` invoke ``fetch`` exactly once; the second
        awaits the first's future. Errors propagate to every waiter.
        """
        async with self._lock:
            cached = self._cache.get(txid)
            if cached is not None and (_time.monotonic() - cached[0]) < self._TTL_SECONDS:
                return cached[1]
            pending = self._inflight.get(txid)
            if pending is not None:
                future = pending
                in_flight_owner = False
            else:
                future = asyncio.get_event_loop().create_future()
                self._inflight[txid] = future
                in_flight_owner = True

        if not in_flight_owner:
            return await future

        try:
            result = await fetch()
        except BaseException as exc:
            async with self._lock:
                self._inflight.pop(txid, None)
            if not future.done():
                future.set_exception(exc)
            raise

        async with self._lock:
            self._cache[txid] = (_time.monotonic(), result)
            self._inflight.pop(txid, None)
        if not future.done():
            future.set_result(result)
        return result


def get_chain_cache(app: Starlette) -> ChainLookupCache:
    """Return the per-app ``ChainLookupCache``, creating it on first use."""
    cache = getattr(app.state, "chain_cache", None)
    if cache is None:
        cache = ChainLookupCache()
        app.state.chain_cache = cache
    return cache


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


def reset_default_broadcaster() -> None:
    """DAEMON-009: drop the module-level singleton.

    Test fixtures call this so the broadcaster from one test's app doesn't
    leak into the next test's ``emit_anchor_*`` callsites. Production
    callers don't need this — there's exactly one daemon per process.

    Use as an autouse pytest fixture::

        @pytest.fixture(autouse=True)
        def _reset_broadcaster():
            from sov_daemon.events import reset_default_broadcaster
            reset_default_broadcaster()
            yield
            reset_default_broadcaster()
    """
    global _default_broadcaster
    _default_broadcaster = None


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
    logger.debug("sse.stream.starting")
    broadcaster = get_broadcaster(app)
    queue = await broadcaster.subscribe()
    logger.debug("sse.stream.subscribed")
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
    "ChainLookupCache",
    "EventBroadcaster",
    "broadcast_shutdown",
    "emit_anchor_batch_complete",
    "emit_anchor_pending_added",
    "get_broadcaster",
    "get_chain_cache",
    "reset_default_broadcaster",
    "sse_stream",
]

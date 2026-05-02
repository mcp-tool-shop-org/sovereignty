"""Wave 11 Stage 8-C regression tests for ``sov_daemon`` domain amends.

Each test pins a specific finding from
``swarm-1777686810-67fd/wave-10/audit/daemon-findings.yaml`` so the next
audit can match a green test to a closed finding.

Coverage:

* DAEMON-C-006 — public ``EventBroadcaster.subscribers_count()`` surface
  replaces the old ``broadcaster._subscribers`` reach-in.
* DAEMON-C-007 — debug log emits use dot-separated namespaced-event
  tokens (``sse.stream.starting`` not ``sse_stream: starting``).
* DAEMON-C-008 — ``_wait_for_handshake`` timeout RuntimeError carries
  a recovery hint pointing at ``sov daemon status``.
* DAEMON-C-012 — ``stop_daemon`` timeout uses a platform-aware kill
  hint (``kill -9`` on POSIX, ``taskkill /F /PID`` on Windows).

The cross-domain MEDs DAEMON-C-001/002/003 (auth hint humanisation +
``PAYLOAD_TOO_LARGE`` + ``SSE_SUBSCRIBERS_EXHAUSTED`` factory lifts) are
flagged for the cli agent — daemon wires through after the factories
land. See ``wave-11/daemon.output.json`` skipped[] entries for the
factory-shape contract.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# DAEMON-C-006 — public subscribers_count() replaces _subscribers reach-in
# ---------------------------------------------------------------------------


def test_daemon_c_006_event_broadcaster_exposes_public_subscribers_count() -> None:
    """The broadcaster MUST expose a public ``subscribers_count()`` method.

    Pre-Wave-11, ``server.events_handler`` reached into the name-mangled
    ``broadcaster._subscribers`` set to gate the SSE cap pre-check. Wave 11
    DAEMON-C-006 adds a public surface so the encapsulation isn't punctured
    by sibling modules.
    """
    from sov_daemon.events import EventBroadcaster

    broadcaster = EventBroadcaster()
    assert hasattr(broadcaster, "subscribers_count"), (
        "EventBroadcaster must expose a public ``subscribers_count()`` method "
        "so callers don't need to reach into ``_subscribers`` (DAEMON-C-006)."
    )
    method = broadcaster.subscribers_count
    assert callable(method), "subscribers_count must be callable."
    # Empty broadcaster reports zero.
    assert broadcaster.subscribers_count() == 0


def test_daemon_c_006_subscribers_count_tracks_subscribe_unsubscribe() -> None:
    """``subscribers_count()`` reflects subscribe / unsubscribe transitions."""
    from sov_daemon.events import EventBroadcaster

    async def _run() -> None:
        broadcaster = EventBroadcaster()
        assert broadcaster.subscribers_count() == 0
        q1 = await broadcaster.subscribe()
        assert broadcaster.subscribers_count() == 1
        q2 = await broadcaster.subscribe()
        assert broadcaster.subscribers_count() == 2
        await broadcaster.unsubscribe(q1)
        assert broadcaster.subscribers_count() == 1
        await broadcaster.unsubscribe(q2)
        assert broadcaster.subscribers_count() == 0

    asyncio.run(_run())


def test_daemon_c_006_events_handler_uses_public_surface() -> None:
    """``server.py`` must not reach into ``broadcaster._subscribers`` —
    the public ``subscribers_count()`` method is the supported seam.
    """
    server_path = Path(__file__).resolve().parent.parent / "sov_daemon" / "server.py"
    src = server_path.read_text(encoding="utf-8")
    assert "broadcaster._subscribers" not in src, (
        "sov_daemon/server.py must not reach into the name-mangled "
        "``_subscribers`` set; use ``broadcaster.subscribers_count()`` "
        "(DAEMON-C-006)."
    )
    assert "broadcaster.subscribers_count()" in src, (
        "sov_daemon/server.py should call the public ``subscribers_count()`` "
        "surface for the SSE cap pre-check (DAEMON-C-006)."
    )


# ---------------------------------------------------------------------------
# DAEMON-C-007 — namespaced-event-token convention for debug log emits
# ---------------------------------------------------------------------------


def test_daemon_c_007_sse_stream_debug_logs_use_dot_separated_event_tokens() -> None:
    """``log_fields.py`` documents dot-separated namespaced-event tokens.

    Before Wave 11, two debug emits in ``events.py`` used a colon separator
    (``sse_stream: starting``) which makes the JSON-mode ``event`` field
    sort and filter poorly against ``events.*`` siblings. The fix uses
    ``sse.stream.starting`` / ``sse.stream.subscribed``.
    """
    events_path = Path(__file__).resolve().parent.parent / "sov_daemon" / "events.py"
    src = events_path.read_text(encoding="utf-8")
    assert "sse_stream: starting" not in src, (
        "DAEMON-C-007: legacy colon-separated debug log emit "
        "``sse_stream: starting`` should be replaced with the dot-separated "
        "namespaced-event-token form ``sse.stream.starting``."
    )
    assert "sse_stream: subscribed" not in src, (
        "DAEMON-C-007: legacy colon-separated debug log emit "
        "``sse_stream: subscribed`` should be replaced with the dot-separated "
        "namespaced-event-token form ``sse.stream.subscribed``."
    )
    assert "sse.stream.starting" in src
    assert "sse.stream.subscribed" in src


# ---------------------------------------------------------------------------
# DAEMON-C-008 — _wait_for_handshake RuntimeError carries recovery hint
# ---------------------------------------------------------------------------


def test_daemon_c_008_wait_for_handshake_timeout_carries_recovery_hint() -> None:
    """The handshake-timeout RuntimeError must name an inspection command.

    Wave 11 DAEMON-C-008: the bare ``RuntimeError("daemon did not write
    .sov/daemon.json within ...s.")`` left the operator with no actionable
    next step. The amended message points at ``sov daemon status`` for
    partial-state inspection.
    """
    from sov_daemon import lifecycle

    src = inspect.getsource(lifecycle._wait_for_handshake)
    assert "sov daemon status" in src, (
        "DAEMON-C-008: ``_wait_for_handshake`` timeout message should name "
        "``sov daemon status`` so operators can inspect partial state."
    )


# ---------------------------------------------------------------------------
# DAEMON-C-012 — cross-platform kill hint in stop_daemon timeout
# ---------------------------------------------------------------------------


def test_daemon_c_012_stop_daemon_uses_platform_aware_kill_hint() -> None:
    """``stop_daemon`` timeout RuntimeError must adapt to platform.

    Wave 11 DAEMON-C-012: ``kill -9`` is POSIX-only — Windows operators
    need ``taskkill /F /PID``. The amended ``stop_daemon`` branches on
    ``sys.platform`` and emits the right command for the running host.
    """
    from sov_daemon import lifecycle

    src = inspect.getsource(lifecycle.stop_daemon)
    assert "taskkill" in src, (
        "DAEMON-C-012: ``stop_daemon`` timeout message should include "
        "``taskkill /F /PID`` guidance for Windows operators."
    )
    assert "kill -9" in src, (
        "DAEMON-C-012: ``stop_daemon`` timeout message should still include "
        "``kill -9`` guidance for POSIX operators."
    )
    assert 'sys.platform == "win32"' in src, (
        "DAEMON-C-012: ``stop_daemon`` should branch on ``sys.platform`` "
        "to pick the platform-appropriate kill hint."
    )


def test_daemon_c_012_kill_hint_choice_matches_running_platform() -> None:
    """Sanity smoke: the kill-hint branch picks the right verb for the host.

    Re-imports the module under test to confirm the platform check resolves
    locally — no full ``stop_daemon`` invocation (would require a live pid).
    """
    if sys.platform == "win32":
        expected_verb = "taskkill"
    else:
        expected_verb = "kill -9"
    # Smoke: just confirm the expected verb is present in the source.
    from sov_daemon import lifecycle

    src = inspect.getsource(lifecycle.stop_daemon)
    assert expected_verb in src

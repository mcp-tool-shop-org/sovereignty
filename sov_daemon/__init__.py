"""Sovereignty daemon — HTTP/JSON IPC over localhost.

The daemon is the trust boundary between the sovereignty engine + transport
layer and any GUI client (Tauri shell in v2.1 Wave 4, audit viewer in
Wave 5). It:

* Exposes 10 HTTP endpoints (audit reads + anchor writes, spec §4).
* Pushes events via SSE (``daemon.ready``, ``anchor.batch_complete``,
  ``game.state_changed``, etc., spec §5).
* Holds the wallet seed in memory only (never written to
  ``.sov/daemon.json``, pinned by ``tests/test_daemon_seed_leak.py``).

Public API used by the CLI (Wave 3 ``cli`` agent):

* ``start_daemon`` — spawn detached background daemon for this project root.
* ``stop_daemon`` — SIGTERM the daemon, wait for clean exit.
* ``daemon_status`` — return ``(DaemonStatus, info | None)``.
* ``run_foreground`` — run uvicorn in the current process (test/dev mode).
* ``DaemonStatus`` — running / stale / none StrEnum.

Reference: ``docs/v2.1-daemon-ipc.md`` (locked Wave 3 contract spec).
"""

from __future__ import annotations

from sov_daemon.lifecycle import (
    DaemonAlreadyRunningError,
    DaemonStatus,
    daemon_info,
    daemon_status,
    run_foreground,
    start_daemon,
    stop_daemon,
)

__version__ = "2.1.0"

__all__ = [
    "DaemonAlreadyRunningError",
    "DaemonStatus",
    "__version__",
    "daemon_info",
    "daemon_status",
    "run_foreground",
    "start_daemon",
    "stop_daemon",
]

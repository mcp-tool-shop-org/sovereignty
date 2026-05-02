"""Entry point for ``python -m sov_daemon``.

Reads ``SOV_DAEMON_*`` env vars (port, token, network, readonly, seed
source) set by the parent ``start_daemon`` call and dispatches into
``run_foreground``. When invoked directly without those env vars (test
or dev use), defaults apply: testnet network, no readonly, ``XRPL_SEED``
seed env, freshly-claimed port and token.

POSIX double-fork
-----------------

When ``SOV_DAEMON_DOUBLE_FORK=1`` is set (the parent ``start_daemon``
sets this on POSIX spawns), this module ``os.fork()``s once before
running uvicorn and the original process exits. The post-fork process
is re-parented to init/launchd so when it eventually exits it gets
reaped properly — the parent CLI doesn't have to stick around as a
zombie reaper, and ``stop_daemon``'s pid-alive check stops returning
True for a dead-but-not-reaped daemon.

The parent ``start_daemon`` waits on the intermediate parent (the
``Popen`` it created) so the parent's pid table doesn't accumulate
zombies of the intermediate process either.
"""

from __future__ import annotations

import os
import sys

from sov_daemon.lifecycle import run_foreground_from_env


def _maybe_double_fork() -> None:
    """POSIX-only: detach this process from its original parent.

    Called when ``SOV_DAEMON_DOUBLE_FORK=1`` env var is set. The original
    process forks; the parent of the fork exits immediately (so the
    spawning ``Popen`` reaps it cleanly); the child continues into
    ``run_foreground_from_env`` and is now a child of init.

    Windows path: never invoked (``SOV_DAEMON_DOUBLE_FORK`` isn't set
    by ``_spawn_detached`` on win32; ``DETACHED_PROCESS`` already
    decouples).
    """
    if os.environ.get("SOV_DAEMON_DOUBLE_FORK") != "1":
        return
    if sys.platform == "win32":
        return
    pid = os.fork()
    if pid != 0:
        # Original process: exit so the Popen.wait() in
        # ``_spawn_detached`` returns immediately.
        os._exit(0)
    # Child continues. Drop the env var so a downstream re-exec doesn't
    # double-fork again.
    os.environ.pop("SOV_DAEMON_DOUBLE_FORK", None)


def main() -> None:
    """Run the daemon in the current process. Blocks until SIGINT/SIGTERM."""
    _maybe_double_fork()
    run_foreground_from_env()


if __name__ == "__main__":
    main()

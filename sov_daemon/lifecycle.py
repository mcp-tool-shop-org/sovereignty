"""Daemon lifecycle: start / stop / status / foreground.

This module owns ``.sov/daemon.json`` — the on-disk handshake file that
declares "a sovereignty daemon is running on this project root, here is its
port + token + pid." See spec §6 / §8 of ``docs/v2.1-daemon-ipc.md``.

Contracts pinned by Wave 3 tests:

* ``start_daemon`` refuses if a live daemon already runs in this project
  root (``DaemonAlreadyRunningError``). It auto-cleans a stale
  ``.sov/daemon.json`` whose pid is dead, then proceeds.
* The token is a fresh ``secrets.token_urlsafe(32)`` per start; it is held
  in memory by the running daemon AND persisted to ``.sov/daemon.json``
  so CLI clients can read it. The seed (``XRPL_SEED`` / ``--signer-file``)
  is **never** written to disk — pinned by ``test_daemon_seed_leak.py``.
* ``run_foreground`` runs uvicorn in the current process; SIGINT (Ctrl-C)
  exits cleanly. Same write-on-start / remove-on-exit handshake.
* ``stop_daemon`` reads the handshake, sends SIGTERM (``terminate()`` on
  Windows), polls ``os.kill(pid, 0)`` until exit (max 10s), removes the
  handshake on success.
* ``daemon_status`` returns a ``DaemonStatus`` enum: ``RUNNING`` (pid
  alive), ``STALE`` (handshake present, pid dead), or ``NONE`` (no
  handshake). ``daemon_info`` is the companion that returns the parsed
  handshake dict for RUNNING / STALE statuses.

The detached-background spawn uses ``subprocess.Popen`` with
``start_new_session=True`` on POSIX and ``DETACHED_PROCESS |
CREATE_NEW_PROCESS_GROUP`` on Windows so the spawned process survives the
parent CLI exiting. Settings, port, token, network, readonly, and seed
sourcing are passed via env vars — argv would expose the token in
``ps`` output.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from sov_engine.io_utils import atomic_write_text, save_root

DAEMON_FILE_NAME = "daemon.json"
DAEMON_SCHEMA_VERSION = 1
IPC_VERSION = 1

# How long ``start_daemon`` waits for the spawned subprocess to write its
# handshake file (and thus be ready to serve). 5s comfortably covers Python
# import + uvicorn boot on a fresh interpreter; any longer suggests the
# subprocess died, in which case we surface the failure rather than hang.
_START_HANDSHAKE_TIMEOUT_SECONDS = 5.0
_START_HANDSHAKE_POLL_INTERVAL_SECONDS = 0.05

# How long ``stop_daemon`` polls for pid exit before raising. SIGTERM on a
# uvicorn process typically completes in <100ms; 10s is the safety cap so
# a hung daemon doesn't deadlock the operator's CLI.
_STOP_POLL_TIMEOUT_SECONDS = 10.0
_STOP_POLL_INTERVAL_SECONDS = 0.05


class DaemonStatus(StrEnum):
    """3-state lifecycle status. Mirrors the spec §8 vocabulary.

    ``RUNNING`` — handshake present, pid responds to ``os.kill(pid, 0)``.
    ``STALE`` — handshake present, pid is dead (crashed without cleanup).
    ``NONE`` — no handshake file in this project root.
    """

    RUNNING = "running"
    STALE = "stale"
    NONE = "none"


class DaemonAlreadyRunningError(RuntimeError):
    """Raised by ``start_daemon`` when a live daemon already runs here.

    The CLI translates this to the structured-error code ``DAEMON_PORT_BUSY``
    so operators see "daemon already running on port X — `sov daemon stop`
    first" rather than a raw exception.
    """


def daemon_file_path() -> Path:
    """Return ``.sov/daemon.json`` — repo-root-level (NOT per-game).

    The daemon serves all games in a project root; the handshake lives at
    the persistence root rather than under any one ``games/<id>/`` subtree.
    """
    return save_root() / DAEMON_FILE_NAME


def _now_iso() -> str:
    """ISO-8601 UTC with ``Z`` suffix and second precision.

    Same shape as the proof envelope's ``timestamp_utc`` and the
    pending-anchor ``added_iso`` — keeps the on-disk serialization style
    uniform across the persistence layer.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid_alive(pid: int) -> bool:
    """Return True if a process with ``pid`` is alive on this OS.

    POSIX: ``os.kill(pid, 0)`` raises ``ProcessLookupError`` if the pid is
    dead, ``PermissionError`` if it's alive but owned by a different user
    (treat as alive — we only care about liveness, not ownership).

    Windows: ``os.kill`` doesn't support signal 0 in a portable way;
    fall back to ``OpenProcess``-style probe via the ``ctypes`` stdlib
    bindings only if the simple ``os.kill(pid, 0)`` raises ``OSError``.
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by another user — counts as alive
        # for our "is something there" check.
        return True
    except OSError:
        # Windows / other quirks. Fall back to a best-effort import probe.
        if sys.platform == "win32":
            return _pid_alive_windows(pid)
        return False
    return True


def _pid_alive_windows(pid: int) -> bool:
    """Windows-specific liveness probe via ``ctypes`` ``OpenProcess``.

    ``os.kill(pid, 0)`` is implemented on Windows in modern CPython but
    its semantics differ; this fallback exists so we can be explicit
    about what "alive" means on Windows: a process handle can be opened
    with ``PROCESS_QUERY_LIMITED_INFORMATION`` and its exit code is
    ``STILL_ACTIVE`` (259).
    """
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return False

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        if not ok:
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _read_handshake() -> dict[str, Any] | None:
    """Read ``.sov/daemon.json`` and return the parsed dict, or None.

    Returns None on missing file, unreadable file, or malformed JSON —
    callers treat any of those as "no daemon" and proceed. A WARNING is
    not logged here; ``daemon_status`` is the right surface for operators
    to see drift, and it consumes this function.
    """
    path = daemon_file_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_handshake(info: dict[str, Any]) -> None:
    """Atomically persist the daemon handshake document.

    Uses ``sov_engine.io_utils.atomic_write_text`` so a crash mid-write
    leaves a ``.tmp`` sibling, never a half-written ``daemon.json``.
    Same atomic-write convention as state, season, anchors, pending-anchors.

    DAEMON-002: ``daemon.json`` carries the bearer token that gates every
    daemon endpoint. Force ``0o600`` after the atomic replace so the file
    is not readable by other local users (default umask leaves it world-
    readable on POSIX; backup processes / co-located users could exfiltrate
    the token otherwise). Windows file modes don't map to POSIX bits — the
    chmod is skipped there. TODO: switch to
    ``atomic_write_text(path, content, mode=0o600)`` once the backend
    agent's BACKEND-005 fix lands the kwarg.
    """
    path = daemon_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        json.dumps(info, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    if sys.platform != "win32":
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)


def _remove_handshake() -> None:
    """Best-effort removal of ``.sov/daemon.json`` on clean exit.

    Idempotent: a missing file is not an error. Any other OSError is
    swallowed silently — the next ``sov daemon start`` will see a stale
    pid via ``daemon_status`` and auto-clean.
    """
    path = daemon_file_path()
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def daemon_status() -> DaemonStatus:
    """Return the lifecycle status for the current project root.

    ``RUNNING`` — handshake present and ``pid`` alive.
    ``STALE`` — handshake present, ``pid`` dead.
    ``NONE`` — no handshake file.

    Companion ``daemon_info()`` returns the parsed handshake dict (or
    None) for callers that need to surface port / network / readonly
    flags alongside the status.
    """
    info = _read_handshake()
    if info is None:
        return DaemonStatus.NONE
    pid = info.get("pid")
    if not isinstance(pid, int) or not _pid_alive(pid):
        return DaemonStatus.STALE
    return DaemonStatus.RUNNING


def daemon_info() -> dict[str, Any] | None:
    """Return the parsed ``.sov/daemon.json`` dict, or None.

    Companion to ``daemon_status``. Returns the same dict for both
    RUNNING and STALE statuses so the CLI can report "daemon at port
    47823 (stale)" without re-reading the file. Returns None when
    the handshake is missing or unreadable — same NONE state as
    ``daemon_status``.
    """
    return _read_handshake()


def _claim_free_port() -> int:
    """Bind to ``127.0.0.1:0`` to claim a free port from the kernel.

    The socket is closed before returning; the kernel keeps the port
    reservable for a brief window (TIME_WAIT etc.), and uvicorn binds
    to it next. Race: if another process snags the port between our
    close and uvicorn's bind, uvicorn surfaces an OSError and the spawn
    fails fast — operator can re-run.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    return port


def _generate_token() -> str:
    """Return a fresh 256-bit URL-safe base64 bearer token.

    ``secrets.token_urlsafe(32)`` returns a 43-char URL-safe string. The
    token is the only auth credential — see ``sov_daemon.auth``. New
    token at every daemon start; never reused; never persisted beyond
    the lifetime of ``.sov/daemon.json``.
    """
    return secrets.token_urlsafe(32)


# DAEMON-010: minimal env allowlist for the spawned daemon. Anything outside
# this set is dropped before ``Popen`` so unrelated secrets (``GITHUB_TOKEN``,
# ``AWS_*``, ``OPENAI_API_KEY``) in the operator's shell never reach the
# daemon's ``/proc/<pid>/environ`` view. ``XRPL_SEED`` (or the named
# ``--seed-env`` var) is forwarded explicitly when seed loading is on.
_SUBPROCESS_ENV_ALLOWLIST = frozenset(
    {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "TMPDIR",
        "TEMP",
        "TMP",
        "LANG",
        "LC_ALL",
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "SOV_LOG_LEVEL",
        "SOV_XRPL_NETWORK",
        # Windows essentials so the spawned interpreter can resolve runtime libs.
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "COMSPEC",
        "PATHEXT",
    }
)


def _build_subprocess_env(
    *,
    port: int,
    token: str,
    network: str,
    readonly: bool,
    seed_env: str | None,
    signer_file: Path | None,
) -> dict[str, str]:
    """Build the env dict for the spawned ``python -m sov_daemon`` process.

    Token + port + readonly are passed via ``SOV_DAEMON_*`` env vars; this
    keeps the token out of ``ps`` output. The seed source is forwarded if
    given: ``SOV_DAEMON_SEED_ENV`` names the env var to read at startup
    (e.g. ``XRPL_SEED``), or ``SOV_DAEMON_SIGNER_FILE`` names a file path.

    DAEMON-010: rather than ``os.environ.copy()`` (which leaks every secret
    in the operator's shell into the daemon's environ), we build the child
    env from a minimal allowlist plus the explicit ``SOV_DAEMON_*`` keys.
    The named seed var is forwarded only when ``seed_env`` is set — a
    ``--signer-file`` daemon never carries the env seed at all.
    """
    env = {k: v for k, v in os.environ.items() if k in _SUBPROCESS_ENV_ALLOWLIST}
    env["SOV_DAEMON_PORT"] = str(port)
    env["SOV_DAEMON_TOKEN"] = token
    env["SOV_DAEMON_NETWORK"] = network
    env["SOV_DAEMON_READONLY"] = "1" if readonly else "0"
    if seed_env:
        env["SOV_DAEMON_SEED_ENV"] = seed_env
        # Forward only the named seed var, nothing else from the parent shell.
        if seed_env in os.environ:
            env[seed_env] = os.environ[seed_env]
    if signer_file is not None:
        env["SOV_DAEMON_SIGNER_FILE"] = str(signer_file)
    return env


def _spawn_detached(env: dict[str, str]) -> int:
    """Spawn ``python -m sov_daemon`` detached from the parent. Returns pid.

    POSIX: ``start_new_session=True`` puts the child in its own session
    so a SIGHUP to the parent's terminal doesn't reach it. The spawned
    process itself does an ``os.fork()`` at startup and the parent of
    that fork exits immediately — so the actual daemon process is
    re-parented to init/launchd and is properly reaped when it exits.
    Without that, the daemon would linger as a zombie under the CLI's
    parent (until pytest / the user's shell exited), and stop_daemon's
    pid-alive check would falsely return True.

    The pid we wait for is the post-fork daemon pid, which the daemon
    writes into ``.sov/daemon.json`` (``info["pid"]``); the
    ``Popen``-returned pid is the intermediate parent that exits in
    milliseconds.

    Windows: ``DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`` plays the
    detachment role; Windows process accounting handles the rest.
    """
    cmd = [sys.executable, "-m", "sov_daemon"]
    popen_kwargs: dict[str, Any] = {
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        popen_kwargs["start_new_session"] = True
        # Tell the child to do an ``os.fork()`` at startup so the
        # post-fork daemon is re-parented to init/launchd.
        env["SOV_DAEMON_DOUBLE_FORK"] = "1"
    proc = subprocess.Popen(cmd, **popen_kwargs)
    if sys.platform != "win32":
        # Reap the intermediate parent process. The post-fork daemon
        # writes its real pid to ``.sov/daemon.json`` and is reaped by
        # init.
        try:
            proc.wait(timeout=_START_HANDSHAKE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            # Intermediate parent didn't exit; surface as a spawn
            # failure rather than leaking a Popen handle.
            proc.kill()
            raise RuntimeError(
                "daemon intermediate-parent process did not exit; spawn aborted."
            ) from None
    return int(proc.pid)


def _wait_for_handshake() -> dict[str, Any]:
    """Poll ``.sov/daemon.json`` until the spawned daemon writes it.

    Returns the parsed handshake dict on success. The dict's ``pid``
    field names the actual running daemon (post-fork on POSIX, the
    Popen pid on Windows).

    Raises ``RuntimeError`` if the file is not written within
    ``_START_HANDSHAKE_TIMEOUT_SECONDS``. Caller is responsible for
    distinguishing "subprocess died" from "handshake-write timeout"
    by checking ``_pid_alive(info['pid'])`` after the call returns.
    """
    deadline = time.monotonic() + _START_HANDSHAKE_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        info = _read_handshake()
        # Accept any well-formed handshake — the post-fork daemon
        # writes it, so the pid we'd compare against here isn't known
        # ahead of time on POSIX.
        if info is not None and isinstance(info.get("pid"), int):
            return info
        time.sleep(_START_HANDSHAKE_POLL_INTERVAL_SECONDS)
    raise RuntimeError(
        f"daemon did not write .sov/daemon.json within {_START_HANDSHAKE_TIMEOUT_SECONDS:.0f}s."
    )


def start_daemon(
    network: str = "testnet",
    *,
    readonly: bool = False,
    seed_env: str | None = "XRPL_SEED",
    signer_file: Path | None = None,
) -> dict[str, Any]:
    """Spawn a detached daemon for this project root.

    Returns ``{"port": int, "token": str, "pid": int}`` on success.

    Refuses (raises ``DaemonAlreadyRunningError``) when a live daemon
    already runs in this project root. Auto-cleans a stale handshake
    whose pid is dead, then proceeds.

    The seed source for anchoring is named — never embedded — in the
    spawn env: ``seed_env`` names an env var the child reads, or
    ``signer_file`` points at a file the child reads. ``readonly=True``
    skips seed loading entirely. Mainnet and testnet are both selected
    via ``network``.
    """
    status = daemon_status()
    if status is DaemonStatus.RUNNING:
        existing = daemon_info() or {}
        port_value = existing.get("port", "?")
        raise DaemonAlreadyRunningError(
            f"daemon already running on port {port_value} — `sov daemon stop` first."
        )
    if status is DaemonStatus.STALE:
        _remove_handshake()

    port = _claim_free_port()
    token = _generate_token()

    env = _build_subprocess_env(
        port=port,
        token=token,
        network=network,
        readonly=readonly,
        seed_env=seed_env,
        signer_file=signer_file,
    )
    _spawn_detached(env)

    try:
        info = _wait_for_handshake()
    except RuntimeError:
        # Best-effort cleanup so the next start sees no stale handshake.
        _remove_handshake()
        raise

    return {
        "port": int(info.get("port", port)),
        "token": str(info.get("token", token)),
        "pid": int(info["pid"]),
    }


def stop_daemon() -> bool:
    """Stop the daemon for this project root. Returns True on success.

    Reads ``.sov/daemon.json``, sends SIGTERM (POSIX) or ``terminate()``
    (Windows) to the recorded pid, polls ``os.kill(pid, 0)`` until exit
    (max 10s). Removes the handshake file on success.

    Returns False if no handshake exists. Raises ``RuntimeError`` if the
    pid does not exit within the polling deadline (operator should
    investigate / SIGKILL by hand).
    """
    info = _read_handshake()
    if info is None:
        return False
    pid = info.get("pid")
    if not isinstance(pid, int):
        _remove_handshake()
        return False

    if not _pid_alive(pid):
        # Stale handshake; nothing to stop, but remove the file so the
        # next status call returns NONE rather than STALE.
        _remove_handshake()
        return True

    # DAEMON-004: soft pid-recycle check. If the pid is alive but no longer
    # names a sov daemon process (recycled mid-CLI), refuse to signal it
    # and clear the handshake so the next status call returns NONE.
    if not _is_sov_daemon_pid(pid):
        _remove_handshake()
        raise RuntimeError(
            f"pid {pid} from .sov/daemon.json no longer points at a sov_daemon "
            "process (likely recycled). Removed stale handshake."
        )

    try:
        if sys.platform == "win32":
            # SIGTERM is not delivered cleanly on Windows console
            # processes; CTRL_BREAK_EVENT to the new process group is
            # the spec-aligned signal. Fall back to terminate() if the
            # break event raises (e.g. detached without a console).
            try:
                os.kill(pid, signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            except (OSError, AttributeError):
                _terminate_windows(pid)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        _remove_handshake()
        return True

    deadline = time.monotonic() + _STOP_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            _remove_handshake()
            return True
        time.sleep(_STOP_POLL_INTERVAL_SECONDS)

    raise RuntimeError(
        f"daemon pid {pid} did not exit within "
        f"{_STOP_POLL_TIMEOUT_SECONDS:.0f}s after SIGTERM. "
        "Investigate or kill by hand: kill -9 " + str(pid)
    )


def _is_sov_daemon_pid(pid: int) -> bool:
    """DAEMON-004: soft check the pid still names a sov_daemon process.

    Pid recycling is a real (if narrow) race: between ``_pid_alive(pid)``
    returning True and the SIGTERM landing, the original daemon could
    exit and the kernel could recycle its pid to an unrelated process —
    a shell, a build, anything the operator is currently running. The
    SIGTERM would then land on the wrong target.

    We don't try to be perfectly safe — that would require holding a
    handle to the daemon process across the whole CLI lifetime, which is
    out of scope. Instead we read the process's command line via
    ``/proc/<pid>/cmdline`` (Linux) or ``ps -p <pid> -o command=`` (Mac)
    and verify it contains ``sov`` before signalling. ``False`` means
    "definitely not the daemon — refuse to signal." Errors / unknown
    platforms fail-OPEN (return True) so a missing /proc or ps doesn't
    block legitimate stops on niche platforms.

    Windows is skipped — pid recycling is rarer in practice (the kernel
    keeps recycled pids out of immediate reuse) and we'd need a different
    probe (``QueryFullProcessImageName``). TODO: Windows soft-check via
    ctypes.
    """
    if sys.platform == "linux":
        try:
            cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            return False
        return b"sov" in cmdline.lower()
    if sys.platform == "win32":
        # TODO: Windows soft-check via QueryFullProcessImageName.
        return True
    # Mac / BSD / other POSIX: ps is the cross-platform fallback.
    try:
        out = subprocess.check_output(
            ["ps", "-o", "command=", "-p", str(pid)],
            timeout=1,
        ).decode("utf-8", errors="replace")
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        # Fail-OPEN: ps unavailable or returned nonzero. Don't block a
        # legitimate stop on a missing utility.
        return True
    return "sov" in out.lower()


def _terminate_windows(pid: int) -> None:
    """Windows fallback: ``TerminateProcess`` via ``ctypes``.

    Used when ``CTRL_BREAK_EVENT`` cannot reach the detached daemon.
    """
    try:
        import ctypes
    except ImportError:
        return
    PROCESS_TERMINATE = 0x0001
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return
    try:
        kernel32.TerminateProcess(handle, 0)
    finally:
        kernel32.CloseHandle(handle)


def run_foreground(
    network: str = "testnet",
    *,
    readonly: bool = False,
    seed_env: str | None = "XRPL_SEED",
    signer_file: Path | None = None,
    port: int | None = None,
    token: str | None = None,
) -> None:
    """Run uvicorn in the current process. Blocks until SIGINT / SIGTERM.

    Writes ``.sov/daemon.json`` on start and removes it on exit (clean
    shutdown via SIGINT, SIGTERM, or uvicorn lifespan completion).

    ``port`` and ``token`` may be supplied (the detached spawn passes
    them via env vars and re-uses the parent-claimed port); when None,
    a free port is claimed and a fresh token is generated. This is the
    sole entry point reachable from ``python -m sov_daemon``.
    """
    import uvicorn

    from sov_daemon.server import build_app

    # DAEMON-003: validate ``network`` at the daemon-startup boundary so
    # operators see a fail-fast SystemExit instead of a generic 500
    # ``INVALID_NETWORK`` on the first anchor write. ``XRPLNetwork(value)``
    # raises ``ValueError`` for typos (``testnetz``) and unknown values;
    # we coerce back to the canonical lowercase form so the rest of the
    # daemon sees one normalized string.
    from sov_transport.xrpl_internals import XRPLNetwork

    try:
        network = str(XRPLNetwork(network).value)
    except ValueError as exc:
        valid = ", ".join(n.value for n in XRPLNetwork)
        raise SystemExit(
            f"invalid SOV_DAEMON_NETWORK / --network: {network!r}; valid: {valid}"
        ) from exc

    if port is None:
        port = _claim_free_port()
    if token is None:
        token = _generate_token()

    started_iso = _now_iso()
    info: dict[str, Any] = {
        "schema_version": DAEMON_SCHEMA_VERSION,
        "pid": os.getpid(),
        "port": port,
        "token": token,
        "network": network,
        "readonly": readonly,
        "ipc_version": IPC_VERSION,
        "started_iso": started_iso,
    }
    _write_handshake(info)

    started_monotonic = time.monotonic()

    app = build_app(
        network=network,
        readonly=readonly,
        token=token,
        seed_env=seed_env,
        signer_file=signer_file,
        started_monotonic=started_monotonic,
    )

    # We do NOT install our own SIGTERM/SIGINT handlers — uvicorn installs
    # its own that flip ``server.should_exit`` and run the lifespan
    # shutdown hook in ``server.py::build_app``. That hook calls
    # ``broadcast_shutdown(app)`` which fires the ``daemon.shutdown`` SSE
    # event. The handshake-removal happens in the ``finally`` block below
    # — guaranteed to run on clean exit, signal-driven exit, or crash.
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level=os.environ.get("SOV_LOG_LEVEL", "warning").lower(),
        access_log=False,
        # uvicorn >= 0.27 understands lifespan; we use it to schedule the
        # state-change polling task in events.py.
        lifespan="on",
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    finally:
        _remove_handshake()


def run_foreground_from_env() -> None:
    """Entry point for the spawned ``python -m sov_daemon`` subprocess.

    Reads ``SOV_DAEMON_*`` env vars set by the parent ``start_daemon``
    call and dispatches into ``run_foreground``. Falls back to defaults
    for direct ``python -m sov_daemon`` invocations (test/dev use).
    """
    port_env = os.environ.get("SOV_DAEMON_PORT")
    token_env = os.environ.get("SOV_DAEMON_TOKEN")
    network = os.environ.get("SOV_DAEMON_NETWORK", "testnet")
    readonly = os.environ.get("SOV_DAEMON_READONLY", "0") == "1"
    seed_env = os.environ.get("SOV_DAEMON_SEED_ENV", "XRPL_SEED")
    signer_file_env = os.environ.get("SOV_DAEMON_SIGNER_FILE")

    port = int(port_env) if port_env else None
    token = token_env if token_env else None
    signer_file = Path(signer_file_env) if signer_file_env else None

    run_foreground(
        network=network,
        readonly=readonly,
        seed_env=seed_env,
        signer_file=signer_file,
        port=port,
        token=token,
    )


__all__ = [
    "DAEMON_FILE_NAME",
    "DAEMON_SCHEMA_VERSION",
    "IPC_VERSION",
    "DaemonAlreadyRunningError",
    "DaemonStatus",
    "daemon_file_path",
    "daemon_info",
    "daemon_status",
    "run_foreground",
    "run_foreground_from_env",
    "start_daemon",
    "stop_daemon",
]

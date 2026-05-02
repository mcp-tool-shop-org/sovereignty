"""Tests for ``sov_daemon.lifecycle`` — start / stop / status / stale-cleanup.

The lifecycle module owns ``.sov/daemon.json``: write at start, remove at
stop, distinguish RUNNING / STALE / NONE based on pid liveness. Stale-state
recovery is the trust pin — a daemon that crashed leaves a stale entry, and
the next ``sov daemon start`` must auto-clean rather than wedge.

Pinned behaviors:

* ``start_daemon(network, readonly)`` writes ``.sov/daemon.json`` with the
  documented schema (pid, port, token, network, readonly, schema_version,
  ipc_version, started_iso) and returns the (port, token) public bits.
* ``daemon_status()`` returns one of NONE / RUNNING / STALE matching pid
  liveness.
* ``start_daemon`` refuses if a *live* daemon is already running.
* ``start_daemon`` auto-cleans + proceeds if an entry exists with a *dead*
  pid (crash recovery).
* ``stop_daemon()`` removes ``.sov/daemon.json`` after the pid exits.
* SIGTERM cleanly removes ``.sov/daemon.json`` (Unix only — Windows uses
  ``terminate()`` and is exercised by ``stop_daemon`` instead).

Cross-platform: SIGTERM tests skip on Windows; ``terminate()`` paths skip
on Unix where signal delivery is the primary path.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# All daemon-package imports are deferred to test bodies because the package
# is a NEW addition this wave — keeping imports inside the test functions
# means a missing/half-built daemon surface fails one test rather than
# masking the whole module at collection time.


def _spawn_sleeper(seconds: float = 60.0) -> subprocess.Popen[bytes]:
    """Spawn a sleeping subprocess we can use as a "live pid" sentinel."""
    return subprocess.Popen([sys.executable, "-c", f"import time; time.sleep({seconds})"])


def _pid_alive(pid: int) -> bool:
    """Cross-platform pid-alive probe matching the daemon's own check."""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, OSError):
        return False
    return True


# ---------------------------------------------------------------------------
# start_daemon happy path
# ---------------------------------------------------------------------------


def test_start_daemon_writes_daemon_json_with_expected_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spec §6: ``.sov/daemon.json`` carries pid, port, token, network,
    readonly, schema_version, ipc_version, started_iso."""
    import json

    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    info = start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    try:
        state_file = tmp_path / ".sov" / "daemon.json"
        assert state_file.exists(), "start_daemon must write .sov/daemon.json"
        payload = json.loads(state_file.read_text(encoding="utf-8"))

        for key in (
            "schema_version",
            "pid",
            "port",
            "token",
            "network",
            "readonly",
            "ipc_version",
            "started_iso",
        ):
            assert key in payload, f"daemon.json missing required field: {key!r}"

        assert payload["schema_version"] == 1
        assert payload["network"] == "testnet"
        assert payload["readonly"] is True
        assert payload["ipc_version"] == 1
        assert isinstance(payload["pid"], int) and payload["pid"] > 0
        assert isinstance(payload["port"], int) and 0 < payload["port"] < 65536
        assert isinstance(payload["token"], str) and len(payload["token"]) >= 32

        # The returned info dict surfaces the operator-facing bits.
        assert "port" in info and "token" in info and "pid" in info
        assert info["port"] == payload["port"]
        assert info["token"] == payload["token"]
        assert info["pid"] == payload["pid"]
    finally:
        stop_daemon()


def test_start_daemon_token_is_url_safe_base64_minimum_256_bits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``secrets.token_urlsafe(32)`` → ≥43 url-safe chars (256-bit entropy)."""
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    info = start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    try:
        token = info["token"]
        # 32 bytes → 43 chars of urlsafe base64 (no padding).
        assert len(token) >= 43, f"token too short: {len(token)} chars"
        # url-safe alphabet: letters, digits, '-' and '_' only.
        bad = [c for c in token if not (c.isalnum() or c in "-_")]
        assert not bad, f"token contains non-url-safe chars: {bad!r}"
    finally:
        stop_daemon()


# ---------------------------------------------------------------------------
# Stale-state recovery (crash → auto-clean)
# ---------------------------------------------------------------------------


def test_start_daemon_auto_cleans_stale_entry_with_dead_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spec §8: if ``.sov/daemon.json`` exists and pid is dead, auto-clean
    + proceed. This is the crash-recovery path — a daemon that died leaves
    its entry behind, and the next ``sov daemon start`` must not wedge."""
    import json

    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    sov_dir = tmp_path / ".sov"
    sov_dir.mkdir(parents=True, exist_ok=True)
    # A pid that is essentially guaranteed dead — picking 999999, way above
    # any normal pid range. ``os.kill(pid, 0)`` will raise ProcessLookupError.
    stale_payload = {
        "schema_version": 1,
        "pid": 999999,
        "port": 12345,
        "token": "stale-token",
        "network": "testnet",
        "readonly": False,
        "ipc_version": 1,
        "started_iso": "2026-04-01T00:00:00Z",
    }
    (sov_dir / "daemon.json").write_text(json.dumps(stale_payload), encoding="utf-8")

    info = start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    try:
        # Auto-clean overwrote the stale entry — new pid is *this* process's
        # subdaemon, not 999999.
        assert info["pid"] != 999999
    finally:
        stop_daemon()


def test_start_daemon_refuses_when_live_daemon_already_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spec §8: start refuses if ``.sov/daemon.json`` exists AND pid is alive."""
    import json

    from sov_daemon.lifecycle import start_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    sov_dir = tmp_path / ".sov"
    sov_dir.mkdir(parents=True, exist_ok=True)

    # Spawn a real subprocess so the pid liveness check returns True.
    live_proc = _spawn_sleeper(60.0)
    try:
        live_payload = {
            "schema_version": 1,
            "pid": live_proc.pid,
            "port": 12345,
            "token": "live-token",
            "network": "testnet",
            "readonly": False,
            "ipc_version": 1,
            "started_iso": "2026-04-01T00:00:00Z",
        }
        (sov_dir / "daemon.json").write_text(json.dumps(live_payload), encoding="utf-8")

        with pytest.raises(Exception) as exc_info:
            start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
        msg = str(exc_info.value).lower()
        assert "already" in msg or "running" in msg or "daemon" in msg, (
            f"refusal message must mention already-running daemon: {msg!r}"
        )
    finally:
        live_proc.terminate()
        live_proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# daemon_status — three-state recogniser
# ---------------------------------------------------------------------------


def test_daemon_status_returns_none_when_no_daemon_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No ``.sov/daemon.json`` → status NONE."""
    from sov_daemon.lifecycle import daemon_status

    monkeypatch.chdir(tmp_path)
    status = daemon_status()
    # Allow either an enum-typed status or a plain string token; both are
    # legitimate. Coerce to lower-case string for comparison.
    token = getattr(status, "value", status)
    assert str(token).lower() == "none"


def test_daemon_status_returns_running_when_pid_alive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``.sov/daemon.json`` with live pid → status RUNNING."""
    from sov_daemon.lifecycle import daemon_status, start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    try:
        status = daemon_status()
        token = getattr(status, "value", status)
        assert str(token).lower() == "running"
    finally:
        stop_daemon()


def test_daemon_status_returns_stale_when_pid_dead(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``.sov/daemon.json`` with dead pid → status STALE (NOT auto-cleaned)."""
    import json

    from sov_daemon.lifecycle import daemon_status

    monkeypatch.chdir(tmp_path)
    sov_dir = tmp_path / ".sov"
    sov_dir.mkdir(parents=True, exist_ok=True)
    (sov_dir / "daemon.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pid": 999999,
                "port": 12345,
                "token": "stale",
                "network": "testnet",
                "readonly": False,
                "ipc_version": 1,
                "started_iso": "2026-04-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    status = daemon_status()
    token = getattr(status, "value", status)
    assert str(token).lower() == "stale"


# ---------------------------------------------------------------------------
# stop_daemon
# ---------------------------------------------------------------------------


def test_stop_daemon_removes_daemon_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """After ``stop_daemon``, ``.sov/daemon.json`` is gone and pid is dead."""
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    info = start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    pid = info["pid"]
    state_file = tmp_path / ".sov" / "daemon.json"
    assert state_file.exists()

    stop_daemon()
    assert not state_file.exists(), "stop_daemon must remove .sov/daemon.json"

    # pid should exit within the 10s deadline; give it a generous margin.
    deadline = time.monotonic() + 10.0
    while _pid_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not _pid_alive(pid), f"daemon pid {pid} still alive after stop"


# ---------------------------------------------------------------------------
# SIGTERM cleanup — Unix only
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="Unix signals only")
def test_daemon_sigterm_removes_daemon_json_on_clean_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """SIGTERM handler removes ``.sov/daemon.json`` (spec §8)."""
    import signal

    from sov_daemon.lifecycle import start_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    info = start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    pid = info["pid"]
    state_file = tmp_path / ".sov" / "daemon.json"
    assert state_file.exists()

    os.kill(pid, signal.SIGTERM)

    deadline = time.monotonic() + 10.0
    while state_file.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not state_file.exists(), (
        ".sov/daemon.json must be removed by SIGTERM handler on clean exit"
    )
    deadline = time.monotonic() + 5.0
    while _pid_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not _pid_alive(pid)


# Wave 10 CLI-D-bis-002: ``sov daemon status`` CLI command surface
# regression. Pre-fix the command read ``.state`` off the
# ``DaemonStatus`` StrEnum (which doesn't have such an attribute), so it
# always reported "none" even when the daemon was alive. Now reads the
# enum's ``.value`` for state and pulls port/pid/network from
# ``daemon_info()``.


def test_cli_daemon_status_reports_running_when_daemon_alive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``sov daemon status`` (text mode) prints state, port, pid when alive."""
    from typer.testing import CliRunner

    from sov_cli.main import app
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    try:
        result = runner.invoke(app, ["daemon", "status"])
        assert result.exit_code == 0, f"exit={result.exit_code} output={result.output!r}"
        # State must surface as "running" (not "none"). Port/pid/network must
        # appear from daemon_info() rather than being defaulted to "?".
        assert "running" in result.output.lower(), (
            f"sov daemon status text output must contain 'running'; got: {result.output!r}"
        )
        assert "none" not in result.output.lower(), (
            f"sov daemon status text output must NOT report 'none' when daemon is alive; "
            f"got: {result.output!r}"
        )
    finally:
        stop_daemon()


def test_cli_daemon_status_json_reports_running_with_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``sov daemon status --json`` envelope carries state + port/pid/network."""
    import json as json_mod

    from typer.testing import CliRunner

    from sov_cli.main import app
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    try:
        result = runner.invoke(app, ["daemon", "status", "--json"])
        assert result.exit_code == 0, f"exit={result.exit_code} output={result.output!r}"
        payload = json_mod.loads(result.output)
        assert payload["status"] == "ok"
        fields = {f["name"]: f for f in payload["fields"]}
        # State field present + value is "running".
        assert fields["state"]["value"] == "running", (
            f"state field value must be 'running'; got: {fields.get('state')!r}"
        )
        # Port + pid + network surface from daemon_info() now.
        assert "port" in fields, f"port field missing from --json envelope: {payload!r}"
        assert "pid" in fields, f"pid field missing from --json envelope: {payload!r}"
        assert "network" in fields, f"network field missing from --json envelope: {payload!r}"
        assert fields["network"]["value"] == "testnet"
    finally:
        stop_daemon()

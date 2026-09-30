"""Coverage tests for ``sov_daemon.lifecycle`` and ``sov_daemon.__main__``.

Everything here is offline and process-free: no real daemon, no real
subprocess, no real waiting. Platform arms are exercised by swapping the
module's ``sys`` reference for a tiny shim (``platform`` + ``executable``),
so the POSIX and Windows branches both run on either host without calling a
real platform API. Time is replaced by a fake clock that advances on every
``monotonic()`` call, so the timeout paths finish instantly.
"""

from __future__ import annotations

import asyncio
import json
import os
import runpy
import signal
import subprocess
import sys
import types
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

import sov_daemon.__main__ as daemon_main
import sov_daemon.lifecycle as lifecycle
from sov_daemon.lifecycle import DaemonAlreadyRunningError, DaemonStatus

# --------------------------------------------------------------------------- helpers


@pytest.fixture(autouse=True)
def _project_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Run every test inside an empty project root (``.sov/`` is relative)."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _fake_sys(platform: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(platform=platform, executable="/fake/python")


def _use_platform(monkeypatch: pytest.MonkeyPatch, platform: str) -> None:
    monkeypatch.setattr(lifecycle, "sys", _fake_sys(platform))


class _FakeTime:
    """Stand-in for the ``time`` module: every ``monotonic()`` jumps ahead."""

    def __init__(self, step: float = 3.0) -> None:
        self.now = 0.0
        self.step = step
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        self.now += self.step
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


def _use_fake_time(monkeypatch: pytest.MonkeyPatch, step: float = 3.0) -> _FakeTime:
    fake = _FakeTime(step)
    monkeypatch.setattr(lifecycle, "time", fake)
    return fake


def _write_raw_handshake(text: str) -> Path:
    path = lifecycle.daemon_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- _pid_alive


def test_pid_alive_rejects_non_positive_pids() -> None:
    assert lifecycle._pid_alive(0) is False
    assert lifecycle._pid_alive(-7) is False


def test_pid_alive_true_for_current_process() -> None:
    assert lifecycle._pid_alive(os.getpid()) is True


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (ProcessLookupError(), False),
        (PermissionError(), True),
    ],
)
def test_pid_alive_maps_kill_errors(
    monkeypatch: pytest.MonkeyPatch, raised: OSError, expected: bool
) -> None:
    def fake_kill(pid: int, sig: int) -> None:
        raise raised

    monkeypatch.setattr(os, "kill", fake_kill)
    assert lifecycle._pid_alive(4321) is expected


def test_pid_alive_other_oserror_on_posix_is_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_kill(pid: int, sig: int) -> None:
        raise OSError("weird")

    monkeypatch.setattr(os, "kill", fake_kill)
    _use_platform(monkeypatch, "linux")
    assert lifecycle._pid_alive(4321) is False


def test_pid_alive_other_oserror_on_windows_falls_back_to_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_kill(pid: int, sig: int) -> None:
        raise OSError("weird")

    probed: list[int] = []

    def fake_probe(pid: int) -> bool:
        probed.append(pid)
        return True

    monkeypatch.setattr(os, "kill", fake_kill)
    monkeypatch.setattr(lifecycle, "_pid_alive_windows", fake_probe)
    _use_platform(monkeypatch, "win32")
    assert lifecycle._pid_alive(4321) is True
    assert probed == [4321]


# --------------------------------------------------------------------------- handshake io


def test_read_handshake_missing_file_is_none() -> None:
    assert lifecycle._read_handshake() is None
    assert lifecycle.daemon_status() is DaemonStatus.NONE
    assert lifecycle.daemon_info() is None


@pytest.mark.parametrize("payload", ["{not json", "", "[1, 2, 3]", '"a string"', "42", "null"])
def test_read_handshake_rejects_malformed_or_non_dict(payload: str) -> None:
    _write_raw_handshake(payload)
    assert lifecycle._read_handshake() is None
    assert lifecycle.daemon_info() is None
    assert lifecycle.daemon_status() is DaemonStatus.NONE


def test_read_handshake_unreadable_file_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _write_raw_handshake('{"pid": 1}')

    def boom(self: Path, *args: Any, **kwargs: Any) -> str:
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "read_text", boom)
    assert lifecycle._read_handshake() is None


def test_write_handshake_round_trips_and_creates_parent_dir() -> None:
    assert not Path(".sov").exists()
    info = {"pid": 99, "port": 4000, "token": "t", "network": "testnet", "readonly": True}

    lifecycle._write_handshake(info)

    path = lifecycle.daemon_file_path()
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == info
    # sort_keys=True keeps the on-disk form stable.
    assert list(json.loads(text)) == sorted(info)
    assert lifecycle._read_handshake() == info
    # No atomic-write temp sibling is left behind.
    assert [p.name for p in path.parent.iterdir()] == [lifecycle.DAEMON_FILE_NAME]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_write_handshake_is_owner_only() -> None:
    lifecycle._write_handshake({"pid": 1, "token": "secret"})
    mode = lifecycle.daemon_file_path().stat().st_mode & 0o777
    assert mode == 0o600


def test_write_handshake_overwrites_previous_document() -> None:
    lifecycle._write_handshake({"pid": 1, "port": 1})
    lifecycle._write_handshake({"pid": 2, "port": 2})
    assert lifecycle._read_handshake() == {"pid": 2, "port": 2}


def test_remove_handshake_is_idempotent() -> None:
    lifecycle._remove_handshake()  # nothing there: must not raise
    lifecycle._write_handshake({"pid": 1})
    lifecycle._remove_handshake()
    assert not lifecycle.daemon_file_path().exists()
    lifecycle._remove_handshake()


# --------------------------------------------------------------------------- daemon_status


def test_status_stale_when_pid_is_not_an_int(monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle._write_handshake({"pid": "123"})
    assert lifecycle.daemon_status() is DaemonStatus.STALE
    assert lifecycle.daemon_info() == {"pid": "123"}


def test_status_stale_when_pid_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle._write_handshake({"pid": 4242})
    monkeypatch.setattr(lifecycle, "_pid_alive", lambda pid: False)
    assert lifecycle.daemon_status() is DaemonStatus.STALE


def test_status_stale_when_pid_recycled(monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle._write_handshake({"pid": 4242})
    monkeypatch.setattr(lifecycle, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(lifecycle, "_is_sov_daemon_pid", lambda pid: False)
    assert lifecycle.daemon_status() is DaemonStatus.STALE


def test_status_running_when_pid_alive_and_identity_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle._write_handshake({"pid": 4242})
    monkeypatch.setattr(lifecycle, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(lifecycle, "_is_sov_daemon_pid", lambda pid: True)
    assert lifecycle.daemon_status() is DaemonStatus.RUNNING


# --------------------------------------------------------------------------- _spawn_detached


class _FakePopen:
    """Records the spawn instead of starting anything."""

    instances: list[_FakePopen] = []
    wait_raises: bool = False

    def __init__(self, cmd: list[str], **kwargs: Any) -> None:
        self.cmd = cmd
        self.kwargs = kwargs
        self.pid = 31337
        self.waited: list[float | None] = []
        self.killed = False
        _FakePopen.instances.append(self)

    def wait(self, timeout: float | None = None) -> int:
        self.waited.append(timeout)
        if _FakePopen.wait_raises:
            raise subprocess.TimeoutExpired(self.cmd, timeout or 0)
        return 0

    def kill(self) -> None:
        self.killed = True


@pytest.fixture
def fake_popen(monkeypatch: pytest.MonkeyPatch) -> type[_FakePopen]:
    _FakePopen.instances = []
    _FakePopen.wait_raises = False
    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    return _FakePopen


def test_spawn_detached_posix_uses_new_session_and_reaps_intermediate(
    monkeypatch: pytest.MonkeyPatch, fake_popen: type[_FakePopen]
) -> None:
    _use_platform(monkeypatch, "linux")
    env = {"SOV_DAEMON_PORT": "1"}

    pid = lifecycle._spawn_detached(env)

    assert pid == 31337
    (proc,) = fake_popen.instances
    assert proc.cmd == ["/fake/python", "-m", "sov_daemon"]
    assert proc.kwargs["start_new_session"] is True
    assert "creationflags" not in proc.kwargs
    assert proc.kwargs["env"] is env
    assert proc.kwargs["close_fds"] is True
    assert proc.kwargs["stdin"] is subprocess.DEVNULL
    assert proc.kwargs["stdout"] is subprocess.DEVNULL
    assert proc.kwargs["stderr"] is subprocess.DEVNULL
    # The child is told to double-fork, and the parent waits for the intermediate.
    assert env["SOV_DAEMON_DOUBLE_FORK"] == "1"
    assert proc.waited == [lifecycle._START_HANDSHAKE_TIMEOUT_SECONDS]
    assert proc.killed is False


def test_spawn_detached_posix_kills_intermediate_that_never_exits(
    monkeypatch: pytest.MonkeyPatch, fake_popen: type[_FakePopen]
) -> None:
    _use_platform(monkeypatch, "linux")
    fake_popen.wait_raises = True

    with pytest.raises(RuntimeError, match="did not exit; spawn aborted"):
        lifecycle._spawn_detached({})

    (proc,) = fake_popen.instances
    assert proc.killed is True


def test_spawn_detached_windows_detaches_and_does_not_wait(
    monkeypatch: pytest.MonkeyPatch, fake_popen: type[_FakePopen]
) -> None:
    _use_platform(monkeypatch, "win32")
    monkeypatch.setattr(subprocess, "DETACHED_PROCESS", 0x8, raising=False)
    monkeypatch.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    env: dict[str, str] = {}

    pid = lifecycle._spawn_detached(env)

    assert pid == 31337
    (proc,) = fake_popen.instances
    assert proc.kwargs["creationflags"] == 0x8 | 0x200
    assert "start_new_session" not in proc.kwargs
    assert "SOV_DAEMON_DOUBLE_FORK" not in env
    assert proc.waited == []


# --------------------------------------------------------------------------- _health_endpoint_ok


class _FakeResponse:
    def __init__(self, status: int | None) -> None:
        if status is not None:
            self.status = status

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakeOpener:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[float] = []

    def open(self, request: urllib.request.Request, timeout: float) -> _FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        assert isinstance(self.outcome, _FakeResponse)
        return self.outcome


def _install_opener(monkeypatch: pytest.MonkeyPatch, outcome: object) -> _FakeOpener:
    opener = _FakeOpener(outcome)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *handlers: opener)
    return opener


def test_health_probe_sends_bearer_token_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = _install_opener(monkeypatch, _FakeResponse(200))

    assert lifecycle._health_endpoint_ok(4711, "tok-abc") is True

    (request,) = opener.requests
    assert request.full_url == "http://127.0.0.1:4711/health"
    assert request.get_header("Authorization") == "Bearer tok-abc"
    assert request.get_method() == "GET"
    assert opener.timeouts == [lifecycle._START_HEALTH_PROBE_TIMEOUT_SECONDS]


@pytest.mark.parametrize(("status", "expected"), [(200, True), (503, False), (None, False)])
def test_health_probe_requires_status_200(
    monkeypatch: pytest.MonkeyPatch, status: int | None, expected: bool
) -> None:
    _install_opener(monkeypatch, _FakeResponse(status))
    assert lifecycle._health_endpoint_ok(1, "t") is expected


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.URLError("refused"),
        TimeoutError("slow"),
        ConnectionResetError("reset"),
        OSError("net down"),
        ValueError("bad url"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_health_probe_swallows_connection_errors(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    _install_opener(monkeypatch, error)
    assert lifecycle._health_endpoint_ok(1, "t") is False


# --------------------------------------------------------------------------- _wait_for_handshake


def test_wait_for_handshake_times_out_when_no_handshake_appears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = _use_fake_time(monkeypatch)

    with pytest.raises(RuntimeError, match=r"did not become ready \(handshake \+ GET /health\)"):
        lifecycle._wait_for_handshake()

    # It polled (via the fake sleep) instead of really waiting.
    assert clock.sleeps
    assert set(clock.sleeps) == {lifecycle._START_HANDSHAKE_POLL_INTERVAL_SECONDS}


def test_wait_for_handshake_timeout_message_names_recovery_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_fake_time(monkeypatch)
    with pytest.raises(RuntimeError) as excinfo:
        lifecycle._wait_for_handshake()
    assert "`sov daemon status`" in str(excinfo.value)
    assert "10s" in str(excinfo.value)


def test_wait_for_handshake_times_out_when_health_never_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle._write_handshake({"pid": 5, "port": 4000, "token": "t"})
    clock = _use_fake_time(monkeypatch)
    probes: list[tuple[int, str]] = []

    def unhealthy(port: int, token: str) -> bool:
        probes.append((port, token))
        return False

    monkeypatch.setattr(lifecycle, "_health_endpoint_ok", unhealthy)

    with pytest.raises(RuntimeError, match="did not become ready"):
        lifecycle._wait_for_handshake()

    assert probes
    assert set(probes) == {(4000, "t")}
    assert clock.sleeps


@pytest.mark.parametrize(
    "handshake",
    [
        {"port": 4000, "token": "t"},  # no pid
        {"pid": "5", "port": 4000, "token": "t"},  # pid not an int
        {"pid": 5, "token": "t"},  # no port
        {"pid": 5, "port": "4000", "token": "t"},  # port not an int
        {"pid": 5, "port": 4000},  # no token
        {"pid": 5, "port": 4000, "token": ""},  # empty token
        {"pid": 5, "port": 4000, "token": 7},  # token not a str
    ],
)
def test_wait_for_handshake_ignores_malformed_handshakes(
    monkeypatch: pytest.MonkeyPatch, handshake: dict[str, Any]
) -> None:
    lifecycle._write_handshake(handshake)
    _use_fake_time(monkeypatch)

    def must_not_probe(port: int, token: str) -> bool:
        raise AssertionError("health probe must not run for a malformed handshake")

    monkeypatch.setattr(lifecycle, "_health_endpoint_ok", must_not_probe)

    with pytest.raises(RuntimeError, match="did not become ready"):
        lifecycle._wait_for_handshake()


def test_wait_for_handshake_returns_info_once_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    info = {"pid": 5, "port": 4000, "token": "tok"}
    lifecycle._write_handshake(info)
    _use_fake_time(monkeypatch)
    monkeypatch.setattr(lifecycle, "_health_endpoint_ok", lambda port, token: True)

    assert lifecycle._wait_for_handshake() == info


# --------------------------------------------------------------------------- start_daemon


def _forbid_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_spawn(env: dict[str, str]) -> int:
        raise AssertionError("must not spawn")

    monkeypatch.setattr(lifecycle, "_spawn_detached", no_spawn)


def test_start_daemon_refuses_when_a_live_daemon_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lifecycle, "daemon_status", lambda: DaemonStatus.RUNNING)
    monkeypatch.setattr(lifecycle, "daemon_info", lambda: {"port": 5555, "pid": 9})
    _forbid_spawn(monkeypatch)

    with pytest.raises(DaemonAlreadyRunningError) as excinfo:
        lifecycle.start_daemon()

    assert "already running on port 5555" in str(excinfo.value)
    assert "`sov daemon stop`" in str(excinfo.value)


def test_start_daemon_refusal_tolerates_missing_handshake_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle, "daemon_status", lambda: DaemonStatus.RUNNING)
    monkeypatch.setattr(lifecycle, "daemon_info", lambda: None)
    _forbid_spawn(monkeypatch)

    with pytest.raises(DaemonAlreadyRunningError, match=r"port \?"):
        lifecycle.start_daemon()


def test_start_daemon_cleans_stale_handshake_and_returns_ready_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle._write_handshake({"pid": 4242, "port": 1111, "token": "old"})
    monkeypatch.setattr(lifecycle, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(lifecycle, "_claim_free_port", lambda: 6000)
    monkeypatch.setattr(lifecycle, "_generate_token", lambda: "fresh-token")
    spawned: list[dict[str, str]] = []
    stale_present_at_spawn: list[bool] = []

    def fake_spawn(env: dict[str, str]) -> int:
        spawned.append(dict(env))
        stale_present_at_spawn.append(lifecycle.daemon_file_path().exists())
        return 1

    monkeypatch.setattr(lifecycle, "_spawn_detached", fake_spawn)
    monkeypatch.setattr(
        lifecycle,
        "_wait_for_handshake",
        lambda: {"pid": 77, "port": 6001, "token": "child-token"},
    )

    result = lifecycle.start_daemon("testnet", readonly=True)

    assert result == {"port": 6001, "token": "child-token", "pid": 77}
    assert stale_present_at_spawn == [False]
    (env,) = spawned
    assert env["SOV_DAEMON_PORT"] == "6000"
    assert env["SOV_DAEMON_TOKEN"] == "fresh-token"
    assert env["SOV_DAEMON_NETWORK"] == "testnet"
    assert env["SOV_DAEMON_READONLY"] == "1"
    assert "SOV_DAEMON_SEED_ENV" not in env


def test_start_daemon_falls_back_to_claimed_port_and_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle, "_claim_free_port", lambda: 6000)
    monkeypatch.setattr(lifecycle, "_generate_token", lambda: "fresh-token")
    monkeypatch.setattr(lifecycle, "_spawn_detached", lambda env: 1)
    monkeypatch.setattr(lifecycle, "_wait_for_handshake", lambda: {"pid": 12})

    assert lifecycle.start_daemon() == {"port": 6000, "token": "fresh-token", "pid": 12}


def test_start_daemon_forwards_seed_source_to_the_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seed_file = tmp_path / "seed.txt"
    spawned: list[dict[str, str]] = []
    monkeypatch.setattr(lifecycle, "_claim_free_port", lambda: 6000)
    monkeypatch.setattr(lifecycle, "_spawn_detached", lambda env: spawned.append(dict(env)) or 1)
    monkeypatch.setattr(lifecycle, "_wait_for_handshake", lambda: {"pid": 12})

    lifecycle.start_daemon("mainnet", seed_env="MY_SEED", signer_file=seed_file)

    (env,) = spawned
    assert env["SOV_DAEMON_READONLY"] == "0"
    assert env["SOV_DAEMON_NETWORK"] == "mainnet"
    assert env["SOV_DAEMON_SEED_ENV"] == "MY_SEED"
    assert env["SOV_DAEMON_SIGNER_FILE"] == str(seed_file)


def test_start_daemon_removes_partial_handshake_when_spawn_never_becomes_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child that wrote a handshake but never answers /health is cleaned up."""
    monkeypatch.setattr(lifecycle, "_claim_free_port", lambda: 6000)
    monkeypatch.setattr(lifecycle, "_generate_token", lambda: "tok")

    def spawn_writes_partial_handshake(env: dict[str, str]) -> int:
        lifecycle._write_handshake({"pid": 555, "port": 6000, "token": "tok"})
        return 555

    monkeypatch.setattr(lifecycle, "_spawn_detached", spawn_writes_partial_handshake)
    monkeypatch.setattr(lifecycle, "_health_endpoint_ok", lambda port, token: False)
    clock = _use_fake_time(monkeypatch)

    with pytest.raises(RuntimeError, match="did not become ready"):
        lifecycle.start_daemon()

    assert not lifecycle.daemon_file_path().exists()
    assert clock.sleeps  # it polled, on the fake clock


# --------------------------------------------------------------------------- stop_daemon


def test_stop_daemon_without_handshake_returns_false() -> None:
    assert lifecycle.stop_daemon() is False


def test_stop_daemon_with_non_int_pid_clears_handshake_and_returns_false() -> None:
    lifecycle._write_handshake({"pid": "not-a-pid", "port": 1})

    assert lifecycle.stop_daemon() is False
    assert not lifecycle.daemon_file_path().exists()


def test_stop_daemon_dead_pid_clears_handshake_and_returns_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle._write_handshake({"pid": 4242})
    monkeypatch.setattr(lifecycle, "_pid_alive", lambda pid: False)
    signalled: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: signalled.append((pid, sig)))

    assert lifecycle.stop_daemon() is True
    assert not lifecycle.daemon_file_path().exists()
    assert signalled == []


def test_stop_daemon_refuses_to_signal_a_recycled_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle._write_handshake({"pid": 4242})
    monkeypatch.setattr(lifecycle, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(lifecycle, "_is_sov_daemon_pid", lambda pid: False)
    signalled: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: signalled.append((pid, sig)))

    with pytest.raises(RuntimeError, match=r"pid 4242 .* no longer points at a sov_daemon"):
        lifecycle.stop_daemon()

    assert signalled == []
    assert not lifecycle.daemon_file_path().exists()


def _arm_live_daemon(
    monkeypatch: pytest.MonkeyPatch, platform: str, alive_after_signal: list[bool]
) -> list[tuple[int, int]]:
    """Live, correctly-identified daemon whose liveness follows a script.

    The first ``_pid_alive`` call (before the signal) is always True; the
    following calls replay ``alive_after_signal`` and then stay False.
    """
    lifecycle._write_handshake({"pid": 4242, "port": 1})
    _use_platform(monkeypatch, platform)
    script = [True, *alive_after_signal]

    def scripted_alive(pid: int) -> bool:
        return script.pop(0) if script else False

    monkeypatch.setattr(lifecycle, "_pid_alive", scripted_alive)
    monkeypatch.setattr(lifecycle, "_is_sov_daemon_pid", lambda pid: True)
    signalled: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: signalled.append((pid, sig)))
    return signalled


def test_stop_daemon_posix_sends_sigterm_and_waits_for_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signalled = _arm_live_daemon(monkeypatch, "linux", [True, True])
    clock = _use_fake_time(monkeypatch, step=0.01)

    assert lifecycle.stop_daemon() is True

    assert signalled == [(4242, signal.SIGTERM)]
    assert len(clock.sleeps) == 2  # two "still alive" polls, then exit
    assert set(clock.sleeps) == {lifecycle._STOP_POLL_INTERVAL_SECONDS}
    assert not lifecycle.daemon_file_path().exists()


def test_stop_daemon_posix_pid_vanishing_at_signal_time_is_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _arm_live_daemon(monkeypatch, "linux", [])

    def gone(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(os, "kill", gone)

    assert lifecycle.stop_daemon() is True
    assert not lifecycle.daemon_file_path().exists()


def test_stop_daemon_posix_timeout_reports_kill_9_and_keeps_handshake(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _arm_live_daemon(monkeypatch, "linux", [True] * 50)
    _use_fake_time(monkeypatch)

    with pytest.raises(RuntimeError) as excinfo:
        lifecycle.stop_daemon()

    message = str(excinfo.value)
    assert "daemon pid 4242 did not exit within 10s after SIGTERM" in message
    assert "kill -9 4242" in message
    assert "taskkill" not in message
    assert lifecycle.daemon_file_path().exists()


def test_stop_daemon_windows_timeout_reports_taskkill(monkeypatch: pytest.MonkeyPatch) -> None:
    _arm_live_daemon(monkeypatch, "win32", [True] * 50)
    monkeypatch.setattr(signal, "CTRL_BREAK_EVENT", 1, raising=False)
    _use_fake_time(monkeypatch)

    with pytest.raises(RuntimeError) as excinfo:
        lifecycle.stop_daemon()

    message = str(excinfo.value)
    assert "taskkill /F /PID 4242" in message
    assert "kill -9" not in message


def test_stop_daemon_windows_sends_ctrl_break(monkeypatch: pytest.MonkeyPatch) -> None:
    signalled = _arm_live_daemon(monkeypatch, "win32", [])
    monkeypatch.setattr(signal, "CTRL_BREAK_EVENT", 1, raising=False)
    terminated: list[int] = []
    monkeypatch.setattr(lifecycle, "_terminate_windows", terminated.append)
    _use_fake_time(monkeypatch, step=0.01)

    assert lifecycle.stop_daemon() is True

    assert signalled == [(4242, 1)]
    assert terminated == []
    assert not lifecycle.daemon_file_path().exists()


@pytest.mark.parametrize("error", [OSError("no console"), ProcessLookupError()])
def test_stop_daemon_windows_falls_back_to_terminate_when_break_fails(
    monkeypatch: pytest.MonkeyPatch, error: OSError
) -> None:
    _arm_live_daemon(monkeypatch, "win32", [])
    monkeypatch.setattr(signal, "CTRL_BREAK_EVENT", 1, raising=False)

    def failing_kill(pid: int, sig: int) -> None:
        raise error

    monkeypatch.setattr(os, "kill", failing_kill)
    terminated: list[int] = []
    monkeypatch.setattr(lifecycle, "_terminate_windows", terminated.append)
    _use_fake_time(monkeypatch, step=0.01)

    assert lifecycle.stop_daemon() is True
    assert terminated == [4242]


# --------------------------------------------------------------------------- identity checks


@pytest.mark.parametrize(
    ("image", "cmdline", "expected"),
    [
        (None, None, False),
        ("C:/Python313/python.exe", 'python -c "import time"', False),
        ("C:/Python313/python.exe", "python -m sov_daemon", True),
        ("C:/venv/SOV_DAEMON.exe", None, True),
        (None, "PYTHON -M SOV_DAEMON", True),
        # ``sov`` alone (e.g. a venv path under sovereignty/) must not match.
        ("C:/sovereignty/.venv/python.exe", "python -m pytest", False),
    ],
)
def test_identity_mentions_sov_daemon(
    image: str | None, cmdline: str | None, expected: bool
) -> None:
    assert lifecycle._identity_mentions_sov_daemon(image, cmdline) is expected


@pytest.mark.parametrize(
    ("image", "cmdline", "expected"),
    [
        (None, None, False),  # both probes failed: fail closed
        ("C:/py/python.exe", "python -m sov_daemon", True),
        (None, "python -m sov_daemon", True),
        ("C:/py/python.exe", None, False),
        ("C:/py/python.exe", "python -m http.server", False),
    ],
)
def test_is_sov_daemon_pid_windows_combines_both_probes(
    monkeypatch: pytest.MonkeyPatch, image: str | None, cmdline: str | None, expected: bool
) -> None:
    monkeypatch.setattr(lifecycle, "_windows_process_image_name", lambda pid: image)
    monkeypatch.setattr(lifecycle, "_windows_process_command_line", lambda pid: cmdline)
    assert lifecycle._is_sov_daemon_pid_windows(99) is expected


def test_is_sov_daemon_pid_delegates_to_windows_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_platform(monkeypatch, "win32")
    seen: list[int] = []

    def fake_windows(pid: int) -> bool:
        seen.append(pid)
        return True

    monkeypatch.setattr(lifecycle, "_is_sov_daemon_pid_windows", fake_windows)
    assert lifecycle._is_sov_daemon_pid(321) is True
    assert seen == [321]


def _patch_proc_cmdline(monkeypatch: pytest.MonkeyPatch, outcome: bytes | OSError) -> list[str]:
    """Make ``Path('/proc/<pid>/cmdline').read_bytes()`` return ``outcome``."""
    original = Path.read_bytes
    requested: list[str] = []

    def fake_read_bytes(self: Path) -> bytes:
        normalized = str(self).replace("\\", "/")
        if normalized.startswith("/proc/"):
            requested.append(normalized)
            if isinstance(outcome, OSError):
                raise outcome
            return outcome
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    return requested


@pytest.mark.parametrize(
    ("cmdline", "expected"),
    [
        (b"/usr/bin/python3\x00-m\x00sov_daemon\x00", True),
        (b"/usr/bin/python3\x00-m\x00SOV_DAEMON\x00", True),
        (b"/usr/bin/python3\x00-m\x00pytest\x00", False),
        (b"/home/x/sovereignty/.venv/bin/python\x00", False),
        (b"", False),
    ],
)
def test_is_sov_daemon_pid_linux_reads_proc_cmdline(
    monkeypatch: pytest.MonkeyPatch, cmdline: bytes, expected: bool
) -> None:
    _use_platform(monkeypatch, "linux")
    requested = _patch_proc_cmdline(monkeypatch, cmdline)

    assert lifecycle._is_sov_daemon_pid(2468) is expected
    assert requested == ["/proc/2468/cmdline"]


def test_is_sov_daemon_pid_linux_fails_closed_when_proc_unreadable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_platform(monkeypatch, "linux")
    _patch_proc_cmdline(monkeypatch, FileNotFoundError("gone"))

    assert lifecycle._is_sov_daemon_pid(2468) is False


@pytest.mark.parametrize(
    ("ps_output", "expected"),
    [
        (b"python -m sov_daemon\n", True),
        (b"/bin/zsh -l\n", False),
        (b"\xff\xfe python SOV_DAEMON", True),  # undecodable bytes are replaced, not fatal
    ],
)
def test_is_sov_daemon_pid_mac_uses_ps(
    monkeypatch: pytest.MonkeyPatch, ps_output: bytes, expected: bool
) -> None:
    _use_platform(monkeypatch, "darwin")
    calls: list[tuple[list[str], float]] = []

    def fake_check_output(cmd: list[str], timeout: float) -> bytes:
        calls.append((cmd, timeout))
        return ps_output

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    assert lifecycle._is_sov_daemon_pid(2468) is expected
    assert calls == [(["ps", "-o", "command=", "-p", "2468"], 1)]


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, "ps"),
        subprocess.TimeoutExpired("ps", 1),
        FileNotFoundError("no ps"),
        PermissionError("denied"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_is_sov_daemon_pid_mac_fails_open_without_ps(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    _use_platform(monkeypatch, "darwin")

    def broken_check_output(cmd: list[str], timeout: float) -> bytes:
        raise error

    monkeypatch.setattr(subprocess, "check_output", broken_check_output)

    assert lifecycle._is_sov_daemon_pid(2468) is True


# --------------------------------------------------------------------------- run_foreground


def _stub_uvicorn(
    monkeypatch: pytest.MonkeyPatch, *, started: bool = True, with_startup: bool = True
) -> dict[str, Any]:
    """Replace ``uvicorn.Config`` / ``uvicorn.Server`` with in-process stubs.

    ``Server.run`` drives the (wrapped) ``startup`` coroutine once, records
    what ``.sov/daemon.json`` held at that moment, and returns.
    """
    import uvicorn

    seen: dict[str, Any] = {"config_kwargs": {}, "handshake_during_run": None}

    class _StubServer:
        def __init__(self, config: Any) -> None:
            self.config = config
            self.started = False

        def run(self) -> None:
            startup = getattr(self, "startup", None)
            if startup is not None:
                asyncio.run(startup(sockets=None))
            seen["handshake_during_run"] = lifecycle._read_handshake()

    async def _startup(self: _StubServer, sockets: Any = None) -> None:
        self.started = started

    if with_startup:
        _StubServer.startup = _startup  # type: ignore[attr-defined]

    def _stub_config(*args: Any, **kwargs: Any) -> Any:
        seen["config_kwargs"] = kwargs
        return types.SimpleNamespace()

    monkeypatch.setattr(uvicorn, "Config", _stub_config)
    monkeypatch.setattr(uvicorn, "Server", _StubServer)
    return seen


def test_run_foreground_writes_handshake_after_startup_and_removes_it_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _stub_uvicorn(monkeypatch)

    lifecycle.run_foreground("testnet", readonly=True, port=4242, token="fixed-token")

    during = seen["handshake_during_run"]
    assert during is not None
    assert during["pid"] == os.getpid()
    assert during["port"] == 4242
    assert during["token"] == "fixed-token"
    assert during["network"] == "testnet"
    assert during["readonly"] is True
    assert during["schema_version"] == lifecycle.DAEMON_SCHEMA_VERSION
    assert during["ipc_version"] == lifecycle.IPC_VERSION
    assert during["started_iso"].endswith("Z")
    assert seen["config_kwargs"]["port"] == 4242
    # The ``finally`` block removed it again.
    assert not lifecycle.daemon_file_path().exists()


def test_run_foreground_claims_port_and_token_when_not_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _stub_uvicorn(monkeypatch)
    monkeypatch.setattr(lifecycle, "_claim_free_port", lambda: 5151)
    monkeypatch.setattr(lifecycle, "_generate_token", lambda: "generated")

    lifecycle.run_foreground("testnet", readonly=True)

    during = seen["handshake_during_run"]
    assert (during["port"], during["token"]) == (5151, "generated")


def test_run_foreground_skips_handshake_when_server_never_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _stub_uvicorn(monkeypatch, started=False)

    lifecycle.run_foreground("testnet", readonly=True, port=4242, token="t")

    assert seen["handshake_during_run"] is None
    assert not lifecycle.daemon_file_path().exists()


def test_run_foreground_without_startup_hook_still_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _stub_uvicorn(monkeypatch, with_startup=False)

    lifecycle.run_foreground("testnet", readonly=True, port=4242, token="t")

    assert seen["handshake_during_run"] is None
    assert not lifecycle.daemon_file_path().exists()


def test_run_foreground_removes_handshake_even_if_server_crashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import uvicorn

    class _CrashingServer:
        def __init__(self, config: Any) -> None:
            self.started = False

        def run(self) -> None:
            lifecycle._write_handshake({"pid": os.getpid()})
            raise RuntimeError("uvicorn blew up")

    monkeypatch.setattr(uvicorn, "Config", lambda *a, **k: types.SimpleNamespace())
    monkeypatch.setattr(uvicorn, "Server", _CrashingServer)

    with pytest.raises(RuntimeError, match="uvicorn blew up"):
        lifecycle.run_foreground("testnet", readonly=True, port=1, token="t")

    assert not lifecycle.daemon_file_path().exists()


@pytest.fixture
def _restore_daemon_loggers():  # type: ignore[no-untyped-def]
    import logging

    names = ("sov_daemon", "sov_engine")
    saved = {
        n: (
            list(logging.getLogger(n).handlers),
            [h.formatter for h in logging.getLogger(n).handlers],
        )
        for n in names
    }
    yield
    for n in names:
        logger = logging.getLogger(n)
        handlers, formatters = saved[n]
        logger.handlers[:] = handlers
        for h, f in zip(handlers, formatters, strict=True):
            h.setFormatter(f)


def test_run_foreground_json_log_format_installs_json_formatter(
    monkeypatch: pytest.MonkeyPatch, _restore_daemon_loggers: None
) -> None:
    import logging

    from sov_daemon.log_fields import JsonLineFormatter

    # One logger has no handler yet (a stderr handler must be added); the
    # other already has one (its formatter must be swapped in place).
    logging.getLogger("sov_daemon").handlers.clear()
    engine_logger = logging.getLogger("sov_engine")
    preexisting = logging.StreamHandler()
    engine_logger.addHandler(preexisting)
    _stub_uvicorn(monkeypatch)

    lifecycle.run_foreground("testnet", readonly=True, port=1, token="t", log_format="json")

    for name in ("sov_daemon", "sov_engine"):
        handlers = logging.getLogger(name).handlers
        assert handlers, f"{name} must have a handler"
        assert all(isinstance(h.formatter, JsonLineFormatter) for h in handlers)
    assert isinstance(preexisting.formatter, JsonLineFormatter)


def test_run_foreground_human_log_format_leaves_formatters_alone(
    monkeypatch: pytest.MonkeyPatch, _restore_daemon_loggers: None
) -> None:
    import logging

    from sov_daemon.log_fields import JsonLineFormatter

    sentinel = logging.Formatter("%(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(sentinel)
    logging.getLogger("sov_daemon").addHandler(handler)
    _stub_uvicorn(monkeypatch)

    lifecycle.run_foreground("testnet", readonly=True, port=1, token="t", log_format="human")

    assert handler.formatter is sentinel
    assert not isinstance(handler.formatter, JsonLineFormatter)


# --------------------------------------------------------------------------- __main__


@pytest.fixture
def _log_format_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # setenv first so monkeypatch restores the variable after the test.
    monkeypatch.setenv("SOV_DAEMON_LOG_FORMAT", "sentinel")


@pytest.mark.parametrize(
    ("argv", "expected_env", "expected_argv"),
    [
        (["prog", "--log-format=json"], "json", ["prog"]),
        (["prog", "--log-format=JSON"], "json", ["prog"]),
        (["prog", "--log-format=human"], "human", ["prog"]),
        (["prog", "--log-format=xml"], "sentinel", ["prog"]),
        (["prog", "--log-format", "json", "extra"], "json", ["prog", "extra"]),
        (["prog", "--log-format", "Human"], "human", ["prog"]),
        (["prog", "--log-format", "yaml", "extra"], "sentinel", ["prog", "extra"]),
        (["prog", "--log-format"], "sentinel", ["prog"]),  # dangling flag is dropped
        (["prog", "keep", "--log-format=json", "me"], "json", ["prog", "keep", "me"]),
        (["prog"], "sentinel", ["prog"]),
        ([], "sentinel", []),
    ],
    ids=[
        "equals-json",
        "equals-uppercase",
        "equals-human",
        "equals-rejected",
        "separate-json",
        "separate-mixed-case",
        "separate-rejected",
        "dangling",
        "other-args-preserved",
        "no-flag",
        "empty-argv",
    ],
)
def test_parse_log_format_arg(
    monkeypatch: pytest.MonkeyPatch,
    _log_format_env: None,
    argv: list[str],
    expected_env: str,
    expected_argv: list[str],
) -> None:
    monkeypatch.setattr(sys, "argv", list(argv))

    daemon_main._parse_log_format_arg()

    assert os.environ["SOV_DAEMON_LOG_FORMAT"] == expected_env
    assert sys.argv == expected_argv


def test_double_fork_is_a_noop_without_the_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOV_DAEMON_DOUBLE_FORK", raising=False)

    def no_fork() -> int:
        raise AssertionError("must not fork")

    monkeypatch.setattr(os, "fork", no_fork, raising=False)

    daemon_main._maybe_double_fork()


def test_double_fork_ignores_env_values_other_than_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOV_DAEMON_DOUBLE_FORK", "0")

    def no_fork() -> int:
        raise AssertionError("must not fork")

    monkeypatch.setattr(os, "fork", no_fork, raising=False)

    daemon_main._maybe_double_fork()
    assert os.environ["SOV_DAEMON_DOUBLE_FORK"] == "0"


def test_double_fork_is_a_noop_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOV_DAEMON_DOUBLE_FORK", "1")
    monkeypatch.setattr(daemon_main, "sys", _fake_sys("win32"))

    def no_fork() -> int:
        raise AssertionError("must not fork on win32")

    monkeypatch.setattr(os, "fork", no_fork, raising=False)

    daemon_main._maybe_double_fork()
    # Untouched: the marker is only cleared by the forked child.
    assert os.environ["SOV_DAEMON_DOUBLE_FORK"] == "1"


class _ExitCalled(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def test_double_fork_original_process_exits_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOV_DAEMON_DOUBLE_FORK", "1")
    monkeypatch.setattr(daemon_main, "sys", _fake_sys("linux"))
    monkeypatch.setattr(os, "fork", lambda: 4321, raising=False)

    def fake_exit(code: int) -> None:
        raise _ExitCalled(code)

    monkeypatch.setattr(os, "_exit", fake_exit)

    with pytest.raises(_ExitCalled) as excinfo:
        daemon_main._maybe_double_fork()

    assert excinfo.value.code == 0


def test_double_fork_child_continues_and_clears_the_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOV_DAEMON_DOUBLE_FORK", "1")
    monkeypatch.setattr(daemon_main, "sys", _fake_sys("linux"))
    monkeypatch.setattr(os, "fork", lambda: 0, raising=False)

    def fake_exit(code: int) -> None:
        raise AssertionError("the child must not exit")

    monkeypatch.setattr(os, "_exit", fake_exit)

    daemon_main._maybe_double_fork()

    assert "SOV_DAEMON_DOUBLE_FORK" not in os.environ


def test_main_parses_args_then_forks_then_runs_the_daemon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    monkeypatch.setattr(daemon_main, "_parse_log_format_arg", lambda: order.append("parse"))
    monkeypatch.setattr(daemon_main, "_maybe_double_fork", lambda: order.append("fork"))
    monkeypatch.setattr(daemon_main, "run_foreground_from_env", lambda: order.append("run"))

    daemon_main.main()

    assert order == ["parse", "fork", "run"]


def test_running_the_module_as_a_script_starts_the_daemon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``python -m sov_daemon`` reaches ``run_foreground_from_env`` (stubbed)."""
    ran: list[dict[str, str | None]] = []
    monkeypatch.setattr(sys, "argv", ["sov_daemon", "--log-format=json"])
    monkeypatch.setenv("SOV_DAEMON_LOG_FORMAT", "sentinel")
    monkeypatch.delenv("SOV_DAEMON_DOUBLE_FORK", raising=False)
    monkeypatch.setattr(
        lifecycle,
        "run_foreground_from_env",
        lambda: ran.append({"format": os.environ.get("SOV_DAEMON_LOG_FORMAT")}),
    )

    runpy.run_path(str(Path(daemon_main.__file__)), run_name="__main__")

    assert ran == [{"format": "json"}]

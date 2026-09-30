"""SOV_DAEMON_HOST — the container-only bind knob.

The daemon binds ``127.0.0.1`` everywhere except inside the container
image, which sets ``SOV_DAEMON_HOST=0.0.0.0`` so Docker can forward the
port. These tests pin the three properties that keep that safe:

1. Unset → loopback (every CLI / desktop spawn keeps today's behaviour).
2. Set → forwarded to uvicorn unchanged.
3. ``sov daemon start`` never forwards it to the detached child, so a
   stray ``SOV_DAEMON_HOST`` in an operator's shell cannot widen a
   desktop daemon's bind.
"""

from __future__ import annotations

from typing import Any

import pytest


def _capture_run_foreground(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    import sov_daemon.lifecycle as lifecycle

    captured: dict[str, Any] = {}

    def fake_run_foreground(network: str = "testnet", **kwargs: Any) -> None:
        captured["network"] = network
        captured.update(kwargs)

    monkeypatch.setattr(lifecycle, "run_foreground", fake_run_foreground)
    for var in ("SOV_DAEMON_PORT", "SOV_DAEMON_TOKEN", "SOV_DAEMON_READONLY"):
        monkeypatch.delenv(var, raising=False)
    return captured


def test_host_defaults_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    from sov_daemon.lifecycle import run_foreground_from_env

    captured = _capture_run_foreground(monkeypatch)
    monkeypatch.delenv("SOV_DAEMON_HOST", raising=False)

    run_foreground_from_env()

    assert captured["host"] == "127.0.0.1"


def test_empty_host_falls_back_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    from sov_daemon.lifecycle import run_foreground_from_env

    captured = _capture_run_foreground(monkeypatch)
    monkeypatch.setenv("SOV_DAEMON_HOST", "")

    run_foreground_from_env()

    assert captured["host"] == "127.0.0.1"


def test_host_env_is_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    from sov_daemon.lifecycle import run_foreground_from_env

    captured = _capture_run_foreground(monkeypatch)
    monkeypatch.setenv("SOV_DAEMON_HOST", "0.0.0.0")
    monkeypatch.setenv("SOV_DAEMON_PORT", "47823")
    monkeypatch.setenv("SOV_DAEMON_READONLY", "1")

    run_foreground_from_env()

    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 47823
    assert captured["readonly"] is True
    assert captured["seed_env"] is None


def test_detached_spawn_never_inherits_host(monkeypatch: pytest.MonkeyPatch) -> None:
    from sov_daemon.lifecycle import _build_subprocess_env

    monkeypatch.setenv("SOV_DAEMON_HOST", "0.0.0.0")

    env = _build_subprocess_env(
        port=12345,
        token="tok",
        network="testnet",
        readonly=True,
        seed_env=None,
        signer_file=None,
    )

    assert "SOV_DAEMON_HOST" not in env

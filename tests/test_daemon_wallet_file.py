"""JOB-011: daemon seed precedence matches CLI (signer-file, wallet file, env)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("starlette", reason="daemon extra not installed")
httpx = pytest.importorskip("httpx", reason="daemon extra not installed")

_FILE = "sEdFILEONLY"
_ENV = "sEdENVONLY"
_SIGNER = "sEdSIGNERONLY"


def _state(*, signer_file: Path | None = None, seed_env: str = "XRPL_SEED") -> SimpleNamespace:
    return SimpleNamespace(signer_file=signer_file, seed_env=seed_env)


def test_load_seed_reads_wallet_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sov_daemon.server import _load_seed

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    (tmp_path / ".sov").mkdir()
    (tmp_path / ".sov" / "wallet_seed.txt").write_text(_FILE + "\n", encoding="utf-8")
    assert _load_seed(_state()) == _FILE


def test_load_seed_wallet_file_beats_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sov_daemon.server import _load_seed

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _ENV)
    (tmp_path / ".sov").mkdir()
    (tmp_path / ".sov" / "wallet_seed.txt").write_text(_FILE + "\n", encoding="utf-8")
    assert _load_seed(_state()) == _FILE


def test_load_seed_signer_file_beats_wallet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from sov_daemon.server import _load_seed

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _ENV)
    (tmp_path / ".sov").mkdir()
    (tmp_path / ".sov" / "wallet_seed.txt").write_text(_FILE + "\n", encoding="utf-8")
    signer = tmp_path / "signer.txt"
    signer.write_text(_SIGNER + "\n", encoding="utf-8")
    assert _load_seed(_state(signer_file=signer)) == _SIGNER


def test_load_seed_none_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sov_daemon.server import _load_seed

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    assert _load_seed(_state()) is None


@pytest.mark.asyncio
async def test_flush_pending_empty_seed_raises_config_no_wallet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from sov_daemon.server import ConfigNoWalletError, flush_pending_anchors
    from sov_engine.io_utils import add_pending_anchor

    monkeypatch.chdir(tmp_path)
    add_pending_anchor("s42", "1", "a" * 64)
    with pytest.raises(ConfigNoWalletError):
        await flush_pending_anchors(
            game_id="s42",
            network="testnet",
            seed="",
            ruleset="campfire_v1",
        )


@pytest.mark.asyncio
async def test_anchor_without_seed_returns_config_no_wallet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from sov_daemon.server import DaemonConfig, build_app
    from tests.test_daemon_endpoints import _AUTH, _FIXED_TOKEN, _seed_game

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    _seed_game(tmp_path, "s42")
    from sov_engine.io_utils import add_pending_anchor

    add_pending_anchor("s42", "1", "a" * 64)
    app = build_app(DaemonConfig(network="testnet", readonly=False, token=_FIXED_TOKEN))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/games/s42/anchor", headers=_AUTH)
    assert response.status_code == 400
    assert response.json().get("code") == "CONFIG_NO_WALLET"

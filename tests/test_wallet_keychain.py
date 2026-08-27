"""JOB-025: mainnet seed prefers OS keychain over plaintext.

Uses an in-memory keyring backend only — no libsecret / keyrings.alt.
Never asserts by printing the seed value into failure messages.
"""

from __future__ import annotations

from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend
from typer.testing import CliRunner

from sov_cli.main import app
from sov_engine.wallet_seed import (
    get_mainnet_seed,
    resolve_wallet_seed,
    set_mainnet_seed,
)

runner = CliRunner()

_SECRET = "sEdVMainnetTestSeedDoNotLogXXXX"


class _MemoryKeyring(KeyringBackend):
    """Test-only in-memory backend (no OS store, no second native dep)."""

    priority = 1.0

    def __init__(self) -> None:
        self._passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._passwords[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self._passwords.pop((service, username), None)


@pytest.fixture()
def memory_keyring(monkeypatch: pytest.MonkeyPatch) -> _MemoryKeyring:
    backend = _MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    # Leave no secret in the process keyring after the test.
    backend._passwords.clear()


def test_mainnet_prefers_keyring_over_plaintext_file(
    memory_keyring: _MemoryKeyring, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    wallet_file = tmp_path / ".sov" / "wallet_seed.txt"
    wallet_file.parent.mkdir(parents=True)
    wallet_file.write_text("sEdVPlaintextFileSeedShouldLoseXXXX\n", encoding="utf-8")
    set_mainnet_seed(_SECRET)

    got = resolve_wallet_seed(
        network="mainnet",
        wallet_file=wallet_file,
        seed_env="XRPL_SEED",
    )
    assert got == _SECRET
    assert got != wallet_file.read_text(encoding="utf-8").strip()


def test_testnet_still_uses_plaintext_file(
    memory_keyring: _MemoryKeyring, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    wallet_file = tmp_path / ".sov" / "wallet_seed.txt"
    wallet_file.parent.mkdir(parents=True)
    file_seed = "sEdVTestnetFileSeedOKXXXXXXXX"
    wallet_file.write_text(file_seed + "\n", encoding="utf-8")
    set_mainnet_seed(_SECRET)

    got = resolve_wallet_seed(
        network="testnet",
        wallet_file=wallet_file,
        seed_env="XRPL_SEED",
    )
    assert got == file_seed


def test_wallet_mainnet_stores_without_printing_seed(
    memory_keyring: _MemoryKeyring, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _SECRET)
    result = runner.invoke(app, ["wallet", "--network", "mainnet"])
    assert result.exit_code == 0, result.output
    assert _SECRET not in result.output
    assert "OS keychain" in result.output or "keychain" in result.output.lower()
    assert get_mainnet_seed() == _SECRET
    # Must not silently write plaintext primary for mainnet.
    plaintext = tmp_path / ".sov" / "wallet_seed.txt"
    assert not plaintext.exists()


def test_signer_file_beats_keyring(
    memory_keyring: _MemoryKeyring, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    set_mainnet_seed(_SECRET)
    override = tmp_path / "override.seed"
    override_seed = "sEdVSignerFileOverrideSeedXXXX"
    override.write_text(override_seed + "\n", encoding="utf-8")
    got = resolve_wallet_seed(
        network="mainnet",
        signer_file=override,
        wallet_file=tmp_path / "missing.txt",
        seed_env="XRPL_SEED",
    )
    assert got == override_seed

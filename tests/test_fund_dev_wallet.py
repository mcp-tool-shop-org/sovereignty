"""Tests for the v2.1 ``fund_dev_wallet`` (faucet rename).

Per ``docs/v2.1-bridge-changes.md`` §6:

* ``fund_dev_wallet(TESTNET)`` — faucet auto-fund.
* ``fund_dev_wallet(DEVNET)`` — faucet auto-fund.
* ``fund_dev_wallet(MAINNET)`` — raises ``MainnetFaucetError``.
* ``fund_testnet_wallet()`` — deprecated; emits ``DeprecationWarning`` and
  delegates to ``fund_dev_wallet(TESTNET)``.

The faucet calls are mocked via fake ``xrpl.*`` modules; this file does not
hit the network.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


def _install_fake_xrpl_modules() -> dict[str, types.ModuleType]:
    fakes: dict[str, types.ModuleType] = {}

    def _make(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        fakes[name] = m
        return m

    xrpl = _make("xrpl")
    clients = _make("xrpl.clients")
    wallet = _make("xrpl.wallet")

    xrpl.__dict__["clients"] = clients
    xrpl.__dict__["wallet"] = wallet

    clients.__dict__["JsonRpcClient"] = MagicMock(name="JsonRpcClient")
    wallet.__dict__["Wallet"] = MagicMock(name="Wallet")
    wallet.__dict__["generate_faucet_wallet"] = MagicMock(name="generate_faucet_wallet")

    return fakes


@pytest.fixture
def fake_xrpl(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    fakes = _install_fake_xrpl_modules()
    for name, mod in fakes.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return fakes


def _stub_faucet_wallet(
    fake_xrpl: dict[str, types.ModuleType],
    *,
    address: str = "rTestAddress",
    seed: str = "sEdLEGACYSEED",
) -> MagicMock:
    fake_wallet = MagicMock()
    fake_wallet.address = address
    fake_wallet.seed = seed
    wallet_mod = fake_xrpl["xrpl.wallet"]
    wallet_mod.generate_faucet_wallet.return_value = fake_wallet
    return fake_wallet


# ---------------------------------------------------------------------------
# fund_dev_wallet
# ---------------------------------------------------------------------------


def test_fund_dev_wallet_testnet_uses_testnet_url(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``fund_dev_wallet(TESTNET)`` constructs a JsonRpcClient at the testnet URL."""
    _stub_faucet_wallet(fake_xrpl, address="rTestAddr", seed="sEdTEST")

    from sov_transport.xrpl import XRPLNetwork, fund_dev_wallet

    address, seed = fund_dev_wallet(XRPLNetwork.TESTNET)
    assert address == "rTestAddr"
    assert seed == "sEdTEST"

    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.assert_called_once()
    url_arg = clients_mod.JsonRpcClient.call_args.args[0]
    assert url_arg == "https://s.altnet.rippletest.net:51234/"


def test_fund_dev_wallet_devnet_uses_devnet_url(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``fund_dev_wallet(DEVNET)`` uses the documented devnet URL."""
    _stub_faucet_wallet(fake_xrpl, address="rDevAddr", seed="sEdDEV")

    from sov_transport.xrpl import XRPLNetwork, fund_dev_wallet

    address, seed = fund_dev_wallet(XRPLNetwork.DEVNET)
    assert address == "rDevAddr"
    assert seed == "sEdDEV"

    clients_mod = fake_xrpl["xrpl.clients"]
    url_arg = clients_mod.JsonRpcClient.call_args.args[0]
    assert url_arg == "https://s.devnet.rippletest.net:51234/"


def test_fund_dev_wallet_mainnet_raises_mainnet_faucet_error(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``fund_dev_wallet(MAINNET)`` raises ``MainnetFaucetError`` with the
    documented operator-actionable message — mainnet has no faucet."""
    from sov_transport.xrpl import MainnetFaucetError, XRPLNetwork, fund_dev_wallet

    with pytest.raises(MainnetFaucetError) as exc_info:
        fund_dev_wallet(XRPLNetwork.MAINNET)

    msg = str(exc_info.value)
    # Operator-actionable hint per spec §6.
    assert "mainnet has no faucet" in msg.lower()
    # Faucet was NOT called (mainnet path short-circuits).
    wallet_mod = fake_xrpl["xrpl.wallet"]
    wallet_mod.generate_faucet_wallet.assert_not_called()


def test_fund_dev_wallet_default_is_testnet(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``fund_dev_wallet()`` with no args defaults to TESTNET (matches v2.0.x)."""
    _stub_faucet_wallet(fake_xrpl)

    from sov_transport.xrpl import fund_dev_wallet

    address, seed = fund_dev_wallet()
    assert address == "rTestAddress"
    assert seed == "sEdLEGACYSEED"

    clients_mod = fake_xrpl["xrpl.clients"]
    url_arg = clients_mod.JsonRpcClient.call_args.args[0]
    assert url_arg == "https://s.altnet.rippletest.net:51234/"


# ---------------------------------------------------------------------------
# fund_testnet_wallet — compat shim
# ---------------------------------------------------------------------------


def test_fund_testnet_wallet_emits_deprecation_warning_and_returns_same(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``fund_testnet_wallet()`` emits ``DeprecationWarning`` AND returns the
    same ``(address, seed)`` shape as ``fund_dev_wallet(TESTNET)``."""
    _stub_faucet_wallet(fake_xrpl, address="rShimAddr", seed="sEdSHIM")

    from sov_transport.xrpl_testnet import fund_testnet_wallet

    with pytest.warns(DeprecationWarning):
        address, seed = fund_testnet_wallet()
    assert address == "rShimAddr"
    assert seed == "sEdSHIM"

    # Faucet was actually called via the testnet URL — the shim delegates,
    # not duplicates.
    clients_mod = fake_xrpl["xrpl.clients"]
    url_arg = clients_mod.JsonRpcClient.call_args.args[0]
    assert url_arg == "https://s.altnet.rippletest.net:51234/"

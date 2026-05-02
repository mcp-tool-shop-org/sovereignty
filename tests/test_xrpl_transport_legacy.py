"""Backward-compat fixture: v2.0.2-anchored proofs verify under v2.1.

Per ``docs/v2.1-bridge-changes.md`` §7, a v2.0.2 anchored proof was
single-memo, single-round per tx. v2.1's verify path MUST handle that
shape unchanged because the on-chain history is read-only — operators
with v2.0.2 anchors must still be able to verify them after upgrading.

This file pins:

1. The v2.0.2 single-memo response shape verifies green via
   ``XRPLTransport(TESTNET).is_anchored_on_chain(...)``.
2. The legacy ``XRPLTestnetTransport`` re-export shim still works
   (constructs and verifies) but emits ``DeprecationWarning`` on
   instantiation. Removed in v2.2.
3. The legacy ``fund_testnet_wallet()`` re-export emits
   ``DeprecationWarning`` and delegates to ``fund_dev_wallet(TESTNET)``.
4. The deprecated ``LedgerTransport.verify(...)`` alias on
   ``XRPLTransport`` emits ``DeprecationWarning`` and delegates to
   ``is_anchored_on_chain`` (also covered in test_xrpl_transport.py;
   pinned again here so the v2.0 -> v2.1 verify path is one file).
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


def _install_fake_xrpl_modules() -> dict[str, types.ModuleType]:
    """Install fake ``xrpl.*`` submodules so deferred imports succeed."""
    fakes: dict[str, types.ModuleType] = {}

    def _make(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        fakes[name] = m
        return m

    xrpl = _make("xrpl")
    clients = _make("xrpl.clients")
    models = _make("xrpl.models")
    transaction = _make("xrpl.transaction")
    wallet = _make("xrpl.wallet")

    xrpl.__dict__["clients"] = clients
    xrpl.__dict__["models"] = models
    xrpl.__dict__["transaction"] = transaction
    xrpl.__dict__["wallet"] = wallet

    clients.__dict__["JsonRpcClient"] = MagicMock(name="JsonRpcClient")
    models.__dict__["Memo"] = MagicMock(name="Memo")
    models.__dict__["Payment"] = MagicMock(name="Payment")
    models.__dict__["Tx"] = MagicMock(name="Tx")
    transaction.__dict__["submit_and_wait"] = MagicMock(name="submit_and_wait")
    wallet.__dict__["Wallet"] = MagicMock(name="Wallet")
    wallet.__dict__["generate_faucet_wallet"] = MagicMock(name="generate_faucet_wallet")

    return fakes


@pytest.fixture
def fake_xrpl(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    fakes = _install_fake_xrpl_modules()
    for name, mod in fakes.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return fakes


# ---------------------------------------------------------------------------
# 1. v2.0.2 single-memo wire shape verifies under v2.1's is_anchored_on_chain
# ---------------------------------------------------------------------------


def test_v2_0_2_single_memo_proof_verifies_under_v2_1(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """Recorded testnet response with a single SOV memo verifies green.

    The wire shape on v2.0.2 was: one Payment, one memo, one round. Today's
    ``XRPLTransport.is_anchored_on_chain`` must handle that shape exactly
    as it handled it in v2.0.2 — the on-chain history is immutable, so any
    operator with v2.0.2 anchors must keep being able to verify them. Note
    the post-BRIDGE-004 return is ``ChainLookupResult.FOUND`` (not ``True``)
    — the v2.0.2 verify call site went through ``verify()`` which still
    returns ``bool``; this test pins the v2.1 surface ``is_anchored_on_chain``
    behavior on the same recorded shape.
    """
    from sov_transport.xrpl import ChainLookupResult, XRPLNetwork, XRPLTransport, _to_hex

    expected_hash = "abc123def4567890abc123def4567890abc123def4567890abc123def4567890"
    legacy_memo = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        # v2.0.2 wire shape: top-level Memos with exactly one entry.
        "Memos": [{"Memo": {"MemoData": _to_hex(legacy_memo)}}],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    transport = XRPLTransport(XRPLNetwork.TESTNET)
    assert (
        transport.is_anchored_on_chain(txid="recorded-tx-hash", expected_hash=expected_hash)
        is ChainLookupResult.FOUND
    )


# ---------------------------------------------------------------------------
# 2. XRPLTestnetTransport compat shim — still works, emits DeprecationWarning
# ---------------------------------------------------------------------------


def test_xrpl_testnet_transport_shim_emits_deprecation_warning() -> None:
    """Importing + instantiating ``XRPLTestnetTransport`` emits
    ``DeprecationWarning`` so users see the v2.1 → v2.2 migration window."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    with pytest.warns(DeprecationWarning):
        XRPLTestnetTransport()


def test_xrpl_testnet_transport_shim_verifies_legacy_anchor(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """The shim's verify path still resolves a v2.0.2 single-memo proof.

    Belt-and-suspenders for the transition window: even if a script is
    pinned to ``XRPLTestnetTransport`` and not yet migrated to
    ``XRPLTransport(network=...)``, its verify must keep returning True for
    a recorded v2.0.2 anchor.
    """
    from sov_transport.xrpl import _to_hex
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    expected_hash = "abc123def4567890abc123def4567890abc123def4567890abc123def4567890"
    legacy_memo = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.result = {
        "Memos": [{"Memo": {"MemoData": _to_hex(legacy_memo)}}],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    # Capture both the instantiation DeprecationWarning AND the .verify()
    # alias DeprecationWarning. We don't assert on the count — just assert
    # the chain returns True.
    with pytest.warns(DeprecationWarning):
        transport = XRPLTestnetTransport()
        result = transport.verify("recorded-tx-hash", expected_hash)
    assert result is True


# ---------------------------------------------------------------------------
# 3. fund_testnet_wallet compat shim — DeprecationWarning + delegates
# ---------------------------------------------------------------------------


def test_fund_testnet_wallet_shim_emits_deprecation_warning(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``fund_testnet_wallet()`` emits ``DeprecationWarning`` + delegates
    to ``fund_dev_wallet(TESTNET)``. Removed in v2.2."""
    fake_wallet = MagicMock()
    fake_wallet.address = "rTestAddress"
    fake_wallet.seed = "sEdLEGACYSEED"
    wallet_mod = fake_xrpl["xrpl.wallet"]
    wallet_mod.generate_faucet_wallet.return_value = fake_wallet

    from sov_transport.xrpl_testnet import fund_testnet_wallet

    with pytest.warns(DeprecationWarning):
        address, seed = fund_testnet_wallet()

    assert address == "rTestAddress"
    assert seed == "sEdLEGACYSEED"


# ---------------------------------------------------------------------------
# 4. LedgerTransport.verify deprecated alias — pinned end-to-end
# ---------------------------------------------------------------------------


def test_xrpl_transport_verify_alias_delegates_to_is_anchored(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``XRPLTransport.verify`` is a thin DeprecationWarning-emitting wrapper.

    Spec §3 keeps ``verify(txid, expected_hash) -> bool`` as a compat alias
    that defers to ``is_anchored_on_chain``. End-to-end here so a downstream
    consumer that hasn't migrated yet keeps working through v2.1.
    """
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport, _to_hex

    expected_hash = "abc123"
    memo = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.result = {
        "Memos": [{"Memo": {"MemoData": _to_hex(memo)}}],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport(XRPLNetwork.TESTNET)
    with pytest.warns(DeprecationWarning):
        assert t.verify("TXID", expected_hash) is True


# ---------------------------------------------------------------------------
# 5. BRIDGE-B-002 — PEP-562 ``__getattr__`` deprecation on private helpers
# ---------------------------------------------------------------------------
#
# The xrpl_testnet shim used to bind ``_to_hex`` / ``_from_hex`` /
# ``_extract_memos`` / ``_classify_submit_error`` / ``TESTNET_URL`` as
# module-level names imported from ``sov_transport.xrpl``. That meant the
# class + faucet helper warned loudly on access while the five sibling
# helpers re-exported silently. Wave-9 closed the gap with a PEP-562
# ``__getattr__`` that emits ``DeprecationWarning`` on access and returns
# the underlying value from ``sov_transport.xrpl_internals``.
#
# These tests pin:
#   - each of the 5 deprecated re-exports warns on access,
#   - the warning message points callers at ``sov_transport.xrpl_internals``,
#   - the returned value is the real underlying object (functions resolve
#     to the same callable; the constant returns the canonical RPC URL),
#   - unknown attributes still raise ``AttributeError`` (PEP-562 contract).


@pytest.mark.parametrize(
    "name",
    ["_to_hex", "_from_hex", "_extract_memos", "_classify_submit_error"],
)
def test_xrpl_testnet_shim_private_helper_access_warns(name: str) -> None:
    """Accessing a deprecated private-helper re-export emits ``DeprecationWarning``.

    Each access goes through the PEP-562 ``__getattr__`` and is redirected to
    ``sov_transport.xrpl_internals`` (BRIDGE-B-002). The returned object is
    the same callable as the canonical home — a downstream caller still on
    the legacy path keeps working unchanged through the v2.2 removal window.
    """
    import sov_transport.xrpl_internals as internals
    import sov_transport.xrpl_testnet as shim

    with pytest.warns(DeprecationWarning, match="sov_transport.xrpl_internals"):
        legacy_value = getattr(shim, name)

    assert legacy_value is getattr(internals, name)


def test_xrpl_testnet_shim_testnet_url_access_warns() -> None:
    """``TESTNET_URL`` is reachable but warns on access.

    The canonical home is ``sov_transport.xrpl_internals._NETWORK_TABLE``;
    the legacy constant resolves to that table's testnet RPC URL so
    pre-existing call sites keep dereferencing the same string.
    """
    import sov_transport.xrpl_testnet as shim
    from sov_transport.xrpl import XRPLNetwork
    from sov_transport.xrpl_internals import _NETWORK_TABLE

    with pytest.warns(DeprecationWarning, match="sov_transport.xrpl_internals"):
        url = shim.TESTNET_URL

    assert url == _NETWORK_TABLE[XRPLNetwork.TESTNET][0]
    assert url == "https://s.altnet.rippletest.net:51234/"


def test_xrpl_testnet_shim_unknown_attribute_raises() -> None:
    """Unknown attribute access raises ``AttributeError`` (PEP-562 contract).

    The ``__getattr__`` only intercepts the documented re-export set; any
    other name falls through to the standard module-attribute lookup and
    must surface as ``AttributeError`` so importers see real errors instead
    of silent ``None``.
    """
    import sov_transport.xrpl_testnet as shim

    with pytest.raises(AttributeError, match="no attribute 'definitely_not_a_real_helper'"):
        _ = shim.definitely_not_a_real_helper  # type: ignore[attr-defined]


def test_xrpl_testnet_shim_class_and_faucet_remain_silent_at_import() -> None:
    """Importing the shim itself does NOT warn — only ACCESS to deprecated
    names warns.

    PEP-562 ``__getattr__`` fires only when a name is not already bound at
    module scope. ``XRPLTestnetTransport``, ``fund_testnet_wallet``,
    ``XRPLNetwork``, and ``__all__`` stay bound directly so a bare ``import
    sov_transport.xrpl_testnet`` does not log spam at module-load time. The
    class + faucet helper still warn at instantiation / call (covered by
    tests 2 and 3 above).
    """
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        # If this raised the import-time would have triggered a warning.
        import sov_transport.xrpl_testnet  # noqa: F401

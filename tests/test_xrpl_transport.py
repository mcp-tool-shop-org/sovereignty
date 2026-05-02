"""Tests for the XRPL transport (v2.1 unified surface).

Migrated from ``tests/test_transport.py`` for the ``XRPLTransport`` /
``XRPLNetwork`` rename. All tests target the v2.1 surface directly:

    from sov_transport.xrpl import XRPLTransport, XRPLNetwork

The legacy ``XRPLTestnetTransport`` shim is exercised in
``tests/test_xrpl_transport_legacy.py`` (which captures the
``DeprecationWarning`` it must emit). NullTransport tests stay in
``tests/test_transport.py``.

Pinned behaviors:

* Per-network endpoint table (TESTNET / MAINNET / DEVNET).
* ``url=`` override and ``allow_insecure`` flag.
* ``transport.explorer_tx_url(txid)`` returns the right per-network prefix.
* ``anchor`` (legacy single-round) — secret scrub on exception, oversized memo
  ValueError, happy-path returns submit_and_wait response hash.
* ``is_anchored_on_chain`` (replaces the v2.0 substring-match ``verify``):
  3-state ``ChainLookupResult`` (FOUND / NOT_FOUND / LOOKUP_FAILED) per
  BRIDGE-004, structured SOV grammar parse, empty expected_hash and txid
  rejected, malformed memos do not DoS, response-shape fallback (top-level
  vs ``result['tx']``).
* ``anchor_batch`` — empty rounds rejected, per-memo cap enforced, total
  batch size capped (BRIDGE-002), caller-frame seed scrub (BRIDGE-001).
* Hex helpers ``_to_hex`` / ``_from_hex`` are crash-free on adversarial input.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock

import pytest

# A recognizable seed string we can grep for in scrubbed exception reprs.
_TEST_SEED = "sEdXXXXXXXXXXXXXXXXXXXXXXX"


# ---------------------------------------------------------------------------
# Import shape
# ---------------------------------------------------------------------------


def test_xrpl_transport_imports_cleanly() -> None:
    """``XRPLTransport`` should import even without xrpl-py installed."""
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(XRPLNetwork.TESTNET)
    assert t.url == "https://s.altnet.rippletest.net:51234/"


def _xrpl_is_importable() -> bool:
    """Probe whether the xrpl package can be imported in this environment."""
    try:
        import xrpl  # noqa: F401
    except ImportError:
        return False
    return True


def test_xrpl_transport_anchor_requires_xrpl_py() -> None:
    """``anchor`` raises RuntimeError when xrpl-py is not importable."""
    if _xrpl_is_importable():
        pytest.skip("xrpl-py is installed; import-guard branch is unreachable")

    from sov_transport.xrpl import XRPLTransport

    t = XRPLTransport()
    with pytest.raises(RuntimeError, match="xrpl-py is not installed"):
        t.anchor("hash", "memo", "signer")


# ---------------------------------------------------------------------------
# Network parameterization
# ---------------------------------------------------------------------------


def test_xrpl_network_enum_values() -> None:
    """``XRPLNetwork`` is a StrEnum with the three canonical values."""
    from sov_transport.xrpl import XRPLNetwork

    assert XRPLNetwork.TESTNET.value == "testnet"
    assert XRPLNetwork.MAINNET.value == "mainnet"
    assert XRPLNetwork.DEVNET.value == "devnet"
    # StrEnum: members round-trip through their string value cleanly via the
    # constructor (used by config / env-var / CLI flag parsing).
    assert XRPLNetwork("testnet") is XRPLNetwork.TESTNET
    assert XRPLNetwork("mainnet") is XRPLNetwork.MAINNET
    assert XRPLNetwork("devnet") is XRPLNetwork.DEVNET


def test_xrpl_transport_testnet_url_matches_endpoint_table() -> None:
    """Constructing with TESTNET pins the documented testnet RPC URL."""
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(XRPLNetwork.TESTNET)
    assert t.url == "https://s.altnet.rippletest.net:51234/"
    assert t.network == XRPLNetwork.TESTNET


def test_xrpl_transport_mainnet_url_matches_endpoint_table() -> None:
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(XRPLNetwork.MAINNET)
    assert t.url == "https://s1.ripple.com:51234/"
    assert t.network == XRPLNetwork.MAINNET


def test_xrpl_transport_devnet_url_matches_endpoint_table() -> None:
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(XRPLNetwork.DEVNET)
    assert t.url == "https://s.devnet.rippletest.net:51234/"
    assert t.network == XRPLNetwork.DEVNET


def test_xrpl_transport_url_override_honored() -> None:
    """``url=`` override replaces the table URL but keeps the network's
    explorer prefix (so a proxy or local testbed against testnet still
    surfaces the right explorer link)."""
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    custom = "https://custom-mainnet.example/"
    t = XRPLTransport(XRPLNetwork.MAINNET, url=custom)
    assert t.url == custom
    # Explorer prefix still derived from the MAINNET table entry.
    assert t.explorer_tx_url("ABC").startswith("https://livenet.xrpl.org/")


def test_xrpl_transport_rejects_http_unless_insecure() -> None:
    """``allow_insecure=False`` (default) rejects http:// endpoints."""
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    with pytest.raises(ValueError, match="https://"):
        XRPLTransport(XRPLNetwork.TESTNET, url="http://insecure.example/")


def test_xrpl_transport_allow_insecure_permits_http() -> None:
    """``allow_insecure=True`` is the documented escape hatch for testbeds."""
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(
        XRPLNetwork.TESTNET,
        url="http://localhost:51234/",
        allow_insecure=True,
    )
    assert t.url == "http://localhost:51234/"


# ---------------------------------------------------------------------------
# explorer_tx_url
# ---------------------------------------------------------------------------


def test_explorer_tx_url_testnet_prefix() -> None:
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(XRPLNetwork.TESTNET)
    assert t.explorer_tx_url("DEADBEEF") == "https://testnet.xrpl.org/transactions/DEADBEEF"


def test_explorer_tx_url_mainnet_prefix() -> None:
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(XRPLNetwork.MAINNET)
    assert t.explorer_tx_url("DEADBEEF") == "https://livenet.xrpl.org/transactions/DEADBEEF"


def test_explorer_tx_url_devnet_prefix() -> None:
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport

    t = XRPLTransport(XRPLNetwork.DEVNET)
    assert t.explorer_tx_url("DEADBEEF") == "https://devnet.xrpl.org/transactions/DEADBEEF"


# ---------------------------------------------------------------------------
# Hex helpers
# ---------------------------------------------------------------------------


def test_memo_hex_encoding_round_trip() -> None:
    from sov_transport.xrpl import _from_hex, _to_hex

    text = "SOV|campfire_v1|s42|r1|sha256:abc123"
    encoded = _to_hex(text)
    decoded = _from_hex(encoded)
    assert decoded == text


def test_from_hex_returns_empty_on_malformed_hex() -> None:
    """Odd-length / non-hex inputs must not crash _from_hex (DoS guard)."""
    from sov_transport.xrpl import _from_hex

    assert _from_hex("abc") == ""
    assert _from_hex("zzzz") == ""
    assert _from_hex("") == ""


def test_from_hex_returns_empty_on_invalid_utf8() -> None:
    """Bytes that aren't valid UTF-8 must not crash _from_hex."""
    from sov_transport.xrpl import _from_hex

    # 0xff alone is never valid leading UTF-8.
    assert _from_hex("ff") == ""


# ---------------------------------------------------------------------------
# Mocked xrpl-py round-trip tests
# ---------------------------------------------------------------------------


def _install_fake_xrpl_modules() -> dict[str, types.ModuleType]:
    """Install lightweight fake ``xrpl.*`` submodules into ``sys.modules``.

    Returns a dict of ``{module_path: module}`` so the caller can mutate the
    placeholder classes/functions on the fakes (e.g. for patching).
    """
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

    # Wire submodule references onto the dynamically-built parents via
    # __dict__ so we don't trip mypy strict's attr-defined check.
    xrpl.__dict__["clients"] = clients
    xrpl.__dict__["models"] = models
    xrpl.__dict__["transaction"] = transaction
    xrpl.__dict__["wallet"] = wallet

    clients.__dict__["JsonRpcClient"] = MagicMock(name="JsonRpcClient")
    models.__dict__["Memo"] = MagicMock(name="Memo")
    # Wave 10 BRIDGE-A-bis-001: anchor swapped Payment → AccountSet (xrpl-py
    # 4.5.0 rejects self-payment). ``Payment`` is preserved on the fake module
    # for any caller that imports it directly; ``AccountSet`` is the live
    # construction site so the test fixture mocks it.
    models.__dict__["Payment"] = MagicMock(name="Payment")
    models.__dict__["AccountSet"] = MagicMock(name="AccountSet")
    models.__dict__["Tx"] = MagicMock(name="Tx")
    transaction.__dict__["submit_and_wait"] = MagicMock(name="submit_and_wait")
    wallet.__dict__["Wallet"] = MagicMock(name="Wallet")
    wallet.__dict__["generate_faucet_wallet"] = MagicMock(name="generate_faucet_wallet")

    return fakes


@pytest.fixture
def fake_xrpl(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    """Stub xrpl.* imports so the transport's deferred imports succeed."""
    fakes = _install_fake_xrpl_modules()
    for name, mod in fakes.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return fakes


def test_xrpl_anchor_happy_path_returns_stub_tx_hash(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``anchor`` builds a Payment and returns the response's tx hash."""
    from sov_transport.xrpl import XRPLTransport

    fake_wallet = MagicMock()
    fake_wallet.address = "rTestAddress"
    fake_wallet.classic_address = "rTestAddress"
    wallet_mod = fake_xrpl["xrpl.wallet"]
    wallet_mod.Wallet.from_seed.return_value = fake_wallet

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {"hash": "DEADBEEFCAFE"}
    transaction_mod = fake_xrpl["xrpl.transaction"]
    transaction_mod.submit_and_wait.return_value = fake_response

    t = XRPLTransport()
    tx_hash = t.anchor(
        "sha256:abc123",
        "SOV|campfire_v1|s42|r1|sha256:abc123",
        _TEST_SEED,
    )

    assert tx_hash == "DEADBEEFCAFE"
    wallet_mod.Wallet.from_seed.assert_called_once_with(_TEST_SEED)
    assert transaction_mod.submit_and_wait.called


def test_is_anchored_on_chain_true_when_memo_matches(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``is_anchored_on_chain`` decodes MemoData from hex and confirms hash."""
    from sov_transport.xrpl import ChainLookupResult, XRPLTransport, _to_hex

    expected_hash = "abc123"
    memo_text = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        "Memos": [{"Memo": {"MemoData": _to_hex(memo_text)}}],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    assert t.is_anchored_on_chain("TXID", expected_hash) is ChainLookupResult.FOUND


def test_is_anchored_on_chain_false_when_memo_missing(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """Returns NOT_FOUND when no memo encodes the expected hash."""
    from sov_transport.xrpl import ChainLookupResult, XRPLTransport, _to_hex

    memo_text = "SOV|campfire_v1|s42|r1|sha256:differenthash"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        "Memos": [{"Memo": {"MemoData": _to_hex(memo_text)}}],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    assert t.is_anchored_on_chain("TXID", "abc123") is ChainLookupResult.NOT_FOUND


def test_is_anchored_on_chain_does_not_crash_on_malformed_hex_memo(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """Regression for transport F-002: malformed memos must not propagate."""
    from sov_transport.xrpl import ChainLookupResult, XRPLTransport, _to_hex

    expected_hash = "abc123"
    good_memo = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        "Memos": [
            {"Memo": {"MemoData": "abc"}},  # odd-length hex
            {"Memo": {"MemoData": "ff"}},  # non-utf8
            {"Memo": {"MemoData": _to_hex(good_memo)}},
        ],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    assert t.is_anchored_on_chain("TXID", expected_hash) is ChainLookupResult.FOUND


def test_is_anchored_on_chain_rejects_empty_expected_hash(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``is_anchored_on_chain`` must reject empty expected_hash."""
    from sov_transport.xrpl import XRPLTransport

    t = XRPLTransport()
    with pytest.raises(ValueError):
        t.is_anchored_on_chain("TXID", "")


def test_is_anchored_on_chain_rejects_empty_txid(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """BRIDGE-004: empty txid is operator-actionable error before any I/O."""
    from sov_transport.xrpl import XRPLTransport

    t = XRPLTransport()
    with pytest.raises(ValueError, match="txid"):
        t.is_anchored_on_chain("", "abc123")


def test_anchor_rejects_oversized_memo(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``anchor`` raises ValueError when the memo exceeds 1024 UTF-8 bytes."""
    from sov_transport.xrpl import XRPLTransport

    big_memo = "A" * 1025  # 1025 ASCII chars == 1025 bytes
    t = XRPLTransport()
    with pytest.raises(ValueError, match="memo exceeds"):
        t.anchor("sha256:abc", big_memo, _TEST_SEED)


def test_anchor_does_not_leak_seed_in_exception_repr(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """Regression for transport F-001 (secret lifecycle).

    If Wallet.from_seed raises, the propagated exception's repr() must NOT
    contain the seed.
    """
    from sov_transport.xrpl import XRPLTransport

    def _raise_with_seed(seed: str) -> Any:
        raise ValueError(f"bad seed: {seed}")

    wallet_mod = fake_xrpl["xrpl.wallet"]
    wallet_mod.Wallet.from_seed.side_effect = _raise_with_seed

    t = XRPLTransport()
    with pytest.raises(Exception) as exc_info:
        t.anchor("sha256:abc", "SOV|memo", _TEST_SEED)

    rep = repr(exc_info.value)
    msg = str(exc_info.value)
    assert _TEST_SEED not in rep, f"seed leaked into exception repr: {rep!r}"
    assert _TEST_SEED not in msg, f"seed leaked into exception str: {msg!r}"
    # Cause chain must be suppressed (raise ... from None).
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_get_memo_text_returns_none_when_no_memos(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    from sov_transport.xrpl import XRPLTransport

    fake_response = MagicMock()
    fake_response.result = {}
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    assert t.get_memo_text("TXID") is None


def test_get_memo_text_decodes_first_good_memo(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    from sov_transport.xrpl import XRPLTransport, _to_hex

    text = "SOV|campfire_v1|s42|r1|sha256:abc"
    fake_response = MagicMock()
    fake_response.result = {
        "Memos": [
            {"Memo": {"MemoData": "abc"}},  # malformed, skipped
            {"Memo": {"MemoData": _to_hex(text)}},
        ],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    assert t.get_memo_text("TXID") == text


# ---------------------------------------------------------------------------
# _extract_memos response-shape coverage
# ---------------------------------------------------------------------------


def test_extract_memos_falls_back_to_nested_tx_memos_path(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``is_anchored_on_chain`` succeeds when memos live under ``result['tx']``."""
    from sov_transport.xrpl import ChainLookupResult, XRPLTransport, _to_hex

    expected_hash = "abc123"
    memo_text = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        "tx": {"Memos": [{"Memo": {"MemoData": _to_hex(memo_text)}}]},
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    assert t.is_anchored_on_chain("TXID", expected_hash) is ChainLookupResult.FOUND


def test_extract_memos_returns_false_on_unexpected_shape(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """Unexpected response shape degrades to NOT_FOUND, not a crash."""
    from sov_transport.xrpl import ChainLookupResult, XRPLTransport

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {"tx": "not a dict"}
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    assert t.is_anchored_on_chain("TXID", "abc123") is ChainLookupResult.NOT_FOUND


# ---------------------------------------------------------------------------
# verify() compat alias — emits DeprecationWarning, delegates to is_anchored
# ---------------------------------------------------------------------------


def test_verify_alias_emits_deprecation_warning(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``transport.verify(...)`` is a deprecated alias for ``is_anchored_on_chain``.

    Per spec §3, ``verify`` stays as a compat alias that emits
    ``DeprecationWarning`` and delegates to ``is_anchored_on_chain``. Removed
    in v2.2 with the rest of the legacy single-round surface. Post-BRIDGE-004
    the alias collapses the 3-state ``ChainLookupResult`` back to a plain
    ``bool`` (FOUND → True, NOT_FOUND / LOOKUP_FAILED → False) for ABI
    parity with v2.0.x.
    """
    from sov_transport.xrpl import XRPLTransport, _to_hex

    expected_hash = "abc123"
    memo_text = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        "Memos": [{"Memo": {"MemoData": _to_hex(memo_text)}}],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    clients_mod = fake_xrpl["xrpl.clients"]
    clients_mod.JsonRpcClient.return_value = fake_client

    t = XRPLTransport()
    with pytest.warns(DeprecationWarning):
        result = t.verify("TXID", expected_hash)
    assert result is True

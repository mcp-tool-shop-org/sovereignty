"""Tests for transport layer."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from sov_transport.null import NullTransport

# ---------------------------------------------------------------------------
# NullTransport
# ---------------------------------------------------------------------------


def test_null_transport_anchor():
    t = NullTransport()
    result = t.anchor("sha256:abc123", "memo", "signer")
    assert result.startswith("offline:")


def test_null_transport_verify():
    t = NullTransport()
    assert t.verify("offline:abc123", "anything") is True
    assert t.verify("xrpl:abc123", "anything") is False


# ---------------------------------------------------------------------------
# XRPL transport — import-guard branch
# ---------------------------------------------------------------------------


def test_xrpl_transport_imports_cleanly():
    """XRPLTestnetTransport should import even without xrpl-py installed."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    t = XRPLTestnetTransport()
    assert t.url == "https://s.altnet.rippletest.net:51234/"


def _xrpl_is_importable() -> bool:
    """Probe whether the xrpl package can be imported in this environment."""
    try:
        import xrpl  # noqa: F401
    except ImportError:
        return False
    return True


def test_xrpl_transport_anchor_requires_xrpl_py():
    """Anchor should raise RuntimeError when xrpl-py is not importable.

    The import-guard branch is unreachable when xrpl-py is installed, so we
    skip in that environment rather than swallowing exceptions with a bare
    ``except Exception: pass`` (the prior implementation always passed
    regardless of behavior).
    """
    if _xrpl_is_importable():
        pytest.skip("xrpl-py is installed; import-guard branch is unreachable")

    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    t = XRPLTestnetTransport()
    with pytest.raises(RuntimeError, match="xrpl-py is not installed"):
        t.anchor("hash", "memo", "signer")


# ---------------------------------------------------------------------------
# Hex encode/decode helpers
# ---------------------------------------------------------------------------


def test_memo_hex_encoding():
    from sov_transport.xrpl_testnet import _from_hex, _to_hex

    text = "SOV|campfire_v1|s42|r1|sha256:abc123"
    encoded = _to_hex(text)
    decoded = _from_hex(encoded)
    assert decoded == text


def test_from_hex_returns_empty_on_malformed_hex():
    """Odd-length / non-hex inputs must not crash _from_hex (DoS guard)."""
    from sov_transport.xrpl_testnet import _from_hex

    # Odd length
    assert _from_hex("abc") == ""
    # Non-hex characters
    assert _from_hex("zzzz") == ""
    # Empty
    assert _from_hex("") == ""


def test_from_hex_returns_empty_on_invalid_utf8():
    """Bytes that aren't valid UTF-8 must not crash _from_hex."""
    from sov_transport.xrpl_testnet import _from_hex

    # 0xff alone is never valid leading UTF-8.
    assert _from_hex("ff") == ""


# ---------------------------------------------------------------------------
# Mocked xrpl-py round-trip tests
# ---------------------------------------------------------------------------


# A recognizable seed string we can grep for in scrubbed exception reprs.
_TEST_SEED = "sEdXXXXXXXXXXXXXXXXXXXXXXX"


def _install_fake_xrpl_modules() -> dict:
    """Install lightweight fake ``xrpl.*`` submodules into ``sys.modules`` so
    that `from xrpl.x import Y` inside the transport works during the test.

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

    xrpl.clients = clients
    xrpl.models = models
    xrpl.transaction = transaction
    xrpl.wallet = wallet

    clients.JsonRpcClient = MagicMock(name="JsonRpcClient")
    models.Memo = MagicMock(name="Memo")
    models.Payment = MagicMock(name="Payment")
    models.Tx = MagicMock(name="Tx")
    transaction.submit_and_wait = MagicMock(name="submit_and_wait")
    wallet.Wallet = MagicMock(name="Wallet")
    wallet.generate_faucet_wallet = MagicMock(name="generate_faucet_wallet")

    return fakes


@pytest.fixture
def fake_xrpl(monkeypatch):
    """Stub xrpl.* imports so the transport's deferred imports succeed."""
    fakes = _install_fake_xrpl_modules()
    for name, mod in fakes.items():
        monkeypatch.setitem(sys.modules, name, mod)
    yield fakes
    # monkeypatch.setitem cleans up automatically.


def test_xrpl_anchor_happy_path_returns_stub_tx_hash(fake_xrpl):
    """anchor() builds a Payment and returns the response's tx hash."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    fake_wallet = MagicMock()
    fake_wallet.address = "rTestAddress"
    fake_xrpl["xrpl.wallet"].Wallet.from_seed.return_value = fake_wallet

    fake_response = MagicMock()
    fake_response.result = {"hash": "DEADBEEFCAFE"}
    fake_xrpl["xrpl.transaction"].submit_and_wait.return_value = fake_response

    t = XRPLTestnetTransport()
    tx_hash = t.anchor(
        "sha256:abc123",
        "SOV|campfire_v1|s42|r1|sha256:abc123",
        _TEST_SEED,
    )

    assert tx_hash == "DEADBEEFCAFE"
    # Wallet was created from the seed
    fake_xrpl["xrpl.wallet"].Wallet.from_seed.assert_called_once_with(_TEST_SEED)
    # submit_and_wait was called
    assert fake_xrpl["xrpl.transaction"].submit_and_wait.called


def test_xrpl_verify_returns_true_when_memo_contains_expected_hash(fake_xrpl):
    """verify() decodes MemoData from hex and confirms the expected hash."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport, _to_hex

    expected_hash = "abc123"
    memo_text = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.result = {
        "Memos": [
            {"Memo": {"MemoData": _to_hex(memo_text)}},
        ],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = fake_client

    t = XRPLTestnetTransport()
    assert t.verify("TXID", expected_hash) is True


def test_xrpl_verify_returns_false_when_memo_missing(fake_xrpl):
    """verify() returns False when no memo encodes the expected hash."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport, _to_hex

    memo_text = "SOV|campfire_v1|s42|r1|sha256:differenthash"

    fake_response = MagicMock()
    fake_response.result = {
        "Memos": [
            {"Memo": {"MemoData": _to_hex(memo_text)}},
        ],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = fake_client

    t = XRPLTestnetTransport()
    assert t.verify("TXID", "abc123") is False


def test_xrpl_verify_does_not_crash_on_malformed_hex_memo(fake_xrpl):
    """Regression for transport F-002: a malformed memo on a fetched tx must
    not propagate an exception out of verify() (DoS guard)."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport, _to_hex

    expected_hash = "abc123"
    good_memo = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.result = {
        "Memos": [
            # Bad memo: odd-length hex, would crash bytes.fromhex() if not guarded.
            {"Memo": {"MemoData": "abc"}},
            # Bad memo: invalid UTF-8 bytes once decoded from hex.
            {"Memo": {"MemoData": "ff"}},
            # Good memo: this should match.
            {"Memo": {"MemoData": _to_hex(good_memo)}},
        ],
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = fake_client

    t = XRPLTestnetTransport()
    # Must NOT raise; must return True after skipping the bad memos.
    assert t.verify("TXID", expected_hash) is True


def test_xrpl_verify_rejects_empty_expected_hash(fake_xrpl):
    """verify() must reject empty expected_hash to avoid trivial-True bugs."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    t = XRPLTestnetTransport()
    with pytest.raises(ValueError):
        t.verify("TXID", "")


def test_xrpl_anchor_rejects_oversized_memo(fake_xrpl):
    """anchor() must raise ValueError when the memo exceeds 1024 UTF-8 bytes."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    big_memo = "A" * 1025  # 1025 ASCII chars == 1025 bytes
    t = XRPLTestnetTransport()
    with pytest.raises(ValueError, match="memo exceeds"):
        t.anchor("sha256:abc", big_memo, _TEST_SEED)


def test_xrpl_anchor_does_not_leak_seed_in_exception_repr(fake_xrpl):
    """Regression for transport F-001 (secret lifecycle).

    If Wallet.from_seed raises, the propagated exception's repr() must NOT
    contain the seed. The transport uses ``raise type(e)(...) from None`` to
    suppress the cause chain so locals (including ``signer``) do not bleed
    into observability layers.
    """
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    # Force Wallet.from_seed to raise an exception that, naively, would
    # include the seed in its message — simulating xrpl's historical behavior.
    def _raise_with_seed(seed):
        raise ValueError(f"bad seed: {seed}")

    fake_xrpl["xrpl.wallet"].Wallet.from_seed.side_effect = _raise_with_seed

    t = XRPLTestnetTransport()
    with pytest.raises(Exception) as exc_info:
        t.anchor("sha256:abc", "SOV|memo", _TEST_SEED)

    # The propagated exception's repr (and str) MUST NOT contain the seed.
    rep = repr(exc_info.value)
    msg = str(exc_info.value)
    assert _TEST_SEED not in rep, f"seed leaked into exception repr: {rep!r}"
    assert _TEST_SEED not in msg, f"seed leaked into exception str: {msg!r}"

    # Cause chain must be suppressed (raise ... from None).
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_xrpl_get_memo_text_returns_none_when_no_memos(fake_xrpl):
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    fake_response = MagicMock()
    fake_response.result = {}  # no Memos at all
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = fake_client

    t = XRPLTestnetTransport()
    assert t.get_memo_text("TXID") is None


def test_xrpl_get_memo_text_decodes_first_good_memo(fake_xrpl):
    from sov_transport.xrpl_testnet import XRPLTestnetTransport, _to_hex

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
    fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = fake_client

    t = XRPLTestnetTransport()
    assert t.get_memo_text("TXID") == text


# ---------------------------------------------------------------------------
# fund_testnet_wallet import-guard branch
# ---------------------------------------------------------------------------


def test_fund_testnet_wallet_requires_xrpl_py():
    """fund_testnet_wallet should raise RuntimeError if xrpl-py is missing."""
    if _xrpl_is_importable():
        pytest.skip("xrpl-py is installed; import-guard branch is unreachable")

    from sov_transport.xrpl_testnet import fund_testnet_wallet

    with pytest.raises(RuntimeError, match="xrpl-py is not installed"):
        fund_testnet_wallet()


# ---------------------------------------------------------------------------
# _extract_memos response-shape coverage (Wave 4 F-003 amend)
# ---------------------------------------------------------------------------


def test_extract_memos_falls_back_to_nested_tx_memos_path(fake_xrpl):
    """``verify`` must succeed when memos live nested under ``result['tx']``.

    The xrpl-py response shape varies across versions: memos may live at the
    top level of ``result`` OR nested under ``result['tx']``. This fixture
    sets ONLY the nested path (no top-level ``Memos`` key) and asserts
    ``verify()`` still returns True. Currently the fallback branch in
    ``_extract_memos`` (``xrpl_testnet.py:45-47``) has zero coverage; if a
    refactor breaks the fallback, this test will fail loud.
    """
    from sov_transport.xrpl_testnet import XRPLTestnetTransport, _to_hex

    expected_hash = "abc123"
    memo_text = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    # Note: NO top-level "Memos" key. Memos live under result['tx']['Memos'].
    fake_response.result = {
        "tx": {
            "Memos": [
                {"Memo": {"MemoData": _to_hex(memo_text)}},
            ],
        },
    }
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = fake_client

    t = XRPLTestnetTransport()
    assert t.verify("TXID", expected_hash) is True


def test_extract_memos_returns_empty_list_on_unexpected_shape(fake_xrpl):
    """An unexpected response shape (no memos in ANY known location) must
    degrade gracefully -- verify() returns False, does not crash.

    Defends against silent regressions where xrpl-py changes its response
    shape again and ``_extract_memos`` would otherwise raise (e.g. KeyError
    or AttributeError).
    """
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    fake_response = MagicMock()
    # Neither top-level Memos NOR result['tx']['Memos']. result['tx'] is
    # also intentionally not a dict to exercise the isinstance(tx, dict)
    # guard at xrpl_testnet.py:46.
    fake_response.result = {"tx": "not a dict"}
    fake_client = MagicMock()
    fake_client.request.return_value = fake_response
    fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = fake_client

    t = XRPLTestnetTransport()
    # Must NOT raise; must return False (no memos => no match).
    assert t.verify("TXID", "abc123") is False

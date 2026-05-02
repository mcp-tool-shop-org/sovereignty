"""Tests for ``sov_transport.xrpl_internals`` — pure shared helpers.

The internals module is the single source of truth for the deterministic,
I/O-free XRPL transport bits that both ``XRPLTransport`` (sync) and
``AsyncXRPLTransport`` (async) consume. The tests below exercise the
helpers in isolation so any drift in network table values, hex codecs,
memo extraction, or error classification surfaces as a unit failure
before the transport-level tests have a chance to mask it.

Pinned behaviors:

* ``XRPLNetwork`` enum values (``"testnet"``, ``"mainnet"``, ``"devnet"``).
* ``_NETWORK_TABLE`` URL + explorer prefix per network.
* ``_to_hex`` / ``_from_hex`` lossless round-trip on arbitrary unicode.
* ``_from_hex`` returns empty string on malformed hex / invalid UTF-8.
* ``_extract_memos`` handles top-level, nested-dict, nested-list-of-dict,
  and unexpected response shapes.
* ``_classify_submit_error`` returns stable tokens by exception class /
  message contents.
* ``MainnetFaucetError`` is raisable + carries an operator-actionable
  message format.
* ``_MAX_MEMO_BYTES`` constant pinned at 1024 (XRPL per-memo cap).
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# XRPLNetwork enum + constants
# ---------------------------------------------------------------------------


def test_xrpl_network_enum_string_values() -> None:
    """``XRPLNetwork`` is a StrEnum with the three canonical values."""
    from sov_transport.xrpl_internals import XRPLNetwork

    assert XRPLNetwork.TESTNET.value == "testnet"
    assert XRPLNetwork.MAINNET.value == "mainnet"
    assert XRPLNetwork.DEVNET.value == "devnet"


def test_xrpl_network_enum_round_trip_via_constructor() -> None:
    """StrEnum members round-trip through their string value."""
    from sov_transport.xrpl_internals import XRPLNetwork

    assert XRPLNetwork("testnet") is XRPLNetwork.TESTNET
    assert XRPLNetwork("mainnet") is XRPLNetwork.MAINNET
    assert XRPLNetwork("devnet") is XRPLNetwork.DEVNET


def test_max_memo_bytes_constant_is_one_kib() -> None:
    """Spec §1: per-memo cap is 1024 bytes. Pinned to catch silent drift."""
    from sov_transport.xrpl_internals import _MAX_MEMO_BYTES

    assert _MAX_MEMO_BYTES == 1024


def test_submit_retry_constants_present() -> None:
    """Retry policy constants are shared across sync + async impls."""
    from sov_transport.xrpl_internals import (
        _SUBMIT_BACKOFF_SECONDS,
        _SUBMIT_DEADLINE_SECONDS,
        _SUBMIT_MAX_ATTEMPTS,
    )

    assert _SUBMIT_MAX_ATTEMPTS == 3
    assert _SUBMIT_BACKOFF_SECONDS == (1.0, 2.0, 4.0)
    assert _SUBMIT_DEADLINE_SECONDS == 30.0


# ---------------------------------------------------------------------------
# _NETWORK_TABLE
# ---------------------------------------------------------------------------


def test_network_table_testnet_entry_matches_spec() -> None:
    """Testnet RPC + explorer prefix pinned per spec."""
    from sov_transport.xrpl_internals import _NETWORK_TABLE, XRPLNetwork

    rpc_url, explorer_prefix = _NETWORK_TABLE[XRPLNetwork.TESTNET]
    assert rpc_url == "https://s.altnet.rippletest.net:51234/"
    assert explorer_prefix == "https://testnet.xrpl.org/transactions/"


def test_network_table_mainnet_entry_matches_spec() -> None:
    from sov_transport.xrpl_internals import _NETWORK_TABLE, XRPLNetwork

    rpc_url, explorer_prefix = _NETWORK_TABLE[XRPLNetwork.MAINNET]
    assert rpc_url == "https://s1.ripple.com:51234/"
    assert explorer_prefix == "https://livenet.xrpl.org/transactions/"


def test_network_table_devnet_entry_matches_spec() -> None:
    from sov_transport.xrpl_internals import _NETWORK_TABLE, XRPLNetwork

    rpc_url, explorer_prefix = _NETWORK_TABLE[XRPLNetwork.DEVNET]
    assert rpc_url == "https://s.devnet.rippletest.net:51234/"
    assert explorer_prefix == "https://devnet.xrpl.org/transactions/"


def test_network_table_covers_all_enum_members() -> None:
    """No XRPLNetwork value is missing from the lookup table."""
    from sov_transport.xrpl_internals import _NETWORK_TABLE, XRPLNetwork

    for net in XRPLNetwork:
        assert net in _NETWORK_TABLE, f"network {net!r} missing from _NETWORK_TABLE"


# ---------------------------------------------------------------------------
# _to_hex / _from_hex round-trip
# ---------------------------------------------------------------------------


def test_to_hex_from_hex_round_trip_ascii() -> None:
    from sov_transport.xrpl_internals import _from_hex, _to_hex

    text = "SOV|campfire_v1|s42|r1|sha256:abc123"
    assert _from_hex(_to_hex(text)) == text


def test_to_hex_from_hex_round_trip_unicode_emoji() -> None:
    """Round-trip survives multi-byte unicode (emoji + CJK + RTL)."""
    from sov_transport.xrpl_internals import _from_hex, _to_hex

    text = "anchor 🪨 主权 العربية"
    assert _from_hex(_to_hex(text)) == text


def test_to_hex_from_hex_round_trip_empty_string() -> None:
    from sov_transport.xrpl_internals import _from_hex, _to_hex

    assert _to_hex("") == ""
    assert _from_hex("") == ""


def test_from_hex_returns_empty_on_odd_length_hex() -> None:
    """``_from_hex`` is intentionally lenient — adversarial inputs return ''."""
    from sov_transport.xrpl_internals import _from_hex

    assert _from_hex("abc") == ""


def test_from_hex_returns_empty_on_non_hex_chars() -> None:
    from sov_transport.xrpl_internals import _from_hex

    assert _from_hex("zzzz") == ""


def test_from_hex_returns_empty_on_invalid_utf8() -> None:
    """Bytes that decode out of hex but aren't UTF-8 must return ''."""
    from sov_transport.xrpl_internals import _from_hex

    # 0xff alone is never valid leading UTF-8.
    assert _from_hex("ff") == ""


# ---------------------------------------------------------------------------
# _extract_memos response-shape coverage
# ---------------------------------------------------------------------------


def test_extract_memos_top_level_shape() -> None:
    """Top-level ``Memos`` key is the v2.0.2 shape and must work."""
    from sov_transport.xrpl_internals import _extract_memos

    memos = [{"Memo": {"MemoData": "deadbeef"}}]
    result = {"Memos": memos}
    assert _extract_memos(result) == memos


def test_extract_memos_nested_under_tx_dict() -> None:
    """``result['tx']`` may be a dict carrying ``Memos`` (xrpl-py 2.x)."""
    from sov_transport.xrpl_internals import _extract_memos

    memos = [{"Memo": {"MemoData": "deadbeef"}}]
    result = {"tx": {"Memos": memos}}
    assert _extract_memos(result) == memos


def test_extract_memos_nested_under_tx_list_first_element() -> None:
    """``result['tx']`` may be a list whose first dict carries ``Memos``."""
    from sov_transport.xrpl_internals import _extract_memos

    memos = [{"Memo": {"MemoData": "deadbeef"}}]
    result = {"tx": [{"Memos": memos}]}
    assert _extract_memos(result) == memos


def test_extract_memos_returns_empty_on_unexpected_shape() -> None:
    """Unexpected shapes (string under ``tx``) degrade to empty list."""
    from sov_transport.xrpl_internals import _extract_memos

    assert _extract_memos({"tx": "not a dict or list"}) == []


def test_extract_memos_returns_empty_when_result_not_dict() -> None:
    """Non-dict input degrades to empty list (logs WARNING but doesn't crash)."""
    from sov_transport.xrpl_internals import _extract_memos

    # type: ignore[arg-type]
    assert _extract_memos("garbage") == []  # type: ignore[arg-type]


def test_extract_memos_returns_empty_when_no_memos_anywhere() -> None:
    from sov_transport.xrpl_internals import _extract_memos

    assert _extract_memos({}) == []


def test_extract_memos_tx_list_with_non_dict_first_element() -> None:
    """``result['tx']`` is a list whose first element isn't a dict → []."""
    from sov_transport.xrpl_internals import _extract_memos

    assert _extract_memos({"tx": ["not-a-dict"]}) == []


# ---------------------------------------------------------------------------
# _classify_submit_error stable token map
# ---------------------------------------------------------------------------


def test_classify_submit_error_ledger_not_found_via_class_name() -> None:
    from sov_transport.xrpl_internals import _classify_submit_error

    class LedgerNotFoundError(Exception):
        pass

    assert _classify_submit_error(LedgerNotFoundError("not found")) == "ledger_not_found"


def test_classify_submit_error_ledger_not_found_via_message() -> None:
    from sov_transport.xrpl_internals import _classify_submit_error

    assert _classify_submit_error(RuntimeError("ledger_not_found in ledger")) == "ledger_not_found"


def test_classify_submit_error_signing_failed_via_class_name() -> None:
    from sov_transport.xrpl_internals import _classify_submit_error

    class WalletSigningError(Exception):
        pass

    assert _classify_submit_error(WalletSigningError("bad seed")) == "signing_failed"


def test_classify_submit_error_timeout_via_message() -> None:
    from sov_transport.xrpl_internals import _classify_submit_error

    assert _classify_submit_error(RuntimeError("operation timed out")) == "timeout"


def test_classify_submit_error_timeout_via_class_name() -> None:
    from sov_transport.xrpl_internals import _classify_submit_error

    assert _classify_submit_error(TimeoutError("late")) == "timeout"


def test_classify_submit_error_network_via_message() -> None:
    from sov_transport.xrpl_internals import _classify_submit_error

    assert _classify_submit_error(RuntimeError("connection refused")) == "network"


def test_classify_submit_error_network_via_class_name() -> None:
    from sov_transport.xrpl_internals import _classify_submit_error

    class ConnectionDropped(Exception):
        pass

    assert _classify_submit_error(ConnectionDropped("oops")) == "network"


def test_classify_submit_error_unknown_fallback() -> None:
    """Unrelated exceptions fall back to the ``unknown`` token."""
    from sov_transport.xrpl_internals import _classify_submit_error

    assert _classify_submit_error(ValueError("totally unrelated")) == "unknown"


# ---------------------------------------------------------------------------
# MainnetFaucetError
# ---------------------------------------------------------------------------


def test_mainnet_faucet_error_is_runtime_error() -> None:
    """``MainnetFaucetError`` is a ``RuntimeError`` subclass for compat."""
    from sov_transport.xrpl_internals import MainnetFaucetError

    assert issubclass(MainnetFaucetError, RuntimeError)


def test_mainnet_faucet_error_carries_message() -> None:
    """Message is operator-facing — must round-trip through ``str()``."""
    from sov_transport.xrpl_internals import MainnetFaucetError

    msg = "mainnet has no faucet — set XRPL_SEED to a funded mainnet wallet"
    with pytest.raises(MainnetFaucetError, match="mainnet has no faucet"):
        raise MainnetFaucetError(msg)


# ---------------------------------------------------------------------------
# _format_memo SOV grammar wire format
# ---------------------------------------------------------------------------


def test_format_memo_numeric_round_renders_with_r_prefix() -> None:
    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_internals import _format_memo

    entry: BatchEntry = {
        "round_key": "3",
        "ruleset": "campfire_v1",
        "game_id": "s42",
        "envelope_hash": "abc123",
    }
    assert _format_memo(entry) == "SOV|campfire_v1|s42|r3|sha256:abc123"


def test_format_memo_final_round_renders_literal_no_r_prefix() -> None:
    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_internals import _format_memo

    entry: BatchEntry = {
        "round_key": "FINAL",
        "ruleset": "campfire_v1",
        "game_id": "s42",
        "envelope_hash": "abc123",
    }
    assert _format_memo(entry) == "SOV|campfire_v1|s42|FINAL|sha256:abc123"


# ---------------------------------------------------------------------------
# Re-export back-compat — xrpl.py must keep XRPLNetwork, MainnetFaucetError,
# _NETWORK_TABLE, _MAX_MEMO_BYTES, _to_hex, _from_hex, _classify_submit_error,
# _extract_memos, _format_memo importable for any external consumer that
# pinned to the old import path. Coordinator brief item #2.
# ---------------------------------------------------------------------------


def test_re_exports_remain_importable_from_xrpl_module() -> None:
    """``from sov_transport.xrpl import XRPLNetwork`` etc. must keep working
    post-internals-extraction. Pinned for back-compat with any external
    consumer (Wave 4 Tauri shell, audit viewer) that imported the old path."""
    from sov_transport.xrpl import (  # noqa: F401
        _MAX_MEMO_BYTES,
        _NETWORK_TABLE,
        MainnetFaucetError,
        XRPLNetwork,
        _classify_submit_error,
        _extract_memos,
        _from_hex,
        _to_hex,
    )

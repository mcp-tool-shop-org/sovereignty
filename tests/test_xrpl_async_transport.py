"""Tests for ``sov_transport.xrpl_async.AsyncXRPLTransport``.

Mirrors ``tests/test_xrpl_transport.py`` for the async sibling. Runs under
``asyncio_mode = "auto"`` (set in ``pyproject.toml``) — async test functions
are picked up without per-test markers.

Pinned behaviors (parallel to the sync transport):

* Per-network endpoint table (TESTNET / MAINNET / DEVNET) selects the right
  RPC URL and explorer prefix.
* ``url=`` override and ``allow_insecure`` flag.
* ``transport.explorer_tx_url(txid)`` returns the right per-network prefix
  (sync — no I/O).
* ``anchor_batch`` builds a Payment carrying N memos and returns the
  response's tx hash.
* ``anchor_batch`` rejects empty rounds list and per-memo size > 1024 B.
* Secret scrub on exception during async submit — seed must not appear in
  the propagated exception's repr or str.
* ``is_anchored_on_chain`` decodes structured SOV grammar and returns False
  on no match.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# A recognizable seed string we can grep for in scrubbed exception reprs.
_TEST_SEED = "sEdAsyncSEEDXXXXXXXXXXXXXXX"


# ---------------------------------------------------------------------------
# Fake xrpl modules — covers sync + async submodules
# ---------------------------------------------------------------------------


def _install_fake_xrpl_async_modules() -> dict[str, types.ModuleType]:
    """Install fake ``xrpl.*`` and ``xrpl.asyncio.*`` submodules.

    ``AsyncXRPLTransport`` defers its imports to the call site for the same
    reason ``XRPLTransport`` does: keep the import surface lazy so the
    module imports cleanly without ``xrpl-py`` installed. The fakes below
    let the deferred import succeed and let tests stub return values.
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
    asyncio_pkg = _make("xrpl.asyncio")
    asyncio_clients = _make("xrpl.asyncio.clients")
    asyncio_transaction = _make("xrpl.asyncio.transaction")

    xrpl.__dict__["clients"] = clients
    xrpl.__dict__["models"] = models
    xrpl.__dict__["transaction"] = transaction
    xrpl.__dict__["wallet"] = wallet
    xrpl.__dict__["asyncio"] = asyncio_pkg
    asyncio_pkg.__dict__["clients"] = asyncio_clients
    asyncio_pkg.__dict__["transaction"] = asyncio_transaction

    clients.__dict__["JsonRpcClient"] = MagicMock(name="JsonRpcClient")
    models.__dict__["Memo"] = MagicMock(name="Memo")
    # Wave 10 BRIDGE-A-bis-001 mirror (see test_xrpl_transport.py): async
    # anchor swapped Payment → AccountSet alongside the sync impl.
    models.__dict__["Payment"] = MagicMock(name="Payment")
    models.__dict__["AccountSet"] = MagicMock(name="AccountSet")
    models.__dict__["Tx"] = MagicMock(name="Tx")
    transaction.__dict__["submit_and_wait"] = MagicMock(name="submit_and_wait")
    wallet.__dict__["Wallet"] = MagicMock(name="Wallet")
    wallet.__dict__["generate_faucet_wallet"] = MagicMock(name="generate_faucet_wallet")

    asyncio_clients.__dict__["AsyncJsonRpcClient"] = MagicMock(name="AsyncJsonRpcClient")
    asyncio_transaction.__dict__["submit_and_wait"] = AsyncMock(name="async_submit_and_wait")

    return fakes


@pytest.fixture
def fake_xrpl_async(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    """Stub ``xrpl.*`` + ``xrpl.asyncio.*`` so deferred imports succeed."""
    fakes = _install_fake_xrpl_async_modules()
    for name, mod in fakes.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return fakes


# ---------------------------------------------------------------------------
# Import shape
# ---------------------------------------------------------------------------


def test_async_xrpl_transport_imports_cleanly() -> None:
    """``AsyncXRPLTransport`` should import even without xrpl-py installed."""
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(XRPLNetwork.TESTNET)
    assert t.url == "https://s.altnet.rippletest.net:51234/"


def test_async_xrpl_transport_re_exported_from_package() -> None:
    """``AsyncXRPLTransport`` is re-exported on ``sov_transport``."""
    from sov_transport import AsyncXRPLTransport
    from sov_transport.xrpl_async import AsyncXRPLTransport as Direct

    assert AsyncXRPLTransport is Direct


# ---------------------------------------------------------------------------
# Network parameterization (sync tests' counterpart)
# ---------------------------------------------------------------------------


def test_async_transport_testnet_url_matches_endpoint_table() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(XRPLNetwork.TESTNET)
    assert t.url == "https://s.altnet.rippletest.net:51234/"
    assert t.network == XRPLNetwork.TESTNET


def test_async_transport_mainnet_url_matches_endpoint_table() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(XRPLNetwork.MAINNET)
    assert t.url == "https://s1.ripple.com:51234/"
    assert t.network == XRPLNetwork.MAINNET


def test_async_transport_devnet_url_matches_endpoint_table() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(XRPLNetwork.DEVNET)
    assert t.url == "https://s.devnet.rippletest.net:51234/"


def test_async_transport_url_override_honored() -> None:
    """``url=`` override replaces the table URL but keeps the explorer prefix."""
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    custom = "https://custom-mainnet.example/"
    t = AsyncXRPLTransport(XRPLNetwork.MAINNET, url=custom)
    assert t.url == custom
    assert t.explorer_tx_url("ABC").startswith("https://livenet.xrpl.org/")


def test_async_transport_rejects_http_unless_insecure() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    with pytest.raises(ValueError, match="https://"):
        AsyncXRPLTransport(XRPLNetwork.TESTNET, url="http://insecure.example/")


def test_async_transport_allow_insecure_permits_http() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(
        XRPLNetwork.TESTNET,
        url="http://localhost:51234/",
        allow_insecure=True,
    )
    assert t.url == "http://localhost:51234/"


# ---------------------------------------------------------------------------
# explorer_tx_url (sync, no I/O)
# ---------------------------------------------------------------------------


def test_async_explorer_tx_url_testnet_prefix() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(XRPLNetwork.TESTNET)
    assert t.explorer_tx_url("DEADBEEF") == "https://testnet.xrpl.org/transactions/DEADBEEF"


def test_async_explorer_tx_url_mainnet_prefix() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(XRPLNetwork.MAINNET)
    assert t.explorer_tx_url("DEADBEEF") == "https://livenet.xrpl.org/transactions/DEADBEEF"


def test_async_explorer_tx_url_devnet_prefix() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    t = AsyncXRPLTransport(XRPLNetwork.DEVNET)
    assert t.explorer_tx_url("DEADBEEF") == "https://devnet.xrpl.org/transactions/DEADBEEF"


# ---------------------------------------------------------------------------
# is_anchored_on_chain — async, mocked AsyncJsonRpcClient
# ---------------------------------------------------------------------------


async def test_async_is_anchored_on_chain_true_when_memo_matches(
    fake_xrpl_async: dict[str, types.ModuleType],
) -> None:
    """``is_anchored_on_chain`` decodes MemoData from hex and confirms hash."""
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import ChainLookupResult, _to_hex

    expected_hash = "abc123"
    memo_text = f"SOV|campfire_v1|s42|r1|sha256:{expected_hash}"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        "Memos": [{"Memo": {"MemoData": _to_hex(memo_text)}}],
    }
    fake_client = MagicMock()
    fake_client.request = AsyncMock(return_value=fake_response)
    asyncio_clients = fake_xrpl_async["xrpl.asyncio.clients"]
    asyncio_clients.AsyncJsonRpcClient.return_value = fake_client

    t = AsyncXRPLTransport()
    assert await t.is_anchored_on_chain("TXID", expected_hash) is ChainLookupResult.FOUND


async def test_async_is_anchored_on_chain_false_when_memo_missing(
    fake_xrpl_async: dict[str, types.ModuleType],
) -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import ChainLookupResult, _to_hex

    memo_text = "SOV|campfire_v1|s42|r1|sha256:differenthash"

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {
        "Memos": [{"Memo": {"MemoData": _to_hex(memo_text)}}],
    }
    fake_client = MagicMock()
    fake_client.request = AsyncMock(return_value=fake_response)
    asyncio_clients = fake_xrpl_async["xrpl.asyncio.clients"]
    asyncio_clients.AsyncJsonRpcClient.return_value = fake_client

    t = AsyncXRPLTransport()
    assert await t.is_anchored_on_chain("TXID", "abc123") is ChainLookupResult.NOT_FOUND


async def test_async_is_anchored_on_chain_rejects_empty_expected_hash() -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport

    t = AsyncXRPLTransport()
    with pytest.raises(ValueError):
        await t.is_anchored_on_chain("TXID", "")


async def test_async_is_anchored_on_chain_rejects_empty_txid() -> None:
    """BRIDGE-004 (async): empty txid is operator-actionable error."""
    from sov_transport.xrpl_async import AsyncXRPLTransport

    t = AsyncXRPLTransport()
    with pytest.raises(ValueError, match="txid"):
        await t.is_anchored_on_chain("", "abc123")


# ---------------------------------------------------------------------------
# anchor_batch — async, mocked async submit_and_wait
# ---------------------------------------------------------------------------


async def test_async_anchor_batch_happy_path_returns_tx_hash(
    fake_xrpl_async: dict[str, types.ModuleType],
) -> None:
    """``anchor_batch`` builds a Payment with N memos and returns the tx hash."""
    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_async import AsyncXRPLTransport

    fake_wallet = MagicMock()
    fake_wallet.address = "rTestAddress"
    fake_wallet.classic_address = "rTestAddress"
    wallet_mod = fake_xrpl_async["xrpl.wallet"]
    wallet_mod.Wallet.from_seed.return_value = fake_wallet

    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {"hash": "ASYNCDEADBEEF"}
    asyncio_transaction = fake_xrpl_async["xrpl.asyncio.transaction"]
    asyncio_transaction.submit_and_wait = AsyncMock(return_value=fake_response)

    rounds: list[BatchEntry] = [
        {
            "round_key": "1",
            "ruleset": "campfire_v1",
            "game_id": "s42",
            "envelope_hash": "h1",
        },
        {
            "round_key": "FINAL",
            "ruleset": "campfire_v1",
            "game_id": "s42",
            "envelope_hash": "hF",
        },
    ]

    t = AsyncXRPLTransport()
    tx_hash = await t.anchor_batch(rounds, _TEST_SEED)
    assert tx_hash == "ASYNCDEADBEEF"
    wallet_mod.Wallet.from_seed.assert_called_once_with(_TEST_SEED)


async def test_async_anchor_batch_rejects_empty_rounds() -> None:
    """Empty rounds list raises ValueError before any I/O."""
    from sov_transport.xrpl_async import AsyncXRPLTransport

    t = AsyncXRPLTransport()
    with pytest.raises(ValueError, match="at least one round entry"):
        await t.anchor_batch([], _TEST_SEED)


async def test_async_anchor_batch_rejects_oversized_memo(
    fake_xrpl_async: dict[str, types.ModuleType],
) -> None:
    """Per-memo size cap enforced by async impl too."""
    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_async import AsyncXRPLTransport

    rounds: list[BatchEntry] = [
        {
            "round_key": "1",
            "ruleset": "campfire_v1",
            "game_id": "s42",
            # 1100-char hash will overflow the 1024-byte memo cap.
            "envelope_hash": "f" * 1100,
        }
    ]

    t = AsyncXRPLTransport()
    with pytest.raises(ValueError, match="exceeds"):
        await t.anchor_batch(rounds, _TEST_SEED)


async def test_async_anchor_batch_does_not_leak_seed_in_exception(
    fake_xrpl_async: dict[str, types.ModuleType],
) -> None:
    """Async secret-scrub regression: exception during submit must not leak seed."""
    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_async import AsyncXRPLTransport

    def _raise_with_seed(seed: str) -> Any:
        raise ValueError(f"bad seed: {seed}")

    wallet_mod = fake_xrpl_async["xrpl.wallet"]
    wallet_mod.Wallet.from_seed.side_effect = _raise_with_seed

    rounds: list[BatchEntry] = [
        {
            "round_key": "1",
            "ruleset": "campfire_v1",
            "game_id": "s42",
            "envelope_hash": "abc",
        }
    ]

    t = AsyncXRPLTransport()
    with pytest.raises(Exception) as exc_info:
        await t.anchor_batch(rounds, _TEST_SEED)

    rep = repr(exc_info.value)
    msg = str(exc_info.value)
    assert _TEST_SEED not in rep, f"seed leaked into exception repr: {rep!r}"
    assert _TEST_SEED not in msg, f"seed leaked into exception str: {msg!r}"
    # Cause chain suppressed so traceback locals don't propagate.
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


# ---------------------------------------------------------------------------
# get_memo_text — async
# ---------------------------------------------------------------------------


async def test_async_get_memo_text_returns_none_when_no_memos(
    fake_xrpl_async: dict[str, types.ModuleType],
) -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport

    fake_response = MagicMock()
    fake_response.result = {}
    fake_client = MagicMock()
    fake_client.request = AsyncMock(return_value=fake_response)
    asyncio_clients = fake_xrpl_async["xrpl.asyncio.clients"]
    asyncio_clients.AsyncJsonRpcClient.return_value = fake_client

    t = AsyncXRPLTransport()
    assert await t.get_memo_text("TXID") is None


async def test_async_get_memo_text_decodes_first_good_memo(
    fake_xrpl_async: dict[str, types.ModuleType],
) -> None:
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import _to_hex

    text = "SOV|campfire_v1|s42|r1|sha256:abc"
    fake_response = MagicMock()
    fake_response.result = {
        "Memos": [
            {"Memo": {"MemoData": "abc"}},  # malformed, skipped
            {"Memo": {"MemoData": _to_hex(text)}},
        ],
    }
    fake_client = MagicMock()
    fake_client.request = AsyncMock(return_value=fake_response)
    asyncio_clients = fake_xrpl_async["xrpl.asyncio.clients"]
    asyncio_clients.AsyncJsonRpcClient.return_value = fake_client

    t = AsyncXRPLTransport()
    assert await t.get_memo_text("TXID") == text

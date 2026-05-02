"""Wave 11 Stage 8-C regression tests for ``sov_transport`` (bridge) amends.

Each test pins a specific finding from
``swarm-1777686810-67fd/wave-10/audit/bridge-findings.yaml`` so the next
audit can match a green test to a closed finding.

Coverage:

* BRIDGE-C-001 — ``XRPLTransport._submit`` ``TransportError`` messages
  carry no banned ``please`` (Pin A voice anti-pattern grep).
* BRIDGE-C-002 — ``AsyncXRPLTransport._submit`` mirrors the sync
  sibling's ``please``-free voice.
* BRIDGE-C-004 — ``MainnetFaucetError`` raised by
  ``fund_dev_wallet(MAINNET)`` carries the doc-ref + backticked
  command pair (env var, testnet command, README anchor).
* BRIDGE-C-005 — ``is_anchored_on_chain`` ``LOOKUP_FAILED`` log lines
  carry an operator-readable ``category=`` token so triage can tell
  network-unreachable from RPC error from malformed envelope.

Cross-domain MEDs surfaced in the audit live elsewhere:

* BRIDGE-C-003 (``MAINNET_UNDERFUNDED`` hint omits explorer URL) —
  factory lives in ``sov_cli/errors.py``, routed to the cli agent.
* BRIDGE-C-005 engine-side reason-token split — ``sov_engine/proof.py``
  maps ``LOOKUP_FAILED`` → ``AnchorStatus.MISSING`` with reason
  ``chain_drift``, routed to the backend agent. Bridge owns the
  transport-level log-detail half (this file).

BRIDGE-C-006 + BRIDGE-C-007 are recorded as verified non-findings in
``wave-11/bridge.output.json``.
"""

from __future__ import annotations

import logging
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Shared fake-xrpl fixture (sync + async submodules) — lifted from
# ``test_xrpl_amend_regressions.py`` to keep fixture surface stable across
# amend waves.
# ---------------------------------------------------------------------------


def _install_fake_xrpl_modules() -> dict[str, types.ModuleType]:
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
    # Wave 10 BRIDGE-A-bis-001 mirror: async anchor swapped Payment → AccountSet.
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
def fake_xrpl(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    fakes = _install_fake_xrpl_modules()
    for name, mod in fakes.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return fakes


_TEST_SEED = "sEdWAVE11seedXXXXXXXXXXXXXXX"


# ---------------------------------------------------------------------------
# BRIDGE-C-001 + BRIDGE-C-002 — Pin A voice grep on TransportError messages
# ---------------------------------------------------------------------------


_BANNED_VOICE_TOKENS: tuple[str, ...] = (
    "please",
    "you should",
    "you might",
    "oops",
    "whoops",
    "sorry",
)


def _assert_no_banned_voice(message: str, where: str) -> None:
    """Pin A — every banned token must be absent from ``message``."""
    lowered = message.lower()
    hits = [token for token in _BANNED_VOICE_TOKENS if token in lowered]
    assert not hits, (
        f"{where} TransportError message contains banned voice token(s) {hits!r}: {message!r}"
    )


def _build_response(
    *,
    is_successful: bool,
    result: Any,
) -> MagicMock:
    response = MagicMock(name="response")
    response.is_successful = MagicMock(return_value=is_successful)
    response.result = result
    return response


def test_bridge_c_001_xrpl_submit_missing_result_dict_no_please(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``XRPLTransport._submit`` must raise without 'please' when the
    response is_successful but ``result`` is not a dict."""
    from sov_transport.xrpl import TransportError, XRPLTransport

    transaction_mod = fake_xrpl["xrpl.transaction"]
    # is_successful=True but result is a non-dict — exercises the
    # "missing the expected result dict" branch.
    transaction_mod.submit_and_wait.return_value = _build_response(
        is_successful=True,
        result="not-a-dict",
    )

    t = XRPLTransport()
    with pytest.raises(TransportError) as exc:
        t.anchor("abc123", "SOV|test", _TEST_SEED)

    _assert_no_banned_voice(str(exc.value), where="XRPLTransport (missing result dict)")


def test_bridge_c_001_xrpl_submit_missing_hash_no_please(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``XRPLTransport._submit`` must raise without 'please' when the
    response is_successful and result is a dict but lacks the 'hash' key."""
    from sov_transport.xrpl import TransportError, XRPLTransport

    transaction_mod = fake_xrpl["xrpl.transaction"]
    transaction_mod.submit_and_wait.return_value = _build_response(
        is_successful=True,
        result={"engine_result": "tesSUCCESS"},  # no 'hash'
    )

    t = XRPLTransport()
    with pytest.raises(TransportError) as exc:
        t.anchor("abc123", "SOV|test", _TEST_SEED)

    _assert_no_banned_voice(str(exc.value), where="XRPLTransport (missing hash)")


def test_bridge_c_002_async_xrpl_submit_missing_result_dict_no_please(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``AsyncXRPLTransport._submit`` mirrors the sync sibling — no 'please'."""
    import asyncio

    from sov_transport.xrpl import TransportError
    from sov_transport.xrpl_async import AsyncXRPLTransport

    asyncio_transaction = fake_xrpl["xrpl.asyncio.transaction"]
    asyncio_transaction.submit_and_wait.return_value = _build_response(
        is_successful=True,
        result="not-a-dict",
    )

    t = AsyncXRPLTransport()
    with pytest.raises(TransportError) as exc:
        asyncio.run(t.anchor("abc123", "SOV|test", _TEST_SEED))

    _assert_no_banned_voice(str(exc.value), where="AsyncXRPLTransport (missing result dict)")


def test_bridge_c_002_async_xrpl_submit_missing_hash_no_please(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """``AsyncXRPLTransport._submit`` missing-hash path is 'please'-free."""
    import asyncio

    from sov_transport.xrpl import TransportError
    from sov_transport.xrpl_async import AsyncXRPLTransport

    asyncio_transaction = fake_xrpl["xrpl.asyncio.transaction"]
    asyncio_transaction.submit_and_wait.return_value = _build_response(
        is_successful=True,
        result={"engine_result": "tesSUCCESS"},
    )

    t = AsyncXRPLTransport()
    with pytest.raises(TransportError) as exc:
        asyncio.run(t.anchor("abc123", "SOV|test", _TEST_SEED))

    _assert_no_banned_voice(str(exc.value), where="AsyncXRPLTransport (missing hash)")


def test_bridge_c_001_002_static_voice_grep_on_transport_module() -> None:
    """Static guard: no banned voice tokens appear inside any string literal
    that ends up in a ``TransportError(...)`` raise within the bridge
    transport modules. This catches future regressions at the source-tree
    level without exercising every code path."""
    import re
    from pathlib import Path

    bridge_root = Path(__file__).resolve().parent.parent / "sov_transport"
    files = [
        bridge_root / "xrpl.py",
        bridge_root / "xrpl_async.py",
    ]

    for path in files:
        text = path.read_text(encoding="utf-8")
        # Strip line/block comments and docstrings is overkill — we instead
        # scope the check to ``raise TransportError(`` blocks. The block
        # boundary is the closing ``)`` at column 16 (matching the leading
        # indent), which is brittle, so we use a coarser heuristic: scan
        # for the literal patterns that previously contained 'please'.
        for token in _BANNED_VOICE_TOKENS:
            # Match the token only when it appears inside a double-quoted
            # string (heuristic — catches the Pin A surface). False
            # positives in code comments (e.g. ``# please file an issue``)
            # are handled by reviewers; the audit shows zero today.
            pattern = re.compile(
                rf'"[^"]*\b{re.escape(token)}\b[^"]*"',
                re.IGNORECASE,
            )
            matches = pattern.findall(text)
            assert not matches, (
                f"{path.name}: banned voice token {token!r} appears inside a "
                f"string literal (Pin A regression). Matches: {matches!r}"
            )


# ---------------------------------------------------------------------------
# BRIDGE-C-004 — MainnetFaucetError carries doc-ref + backticked command
# ---------------------------------------------------------------------------


def test_bridge_c_004_mainnet_faucet_error_has_backticked_command(
    fake_xrpl: dict[str, types.ModuleType],  # noqa: ARG001 — unused, fixture installed for import safety
) -> None:
    """``fund_dev_wallet(MAINNET)`` raises with backticked env var + command
    and a doc-ref pointing at the README network-selection anchor."""
    from sov_transport.xrpl import MainnetFaucetError, XRPLNetwork, fund_dev_wallet

    with pytest.raises(MainnetFaucetError) as exc:
        fund_dev_wallet(XRPLNetwork.MAINNET)

    msg = str(exc.value)
    # Pin A: imperative voice, no "please".
    _assert_no_banned_voice(msg, where="MainnetFaucetError")
    # Backticks frame the env var and the testnet command per
    # SovError hint discipline.
    assert "`XRPL_SEED`" in msg, f"MainnetFaucetError message must backtick `XRPL_SEED`: {msg!r}"
    assert "`sov wallet --network testnet`" in msg, (
        f"MainnetFaucetError message must backtick the testnet command: {msg!r}"
    )
    # Doc-ref for mainnet seed management — README network-selection anchor.
    assert "#network-selection" in msg, (
        f"MainnetFaucetError message must reference the README #network-selection anchor: {msg!r}"
    )


# ---------------------------------------------------------------------------
# BRIDGE-C-005 — LOOKUP_FAILED log lines carry operator-readable category
# ---------------------------------------------------------------------------


def test_bridge_c_005_lookup_failed_network_unreachable_log_category(
    fake_xrpl: dict[str, types.ModuleType],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``is_anchored_on_chain`` logs ``category=network_unreachable`` when
    ``client.request`` raises (RPC unreachable / 5xx propagated as exception)."""
    from sov_transport.xrpl import XRPLTransport
    from sov_transport.xrpl_internals import ChainLookupResult

    clients_mod = fake_xrpl["xrpl.clients"]
    fake_client = MagicMock(name="JsonRpcClientInstance")
    fake_client.request = MagicMock(
        side_effect=ConnectionError("rpc unreachable"),
    )
    clients_mod.JsonRpcClient = MagicMock(return_value=fake_client)

    t = XRPLTransport()
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        result = t.is_anchored_on_chain("txid123", "abc")

    assert result is ChainLookupResult.LOOKUP_FAILED
    assert any(
        "lookup_failed" in r.getMessage() and "category=network_unreachable" in r.getMessage()
        for r in caplog.records
    ), (
        f"LOOKUP_FAILED log must carry category=network_unreachable; "
        f"got: {[r.getMessage() for r in caplog.records]!r}"
    )


def test_bridge_c_005_lookup_failed_rpc_error_log_category(
    fake_xrpl: dict[str, types.ModuleType],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``is_anchored_on_chain`` logs ``category=rpc_error`` when the response
    has ``is_successful=False`` and a non-``txnNotFound`` error token."""
    from sov_transport.xrpl import XRPLTransport
    from sov_transport.xrpl_internals import ChainLookupResult

    clients_mod = fake_xrpl["xrpl.clients"]
    fake_client = MagicMock(name="JsonRpcClientInstance")
    response = _build_response(
        is_successful=False,
        result={"error": "internalError"},
    )
    fake_client.request = MagicMock(return_value=response)
    clients_mod.JsonRpcClient = MagicMock(return_value=fake_client)

    t = XRPLTransport()
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        result = t.is_anchored_on_chain("txid123", "abc")

    assert result is ChainLookupResult.LOOKUP_FAILED
    assert any(
        "lookup_failed" in r.getMessage() and "category=rpc_error" in r.getMessage()
        for r in caplog.records
    ), (
        f"LOOKUP_FAILED log must carry category=rpc_error; "
        f"got: {[r.getMessage() for r in caplog.records]!r}"
    )


def test_bridge_c_005_lookup_failed_malformed_response_log_category(
    fake_xrpl: dict[str, types.ModuleType],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``is_anchored_on_chain`` logs ``category=malformed_response`` when the
    response has ``is_successful=False`` and no error token at all."""
    from sov_transport.xrpl import XRPLTransport
    from sov_transport.xrpl_internals import ChainLookupResult

    clients_mod = fake_xrpl["xrpl.clients"]
    fake_client = MagicMock(name="JsonRpcClientInstance")
    response = _build_response(
        is_successful=False,
        result={},  # no 'error' key
    )
    fake_client.request = MagicMock(return_value=response)
    clients_mod.JsonRpcClient = MagicMock(return_value=fake_client)

    t = XRPLTransport()
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        result = t.is_anchored_on_chain("txid123", "abc")

    assert result is ChainLookupResult.LOOKUP_FAILED
    assert any(
        "lookup_failed" in r.getMessage() and "category=malformed_response" in r.getMessage()
        for r in caplog.records
    ), (
        f"LOOKUP_FAILED log must carry category=malformed_response; "
        f"got: {[r.getMessage() for r in caplog.records]!r}"
    )


def test_bridge_c_005_async_lookup_failed_network_unreachable_log_category(
    fake_xrpl: dict[str, types.ModuleType],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Async sibling mirrors the sync category-token contract on the
    network-unreachable path."""
    import asyncio

    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import ChainLookupResult

    asyncio_clients_mod = fake_xrpl["xrpl.asyncio.clients"]
    fake_client = MagicMock(name="AsyncJsonRpcClientInstance")
    fake_client.request = AsyncMock(side_effect=ConnectionError("rpc unreachable"))
    asyncio_clients_mod.AsyncJsonRpcClient = MagicMock(return_value=fake_client)

    t = AsyncXRPLTransport()
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        result = asyncio.run(t.is_anchored_on_chain("txid123", "abc"))

    assert result is ChainLookupResult.LOOKUP_FAILED
    assert any(
        "lookup_failed" in r.getMessage() and "category=network_unreachable" in r.getMessage()
        for r in caplog.records
    ), (
        f"Async LOOKUP_FAILED log must carry category=network_unreachable; "
        f"got: {[r.getMessage() for r in caplog.records]!r}"
    )

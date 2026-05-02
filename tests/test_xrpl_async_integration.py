"""Integration tests for ``AsyncXRPLTransport`` — opt-in real testnet.

Mirrors ``tests/test_xrpl_integration.py`` for the async sibling. Hits
real XRPL testnet via ``AsyncJsonRpcClient`` + the testnet faucet, so
gated behind ``RUN_INTEGRATION=1``.

Mainnet integration is **NOT** included here. Anchoring on mainnet costs
real (small) money and requires a funded wallet that the test harness
cannot mint on demand. Mainnet integration is gated behind a separate
``RUN_MAINNET_INTEGRATION=1`` env var AND a funded ``XRPL_SEED`` value;
neither is set in CI, so mainnet tests are always skipped there.
"""

from __future__ import annotations

import os

import pytest

# Reuse the existing integration marker so `pytest -m integration` finds it.
pytestmark = pytest.mark.integration


_INTEGRATION_OPT_IN = os.environ.get("RUN_INTEGRATION") == "1"
_MAINNET_OPT_IN = os.environ.get("RUN_MAINNET_INTEGRATION") == "1" and bool(
    os.environ.get("XRPL_SEED")
)


@pytest.mark.skipif(
    not _INTEGRATION_OPT_IN,
    reason="set RUN_INTEGRATION=1 to hit live XRPL testnet via async client",
)
async def test_async_anchor_batch_three_rounds_returns_single_txid() -> None:
    """Anchor a 3-round async batch on testnet → returns a single txid.

    Uses the public faucet to mint a fresh wallet so the test does not
    depend on operator-provided seeds. The test asserts the wire shape:
    one Payment, one txid, three rounds resolvable via
    ``is_anchored_on_chain``.
    """
    pytest.importorskip("xrpl", reason="xrpl-py is required for async integration")

    from sov_transport.base import BatchEntry
    from sov_transport.xrpl import fund_dev_wallet
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    # Mint a faucet-funded wallet on testnet (sync helper — minting is
    # one-shot and the existing code path is sufficient).
    _, seed = fund_dev_wallet(XRPLNetwork.TESTNET)

    rounds: list[BatchEntry] = [
        {
            "round_key": "1",
            "ruleset": "campfire_v1",
            "game_id": "sASYNC1",
            "envelope_hash": "a" * 64,
        },
        {
            "round_key": "2",
            "ruleset": "campfire_v1",
            "game_id": "sASYNC1",
            "envelope_hash": "b" * 64,
        },
        {
            "round_key": "FINAL",
            "ruleset": "campfire_v1",
            "game_id": "sASYNC1",
            "envelope_hash": "f" * 64,
        },
    ]
    transport = AsyncXRPLTransport(XRPLNetwork.TESTNET)
    txid = await transport.anchor_batch(rounds, seed)
    assert isinstance(txid, str) and len(txid) > 0

    # Verify each round's hash resolves on-chain via the same async transport.
    for entry in rounds:
        assert (await transport.is_anchored_on_chain(txid, entry["envelope_hash"])) is True


@pytest.mark.skipif(
    not _MAINNET_OPT_IN,
    reason=(
        "mainnet async integration requires both RUN_MAINNET_INTEGRATION=1 "
        "AND a funded XRPL_SEED env var; neither is set in CI"
    ),
)
async def test_async_anchor_batch_against_mainnet_skipped_without_funded_wallet() -> None:
    """Mainnet integration: documented but never run in CI.

    This test exists so the contract surface is covered when an operator
    locally exports ``RUN_MAINNET_INTEGRATION=1`` and a funded mainnet
    seed via ``XRPL_SEED``. CI never sets either, so the skipif gate
    keeps it dormant.
    """
    pytest.importorskip("xrpl")

    from sov_transport.base import BatchEntry
    from sov_transport.xrpl_async import AsyncXRPLTransport
    from sov_transport.xrpl_internals import XRPLNetwork

    seed = os.environ["XRPL_SEED"]
    rounds: list[BatchEntry] = [
        {
            "round_key": "1",
            "ruleset": "campfire_v1",
            "game_id": "sMAINNET1",
            "envelope_hash": "deadbeef" + "0" * 56,
        }
    ]
    transport = AsyncXRPLTransport(XRPLNetwork.MAINNET)
    txid = await transport.anchor_batch(rounds, seed)
    assert isinstance(txid, str) and len(txid) > 0

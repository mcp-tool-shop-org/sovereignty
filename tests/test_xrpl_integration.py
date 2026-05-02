"""Real XRPL Testnet integration test.

Skipped by default; opt in via:
    RUN_INTEGRATION=1 pytest tests/test_xrpl_integration.py

Hits the actual XRPL Testnet (https://s.altnet.rippletest.net:51234/),
funds a fresh wallet via the public faucet, anchors a memo, fetches it
back, and verifies the round-trip. Catches drift between mocked and real
xrpl-py response shapes (the gap that Stage B's mocked tests can't see).
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 to opt in to real-testnet tests",
    ),
]


def test_real_testnet_anchor_verify_roundtrip():
    """Fund a fresh wallet, anchor a memo, fetch it back, verify."""
    pytest.importorskip("xrpl")
    from sov_transport.xrpl_testnet import XRPLTestnetTransport, fund_testnet_wallet

    transport = XRPLTestnetTransport()
    address, seed = fund_testnet_wallet()

    expected_hash = "abc123def456" * 5  # 60 chars, valid-looking hex
    memo = f"SOV|test_v1|s42|r1|sha256:{expected_hash}"

    # Anchor
    txid = transport.anchor(round_hash=expected_hash, memo=memo, signer=seed)
    assert isinstance(txid, str)
    assert len(txid) == 64  # XRPL tx hashes are 64-char uppercase hex

    # Verify
    valid = transport.verify(txid=txid, expected_hash=expected_hash)
    assert valid, f"verify() failed for txid={txid}; memo not found or hash mismatch"

    # get_memo_text
    memo_back = transport.get_memo_text(txid)
    assert memo_back == memo, f"memo round-trip drift: sent {memo!r}, got {memo_back!r}"


def test_real_testnet_verify_returns_false_for_unknown_txid():
    pytest.importorskip("xrpl")
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    transport = XRPLTestnetTransport()
    bogus_txid = "0" * 64
    # Should not crash; expect False (or a typed TransportError if get_tx fails)
    try:
        valid = transport.verify(txid=bogus_txid, expected_hash="anything")
        assert valid is False
    except Exception as e:
        # Acceptable: typed TransportError. Not acceptable: bare exception with
        # seed in repr (regression guard).
        from sov_transport import TransportError

        assert isinstance(e, TransportError), f"unexpected exception type: {type(e).__name__}"


def test_real_testnet_anchor_batch_three_rounds_one_tx():
    """v2.1 batch path: anchor 3 rounds in one Payment, verify all three.

    Catches drift between the multi-memo wire shape (one Payment with N
    Memos) and what real XRPL Testnet actually accepts and returns. The
    mocked tests in ``test_anchor_batch.py`` only see the model-level
    submission; this test pins that the batch path round-trips against the
    live testnet.
    """
    pytest.importorskip("xrpl")
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport, fund_dev_wallet

    transport = XRPLTransport(XRPLNetwork.TESTNET)
    address, seed = fund_dev_wallet(XRPLNetwork.TESTNET)
    assert address  # faucet returned a real address

    h1 = "abc123def456" * 5 + "abcd"  # 64 chars
    h2 = "deadbeefcafe" * 5 + "1234"
    h3 = "feedfacefeed" * 5 + "5678"
    rounds = [
        {
            "round_key": "1",
            "ruleset": "test_v1",
            "game_id": "s42",
            "envelope_hash": h1,
        },
        {
            "round_key": "2",
            "ruleset": "test_v1",
            "game_id": "s42",
            "envelope_hash": h2,
        },
        {
            "round_key": "FINAL",
            "ruleset": "test_v1",
            "game_id": "s42",
            "envelope_hash": h3,
        },
    ]

    txid = transport.anchor_batch(rounds, signer=seed)
    assert isinstance(txid, str)
    assert len(txid) == 64  # XRPL tx hashes are 64-char uppercase hex

    # All three round hashes resolve via is_anchored_on_chain on the same txid.
    for h in (h1, h2, h3):
        assert transport.is_anchored_on_chain(txid=txid, expected_hash=h), (
            f"is_anchored_on_chain failed for hash={h} on batch txid={txid}"
        )

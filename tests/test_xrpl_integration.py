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
    """Fund a fresh wallet, anchor a memo, fetch it back, verify.

    Uses the legacy ``XRPLTestnetTransport`` + ``verify()`` shims; both are
    deprecated and emit ``DeprecationWarning`` (Wave 2 deprecation). The
    CI ``-W error::DeprecationWarning`` filter promotes those to errors, so
    we wrap in ``warnings.catch_warnings()`` to absorb the expected
    deprecation noise. The deprecation contracts themselves are pinned by
    ``tests/test_xrpl_transport_legacy.py``; this test exercises the same
    shim against live testnet, so the pattern repeats.
    """
    import warnings

    pytest.importorskip("xrpl")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
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
    import warnings

    pytest.importorskip("xrpl")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
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

    # Wave 10 BRIDGE-A-bis-003: anchor_batch returns ``list[str]``.
    # 3 memos fits in 1 chunk so the list has 1 element.
    txids = transport.anchor_batch(rounds, signer=seed)
    assert isinstance(txids, list)
    assert len(txids) == 1
    assert all(isinstance(t, str) and len(t) == 64 for t in txids)
    txid = txids[0]

    # All three round hashes resolve via is_anchored_on_chain on the same
    # txid. Post-BRIDGE-004 the return is ``ChainLookupResult.FOUND`` (not
    # the legacy ``True``) — the truthy check on the enum still works as a
    # smoke gate, and the explicit comparison pins the new contract.
    from sov_transport import ChainLookupResult

    for h in (h1, h2, h3):
        assert transport.is_anchored_on_chain(txid=txid, expected_hash=h) is (
            ChainLookupResult.FOUND
        ), f"is_anchored_on_chain failed for hash={h} on batch txid={txid}"


# Wave 10 BRIDGE-A-bis-003: real-testnet boundary regression. Pins the
# empirical 8/9-memo cap against rippled's local-checks rejection so future
# memo-format changes (longer game-id, longer ruleset) that shift the
# boundary get caught HERE rather than discovered at production submit time.


def test_real_testnet_anchor_batch_boundary_8_memos_succeeds():
    """8 memos at SOV grammar (~95 B/memo) submits to testnet OK.

    Empirical boundary upper bound. Future memo-format changes that push
    8 memos over rippled's aggregate Memos-field cap (~1 KB) will fail
    this test, signalling the constant ``_MAX_MEMOS_PER_TX`` needs to
    drop to 7.
    """
    pytest.importorskip("xrpl")
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport, fund_dev_wallet

    transport = XRPLTransport(XRPLNetwork.TESTNET)
    _, seed = fund_dev_wallet(XRPLNetwork.TESTNET)

    rounds = [
        {
            "round_key": str(i),
            "ruleset": "campfire_v1",
            "game_id": "s42",
            "envelope_hash": format(i, "064x"),
        }
        for i in range(1, 9)  # 8 rounds
    ]

    txids = transport.anchor_batch(rounds, signer=seed)
    assert len(txids) == 1, f"expected 1 chunk for 8 memos, got {len(txids)}"
    assert len(txids[0]) == 64


def test_real_testnet_anchor_batch_boundary_16_memos_chunks_to_two_txs():
    """16 memos chunk into 2 sequential txs of 8 each.

    Pins the typical-game arc (15 rounds + FINAL). Each chunk is verified
    on chain by walking ``is_anchored_on_chain`` for every round_hash
    against the expected chunk's txid.
    """
    pytest.importorskip("xrpl")
    from sov_transport import ChainLookupResult
    from sov_transport.xrpl import XRPLNetwork, XRPLTransport, fund_dev_wallet

    transport = XRPLTransport(XRPLNetwork.TESTNET)
    _, seed = fund_dev_wallet(XRPLNetwork.TESTNET)

    # Build 15 rounds + FINAL (16 total). Sort order at the bridge places
    # FINAL last, so chunk 1 = rounds 1-8, chunk 2 = rounds 9-15 + FINAL.
    rounds = [
        {
            "round_key": str(i),
            "ruleset": "campfire_v1",
            "game_id": "s42",
            "envelope_hash": format(i, "064x"),
        }
        for i in range(1, 16)
    ]
    rounds.append(
        {
            "round_key": "FINAL",
            "ruleset": "campfire_v1",
            "game_id": "s42",
            "envelope_hash": "f" * 64,
        }
    )

    txids = transport.anchor_batch(rounds, signer=seed)
    assert len(txids) == 2, f"expected 2 chunks for 16 memos, got {len(txids)}"
    assert all(len(t) == 64 for t in txids)
    # Chunks should be distinct txs.
    assert txids[0] != txids[1], "chunks must produce distinct txids"

    # Verify chunk 1 (rounds 1-8) resolves on txids[0].
    for i in range(1, 9):
        h = format(i, "064x")
        assert (
            transport.is_anchored_on_chain(txid=txids[0], expected_hash=h)
            is ChainLookupResult.FOUND
        ), f"chunk-1 round {i} hash {h} not found on txid {txids[0]}"

    # Verify chunk 2 (rounds 9-15 + FINAL) resolves on txids[1].
    for i in range(9, 16):
        h = format(i, "064x")
        assert (
            transport.is_anchored_on_chain(txid=txids[1], expected_hash=h)
            is ChainLookupResult.FOUND
        ), f"chunk-2 round {i} hash {h} not found on txid {txids[1]}"
    assert (
        transport.is_anchored_on_chain(txid=txids[1], expected_hash="f" * 64)
        is ChainLookupResult.FOUND
    ), "FINAL hash not found on chunk-2 txid"

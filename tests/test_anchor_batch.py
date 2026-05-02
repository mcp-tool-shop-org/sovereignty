"""Tests for ``XRPLTransport.anchor_batch`` (v2.1 multi-memo single-tx).

Pins the audit-ergonomics primary of v2.1: one verifiable chain pointer per
game, not a 16-tx trail. ``anchor_batch`` puts N memos on a single Payment
(one SOV grammar line per memo) and returns one txid. Per-memo cap is
unchanged at 1024 bytes; per-tx cap is XRPL-native (~150 memo fields).

Mocks ``submit_and_wait`` via ``unittest.mock.patch`` on the deferred xrpl
imports so these tests don't hit the network. The batch path reuses the
same retry / scrub / response-shape machinery as single-anchor — these
tests pin the multi-memo wire shape and the size + emptiness guards.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from sov_transport.base import BatchEntry

_TEST_SEED = "sEdXXXXXXXXXXXXXXXXXXXXXXX"


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

    # Wire submodule references onto the dynamically-built parents so the
    # transport's ``from xrpl.x import Y`` works under sys.modules patching.
    # Stored on a generic ``ModuleType``; access is through the fixture's
    # dict rather than attribute access, which keeps mypy strict happy.
    xrpl.__dict__["clients"] = clients
    xrpl.__dict__["models"] = models
    xrpl.__dict__["transaction"] = transaction
    xrpl.__dict__["wallet"] = wallet

    clients.__dict__["JsonRpcClient"] = MagicMock(name="JsonRpcClient")
    models.__dict__["Memo"] = MagicMock(name="Memo")
    # Wave 10 BRIDGE-A-bis-001 mirror: anchor_batch swapped Payment →
    # AccountSet (xrpl-py 4.5.0 self-payment validation).
    models.__dict__["Payment"] = MagicMock(name="Payment")
    models.__dict__["AccountSet"] = MagicMock(name="AccountSet")
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


def _stub_wallet(fake_xrpl: dict[str, types.ModuleType]) -> MagicMock:
    """Configure Wallet.from_seed to return a stub wallet object."""
    fake_wallet = MagicMock()
    fake_wallet.address = "rTestAddress"
    fake_wallet.classic_address = "rTestAddress"
    wallet_mod = fake_xrpl["xrpl.wallet"]
    wallet_mod.Wallet.from_seed.return_value = fake_wallet
    return fake_wallet


def _stub_submit_response(
    fake_xrpl: dict[str, types.ModuleType],
    *,
    tx_hash: str = "BATCHTXHASH",
) -> MagicMock:
    """Configure submit_and_wait to return a successful response."""
    fake_response = MagicMock()
    fake_response.is_successful.return_value = True
    fake_response.result = {"hash": tx_hash}
    transaction_mod = fake_xrpl["xrpl.transaction"]
    transaction_mod.submit_and_wait.return_value = fake_response
    return fake_response


def _make_entry(round_key: str, envelope_hash: str) -> BatchEntry:
    """Build a ``BatchEntry`` for the given round + hash."""
    return BatchEntry(
        round_key=round_key,
        ruleset="campfire_v1",
        game_id="s42",
        envelope_hash=envelope_hash,
    )


def _captured_memos(
    fake_xrpl: dict[str, types.ModuleType],
) -> list[str]:
    """Decode the memos passed to ``Memo(memo_data=...)`` during the call.

    Returns the list of UTF-8 SOV strings carried on the submitted Payment.
    """
    memo_cls = fake_xrpl["xrpl.models"].Memo
    memos: list[str] = []
    for call in memo_cls.call_args_list:
        kwargs = call.kwargs
        hex_data = kwargs.get("memo_data")
        if hex_data is None and call.args:
            hex_data = call.args[0]
        if not isinstance(hex_data, str):
            continue
        try:
            memos.append(bytes.fromhex(hex_data).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
    return memos


# ---------------------------------------------------------------------------
# Happy-path batch sizes
# ---------------------------------------------------------------------------


def test_anchor_batch_n_eq_1_single_memo(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """N=1: single BatchEntry returns a 1-element txid list (Wave 10 BRIDGE-A-bis-003)."""
    from sov_transport.xrpl import XRPLTransport

    _stub_wallet(fake_xrpl)
    _stub_submit_response(fake_xrpl, tx_hash="TX1")

    t = XRPLTransport()
    txids = t.anchor_batch([_make_entry("1", "a" * 64)], _TEST_SEED)
    assert txids == ["TX1"]

    memos = _captured_memos(fake_xrpl)
    sov_memos = [m for m in memos if m.startswith("SOV|")]
    assert len(sov_memos) == 1
    assert sov_memos[0] == f"SOV|campfire_v1|s42|r1|sha256:{'a' * 64}"


def test_anchor_batch_n_eq_15_full_round_set(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """N=15: chunks into 2 txs (8 + 7 memos) per Wave 10 BRIDGE-A-bis-003.

    15 is ``MAX_ROUNDS`` from sov_engine.models. The rippled aggregate
    Memos-field cap (~1 KB on the wire, ≤8 SOV-grammar memos) forces the
    split. All 15 SOV grammar lines still appear, partitioned across 2
    txs in round-key order.
    """
    from sov_transport.xrpl import XRPLTransport

    _stub_wallet(fake_xrpl)
    _stub_submit_response(fake_xrpl, tx_hash="TX15")

    entries = [
        _make_entry(str(i), format(i, "064x"))  # unique 64-char hex per round
        for i in range(1, 16)
    ]

    t = XRPLTransport()
    txids = t.anchor_batch(entries, _TEST_SEED)
    # 15 memos / 8 per tx = 2 chunks (8 + 7). Mock returns "TX15" for
    # both submit_and_wait calls (since we stubbed a single response).
    assert txids == ["TX15", "TX15"]

    memos = _captured_memos(fake_xrpl)
    sov_memos = [m for m in memos if m.startswith("SOV|")]
    assert len(sov_memos) == 15
    # Every round 1..15 appears exactly once with the right hash.
    for i in range(1, 16):
        expected = f"SOV|campfire_v1|s42|r{i}|sha256:{format(i, '064x')}"
        assert expected in sov_memos, f"missing memo for round {i}: {sov_memos!r}"


def test_anchor_batch_n_eq_16_with_final(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """N=16: 15 rounds + FINAL → 2 txs (8 + 8). ``FINAL`` renders without ``r``-prefix.

    Wave 10 BRIDGE-A-bis-003: 16 memos chunk into 2 txs of 8 each. FINAL
    lands in the second chunk (sort order places FINAL last via
    ``_sort_key``).
    """
    from sov_transport.xrpl import XRPLTransport

    _stub_wallet(fake_xrpl)
    _stub_submit_response(fake_xrpl, tx_hash="TX16")

    entries = [_make_entry(str(i), format(i, "064x")) for i in range(1, 16)]
    entries.append(_make_entry("FINAL", "f" * 64))

    t = XRPLTransport()
    txids = t.anchor_batch(entries, _TEST_SEED)
    # 16 memos / 8 per tx = 2 chunks of 8.
    assert txids == ["TX16", "TX16"]

    memos = _captured_memos(fake_xrpl)
    sov_memos = [m for m in memos if m.startswith("SOV|")]
    assert len(sov_memos) == 16

    final_memo = f"SOV|campfire_v1|s42|FINAL|sha256:{'f' * 64}"
    assert final_memo in sov_memos, (
        f"FINAL memo must use the literal 'FINAL' field (no 'r' prefix); "
        f"got: {[m for m in sov_memos if 'FINAL' in m or 'rFINAL' in m]!r}"
    )
    assert not any("rFINAL" in m for m in sov_memos), (
        f"FINAL memo must NOT carry an 'rFINAL' field; got: {sov_memos!r}"
    )


# Wave 10 BRIDGE-A-bis-003: explicit chunking-boundary regression tests.


def test_anchor_batch_n_eq_8_single_chunk(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """N=8: at the per-tx cap, returns a single-element txid list."""
    from sov_transport.xrpl import XRPLTransport

    _stub_wallet(fake_xrpl)
    _stub_submit_response(fake_xrpl, tx_hash="TX8")

    entries = [_make_entry(str(i), format(i, "064x")) for i in range(1, 9)]
    t = XRPLTransport()
    txids = t.anchor_batch(entries, _TEST_SEED)
    assert txids == ["TX8"]


def test_anchor_batch_n_eq_9_chunks_to_two(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """N=9: just over the cap chunks into 2 txs (8 + 1)."""
    from sov_transport.xrpl import XRPLTransport

    _stub_wallet(fake_xrpl)
    _stub_submit_response(fake_xrpl, tx_hash="TX9")

    entries = [_make_entry(str(i), format(i, "064x")) for i in range(1, 10)]
    t = XRPLTransport()
    txids = t.anchor_batch(entries, _TEST_SEED)
    assert txids == ["TX9", "TX9"]


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_anchor_batch_empty_list_raises_value_error(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """Empty input is a programming error, not a no-op anchor."""
    from sov_transport.xrpl import XRPLTransport

    t = XRPLTransport()
    with pytest.raises(ValueError):
        t.anchor_batch([], _TEST_SEED)


def test_anchor_batch_oversized_single_memo_raises(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """The 1024-byte cap is per-memo, not per-tx.

    A single BatchEntry whose rendered memo exceeds 1024 bytes must raise
    ``ValueError`` with a message identifying the offending round_key, even
    if the rest of the batch would fit.
    """
    from sov_transport.xrpl import XRPLTransport

    huge_ruleset_name = "x" * 1100  # forces rendered memo over 1024
    big_entry = BatchEntry(
        round_key="1",
        ruleset=huge_ruleset_name,
        game_id="s42",
        envelope_hash="a" * 64,
    )

    t = XRPLTransport()
    with pytest.raises(ValueError, match="exceeds"):
        t.anchor_batch([big_entry], _TEST_SEED)


def test_anchor_batch_secret_scrubbed_when_submission_raises(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    """Mirrors the secret-scrub guarantee for single ``anchor`` (F-001).

    If submit_and_wait or wallet construction raises, the propagated
    exception's repr/str MUST NOT contain the seed. The cause chain must be
    suppressed (``raise ... from None``) so traceback locals carrying the
    seed do not bleed into observability layers.
    """
    from sov_transport.xrpl import XRPLTransport

    def _raise_with_seed(seed: str) -> None:
        raise ValueError(f"bad seed: {seed}")

    wallet_mod = fake_xrpl["xrpl.wallet"]
    wallet_mod.Wallet.from_seed.side_effect = _raise_with_seed

    t = XRPLTransport()
    entry = _make_entry("1", "a" * 64)
    with pytest.raises(Exception) as exc_info:
        t.anchor_batch([entry], _TEST_SEED)

    rep = repr(exc_info.value)
    msg = str(exc_info.value)
    assert _TEST_SEED not in rep
    assert _TEST_SEED not in msg
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True

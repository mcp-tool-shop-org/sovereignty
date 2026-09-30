"""Coverage tests for the transport layer (coverage handoff, Phase 4).

Fills the gaps in ``sov_transport`` that the existing transport suites leave
open:

* ``XRPLTransport._submit`` / ``AsyncXRPLTransport._submit`` -- success, every
  ``_classify_submit_error`` class, retry with backoff, deadline handling,
  retry exhaustion, and each unexpected-response shape. The retry loops never
  sleep for real: ``time`` (and ``asyncio`` for the async sibling) is swapped
  for a recording, controllable stand-in inside the transport module.
* ``is_anchored_on_chain`` -- FOUND / NOT_FOUND / LOOKUP_FAILED.
* ``get_memo_text`` -- all four ``Tx`` response envelope shapes.
* ``_maybe_aclose``, ``NullTransport``, ``LedgerTransport`` defaults, and
  ``fund_dev_wallet`` edge cases.

Every transport test is parametrized over the sync and async impls through the
``sut`` fixture, so the two retry loops cannot drift apart unnoticed. No test
touches the network: ``xrpl`` is replaced by fake modules in ``sys.modules``.
"""

from __future__ import annotations

import inspect
import logging
import sys
import types
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sov_transport import TransportError
from sov_transport.base import BatchEntry, LedgerTransport
from sov_transport.null import NullTransport
from sov_transport.xrpl_internals import (
    ChainLookupResult,
    XRPLNetwork,
    _classify_submit_error,
    _extract_memos,
    _from_hex,
    _to_hex,
)

_SEED = "sEdCOVERAGEseedXXXXXXXXXXXXXX"
_TXID = "A" * 64
_GOOD_HASH = "abc123"
_GOOD_MEMO = f"SOV|campfire_v1|s42|r1|sha256:{_GOOD_HASH}"


# ---------------------------------------------------------------------------
# Fake xrpl modules + sync/async harness
# ---------------------------------------------------------------------------


def _install_fake_xrpl(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    """Install fake ``xrpl`` (sync + asyncio) modules; return them by name."""
    fakes: dict[str, types.ModuleType] = {}

    def _make(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        fakes[name] = mod
        return mod

    xrpl = _make("xrpl")
    clients = _make("xrpl.clients")
    models = _make("xrpl.models")
    transaction = _make("xrpl.transaction")
    wallet = _make("xrpl.wallet")
    aio = _make("xrpl.asyncio")
    aio_clients = _make("xrpl.asyncio.clients")
    aio_transaction = _make("xrpl.asyncio.transaction")

    xrpl.__dict__.update(
        clients=clients, models=models, transaction=transaction, wallet=wallet, asyncio=aio
    )
    aio.__dict__.update(clients=aio_clients, transaction=aio_transaction)

    clients.JsonRpcClient = MagicMock(name="JsonRpcClient")  # type: ignore[attr-defined]
    models.Memo = MagicMock(name="Memo")  # type: ignore[attr-defined]
    models.AccountSet = MagicMock(name="AccountSet")  # type: ignore[attr-defined]
    models.Tx = MagicMock(name="Tx")  # type: ignore[attr-defined]
    transaction.submit_and_wait = MagicMock(name="submit_and_wait")  # type: ignore[attr-defined]
    fake_wallet = MagicMock(name="wallet")
    fake_wallet.classic_address = "rTESTclassicAddress"
    fake_wallet.address = "rTESTaddress"
    wallet.Wallet = MagicMock(name="Wallet")  # type: ignore[attr-defined]
    wallet.Wallet.from_seed.return_value = fake_wallet
    wallet.generate_faucet_wallet = MagicMock(name="generate_faucet_wallet")  # type: ignore[attr-defined]
    aio_clients.AsyncJsonRpcClient = MagicMock(name="AsyncJsonRpcClient")  # type: ignore[attr-defined]
    aio_transaction.submit_and_wait = AsyncMock(name="async_submit_and_wait")  # type: ignore[attr-defined]

    for name, mod in fakes.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return fakes


def _block_xrpl(monkeypatch: pytest.MonkeyPatch, fakes: dict[str, types.ModuleType]) -> None:
    """Make every ``import xrpl...`` raise ImportError (xrpl-py not installed)."""
    for name in fakes:
        monkeypatch.setitem(sys.modules, name, None)


class _Clock:
    """Controllable stand-in for ``time.monotonic`` (last tick repeats forever)."""

    def __init__(self) -> None:
        self.ticks: list[float] = [0.0]

    def set(self, *ticks: float) -> None:
        self.ticks = list(ticks)

    def monotonic(self) -> float:
        if len(self.ticks) > 1:
            return self.ticks.pop(0)
        return self.ticks[0]


class Sut:
    """One transport (sync or async) wired to fake xrpl modules + fake clock."""

    def __init__(
        self,
        kind: str,
        fakes: dict[str, types.ModuleType],
        transport: Any,
        client: MagicMock,
        submit_mock: MagicMock,
        clock: _Clock,
        sleeps: list[float],
    ) -> None:
        self.kind = kind
        self.fakes = fakes
        self.transport = transport
        self.client = client
        self.submit_mock = submit_mock
        self.clock = clock
        self.sleeps = sleeps

    @property
    def is_async(self) -> bool:
        return self.kind == "async"

    @property
    def request(self) -> MagicMock:
        return self.client.request  # type: ignore[no-any-return]

    @property
    def closer(self) -> MagicMock:
        """The client-lifecycle method each transport invokes after a lookup."""
        return self.client.aclose if self.is_async else self.client.close  # type: ignore[no-any-return]

    async def call(self, name: str, *args: Any) -> Any:
        result = getattr(self.transport, name)(*args)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def submit(self, memos: list[str] | None = None, seed: str = _SEED) -> str:
        out = await self.call("_submit", memos or [_GOOD_MEMO], seed)
        assert isinstance(out, str)
        return out


@pytest.fixture
def fake_xrpl(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    return _install_fake_xrpl(monkeypatch)


@pytest.fixture(params=["sync", "async"])
def sut(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    fake_xrpl: dict[str, types.ModuleType],
) -> Sut:
    kind: str = request.param
    clock = _Clock()
    sleeps: list[float] = []

    async def _fake_async_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    if kind == "sync":
        import sov_transport.xrpl as mod

        monkeypatch.setattr(
            mod, "time", SimpleNamespace(monotonic=clock.monotonic, sleep=sleeps.append)
        )
        transport: Any = mod.XRPLTransport()
        client = MagicMock(name="client")
        client.request = MagicMock(name="request")
        fake_xrpl["xrpl.clients"].JsonRpcClient.return_value = client  # type: ignore[attr-defined]
        submit_mock = fake_xrpl["xrpl.transaction"].submit_and_wait  # type: ignore[attr-defined]
    else:
        import sov_transport.xrpl_async as amod

        monkeypatch.setattr(
            amod,
            "time",
            SimpleNamespace(monotonic=clock.monotonic),
        )
        monkeypatch.setattr(amod, "asyncio", SimpleNamespace(sleep=_fake_async_sleep))
        transport = amod.AsyncXRPLTransport()
        client = MagicMock(name="client")
        client.request = AsyncMock(name="request")
        fake_xrpl["xrpl.asyncio.clients"].AsyncJsonRpcClient.return_value = client  # type: ignore[attr-defined]
        submit_mock = fake_xrpl["xrpl.asyncio.transaction"].submit_and_wait  # type: ignore[attr-defined]
    return Sut(kind, fake_xrpl, transport, client, submit_mock, clock, sleeps)


def _response(result: Any, *, ok: bool = True) -> MagicMock:
    resp = MagicMock(name="response")
    resp.is_successful.return_value = ok
    resp.result = result
    return resp


def _ok(tx_hash: str = "HASH1") -> MagicMock:
    return _response({"hash": tx_hash})


def _memo(text: str) -> dict[str, Any]:
    return {"Memo": {"MemoData": _to_hex(text)}}


def _root_cause(exc: BaseException) -> BaseException:
    """Deepest ``__context__`` -- the un-sanitized original failure."""
    while exc.__context__ is not None:
        exc = exc.__context__
    return exc


class LedgerNotFound(Exception):
    pass


class SigningProblem(Exception):
    pass


def _entry(round_key: str, game_id: str = "s42") -> BatchEntry:
    return BatchEntry(
        round_key=round_key,
        ruleset="campfire_v1",
        game_id=game_id,
        envelope_hash=("%064x" % (abs(hash(round_key)) % 16**16)),
    )


# ---------------------------------------------------------------------------
# _submit: success path
# ---------------------------------------------------------------------------


async def test_submit_success_returns_hash_and_builds_memos(
    sut: Sut, caplog: pytest.LogCaptureFixture
) -> None:
    sut.submit_mock.return_value = _ok("TXHASH")
    memos = ["SOV|a|s1|r1|sha256:" + "1" * 64, "SOV|a|s1|FINAL|sha256:" + "2" * 64]
    with caplog.at_level(logging.INFO, logger="sov_transport"):
        assert await sut.submit(memos) == "TXHASH"

    models = sut.fakes["xrpl.models"]
    memo_calls = models.Memo.call_args_list  # type: ignore[attr-defined]
    assert [c.kwargs["memo_data"] for c in memo_calls] == [_to_hex(m) for m in memos]
    assert all(c.kwargs["memo_type"] == _to_hex("text/plain") for c in memo_calls)
    account_set = models.AccountSet  # type: ignore[attr-defined]
    account_set.assert_called_once()
    assert account_set.call_args.kwargs["account"] == "rTESTaddress"
    assert len(account_set.call_args.kwargs["memos"]) == 2
    assert sut.submit_mock.call_count == 1
    assert sut.sleeps == []
    assert "anchor.success tx=TXHASH attempts=1 memos=2" in caplog.text
    assert _SEED not in caplog.text


async def test_submit_success_when_response_has_no_is_successful(sut: Sut) -> None:
    """A response object without ``is_successful`` is trusted on its result dict."""
    sut.submit_mock.return_value = SimpleNamespace(result={"hash": "PLAIN"})
    assert await sut.submit() == "PLAIN"


async def test_submit_success_when_is_successful_raises(sut: Sut) -> None:
    """A broken ``is_successful()`` must not turn a good response into a failure."""
    resp = _ok("STILLOK")
    resp.is_successful.side_effect = RuntimeError("introspection blew up")
    sut.submit_mock.return_value = resp
    assert await sut.submit() == "STILLOK"


async def test_submit_missing_xrpl_raises_runtime_error(
    sut: Sut, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_xrpl(monkeypatch, sut.fakes)
    with pytest.raises(RuntimeError, match=r"xrpl-py is not installed.*sovereignty-game\[xrpl\]"):
        await sut.submit()
    assert sut.submit_mock.call_count == 0


# ---------------------------------------------------------------------------
# _submit: unexpected response shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("response", "needle"),
    [
        (_response({"engine_result": "tecUNFUNDED"}, ok=False), "engine_result: tecUNFUNDED"),
        (_response({}, ok=False), "was not successful"),
        (_response("not-a-dict", ok=False), "was not successful"),
        (_response(["not", "a", "dict"]), "got list"),
        (_response(None), "got NoneType"),
        (_response({"ledger_index": 7, "validated": True}), "['ledger_index', 'validated']"),
        (_response({}), "missing the 'hash' field"),
        (_response({"hash": ""}), "missing the 'hash' field"),
        (_response({"hash": 12345}), "missing the 'hash' field"),
    ],
    ids=[
        "unsuccessful-with-engine-result",
        "unsuccessful-empty-result",
        "unsuccessful-non-dict-result",
        "result-is-list",
        "result-is-none",
        "hash-missing-shape-keys",
        "hash-missing-empty-result",
        "hash-empty-string",
        "hash-not-a-string",
    ],
)
async def test_submit_rejects_unexpected_response_shapes(
    sut: Sut, response: MagicMock, needle: str
) -> None:
    sut.submit_mock.return_value = response
    with pytest.raises(TransportError) as excinfo:
        await sut.submit()

    # The public message is sanitized (no library details, no seed)...
    assert "details suppressed to protect signer secret" in str(excinfo.value)
    assert _SEED not in str(excinfo.value)
    # ...while the un-sanitized diagnostic stays reachable for debuggers.
    root = _root_cause(excinfo.value)
    assert isinstance(root, TransportError)
    assert needle in str(root)
    # A definitive (non-transient) rejection is not retried.
    assert sut.submit_mock.call_count == 1
    assert sut.sleeps == []


async def test_submit_unsuccessful_response_hint_names_network_explorer(sut: Sut) -> None:
    sut.submit_mock.return_value = _response({"engine_result": "tecNO_DST"}, ok=False)
    with pytest.raises(TransportError) as excinfo:
        await sut.submit()
    root = str(_root_cause(excinfo.value))
    assert "https://testnet.xrpl.org" in root
    assert "insufficient balance" in root


# ---------------------------------------------------------------------------
# _submit: retry, deadline, exhaustion
# ---------------------------------------------------------------------------


async def test_submit_retries_transient_errors_then_succeeds(
    sut: Sut, caplog: pytest.LogCaptureFixture
) -> None:
    sut.submit_mock.side_effect = [
        LedgerNotFound("no ledger yet"),
        ConnectionError("x"),
        _ok("OK3"),
    ]
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        assert await sut.submit() == "OK3"

    assert sut.submit_mock.call_count == 3
    assert sut.sleeps == [1.0, 2.0]
    assert "anchor.retry attempt=1/3 reason=ledger_not_found exc=LedgerNotFound" in caplog.text
    assert "anchor.retry attempt=2/3 reason=network exc=ConnectionError" in caplog.text


@pytest.mark.parametrize(
    ("exc", "reason"),
    [
        (LedgerNotFound("gone"), "ledger_not_found"),
        (SigningProblem("bad key"), "signing_failed"),
        (TimeoutError("request timed out"), "timeout"),
        (ConnectionError("Connection refused"), "network"),
        (ValueError("boom"), "unknown"),
    ],
    ids=["ledger", "signing", "timeout", "network", "unknown"],
)
async def test_submit_exhausts_retries_for_each_error_class(
    sut: Sut, caplog: pytest.LogCaptureFixture, exc: Exception, reason: str
) -> None:
    sut.submit_mock.side_effect = exc
    with (
        caplog.at_level(logging.INFO, logger="sov_transport"),
        pytest.raises(TransportError) as excinfo,
    ):
        await sut.submit()

    assert sut.submit_mock.call_count == 3
    assert sut.sleeps == [1.0, 2.0]  # no sleep after the final attempt
    assert (
        f"anchor.exhausted attempts=3 deadline_s=30.0 reason={reason} exc={type(exc).__name__}"
        in (caplog.text)
    )
    assert "anchor.terminal exc=TransportError" in caplog.text
    # Chain: sanitized TransportError -> sanitized intermediate -> exhaustion error,
    # whose __cause__ is the last raw submit failure.
    intermediate = excinfo.value.__context__
    assert intermediate is not None
    assert "details suppressed" in str(intermediate)
    exhausted = _root_cause(excinfo.value)
    assert str(exhausted).startswith("Anchor failed after 3 attempts")
    assert exhausted.__cause__ is exc


async def test_submit_exhaustion_message_names_reason_and_recovery(sut: Sut) -> None:
    sut.submit_mock.side_effect = LedgerNotFound("gone")
    with pytest.raises(TransportError) as excinfo:
        await sut.submit()
    # The exhaustion diagnostic (un-sanitized) is one hop down the context chain.
    ctx = excinfo.value.__context__
    assert ctx is not None and ctx.__context__ is not None
    text = str(ctx.__context__)
    assert "Anchor failed after 3 attempts within 30s deadline" in text
    assert "last reason: ledger_not_found" in text
    assert "https://testnet.xrpl.org/network/validators" in text
    assert "`sov anchor`" in text


async def test_submit_never_leaks_seed_through_logs_or_message(
    sut: Sut, caplog: pytest.LogCaptureFixture
) -> None:
    sut.submit_mock.side_effect = ValueError(f"cannot sign with {_SEED}")
    with (
        caplog.at_level(logging.DEBUG, logger="sov_transport"),
        pytest.raises(TransportError) as excinfo,
    ):
        await sut.submit()
    assert _SEED not in str(excinfo.value)
    assert _SEED not in caplog.text


async def test_submit_deadline_already_elapsed_skips_submission(
    sut: Sut, caplog: pytest.LogCaptureFixture
) -> None:
    # tick 1: deadline = 0 + 30; tick 2: loop guard sees 31s elapsed.
    sut.clock.set(0.0, 31.0)
    with caplog.at_level(logging.INFO, logger="sov_transport"), pytest.raises(TransportError):
        await sut.submit()
    assert sut.submit_mock.call_count == 0
    assert "anchor.exhausted attempts=0 deadline_s=30.0 reason=deadline exc=Deadline" in caplog.text


async def test_submit_stops_retrying_when_deadline_passes_after_failure(
    sut: Sut, caplog: pytest.LogCaptureFixture
) -> None:
    # tick1 deadline calc, tick2 loop guard, tick3 remaining -> already past deadline.
    sut.clock.set(0.0, 0.0, 31.0)
    sut.submit_mock.side_effect = ConnectionError("down")
    with caplog.at_level(logging.INFO, logger="sov_transport"), pytest.raises(TransportError):
        await sut.submit()
    assert sut.submit_mock.call_count == 1
    assert sut.sleeps == []
    assert "anchor.exhausted attempts=1" in caplog.text
    assert "reason=network" in caplog.text


async def test_submit_clamps_backoff_to_remaining_deadline(sut: Sut) -> None:
    # deadline=30; first failure leaves only 0.5s, so the 1.0s backoff is clamped.
    sut.clock.set(0.0, 0.0, 29.5, 29.5)
    sut.submit_mock.side_effect = [LedgerNotFound("gone"), _ok("LATE")]
    assert await sut.submit() == "LATE"
    assert sut.sleeps == [0.5]


# ---------------------------------------------------------------------------
# Public anchor / anchor_batch (delegation into _submit)
# ---------------------------------------------------------------------------


async def test_anchor_submits_memo_and_returns_hash(sut: Sut) -> None:
    sut.submit_mock.return_value = _ok("ANCHORED")
    assert await sut.call("anchor", "unused-round-hash", _GOOD_MEMO, _SEED) == "ANCHORED"
    memo_kwargs = sut.fakes["xrpl.models"].Memo.call_args.kwargs  # type: ignore[attr-defined]
    assert memo_kwargs["memo_data"] == _to_hex(_GOOD_MEMO)


async def test_anchor_rejects_oversized_memo_before_any_submission(sut: Sut) -> None:
    with pytest.raises(ValueError, match="memo exceeds 1024 bytes"):
        await sut.call("anchor", "h", "x" * 1025, _SEED)
    assert sut.submit_mock.call_count == 0


async def test_anchor_batch_rejects_empty_rounds(sut: Sut) -> None:
    with pytest.raises(ValueError, match="at least one round entry"):
        await sut.call("anchor_batch", [], _SEED)
    assert sut.submit_mock.call_count == 0


async def test_anchor_batch_rejects_chunk_over_aggregate_byte_cap(sut: Sut) -> None:
    rounds = [_entry(str(i), game_id="g" * 150) for i in range(8)]
    with pytest.raises(ValueError, match="exceeds aggregate cap 1024 bytes"):
        await sut.call("anchor_batch", rounds, _SEED)
    assert sut.submit_mock.call_count == 0


async def test_anchor_batch_rejects_single_oversized_memo(sut: Sut) -> None:
    with pytest.raises(ValueError, match=r"round_key='1' exceeds 1024 bytes"):
        await sut.call("anchor_batch", [_entry("1", game_id="g" * 1100)], _SEED)
    assert sut.submit_mock.call_count == 0


async def test_anchor_batch_chunks_at_eight_memos_and_keeps_order(sut: Sut) -> None:
    sut.submit_mock.side_effect = [_ok("TX-A"), _ok("TX-B")]
    rounds = [_entry(str(i)) for i in range(1, 10)]  # 9 rounds -> chunks of 8 + 1
    txids = await sut.call("anchor_batch", rounds, _SEED)
    assert txids == ["TX-A", "TX-B"]
    memo_data = [c.kwargs["memo_data"] for c in sut.fakes["xrpl.models"].Memo.call_args_list]  # type: ignore[attr-defined]
    assert len(memo_data) == 9
    assert _from_hex(memo_data[0]).split("|")[3] == "r1"
    assert _from_hex(memo_data[8]).split("|")[3] == "r9"


async def test_anchor_batch_partial_failure_surfaces_transport_error(sut: Sut) -> None:
    """Chunk 1 lands on chain; chunk 2 fails -> TransportError, no silent success."""
    sut.submit_mock.side_effect = [_ok("TX-A")] + [ConnectionError("down")] * 3
    rounds = [_entry(str(i)) for i in range(1, 10)]
    with pytest.raises(TransportError):
        await sut.call("anchor_batch", rounds, _SEED)
    assert sut.submit_mock.call_count == 4  # 1 success + 3 attempts on chunk 2


# ---------------------------------------------------------------------------
# is_anchored_on_chain
# ---------------------------------------------------------------------------

_SHAPES: dict[str, Callable[[list[Any]], dict[str, Any]]] = {
    "top-level-Memos": lambda memos: {"Memos": memos},
    "tx_json-Memos": lambda memos: {"tx_json": {"Memos": memos}},
    "tx-dict-Memos": lambda memos: {"tx": {"Memos": memos}},
    "tx-list-Memos": lambda memos: {"tx": [{"Memos": memos}]},
}


@pytest.mark.parametrize("shape", sorted(_SHAPES))
async def test_is_anchored_found_for_every_envelope_shape(sut: Sut, shape: str) -> None:
    sut.request.return_value = _response(_SHAPES[shape]([_memo(_GOOD_MEMO)]))
    result = await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH)
    assert result is ChainLookupResult.FOUND
    sut.fakes["xrpl.models"].Tx.assert_called_once_with(transaction=_TXID)  # type: ignore[attr-defined]


async def test_is_anchored_not_found_when_hash_differs_or_is_only_a_prefix(sut: Sut) -> None:
    sut.request.return_value = _response({"Memos": [_memo("SOV|c|s1|r1|sha256:abc12345")]})
    # "abc123" is a prefix of the on-chain hash but must not match: equality, not startswith.
    assert await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH) is ChainLookupResult.NOT_FOUND


@pytest.mark.parametrize(
    "result",
    [{}, {"Memos": []}, {"tx": []}, {"tx": {"Memos": "nope"}}, {"tx": ["junk"]}, "junk", None],
    ids=["empty", "empty-memos", "empty-tx-list", "memos-not-list", "tx-list-junk", "str", "none"],
)
async def test_is_anchored_not_found_when_no_memos_extractable(sut: Sut, result: Any) -> None:
    sut.request.return_value = _response(result)
    assert await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH) is ChainLookupResult.NOT_FOUND


async def test_is_anchored_skips_junk_memos_and_finds_later_match(sut: Sut) -> None:
    memos = [
        "not-a-dict",
        {"Memo": "not-a-dict"},
        {"Memo": {}},
        {"Memo": {"MemoData": "zz-not-hex"}},
        {"Memo": {"MemoData": _to_hex("unrelated|fields|here")}},
        _memo(_GOOD_MEMO),
    ]
    sut.request.return_value = _response({"Memos": memos})
    assert await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH) is ChainLookupResult.FOUND


async def test_is_anchored_found_when_is_successful_raises(sut: Sut) -> None:
    resp = _response({"Memos": [_memo(_GOOD_MEMO)]})
    resp.is_successful.side_effect = RuntimeError("introspection blew up")
    sut.request.return_value = resp
    assert await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH) is ChainLookupResult.FOUND


async def test_is_anchored_found_when_response_has_no_is_successful(sut: Sut) -> None:
    sut.request.return_value = SimpleNamespace(result={"Memos": [_memo(_GOOD_MEMO)]})
    assert await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH) is ChainLookupResult.FOUND


async def test_is_anchored_txn_not_found_is_definitive_not_found(sut: Sut) -> None:
    sut.request.return_value = _response({"error": "txnNotFound"}, ok=False)
    assert await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH) is ChainLookupResult.NOT_FOUND


@pytest.mark.parametrize(
    ("result", "category", "error"),
    [
        ({"error": "slowDown"}, "rpc_error", "slowDown"),
        ({}, "malformed_response", "none"),
        ("junk", "malformed_response", "none"),
    ],
    ids=["rpc-error-token", "empty-envelope", "non-dict-envelope"],
)
async def test_is_anchored_lookup_failed_on_unsuccessful_response(
    sut: Sut, caplog: pytest.LogCaptureFixture, result: Any, category: str, error: str
) -> None:
    sut.request.return_value = _response(result, ok=False)
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        got = await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH)
    assert got is ChainLookupResult.LOOKUP_FAILED
    assert f"category={category} error={error}" in caplog.text


@pytest.mark.parametrize(
    ("exc", "detail"),
    [(ConnectionError("rpc down"), "rpc down"), (TimeoutError(), "no detail")],
    ids=["with-detail", "without-detail"],
)
async def test_is_anchored_lookup_failed_when_request_raises(
    sut: Sut, caplog: pytest.LogCaptureFixture, exc: Exception, detail: str
) -> None:
    sut.request.side_effect = exc
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        got = await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH)
    assert got is ChainLookupResult.LOOKUP_FAILED
    assert f"category=network_unreachable exc={type(exc).__name__} detail={detail}" in caplog.text
    # The client is still released when the lookup blows up.
    sut.closer.assert_called_once_with()


async def test_is_anchored_releases_client_and_survives_close_failure(sut: Sut) -> None:
    sut.request.return_value = _response({"Memos": [_memo(_GOOD_MEMO)]})
    sut.closer.side_effect = RuntimeError("close failed")
    assert await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH) is ChainLookupResult.FOUND
    sut.closer.assert_called_once_with()


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("", _GOOD_HASH), "txid must be non-empty"),
        ((_TXID, ""), "expected_hash must be non-empty"),
    ],
)
async def test_is_anchored_rejects_empty_arguments(
    sut: Sut, args: tuple[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        await sut.call("is_anchored_on_chain", *args)
    assert sut.request.call_count == 0


async def test_is_anchored_missing_xrpl_raises_runtime_error(
    sut: Sut, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_xrpl(monkeypatch, sut.fakes)
    with pytest.raises(RuntimeError, match="xrpl-py is not installed"):
        await sut.call("is_anchored_on_chain", _TXID, _GOOD_HASH)


# ---------------------------------------------------------------------------
# get_memo_text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shape", sorted(_SHAPES))
async def test_get_memo_text_decodes_every_envelope_shape(sut: Sut, shape: str) -> None:
    sut.request.return_value = _response(_SHAPES[shape]([_memo(_GOOD_MEMO)]))
    assert await sut.call("get_memo_text", _TXID) == _GOOD_MEMO
    sut.closer.assert_called_once_with()


@pytest.mark.parametrize(
    "result",
    [{}, {"Memos": []}, {"tx_json": {"Memos": []}}, "junk"],
    ids=["empty", "empty-memos", "empty-tx_json-memos", "non-dict"],
)
async def test_get_memo_text_none_when_no_memos(sut: Sut, result: Any) -> None:
    sut.request.return_value = _response(result)
    assert await sut.call("get_memo_text", _TXID) is None


async def test_get_memo_text_skips_undecodable_memos_and_returns_first_good(sut: Sut) -> None:
    memos = [
        42,
        {"Memo": ["not", "a", "dict"]},
        {"Memo": {}},
        {"Memo": {"MemoData": "abc"}},  # odd-length hex
        {"Memo": {"MemoData": "ff"}},  # invalid UTF-8
        _memo("first good"),
        _memo("second good"),
    ]
    sut.request.return_value = _response({"tx_json": {"Memos": memos}})
    assert await sut.call("get_memo_text", _TXID) == "first good"


async def test_get_memo_text_none_when_every_memo_is_undecodable(sut: Sut) -> None:
    sut.request.return_value = _response({"Memos": [{"Memo": {"MemoData": "zz"}}, {"Memo": {}}]})
    assert await sut.call("get_memo_text", _TXID) is None


async def test_get_memo_text_rejects_empty_txid(sut: Sut) -> None:
    with pytest.raises(ValueError, match="txid must be non-empty"):
        await sut.call("get_memo_text", "")
    assert sut.request.call_count == 0


async def test_get_memo_text_missing_xrpl_raises_runtime_error(
    sut: Sut, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_xrpl(monkeypatch, sut.fakes)
    with pytest.raises(RuntimeError, match="xrpl-py is not installed"):
        await sut.call("get_memo_text", _TXID)


async def test_get_memo_text_propagates_request_failure_but_releases_client(sut: Sut) -> None:
    sut.request.side_effect = ConnectionError("rpc down")
    with pytest.raises(ConnectionError, match="rpc down"):
        await sut.call("get_memo_text", _TXID)
    sut.closer.assert_called_once_with()


# ---------------------------------------------------------------------------
# Small transport surface (explorer root)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("network", "root"),
    [
        (XRPLNetwork.TESTNET, "https://testnet.xrpl.org"),
        (XRPLNetwork.MAINNET, "https://livenet.xrpl.org"),
        (XRPLNetwork.DEVNET, "https://devnet.xrpl.org"),
    ],
)
def test_explorer_root_strips_transactions_segment(network: XRPLNetwork, root: str) -> None:
    from sov_transport.xrpl import XRPLTransport
    from sov_transport.xrpl_async import AsyncXRPLTransport

    for cls in (XRPLTransport, AsyncXRPLTransport):
        t = cls(network)
        assert t._explorer_root() == root
        assert t.explorer_tx_url("ABC") == f"{root}/transactions/ABC"


# ---------------------------------------------------------------------------
# _maybe_aclose
# ---------------------------------------------------------------------------


class _AsyncAclose:
    def __init__(self) -> None:
        self.awaited = False

    async def aclose(self) -> None:
        self.awaited = True


class _SyncAclose:
    def __init__(self) -> None:
        self.called = False

    def aclose(self) -> None:
        self.called = True


class _SyncClose:
    def __init__(self) -> None:
        self.called = False

    def close(self) -> None:
        self.called = True


class _AsyncClose:
    def __init__(self) -> None:
        self.awaited = False

    async def close(self) -> None:
        self.awaited = True


class _AcloseAndClose(_AsyncAclose):
    def __init__(self) -> None:
        super().__init__()
        self.close_called = False

    def close(self) -> None:
        self.close_called = True


class _RaisingAclose:
    def aclose(self) -> None:
        raise RuntimeError("aclose failed")

    def close(self) -> None:  # must NOT be reached
        raise AssertionError("close() must not run after aclose() was attempted")


class _RaisingClose:
    def close(self) -> None:
        raise RuntimeError("close failed")


async def test_maybe_aclose_awaits_async_aclose() -> None:
    from sov_transport.xrpl_async import _maybe_aclose

    c = _AsyncAclose()
    await _maybe_aclose(c)
    assert c.awaited


async def test_maybe_aclose_calls_sync_aclose_without_awaiting() -> None:
    from sov_transport.xrpl_async import _maybe_aclose

    c = _SyncAclose()
    await _maybe_aclose(c)
    assert c.called


async def test_maybe_aclose_prefers_aclose_over_close() -> None:
    from sov_transport.xrpl_async import _maybe_aclose

    c = _AcloseAndClose()
    await _maybe_aclose(c)
    assert c.awaited
    assert not c.close_called


async def test_maybe_aclose_falls_back_to_sync_close() -> None:
    from sov_transport.xrpl_async import _maybe_aclose

    c = _SyncClose()
    await _maybe_aclose(c)
    assert c.called


async def test_maybe_aclose_falls_back_to_async_close() -> None:
    from sov_transport.xrpl_async import _maybe_aclose

    c = _AsyncClose()
    await _maybe_aclose(c)
    assert c.awaited


async def test_maybe_aclose_noop_when_client_has_no_lifecycle_method() -> None:
    from sov_transport.xrpl_async import _maybe_aclose

    assert await _maybe_aclose(object()) is None


@pytest.mark.parametrize("client", [_RaisingAclose(), _RaisingClose()], ids=["aclose", "close"])
async def test_maybe_aclose_swallows_cleanup_errors(client: object) -> None:
    from sov_transport.xrpl_async import _maybe_aclose

    assert await _maybe_aclose(client) is None


# ---------------------------------------------------------------------------
# xrpl_internals helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc", "token"),
    [
        (LedgerNotFound("x"), "ledger_not_found"),
        (RuntimeError("ledger_not_found while polling"), "ledger_not_found"),
        (SigningProblem("x"), "signing_failed"),
        (RuntimeError("signing failed"), "signing_failed"),
        (RuntimeError("wallet locked"), "unknown"),
        (TimeoutError("x"), "timeout"),
        (RuntimeError("request timed out"), "timeout"),
        (ConnectionError("x"), "network"),
        (RuntimeError("connect failed"), "network"),
        (RuntimeError("host unreachable"), "network"),
        (RuntimeError("connection refused"), "network"),
        (ValueError("boom"), "unknown"),
    ],
)
def test_classify_submit_error_tokens(exc: Exception, token: str) -> None:
    assert _classify_submit_error(exc) == token


@pytest.mark.parametrize(
    ("value", "decoded"),
    [(_to_hex("héllo"), "héllo"), ("", ""), ("abc", ""), ("zz", ""), ("ff", "")],
    ids=["utf8", "empty", "odd-length", "non-hex", "invalid-utf8"],
)
def test_from_hex_is_lenient(value: str, decoded: str) -> None:
    assert _from_hex(value) == decoded


def test_extract_memos_prefers_top_level_then_tx_json_then_tx() -> None:
    top = [{"Memo": {"MemoData": "aa"}}]
    nested = [{"Memo": {"MemoData": "bb"}}]
    legacy = [{"Memo": {"MemoData": "cc"}}]
    assert _extract_memos({"Memos": top, "tx_json": {"Memos": nested}}) is top
    assert _extract_memos({"Memos": [], "tx_json": {"Memos": nested}}) is nested
    assert _extract_memos({"tx_json": {"Memos": nested}, "tx": {"Memos": legacy}}) is nested
    assert _extract_memos({"tx": {"Memos": legacy}}) is legacy
    assert _extract_memos({"tx": [{"Memos": legacy}]}) is legacy


def test_extract_memos_tolerates_malformed_shapes(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        assert _extract_memos({"tx": ["junk"]}) == []
        assert _extract_memos({"tx": [{"Memos": "junk"}]}) == []
        assert _extract_memos({"tx_json": {"Memos": "junk"}}) == []
        assert _extract_memos("not-a-dict") == []  # type: ignore[arg-type]
    assert "first element is str" in caplog.text
    assert "unexpected result type str" in caplog.text


# ---------------------------------------------------------------------------
# fund_dev_wallet edge cases
# ---------------------------------------------------------------------------


def test_fund_dev_wallet_returns_address_and_seed(fake_xrpl: dict[str, types.ModuleType]) -> None:
    from sov_transport.xrpl import fund_dev_wallet
    from sov_transport.xrpl_internals import _NETWORK_TABLE

    faucet = fake_xrpl["xrpl.wallet"].generate_faucet_wallet  # type: ignore[attr-defined]
    faucet.return_value = SimpleNamespace(address="rFunded", seed="sEdFunded")
    assert fund_dev_wallet(XRPLNetwork.DEVNET) == ("rFunded", "sEdFunded")
    fake_xrpl["xrpl.clients"].JsonRpcClient.assert_called_once_with(  # type: ignore[attr-defined]
        _NETWORK_TABLE[XRPLNetwork.DEVNET][0]
    )


def test_fund_dev_wallet_rejects_wallet_without_seed(
    fake_xrpl: dict[str, types.ModuleType],
) -> None:
    from sov_transport.xrpl import fund_dev_wallet

    fake_xrpl["xrpl.wallet"].generate_faucet_wallet.return_value = SimpleNamespace(  # type: ignore[attr-defined]
        address="rNoSeed", seed=None
    )
    with pytest.raises(RuntimeError, match="xrpl wallet has no seed"):
        fund_dev_wallet()


def test_fund_dev_wallet_missing_xrpl_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch, fake_xrpl: dict[str, types.ModuleType]
) -> None:
    from sov_transport.xrpl import fund_dev_wallet

    _block_xrpl(monkeypatch, fake_xrpl)
    with pytest.raises(RuntimeError, match=r"xrpl-py is not installed.*sovereignty-game\[xrpl\]"):
        fund_dev_wallet()


def test_fund_dev_wallet_mainnet_has_no_faucet(fake_xrpl: dict[str, types.ModuleType]) -> None:
    from sov_transport.xrpl import fund_dev_wallet
    from sov_transport.xrpl_internals import MainnetFaucetError

    with pytest.raises(MainnetFaucetError, match="Mainnet has no faucet"):
        fund_dev_wallet(XRPLNetwork.MAINNET)
    fake_xrpl["xrpl.wallet"].generate_faucet_wallet.assert_not_called()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# NullTransport + LedgerTransport defaults
# ---------------------------------------------------------------------------


def test_null_anchor_returns_offline_marker() -> None:
    assert NullTransport().anchor("f" * 64, "memo", _SEED) == "offline:" + "f" * 16


def test_null_anchor_batch_returns_single_marker_keyed_off_first_entry() -> None:
    first = _entry("1")
    trail = NullTransport().anchor_batch([first, _entry("2"), _entry("FINAL")], _SEED)
    assert trail == [f"offline:batch:{first['envelope_hash'][:16]}"]


def test_null_anchor_batch_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one round entry"):
        NullTransport().anchor_batch([], _SEED)


def test_null_is_anchored_passthrough_for_offline_txids_only() -> None:
    t = NullTransport()
    assert t.is_anchored_on_chain("offline:abc", _GOOD_HASH) is ChainLookupResult.FOUND
    assert t.is_anchored_on_chain(_TXID, _GOOD_HASH) is ChainLookupResult.NOT_FOUND


def test_null_strict_verify_refuses_to_pass_through() -> None:
    t = NullTransport(strict_verify=True)
    assert t.strict_verify is True
    with pytest.raises(NotImplementedError, match="strict_verify=False"):
        t.is_anchored_on_chain("offline:abc", _GOOD_HASH)


def test_null_explorer_url_and_memo_text_are_offline_placeholders() -> None:
    t = NullTransport()
    assert t.explorer_tx_url("offline:abc") == "offline://tx/offline:abc"
    assert t.get_memo_text("offline:abc") is None


class _BareTransport(LedgerTransport):
    """Implements only the abstract surface, so ``get_memo_text`` is the base default."""

    def anchor(self, round_hash: str, memo: str, signer: str) -> str:
        return "tx"

    def anchor_batch(self, rounds: list[BatchEntry], signer: str) -> list[str]:
        return ["tx"]

    def is_anchored_on_chain(self, txid: str, expected_hash: str) -> ChainLookupResult:
        return ChainLookupResult.FOUND if expected_hash == "yes" else ChainLookupResult.NOT_FOUND

    def explorer_tx_url(self, txid: str) -> str:
        return txid


def test_base_get_memo_text_default_refuses_by_name() -> None:
    with pytest.raises(
        NotImplementedError, match="_BareTransport does not implement get_memo_text"
    ):
        _BareTransport().get_memo_text("tx")


def test_base_verify_is_a_deprecated_bool_alias() -> None:
    t = _BareTransport()
    with pytest.warns(DeprecationWarning, match="is_anchored_on_chain"):
        assert t.verify("tx", "yes") is True
    with pytest.warns(DeprecationWarning, match="removed in v2.2"):
        assert t.verify("tx", "no") is False


# ---------------------------------------------------------------------------
# Constructor scheme guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["sync", "async"])
def test_constructor_https_guard_and_insecure_escape_hatch(
    kind: str, caplog: pytest.LogCaptureFixture
) -> None:
    from sov_transport.xrpl import XRPLTransport
    from sov_transport.xrpl_async import AsyncXRPLTransport

    cls = XRPLTransport if kind == "sync" else AsyncXRPLTransport
    with pytest.raises(ValueError, match=r"must use https:// scheme"):
        cls(url="http://localhost:5005/")
    with caplog.at_level(logging.WARNING, logger="sov_transport"):
        t = cls(url="http://localhost:5005/", allow_insecure=True)
    assert t.url == "http://localhost:5005/"
    assert "allow_insecure=True" in caplog.text

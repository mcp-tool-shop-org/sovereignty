"""A test network reset after a round proof was anchored.

Testnet and Devnet are wiped on 2026-11-25. A proof anchored before that keeps
a valid local hash, but its anchor transaction is on no ledger afterwards. A
chain lookup then answers "not found", which read as an anchor mismatch.

The verdict here is ``reset``: the anchor can no longer be checked. It is
never a pass, and it applies only when the transaction is really absent and
an announced reset covers the time the proof was made.
"""

from __future__ import annotations

import json
import types
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
from typer.testing import CliRunner

from sov_cli.errors import anchor_reset_error
from sov_cli.main import EXIT_ANCHOR_RESET, app
from sov_transport import resets
from sov_transport.base import ChainLookupResult
from tests.test_cli_ops_commands import _flat, _make_proof, _transport_factory
from tests.test_transport_coverage import _install_fake_xrpl, _response

runner = CliRunner()
RESET_DAY = date(2026, 11, 25)
RESET_SOURCE = "https://xrpl.org/blog/2026/testnet-devnet-reset"
BEFORE_RESET = datetime(2026, 11, 20, tzinfo=UTC)
AFTER_RESET = datetime(2026, 12, 1, tzinfo=UTC)
OLD_PROOF_TIME = "2026-11-06T00:00:00Z"


@pytest.fixture
def after_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sov_transport.resets._now", lambda: AFTER_RESET)


@pytest.fixture
def cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    for var in ("XRPL_SEED", "SOV_XRPL_NETWORK", "SOV_TAURI_SHELL"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


class _Probe:
    """A transport that only answers whether a transaction is on the ledger."""

    def __init__(self, exists: bool | None) -> None:
        self.exists = exists
        self.asked: list[str] = []

    def tx_exists(self, txid: str) -> bool | None:
        self.asked.append(txid)
        return self.exists


# ── the announced-reset list ──────────────────────────────────────────


def test_the_2026_11_25_reset_is_listed_for_both_test_networks() -> None:
    assert {(r.network, r.day) for r in resets.KNOWN_RESETS} == {
        ("testnet", RESET_DAY),
        ("devnet", RESET_DAY),
    }
    for reset in resets.KNOWN_RESETS:
        source = urlparse(reset.source)
        assert (source.scheme, source.hostname) == ("https", "xrpl.org")
        assert reset.source == RESET_SOURCE


def test_mainnet_is_never_listed() -> None:
    assert "mainnet" not in {r.network for r in resets.KNOWN_RESETS}
    assert resets.announced_reset_after("mainnet", None, now=AFTER_RESET) is None


def test_a_reset_day_spans_every_timezone() -> None:
    r = resets.KnownReset("testnet", RESET_DAY, "src")
    assert r.starts == datetime(2026, 11, 24, 10, 0, tzinfo=UTC)
    assert r.ends == datetime(2026, 11, 26, 12, 0, tzinfo=UTC)
    assert r.label() == "Testnet was reset on 2026-11-25"


@pytest.mark.parametrize(
    ("network", "recorded", "now", "covered"),
    [
        ("testnet", datetime(2026, 11, 6, tzinfo=UTC), AFTER_RESET, True),
        ("devnet", datetime(2026, 11, 25, 18, tzinfo=UTC), AFTER_RESET, True),
        ("testnet", None, AFTER_RESET, True),  # no time recorded
        ("testnet", datetime(2026, 11, 26, 12, tzinfo=UTC), AFTER_RESET, False),  # after it
        ("testnet", datetime(2026, 11, 6, tzinfo=UTC), BEFORE_RESET, False),  # not yet
        (
            "testnet",
            datetime(2026, 11, 6, tzinfo=UTC),
            datetime(2026, 11, 24, 9, 59, tzinfo=UTC),
            False,
        ),
        ("local", None, AFTER_RESET, False),
    ],
)
def test_which_proofs_an_announced_reset_covers(
    network: str, recorded: datetime | None, now: datetime, covered: bool
) -> None:
    found = resets.announced_reset_after(network, recorded, now=now)
    assert (found is not None) is covered
    if found is not None:
        assert (found.network, found.day) == (network, RESET_DAY)


@pytest.mark.parametrize(
    ("raw", "parsed"),
    [
        ("2026-11-06T00:00:00Z", datetime(2026, 11, 6, tzinfo=UTC)),
        ("2026-11-06T00:00:00+00:00", datetime(2026, 11, 6, tzinfo=UTC)),
        ("2026-11-06T00:00:00", datetime(2026, 11, 6, tzinfo=UTC)),  # naive reads as UTC
        ("", None),
        ("   ", None),
        ("not a time", None),
        (None, None),
        (12345, None),
    ],
)
def test_parse_time(raw: object, parsed: datetime | None) -> None:
    assert resets.parse_time(raw) == parsed


def test_the_suite_pins_the_reset_clock_before_any_listed_reset() -> None:
    pinned = resets._now()
    assert all(pinned < r.starts for r in resets.KNOWN_RESETS)


def test_the_unpinned_clock_reads_the_real_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()  # drop the suite's pin for this test
    assert abs((datetime.now(tz=UTC) - resets._now()).total_seconds()) < 5


# ── does a reset explain a missing anchor ─────────────────────────────


def test_an_absent_tx_after_a_covering_reset_is_explained(after_reset: None) -> None:
    probe = _Probe(False)
    found = resets.reset_explains_missing_anchor(probe, "testnet", "TX1", OLD_PROOF_TIME)
    assert found is not None and found.label() == "Testnet was reset on 2026-11-25"
    assert probe.asked == ["TX1"]


@pytest.mark.parametrize("exists", [True, None])
def test_a_tx_that_is_there_or_unknown_is_not_explained(
    after_reset: None, exists: bool | None
) -> None:
    """Present with a different hash is a real mismatch; unknown is no verdict."""
    probe = _Probe(exists)
    assert resets.reset_explains_missing_anchor(probe, "testnet", "TX1", OLD_PROOF_TIME) is None


def test_a_transport_that_cannot_say_gives_no_reset_verdict(after_reset: None) -> None:
    assert resets.reset_explains_missing_anchor(object(), "testnet", "TX1", OLD_PROOF_TIME) is None


def test_before_the_reset_the_ledger_is_not_even_asked() -> None:
    probe = _Probe(False)
    assert resets.reset_explains_missing_anchor(probe, "testnet", "TX1", OLD_PROOF_TIME) is None
    assert probe.asked == []


def test_a_proof_made_after_the_reset_is_not_explained_by_it(after_reset: None) -> None:
    probe = _Probe(False)
    late = "2026-11-28T00:00:00Z"
    assert resets.reset_explains_missing_anchor(probe, "testnet", "TX1", late) is None
    assert probe.asked == []


def test_mainnet_is_never_explained_by_a_reset(after_reset: None) -> None:
    probe = _Probe(False)
    assert resets.reset_explains_missing_anchor(probe, "mainnet", "TX1", OLD_PROOF_TIME) is None


# ── the lookup vocabulary ─────────────────────────────────────────────


def test_reset_is_a_chain_lookup_value_and_never_the_found_one() -> None:
    assert ChainLookupResult.RESET.value == "reset"
    assert ChainLookupResult.RESET is not ChainLookupResult.FOUND
    assert {s.value for s in ChainLookupResult} == {
        "found",
        "not_found",
        "lookup_failed",
        "reset",
    }


# ── the transport probe ───────────────────────────────────────────────


@pytest.fixture
def sync_transport(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, MagicMock]:
    fake: dict[str, types.ModuleType] = _install_fake_xrpl(monkeypatch)
    import sov_transport.xrpl as mod

    client = MagicMock(name="client")
    client.request = MagicMock(name="request")
    fake["xrpl.clients"].JsonRpcClient.return_value = client  # type: ignore[attr-defined]
    return mod.XRPLTransport(), client


def test_tx_exists_true_when_the_ledger_has_it(sync_transport: tuple[Any, MagicMock]) -> None:
    transport, client = sync_transport
    client.request.return_value = _response({"hash": "TX1"})
    assert transport.tx_exists("TX1") is True
    client.close.assert_called_once()


def test_tx_exists_false_on_txn_not_found(sync_transport: tuple[Any, MagicMock]) -> None:
    transport, client = sync_transport
    client.request.return_value = _response({"error": "txnNotFound"}, ok=False)
    assert transport.tx_exists("TX1") is False


@pytest.mark.parametrize(
    "response",
    [
        _response({"error": "slowDown"}, ok=False),  # another RPC error
        _response("not-a-dict", ok=False),  # malformed
    ],
)
def test_tx_exists_none_when_the_answer_cannot_be_told(
    sync_transport: tuple[Any, MagicMock], response: MagicMock
) -> None:
    transport, client = sync_transport
    client.request.return_value = response
    assert transport.tx_exists("TX1") is None


def test_tx_exists_none_when_the_read_fails(sync_transport: tuple[Any, MagicMock]) -> None:
    transport, client = sync_transport
    client.request.side_effect = ConnectionError("rpc down")
    assert transport.tx_exists("TX1") is None


def test_tx_exists_none_when_is_successful_itself_raises(
    sync_transport: tuple[Any, MagicMock],
) -> None:
    transport, client = sync_transport
    response = _response({"hash": "TX1"})
    response.is_successful.side_effect = RuntimeError("boom")
    client.request.return_value = response
    assert transport.tx_exists("TX1") is None


def test_tx_exists_none_for_a_response_without_is_successful(
    sync_transport: tuple[Any, MagicMock],
) -> None:
    transport, client = sync_transport
    client.request.return_value = types.SimpleNamespace(result={"hash": "TX1"})
    assert transport.tx_exists("TX1") is None


def test_tx_exists_rejects_an_empty_txid(sync_transport: tuple[Any, MagicMock]) -> None:
    transport, _client = sync_transport
    with pytest.raises(ValueError, match="txid must be non-empty"):
        transport.tx_exists("")


def test_tx_exists_names_the_install_when_xrpl_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    import sov_transport.xrpl as mod

    monkeypatch.setitem(sys.modules, "xrpl.clients", None)
    with pytest.raises(RuntimeError, match="xrpl-py is not installed"):
        mod.XRPLTransport().tx_exists("TX1")


# ── the error a learner reads ─────────────────────────────────────────


def test_the_reset_error_says_it_cannot_be_checked_and_is_not_a_pass() -> None:
    err = anchor_reset_error("Testnet was reset on 2026-11-25", RESET_SOURCE)
    assert err.code == "NET_ANCHOR_RESET"
    assert "can no longer be checked" in err.message
    assert "Testnet was reset on 2026-11-25" in err.message
    assert "The local proof is still valid" in err.hint
    assert "a made-up `--tx` dated before the reset reads the same way" in err.hint
    assert f"Signal: announced reset ({RESET_SOURCE})." in err.hint


# ── sov verify --tx ───────────────────────────────────────────────────


def _not_found_factory(*, exists: bool | None) -> MagicMock:
    factory = _transport_factory()
    transport = factory.return_value
    transport.is_anchored_on_chain.return_value = ChainLookupResult.NOT_FOUND
    transport.tx_exists.return_value = exists
    return factory


def test_verify_reports_a_reset_anchor_with_exit_3(cwd: Path, after_reset: None) -> None:
    proof = _make_proof(cwd)
    factory = _not_found_factory(exists=False)
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXOLD"])
    assert result.exit_code == EXIT_ANCHOR_RESET == 3, result.output
    out = _flat(result.output)
    assert "Local proof valid." in out
    assert "Anchor can no longer be checked" in out
    assert "Testnet was reset on 2026-11-25" in out
    assert "Signal: announced reset" in out
    # Never a pass, and not called a mismatch.
    assert "Anchor verified" not in out
    assert "Anchor mismatch" not in out
    factory.return_value.tx_exists.assert_called_once_with("TXOLD")


def test_verify_on_devnet_names_devnet(cwd: Path, after_reset: None) -> None:
    proof = _make_proof(cwd)
    with patch("sov_transport.xrpl.XRPLTransport", _not_found_factory(exists=False)):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXOLD", "--network", "devnet"])
    assert result.exit_code == 3, result.output
    assert "Devnet was reset on 2026-11-25" in _flat(result.output)


@pytest.mark.parametrize("exists", [True, None])
def test_verify_keeps_the_mismatch_when_the_tx_is_there_or_unknown(
    cwd: Path, after_reset: None, exists: bool | None
) -> None:
    proof = _make_proof(cwd)
    with patch("sov_transport.xrpl.XRPLTransport", _not_found_factory(exists=exists)):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXNEW"])
    assert result.exit_code == 1
    out = _flat(result.output)
    assert "Anchor mismatch" in out and "can no longer be checked" not in out


def test_verify_before_the_reset_is_a_mismatch_as_it_always_was(cwd: Path) -> None:
    proof = _make_proof(cwd)
    factory = _not_found_factory(exists=False)
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXOLD"])
    assert result.exit_code == 1
    assert "Anchor mismatch" in _flat(result.output)
    factory.return_value.tx_exists.assert_not_called()


def test_verify_on_mainnet_is_never_a_reset(cwd: Path, after_reset: None) -> None:
    proof = _make_proof(cwd)
    with patch("sov_transport.xrpl.XRPLTransport", _not_found_factory(exists=False)):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXOLD", "--network", "mainnet"])
    assert result.exit_code == 1
    assert "Anchor mismatch" in _flat(result.output)


def test_verify_a_found_anchor_is_untouched_by_the_reset(cwd: Path, after_reset: None) -> None:
    proof = _make_proof(cwd)
    factory = _transport_factory()
    factory.return_value.is_anchored_on_chain.return_value = ChainLookupResult.FOUND
    factory.return_value.get_memo_text.return_value = None
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["verify", str(proof), "--tx", "TXNEW"])
    assert result.exit_code == 0, result.output
    assert "Anchor verified." in result.output
    factory.return_value.tx_exists.assert_not_called()


# ── the daemon's verify endpoint ──────────────────────────────────────

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")

_TOKEN = "test-token-fixed-for-tests"
_HASH = "0" * 64
_TXID = "TXIDRESET0001"


class _DaemonTransport:
    def __init__(self, result: ChainLookupResult, exists: bool | None) -> None:
        self.result = result
        self.exists = exists
        self.probed: list[str] = []

    def is_anchored_on_chain(self, txid: str, envelope_hash: str) -> ChainLookupResult:
        return self.result

    def tx_exists(self, txid: str) -> bool | None:
        self.probed.append(txid)
        return self.exists


def _seed_game(root: Path, *, timestamp: str | None, network_dir: str = "s42") -> None:
    game_dir = root / ".sov" / "games" / network_dir
    proofs = game_dir / "proofs"
    proofs.mkdir(parents=True, exist_ok=True)
    (game_dir / "state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "game_id": "s42",
                "round": 0,
                "ruleset": "campfire_v1",
                "players": ["A", "B"],
                "rng_seed": "42",
            }
        ),
        encoding="utf-8",
    )
    proof: dict[str, Any] = {
        "proof_version": 2,
        "game_id": "s42",
        "round": 1,
        "envelope_hash": _HASH,
    }
    if timestamp is not None:
        proof["timestamp_utc"] = timestamp
    (proofs / "round_001.proof.json").write_text(json.dumps(proof), encoding="utf-8")
    (game_dir / "pending-anchors.json").write_text(
        json.dumps({"schema_version": 1, "entries": {}}), encoding="utf-8"
    )


async def _verify_round(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    transport: _DaemonTransport,
    *,
    timestamp: str | None = OLD_PROOF_TIME,
    network: str = "testnet",
) -> dict[str, Any]:
    from sov_daemon.server import DaemonConfig, build_app
    from sov_engine.proof import record_anchors

    monkeypatch.chdir(tmp_path)
    _seed_game(tmp_path, timestamp=timestamp)
    record_anchors("s42", {"1": _TXID})
    monkeypatch.setattr("sov_daemon.server.get_verify_transport", lambda net: transport)
    daemon = build_app(DaemonConfig(network=network, readonly=True, token=_TOKEN))
    asgi = httpx.ASGITransport(app=daemon)
    async with httpx.AsyncClient(transport=asgi, base_url="http://test") as client:
        r = await client.get("/games/s42/verify/1", headers={"Authorization": f"Bearer {_TOKEN}"})
    assert r.status_code == 200
    body: dict[str, Any] = r.json()
    return body


async def test_daemon_reports_reset_with_its_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_reset: None
) -> None:
    transport = _DaemonTransport(ChainLookupResult.NOT_FOUND, exists=False)
    body = await _verify_round(tmp_path, monkeypatch, transport)
    assert body["chain_lookup"] == "reset"
    assert body["reset_signal"] == "announced"
    assert body["reset_note"] == f"Testnet was reset on 2026-11-25 ({RESET_SOURCE})"
    # The local index is unchanged, and the lookup is not "found".
    assert body["anchor_status"] == "anchored"
    assert transport.probed == [_TXID]


async def test_daemon_covers_a_proof_with_no_recorded_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_reset: None
) -> None:
    transport = _DaemonTransport(ChainLookupResult.NOT_FOUND, exists=False)
    body = await _verify_round(tmp_path, monkeypatch, transport, timestamp=None)
    assert body["chain_lookup"] == "reset"


@pytest.mark.parametrize("exists", [True, None])
async def test_daemon_keeps_not_found_when_the_tx_is_there_or_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_reset: None, exists: bool | None
) -> None:
    transport = _DaemonTransport(ChainLookupResult.NOT_FOUND, exists=exists)
    body = await _verify_round(tmp_path, monkeypatch, transport)
    assert body["chain_lookup"] == "not_found"
    assert "reset_signal" not in body and "reset_note" not in body


async def test_daemon_before_the_reset_is_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = _DaemonTransport(ChainLookupResult.NOT_FOUND, exists=False)
    body = await _verify_round(tmp_path, monkeypatch, transport)
    assert body["chain_lookup"] == "not_found"
    assert transport.probed == []


async def test_daemon_on_mainnet_is_never_a_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_reset: None
) -> None:
    transport = _DaemonTransport(ChainLookupResult.NOT_FOUND, exists=False)
    body = await _verify_round(tmp_path, monkeypatch, transport, network="mainnet")
    assert body["chain_lookup"] == "not_found"


@pytest.mark.parametrize(
    ("result", "wire"),
    [(ChainLookupResult.FOUND, "found"), (ChainLookupResult.LOOKUP_FAILED, "lookup_failed")],
)
async def test_daemon_found_and_failed_lookups_are_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    after_reset: None,
    result: ChainLookupResult,
    wire: str,
) -> None:
    transport = _DaemonTransport(result, exists=False)
    body = await _verify_round(tmp_path, monkeypatch, transport)
    assert body["chain_lookup"] == wire
    assert transport.probed == []
    assert "reset_signal" not in body


async def test_daemon_never_passes_a_transport_reset_value_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_reset: None
) -> None:
    """Only the daemon's own reset check may say "reset"; a transport cannot."""
    transport = _DaemonTransport(ChainLookupResult.RESET, exists=False)
    body = await _verify_round(tmp_path, monkeypatch, transport)
    assert body["chain_lookup"] == "lookup_failed"
    assert "reset_signal" not in body


def test_verify_help_lists_the_exit_codes() -> None:
    result = runner.invoke(app, ["verify", "--help"])
    out = _flat(result.output)
    assert result.exit_code == 0
    assert "Exit 3" in out and "not a pass" in out

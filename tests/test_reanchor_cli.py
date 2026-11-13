"""``sov anchor --reanchor``: put lost rounds back on the ledger.

A test network reset deletes every transaction. A round recorded as anchored
then has a txid that is on no ledger, and the normal flush skips it because a
recorded txid means "already sent". ``--reanchor`` asks the ledger about each
recorded txid and sends again only the rounds whose transaction is gone.

The bridge is stubbed at ``sov_transport.xrpl.XRPLTransport``; nothing here
touches a network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sov_cli.errors import anchor_reset_error
from sov_cli.main import app
from sov_engine.hashing import mark_final_proof
from sov_engine.io_utils import anchors_file, proofs_dir
from sov_engine.proof import read_anchors_file, record_anchors
from tests.test_anchor_cli import _seed_game
from tests.test_cli_ops_commands import _flat, _make_proof, _transport_factory

runner = CliRunner()
_TEST_SEED = "sEdXXXXXXXXXXXXXXXXXXXXXXX"
AFTER_RESET = datetime(2026, 12, 1, tzinfo=UTC)


@pytest.fixture
def cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    for var in ("SOV_XRPL_NETWORK", "SOV_TAURI_SHELL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    return tmp_path


def _anchored_game(cwd: Path, txid: str = "TXOLD") -> tuple[str, Path, str]:
    """A game with one valid round proof, recorded as anchored at ``txid``."""
    proof = _make_proof(cwd)
    data = json.loads(proof.read_text(encoding="utf-8"))
    game_id = str(data["game_id"])
    record_anchors(game_id, {str(data["round"]): txid})
    return game_id, proof, str(data["envelope_hash"])


def _add_final_proof(game_id: str, proof: Path, txid: str) -> str:
    """Add a valid FINAL proof beside ``proof``, recorded as anchored."""
    data = mark_final_proof(json.loads(proof.read_text(encoding="utf-8")))
    (proofs_dir(game_id) / "final.proof.json").write_text(json.dumps(data), encoding="utf-8")
    record_anchors(game_id, {"FINAL": txid})
    return str(data["envelope_hash"])


def _factory(*, exists: object, new_txid: str = "TXNEW") -> MagicMock:
    factory = _transport_factory()
    transport = factory.return_value
    if isinstance(exists, dict):
        transport.tx_exists.side_effect = lambda t: exists[t]
    else:
        transport.tx_exists.return_value = exists
    transport.anchor_batch.return_value = [new_txid]
    return factory


def _run(factory: MagicMock, *extra: str) -> tuple[int, str]:
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--reanchor", *extra])
    return result.exit_code, _flat(result.output)


def _recorded(game_id: str) -> dict[str, str]:
    return read_anchors_file(anchors_file(game_id))


# ── the recovery path ─────────────────────────────────────────────────


def test_a_lost_round_is_anchored_again(cwd: Path) -> None:
    game_id, _, envelope_hash = _anchored_game(cwd)
    factory = _factory(exists=False)
    code, out = _run(factory)
    assert code == 0, out
    transport = factory.return_value
    transport.tx_exists.assert_called_once_with("TXOLD")
    (rounds, seed), _ = transport.anchor_batch.call_args
    assert seed == _TEST_SEED
    assert [(r["round_key"], r["game_id"], r["envelope_hash"]) for r in rounds] == [
        ("1", game_id, envelope_hash)
    ]
    assert _recorded(game_id) == {"1": "TXNEW"}
    assert "1 still on the ledger" not in out
    assert "0 still on the ledger, 1 gone, 0 not answered" in out
    assert "1 round anchored again on XRPL testnet" in out
    assert "TXNEW" in out and "was TXOLD" in out


def test_a_round_still_on_the_ledger_is_never_sent_twice(cwd: Path) -> None:
    game_id, _, _ = _anchored_game(cwd)
    factory = _factory(exists=True)
    code, out = _run(factory)
    assert code == 0, out
    factory.return_value.anchor_batch.assert_not_called()
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "1 still on the ledger, 0 gone" in out
    assert "Nothing to anchor again" in out


def test_a_round_the_ledger_gave_no_answer_for_is_left_alone(cwd: Path) -> None:
    game_id, _, _ = _anchored_game(cwd)
    factory = _factory(exists=None)
    code, out = _run(factory)
    assert code == 1
    factory.return_value.anchor_batch.assert_not_called()
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "The ledger gave no answer for: 1" in out
    assert "Nothing to anchor again" not in out


def test_only_the_lost_rounds_of_a_game_are_sent(cwd: Path) -> None:
    game_id, proof, _ = _anchored_game(cwd, "TXGONE")
    final_hash = _add_final_proof(game_id, proof, "TXKEPT")
    record_anchors(game_id, {"1": "TXKEPT"})
    record_anchors(game_id, {"FINAL": "TXGONE"})
    factory = _factory(exists={"TXGONE": False, "TXKEPT": True})
    code, out = _run(factory)
    assert code == 0, out
    (rounds, _), _ = factory.return_value.anchor_batch.call_args
    assert [(r["round_key"], r["envelope_hash"]) for r in rounds] == [("FINAL", final_hash)]
    assert _recorded(game_id) == {"1": "TXKEPT", "FINAL": "TXNEW"}
    assert "FINAL: TXNEW" in out


def test_rounds_sharing_one_transaction_ask_the_ledger_once(cwd: Path) -> None:
    game_id, proof, _ = _anchored_game(cwd)
    _add_final_proof(game_id, proof, "TXOLD")
    factory = _factory(exists=False)
    code, out = _run(factory)
    assert code == 0, out
    factory.return_value.tx_exists.assert_called_once_with("TXOLD")
    assert _recorded(game_id) == {"1": "TXNEW", "FINAL": "TXNEW"}
    assert "2 rounds anchored again" in out


def test_no_recorded_anchors_is_a_no_op(cwd: Path) -> None:
    _seed_game(cwd)
    factory = _factory(exists=False)
    code, out = _run(factory)
    assert code == 0, out
    factory.assert_not_called()
    assert "No anchored rounds to check" in out


# ── what is never sent ────────────────────────────────────────────────


def test_a_changed_proof_is_not_anchored_again(cwd: Path) -> None:
    game_id, proof, _ = _anchored_game(cwd)
    data = json.loads(proof.read_text(encoding="utf-8"))
    data["rng_seed"] = 999
    proof.write_text(json.dumps(data), encoding="utf-8")
    factory = _factory(exists=False)
    code, out = _run(factory)
    assert code == 1
    factory.return_value.anchor_batch.assert_not_called()
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "No valid local proof for: 1" in out


def test_a_round_with_no_proof_is_left_out_and_the_rest_are_sent(cwd: Path) -> None:
    game_id, _, _ = _anchored_game(cwd)
    record_anchors(game_id, {"7": "TXOLD"})
    (proofs_dir(game_id) / "broken.proof.json").write_text("{not json", encoding="utf-8")
    (proofs_dir(game_id) / "list.proof.json").write_text("[]", encoding="utf-8")
    factory = _factory(exists=False)
    code, out = _run(factory)
    assert code == 1
    (rounds, _), _ = factory.return_value.anchor_batch.call_args
    assert [r["round_key"] for r in rounds] == ["1"]
    assert _recorded(game_id) == {"1": "TXNEW", "7": "TXOLD"}
    assert "No valid local proof for: 7" in out
    assert "1 round anchored again" in out


def test_a_game_with_no_proofs_folder_sends_nothing(cwd: Path) -> None:
    game_id = _seed_game(cwd)
    record_anchors(game_id, {"1": "TXOLD"})
    factory = _factory(exists=False)
    code, out = _run(factory)
    assert code == 1
    factory.return_value.anchor_batch.assert_not_called()
    assert "No valid local proof for: 1" in out


def test_no_wallet_sends_nothing(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    game_id, _, _ = _anchored_game(cwd)
    monkeypatch.delenv("XRPL_SEED")
    factory = _factory(exists=False)
    code, out = _run(factory)
    assert code == 1
    factory.return_value.anchor_batch.assert_not_called()
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "sov wallet" in out


# ── failures ──────────────────────────────────────────────────────────


def test_a_failed_send_keeps_the_old_record(cwd: Path) -> None:
    game_id, _, _ = _anchored_game(cwd)
    factory = _factory(exists=False)
    factory.return_value.anchor_batch.side_effect = RuntimeError("actNotFound")
    code, out = _run(factory)
    assert code == 1
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "Anchor submission failed: actNotFound" in out
    assert "anchored again on XRPL" not in out


def test_a_send_that_returns_no_txid_is_a_failure(cwd: Path) -> None:
    game_id, _, _ = _anchored_game(cwd)
    factory = _factory(exists=False)
    factory.return_value.anchor_batch.return_value = []
    code, out = _run(factory)
    assert code == 1
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "anchor_batch returned no txids" in out


def test_a_later_chunk_failing_keeps_the_earlier_chunks_txid(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sov_transport.xrpl_internals._MAX_MEMOS_PER_TX", 1)
    game_id, proof, _ = _anchored_game(cwd)
    _add_final_proof(game_id, proof, "TXOLD")
    factory = _factory(exists=False)
    factory.return_value.anchor_batch.side_effect = [["TXNEW1"], RuntimeError("dropped")]
    code, out = _run(factory)
    assert code == 1
    assert _recorded(game_id) == {"1": "TXNEW1", "FINAL": "TXOLD"}
    assert "Round 1: TXNEW1" in out
    assert "Anchor submission failed: dropped" in out


def test_a_ledger_that_cannot_be_asked_is_a_failed_lookup(cwd: Path) -> None:
    game_id, _, _ = _anchored_game(cwd)
    factory = _factory(exists=False)
    factory.return_value.tx_exists.side_effect = RuntimeError("xrpl-py is not installed")
    code, out = _run(factory)
    assert code == 1
    factory.return_value.anchor_batch.assert_not_called()
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "xrpl-py is not installed" in out


# ── the surface ───────────────────────────────────────────────────────


def test_reanchor_takes_no_proof_file(cwd: Path) -> None:
    _, proof, _ = _anchored_game(cwd)
    factory = _factory(exists=False)
    code, _ = _run(factory, str(proof))
    assert code == 2
    factory.assert_not_called()


def test_after_a_reset_the_output_says_the_old_wallet_is_gone(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _anchored_game(cwd)
    _, before = _run(_factory(exists=False))
    assert "The wallet from before it is gone too" not in before

    monkeypatch.setattr("sov_transport.resets._now", lambda: AFTER_RESET)
    code, after = _run(_factory(exists=False, new_txid="TXNEW2"))
    assert code == 0, after
    assert "Testnet was reset on 2026-11-25" in after
    assert "The wallet from before it is gone too" in after
    assert "sov wallet" in after


def test_reanchor_uses_the_chosen_network(cwd: Path) -> None:
    from sov_transport.xrpl import XRPLNetwork

    _anchored_game(cwd)
    factory = _factory(exists=False)
    code, out = _run(factory, "--network", "devnet")
    assert code == 0, out
    assert factory.call_args.kwargs["network"] == XRPLNetwork.DEVNET
    assert "anchored again on XRPL devnet" in out


def test_plain_anchor_still_ignores_an_anchored_round(cwd: Path) -> None:
    """Why --reanchor exists: the normal flush never re-sends a recorded round."""
    game_id, _, _ = _anchored_game(cwd)
    factory = _factory(exists=False)
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--checkpoint"])
    assert result.exit_code == 0, result.output
    factory.return_value.anchor_batch.assert_not_called()
    assert _recorded(game_id) == {"1": "TXOLD"}
    assert "No pending anchors" in _flat(result.output)


def test_the_help_and_the_reset_hint_name_the_command() -> None:
    result = runner.invoke(app, ["anchor", "--help"])
    assert result.exit_code == 0
    assert "--reanchor" in result.output
    hint = anchor_reset_error("Testnet was reset on 2026-11-25", "https://x.example").hint
    assert "`sov anchor --reanchor`" in hint

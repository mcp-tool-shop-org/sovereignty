"""Tests for the v2.1 ``sov anchor`` CLI surface.

Covers:

* `sov anchor` with empty pending → exit 0, "no pending" message.
* `sov anchor` mid-game with pending but no `--checkpoint` → exit 1 with hint.
* `sov anchor --checkpoint` mid-game flushes pending via `transport.anchor_batch`.
* `sov anchor` post-game-end flushes pending.
* `sov anchor <proof_file>` (legacy) emits ``DeprecationWarning``.
* `sov anchor --network mainnet` constructs the transport with MAINNET.
* `sov anchor --network bogus` exits 1 with structured INVALID_NETWORK.
* Network precedence: env var alone → DEVNET; env var + flag → flag wins.

Tests stub the bridge layer at the import boundary
(`sov_transport.xrpl.XRPLTransport`) so we exercise the CLI's flow without
hitting the network or even importing xrpl-py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sov_cli.main import app
from sov_engine.io_utils import (
    active_game_pointer_path,
    add_pending_anchor,
    game_dir,
    pending_anchors_path,
    proofs_dir,
    rng_seed_file,
    state_file,
)

runner = CliRunner()

_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_FINAL = "f" * 64
_TEST_SEED = "sEdXXXXXXXXXXXXXXXXXXXXXXX"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_game(
    cwd: Path,
    *,
    seed: int = 42,
    players: list[str] | None = None,
    game_over: bool = False,
) -> str:
    """Write a minimal active game under ``cwd/.sov/``.

    Returns the resolved game-id (``f"s{seed}"``).
    """
    from sov_engine.rules.campfire import new_game
    from sov_engine.serialize import canonical_json, game_state_snapshot

    players = players or ["Alice", "Bob"]
    state, _ = new_game(seed, players)
    game_id = f"s{seed}"
    (cwd / ".sov").mkdir(parents=True, exist_ok=True)
    game_dir(game_id).mkdir(parents=True, exist_ok=True)

    # Manually flip game_over for end-of-game test cases. Snapshot serializer
    # picks up the field; we don't mutate other state.
    if game_over:
        state.game_over = True

    snapshot = game_state_snapshot(state)
    state_file(game_id).write_text(
        canonical_json(snapshot),
        encoding="utf-8",
        newline="\n",
    )
    rng_seed_file(game_id).write_text(str(seed), encoding="utf-8")
    active_game_pointer_path().write_text(game_id, encoding="utf-8")
    return game_id


def _seed_proof_file(game_id: str, round_num: int, envelope_hash: str) -> Path:
    """Write a minimal v2 proof file under .sov/games/<game_id>/proofs/."""
    pdir = proofs_dir(game_id)
    pdir.mkdir(parents=True, exist_ok=True)
    proof_path = pdir / f"round_{round_num:02d}.proof.json"
    proof_path.write_text(
        json.dumps(
            {
                "proof_version": 2,
                "game_id": game_id,
                "round": round_num,
                "ruleset": "campfire_v1",
                "rng_seed": 42,
                "timestamp_utc": "2026-05-01T00:00:00Z",
                "players": [],
                "state": {},
                "envelope_hash": envelope_hash,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return proof_path


def _make_mock_transport_factory(*, txid: str = "BATCHTX") -> MagicMock:
    """Build a factory that returns a mock transport with anchor_batch wired."""
    transport = MagicMock()
    transport.anchor_batch.return_value = txid
    transport.anchor.return_value = txid
    transport.explorer_tx_url.side_effect = lambda t: f"https://explorer.example/{t}"

    factory = MagicMock(return_value=transport)
    return factory


# ---------------------------------------------------------------------------
# `sov anchor` with empty pending
# ---------------------------------------------------------------------------


def test_anchor_empty_pending_exits_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Game complete + nothing pending → exit 0 with "no pending" message."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    _seed_game(tmp_path, game_over=True)

    factory = _make_mock_transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor"])

    assert result.exit_code == 0, f"output: {result.output!r}"
    assert "No pending anchors" in result.output or "no pending" in result.output.lower()
    factory.return_value.anchor_batch.assert_not_called()


# ---------------------------------------------------------------------------
# Mid-game refusal without --checkpoint
# ---------------------------------------------------------------------------


def test_anchor_midgame_without_checkpoint_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Game in progress + pending entries + no --checkpoint → exit 1 with hint."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    game_id = _seed_game(tmp_path, game_over=False)
    add_pending_anchor(game_id, "1", _HASH_A)

    factory = _make_mock_transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor"])

    assert result.exit_code == 1, f"output: {result.output!r}"
    assert "--checkpoint" in result.output
    factory.return_value.anchor_batch.assert_not_called()


# ---------------------------------------------------------------------------
# Mid-game with --checkpoint flushes
# ---------------------------------------------------------------------------


def test_anchor_midgame_with_checkpoint_flushes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`sov anchor --checkpoint` mid-game with pending → calls anchor_batch.

    Asserts:
      - transport.anchor_batch called once with the BatchEntry list.
      - anchors.json updated (round 1 → BATCHTX).
      - pending-anchors.json no longer carries round "1".
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    game_id = _seed_game(tmp_path, game_over=False)
    add_pending_anchor(game_id, "1", _HASH_A)
    add_pending_anchor(game_id, "2", _HASH_B)

    factory = _make_mock_transport_factory(txid="BATCHTX-MID")
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--checkpoint"])

    assert result.exit_code == 0, f"output: {result.output!r}"
    factory.return_value.anchor_batch.assert_called_once()
    # First positional arg is the BatchEntry list.
    call = factory.return_value.anchor_batch.call_args
    rounds_arg = call.args[0] if call.args else call.kwargs.get("rounds")
    assert isinstance(rounds_arg, list)
    assert len(rounds_arg) == 2
    keys = {entry["round_key"] for entry in rounds_arg}
    assert keys == {"1", "2"}

    # anchors.json now has both rounds → same txid.
    from sov_engine.io_utils import anchors_file, read_pending_anchors

    anchors = json.loads(anchors_file(game_id).read_text(encoding="utf-8"))
    assert anchors == {"1": "BATCHTX-MID", "2": "BATCHTX-MID"}

    # Pending cleared.
    assert read_pending_anchors(game_id) == {}


# ---------------------------------------------------------------------------
# Post-game-end flush (no --checkpoint needed)
# ---------------------------------------------------------------------------


def test_anchor_post_game_end_flushes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Game over + pending → flush without --checkpoint."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    game_id = _seed_game(tmp_path, game_over=True)
    add_pending_anchor(game_id, "1", _HASH_A)
    add_pending_anchor(game_id, "FINAL", _HASH_FINAL)

    factory = _make_mock_transport_factory(txid="BATCHTX-END")
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor"])

    assert result.exit_code == 0, f"output: {result.output!r}"
    factory.return_value.anchor_batch.assert_called_once()

    # Pending cleared.
    from sov_engine.io_utils import read_pending_anchors

    assert read_pending_anchors(game_id) == {}


# ---------------------------------------------------------------------------
# Legacy `sov anchor <proof_file>` form — DeprecationWarning
# ---------------------------------------------------------------------------


def test_anchor_legacy_proof_file_emits_deprecation_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`sov anchor <proof_file>` still works but emits DeprecationWarning.

    CliRunner swallows warnings unless we propagate them; we patch
    ``warnings.warn`` to capture the deprecation explicitly.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    game_id = _seed_game(tmp_path, game_over=False)
    proof_path = _seed_proof_file(game_id, 1, _HASH_A)

    factory = _make_mock_transport_factory(txid="LEGACYTX")

    captured_warnings: list[tuple[Any, type]] = []
    real_warn = __import__("warnings").warn

    def _capturing_warn(message: Any, category: type = UserWarning, **kwargs: Any) -> None:
        captured_warnings.append((message, category))
        real_warn(message, category, **kwargs)

    with (
        patch("sov_transport.xrpl.XRPLTransport", factory),
        patch("warnings.warn", side_effect=_capturing_warn),
    ):
        result = runner.invoke(app, ["anchor", str(proof_path)])

    assert result.exit_code == 0, f"output: {result.output!r}"
    # Single anchor (legacy path) → transport.anchor, NOT anchor_batch.
    factory.return_value.anchor.assert_called_once()
    factory.return_value.anchor_batch.assert_not_called()
    # DeprecationWarning was emitted.
    assert any(cat is DeprecationWarning for _, cat in captured_warnings), (
        f"expected DeprecationWarning; got: {captured_warnings!r}"
    )


# ---------------------------------------------------------------------------
# `--network` flag
# ---------------------------------------------------------------------------


def test_anchor_network_mainnet_constructs_transport_with_mainnet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`sov anchor --network mainnet` calls XRPLTransport with MAINNET."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    monkeypatch.delenv("SOV_XRPL_NETWORK", raising=False)
    game_id = _seed_game(tmp_path, game_over=True)
    add_pending_anchor(game_id, "1", _HASH_A)

    factory = _make_mock_transport_factory(txid="MAINTX")
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--network", "mainnet"])

    assert result.exit_code == 0, f"output: {result.output!r}"
    factory.assert_called()
    # Inspect the kwargs passed to XRPLTransport(network=...).
    from sov_transport.xrpl import XRPLNetwork

    last_call = factory.call_args
    network_arg = last_call.kwargs.get("network")
    if network_arg is None and last_call.args:
        network_arg = last_call.args[0]
    assert network_arg == XRPLNetwork.MAINNET


def test_anchor_network_bogus_exits_with_invalid_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`sov anchor --network bogus` exits 1 with INVALID_NETWORK."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    monkeypatch.delenv("SOV_XRPL_NETWORK", raising=False)
    _seed_game(tmp_path, game_over=True)

    factory = _make_mock_transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--network", "bogus"])

    assert result.exit_code == 1, f"output: {result.output!r}"
    # Operator-facing copy — error codes (INVALID_NETWORK) live in --json
    # / structured logs per CLAUDE.md "JSON output schema" decision, not in
    # human stderr. Pin the actionable hint surface instead.
    assert "not a valid XRPL network" in result.output
    assert "testnet, mainnet, devnet" in result.output
    factory.assert_not_called()


# ---------------------------------------------------------------------------
# Network selection precedence (env var + flag)
# ---------------------------------------------------------------------------


def test_anchor_network_env_var_resolves_devnet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``SOV_XRPL_NETWORK=devnet`` + no ``--network`` → DEVNET."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    monkeypatch.setenv("SOV_XRPL_NETWORK", "devnet")
    game_id = _seed_game(tmp_path, game_over=True)
    add_pending_anchor(game_id, "1", _HASH_A)

    factory = _make_mock_transport_factory(txid="DEVTX")
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor"])

    assert result.exit_code == 0, f"output: {result.output!r}"
    from sov_transport.xrpl import XRPLNetwork

    last_call = factory.call_args
    network_arg = last_call.kwargs.get("network")
    if network_arg is None and last_call.args:
        network_arg = last_call.args[0]
    assert network_arg == XRPLNetwork.DEVNET


def test_anchor_network_flag_beats_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``--network testnet`` wins over ``SOV_XRPL_NETWORK=devnet``."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    monkeypatch.setenv("SOV_XRPL_NETWORK", "devnet")
    game_id = _seed_game(tmp_path, game_over=True)
    add_pending_anchor(game_id, "1", _HASH_A)

    factory = _make_mock_transport_factory(txid="TESTTX")
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor", "--network", "testnet"])

    assert result.exit_code == 0, f"output: {result.output!r}"
    from sov_transport.xrpl import XRPLNetwork

    last_call = factory.call_args
    network_arg = last_call.kwargs.get("network")
    if network_arg is None and last_call.args:
        network_arg = last_call.args[0]
    assert network_arg == XRPLNetwork.TESTNET


# ---------------------------------------------------------------------------
# Pending file cleanup invariant: failed batch leaves pending intact
# ---------------------------------------------------------------------------


def test_anchor_failed_batch_keeps_pending_intact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If anchor_batch raises, pending stays — operator retries with `sov anchor`."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    monkeypatch.delenv("SOV_XRPL_NETWORK", raising=False)
    game_id = _seed_game(tmp_path, game_over=True)
    add_pending_anchor(game_id, "1", _HASH_A)
    add_pending_anchor(game_id, "2", _HASH_B)

    factory = MagicMock()
    transport = MagicMock()
    transport.anchor_batch.side_effect = RuntimeError("transient network blip")
    factory.return_value = transport

    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor"])

    assert result.exit_code != 0, f"output: {result.output!r}"

    # Pending stays untouched — operator retries idempotently.
    from sov_engine.io_utils import read_pending_anchors

    pending = read_pending_anchors(game_id)
    assert set(pending.keys()) == {"1", "2"}
    # The pending file is the same path; was not deleted on failure.
    assert pending_anchors_path(game_id).exists()

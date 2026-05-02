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

    # anchors.json now has both rounds → same txid. Stage 7-B amend
    # (CLI-B-003) wraps anchors.json with schema_version; assert through
    # the canonical reader so we test the operator-visible map shape,
    # not the wire format.
    from sov_cli.main import _read_anchors_entries
    from sov_engine.io_utils import anchors_file, read_pending_anchors

    assert _read_anchors_entries(anchors_file(game_id)) == {
        "1": "BATCHTX-MID",
        "2": "BATCHTX-MID",
    }

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

    # Use catch_warnings so the deprecation propagates to the recorder
    # without being promoted to an error by the CI ``-W error`` filter
    # (which converts a re-raised ``warnings.warn`` into a hard exception
    # that CliRunner stuffs into ``result.exception``).
    import warnings

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with patch("sov_transport.xrpl.XRPLTransport", factory):
            result = runner.invoke(app, ["anchor", str(proof_path)])

    assert result.exit_code == 0, f"output: {result.output!r}"
    # Single anchor (legacy path) → transport.anchor, NOT anchor_batch.
    factory.return_value.anchor.assert_called_once()
    factory.return_value.anchor_batch.assert_not_called()
    # DeprecationWarning was emitted.
    assert any(issubclass(w.category, DeprecationWarning) for w in captured), (
        f"expected DeprecationWarning; got: {[w.category for w in captured]!r}"
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


# ---------------------------------------------------------------------------
# Wave-7 regressions
# ---------------------------------------------------------------------------
# Each test below pins one of the Wave-6 audit findings (CLI-002 / CLI-003 /
# CLI-004) so the next refactor doesn't quietly regress the contract.


# CLI-002: legacy single-round anchor must clear the pending entry on success
# so the next batch flush doesn't re-anchor the same round as a duplicate.
def test_anchor_legacy_clears_pending_after_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Legacy ``sov anchor <proof_file>`` clears the pending row on success.

    Without the fix, ``end-round`` queues round N pending, the legacy
    single-round anchor records the txid in ``anchors.json`` AND leaves
    the pending row, and a subsequent batch flush re-anchors round N as
    a duplicate on chain.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    game_id = _seed_game(tmp_path, game_over=False)
    proof_path = _seed_proof_file(game_id, 1, _HASH_A)
    # Simulate the queued pending row that ``end-round`` leaves behind.
    add_pending_anchor(game_id, "1", _HASH_A)
    add_pending_anchor(game_id, "2", _HASH_B)

    from sov_engine.io_utils import read_pending_anchors

    # Sanity: pending starts populated.
    assert set(read_pending_anchors(game_id).keys()) == {"1", "2"}

    # The legacy path emits DeprecationWarning; catch it so the CI
    # ``-W error::DeprecationWarning`` filter doesn't promote it to an
    # exception inside CliRunner.
    import warnings

    factory = _make_mock_transport_factory(txid="LEGACYTX")
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        with patch("sov_transport.xrpl.XRPLTransport", factory):
            result = runner.invoke(app, ["anchor", str(proof_path)])

    assert result.exit_code == 0, f"output: {result.output!r}"
    factory.return_value.anchor.assert_called_once()

    # CLI-002 invariant: round "1" is no longer pending; round "2" is
    # untouched (the legacy path only clears the round it just anchored).
    remaining = read_pending_anchors(game_id)
    assert "1" not in remaining
    assert "2" in remaining


# CLI-003: empty pending must exit 0 even with no wallet seed configured.
def test_anchor_empty_pending_succeeds_without_wallet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`sov anchor` with no pending exits 0 even when XRPL_SEED is unset.

    Spec §5: "`sov anchor` with empty pending → idempotent no-op, info exit,
    no tx submitted." Before the fix, the seed gate fired first and the
    user saw CONFIG_NO_WALLET when they should have seen "no pending".
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    monkeypatch.delenv("SOV_XRPL_NETWORK", raising=False)
    _seed_game(tmp_path, game_over=True)  # no pending, no wallet

    factory = _make_mock_transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["anchor"])

    assert result.exit_code == 0, f"output: {result.output!r}"
    assert "No pending anchors" in result.output or "no pending" in result.output.lower()
    # Crucially: no CONFIG_NO_WALLET surfaced — the wallet gate did NOT fire
    # because the empty-pending fast-path returned first.
    assert "CONFIG_NO_WALLET" not in result.output
    assert "No wallet seed" not in result.output
    factory.return_value.anchor_batch.assert_not_called()
    factory.return_value.anchor.assert_not_called()


# CLI-004: structured ANCHOR_PENDING surfaces in `sov status --json` when
# at least one round is queued in pending-anchors.json.
def test_status_json_emits_anchor_pending_when_pending_nonempty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`sov status --json` embeds ``anchor_pending`` envelope when pending is non-empty.

    The structured shape (``code``, ``message``, ``hint``, ``rounds``)
    matches ``anchor_pending_error`` from ``sov_cli/errors.py``. External
    audit-tier consumers can reason about the failure code without
    parsing prose.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    game_id = _seed_game(tmp_path, game_over=False)
    add_pending_anchor(game_id, "1", _HASH_A)
    add_pending_anchor(game_id, "FINAL", _HASH_FINAL)

    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0, f"output: {result.output!r}"

    payload = json.loads(result.output)
    assert "anchor_pending" in payload
    ap = payload["anchor_pending"]
    assert ap["code"] == "ANCHOR_PENDING"
    # FINAL must sort after numeric rounds — same convention as the
    # rounds[] list and anchors.json.
    assert ap["rounds"] == ["1", "FINAL"]
    # Hint is the locked text from ``anchor_pending_error``.
    assert "sov anchor" in ap["hint"]


def test_status_json_omits_anchor_pending_when_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`sov status --json` omits ``anchor_pending`` when nothing is pending.

    The field is additive — present when there's something to report,
    absent otherwise. Consumers can use ``"anchor_pending" in payload``
    as the discriminator.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    _seed_game(tmp_path, game_over=False)

    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0, f"output: {result.output!r}"

    payload = json.loads(result.output)
    assert "anchor_pending" not in payload

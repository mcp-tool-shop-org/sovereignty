"""Tests for the 3-state ``proof_anchor_status`` (v2.1 §3).

The engine layer (``sov_engine.proof``) composes ANCHORED / PENDING / MISSING
by consulting the local ``pending-anchors.json`` index and deferring to the
transport's pure-chain ``is_anchored_on_chain`` method. Transport stays
free of engine-state coupling; engine owns the 3-state.

State table:

| anchors.json has txid | pending has round_key | chain confirms | Status     |
|-----------------------|-----------------------|----------------|------------|
| yes                   | no                    | yes            | ANCHORED   |
| any                   | yes                   | -              | PENDING    |
| no                    | no                    | -              | MISSING    |
| yes                   | no                    | no             | MISSING    |

PENDING beats ANCHORED when both indexes name the round (race condition
during flush — pending wins so the next ``sov anchor`` retries cleanly).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sov_engine.io_utils import (
    add_pending_anchor,
    anchors_file,
    game_dir,
    proofs_dir,
)

_HASH_A = "a" * 64


def _write_proof_file(game_id: str, round_num: int, envelope_hash: str) -> Path:
    """Stand up a minimal proof file at .sov/games/<game_id>/proofs/round_N.proof.json."""
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


def _write_anchors_json(game_id: str, mapping: dict[str, str]) -> None:
    """Write ``anchors.json`` mapping round-key strings to txids."""
    pdir = proofs_dir(game_id)
    pdir.mkdir(parents=True, exist_ok=True)
    anchors_file(game_id).write_text(
        json.dumps(mapping, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ensure_game_dir(game_id: str) -> None:
    """Create .sov/games/<game-id>/ so subdir helpers can write."""
    game_dir(game_id).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# ANCHORED
# ---------------------------------------------------------------------------


def test_proof_anchor_status_anchored_when_chain_confirms(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """anchors.json + chain confirms → ANCHORED."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    proof_path = _write_proof_file("s42", 1, _HASH_A)
    _write_anchors_json("s42", {"1": "TX-RECORDED"})

    transport = MagicMock()
    transport.is_anchored_on_chain.return_value = True

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.ANCHORED
    transport.is_anchored_on_chain.assert_called_once_with("TX-RECORDED", _HASH_A)


# ---------------------------------------------------------------------------
# PENDING
# ---------------------------------------------------------------------------


def test_proof_anchor_status_pending_when_in_pending_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """pending-anchors.json has the round → PENDING (regardless of anchors.json)."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    proof_path = _write_proof_file("s42", 1, _HASH_A)
    add_pending_anchor("s42", "1", _HASH_A)

    transport = MagicMock()
    # Transport not consulted in PENDING path — set to fail loud if it is.
    transport.is_anchored_on_chain.side_effect = AssertionError(
        "transport should not be consulted when round is PENDING"
    )

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.PENDING


def test_proof_anchor_status_pending_beats_anchored_during_flush_race(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Both indexes name the round → PENDING wins.

    This models the brief window during ``sov anchor`` flush where the txid
    has been written into ``anchors.json`` but the pending row has not yet
    been cleared. PENDING wins so the next ``sov anchor`` invocation
    retries the flush cleanly without skipping the round.
    """
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    proof_path = _write_proof_file("s42", 1, _HASH_A)
    _write_anchors_json("s42", {"1": "TX-MAYBE"})
    add_pending_anchor("s42", "1", _HASH_A)

    transport = MagicMock()

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.PENDING


# ---------------------------------------------------------------------------
# MISSING
# ---------------------------------------------------------------------------


def test_proof_anchor_status_missing_when_no_index_mentions_round(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Neither pending nor anchors.json names the round → MISSING."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    proof_path = _write_proof_file("s42", 1, _HASH_A)
    # No anchors.json, no pending-anchors.json.

    transport = MagicMock()

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.MISSING


def test_proof_anchor_status_missing_on_chain_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """anchors.json has a txid, but ``is_anchored_on_chain`` returns False
    → MISSING (the recorded txid does not actually carry the expected hash;
    likely the operator's anchors.json drifted from the chain).
    """
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    proof_path = _write_proof_file("s42", 1, _HASH_A)
    _write_anchors_json("s42", {"1": "TX-DRIFTED"})

    transport = MagicMock()
    transport.is_anchored_on_chain.return_value = False

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.MISSING

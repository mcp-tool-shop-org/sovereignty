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

    from sov_transport.xrpl_internals import ChainLookupResult

    transport = MagicMock()
    # Wave 6 BRIDGE-004: is_anchored_on_chain returns ChainLookupResult enum,
    # not bool. Mock with the FOUND variant so engine's strict-identity check
    # against ChainLookupResult.FOUND succeeds.
    transport.is_anchored_on_chain.return_value = ChainLookupResult.FOUND

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

    from sov_transport.xrpl_internals import ChainLookupResult

    transport = MagicMock()
    # NOT_FOUND specifically — the recorded txid exists but doesn't carry
    # the expected hash. LOOKUP_FAILED would model a transient network
    # error, which a separate test should pin if needed.
    transport.is_anchored_on_chain.return_value = ChainLookupResult.NOT_FOUND

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.MISSING


# ---------------------------------------------------------------------------
# anchors.json wrapper migration (Stage 7-B BACKEND-B-002)
# ---------------------------------------------------------------------------


def test_anchors_json_bare_dict_migrates_to_wrapped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A pre-Stage-7-B ``anchors.json`` written as a bare ``{round: txid}``
    dict is read cleanly AND rewritten in wrapped form on first access.

    Pins the migrate-on-read backward-compat path from BACKEND-B-002 — the
    wrapper rollout cannot break operators with existing anchors.json files
    on disk."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")

    # Bare-dict shape (pre-Stage-7-B writers).
    bare_path = anchors_file("s42")
    bare_path.parent.mkdir(parents=True, exist_ok=True)
    bare_path.write_text(
        json.dumps({"1": "TX-LEGACY", "FINAL": "TX-FINAL"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    proof_path = _write_proof_file("s42", 1, _HASH_A)

    from sov_transport.xrpl_internals import ChainLookupResult

    transport = MagicMock()
    transport.is_anchored_on_chain.return_value = ChainLookupResult.FOUND

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.ANCHORED

    # Disk shape after the read: wrapped, with schema_version + anchors.
    rewritten = json.loads(bare_path.read_text(encoding="utf-8"))
    assert rewritten == {
        "schema_version": 1,
        "anchors": {"1": "TX-LEGACY", "FINAL": "TX-FINAL"},
    }


def test_anchors_json_wrapped_form_round_trips(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A post-Stage-7-B ``anchors.json`` (wrapped) reads cleanly with no
    rewrite. Pins that the migrate-on-read path is one-shot."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")

    wrapped_path = anchors_file("s42")
    wrapped_path.parent.mkdir(parents=True, exist_ok=True)
    wrapped_payload = {
        "schema_version": 1,
        "anchors": {"1": "TX-WRAPPED"},
    }
    wrapped_path.write_text(
        json.dumps(wrapped_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Capture mtime so we can assert the wrapped file is NOT rewritten.
    pre_read_mtime = wrapped_path.stat().st_mtime_ns

    proof_path = _write_proof_file("s42", 1, _HASH_A)

    from sov_transport.xrpl_internals import ChainLookupResult

    transport = MagicMock()
    transport.is_anchored_on_chain.return_value = ChainLookupResult.FOUND

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.ANCHORED

    # Wrapped files don't get re-rewritten on read.
    assert wrapped_path.stat().st_mtime_ns == pre_read_mtime
    after = json.loads(wrapped_path.read_text(encoding="utf-8"))
    assert after == wrapped_payload


def test_anchors_json_unknown_schema_version_treated_as_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A forward-bumped ``anchors.json`` (schema_version newer than this
    binary supports) yields MISSING — the read-side fail-closed posture."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")

    future_path = anchors_file("s42")
    future_path.parent.mkdir(parents=True, exist_ok=True)
    future_path.write_text(
        json.dumps(
            {"schema_version": 999, "anchors": {"1": "TX-FUTURE"}},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    proof_path = _write_proof_file("s42", 1, _HASH_A)

    transport = MagicMock()

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.MISSING
    # Transport should never be consulted — there's no recorded txid to verify.
    transport.is_anchored_on_chain.assert_not_called()

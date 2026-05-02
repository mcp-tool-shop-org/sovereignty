"""Regression test for BACKEND-C-003 — _load_proof structural errors carry hints.

Stage 8-C amend (Wave 11) lifted ``_load_proof``'s structural-error
messages so each names a recovery action. DISPATCH target A: every
engine error names a recovery action so the user surface (uncaught
traceback or wrapped SovError fallback) is actionable rather than just
descriptive.

Also pins BACKEND-C-004: error messages render the proof path relative
to the ``.sov/`` ancestor when one exists, falling back to the supplied
path otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sov_cli.errors import ProofFormatError
from sov_engine.proof import _load_proof, _render_proof_path
from sov_engine.serialize import canonical_json


def _write(path: Path, payload: Any) -> None:
    if isinstance(payload, (dict, list)):
        path.write_text(canonical_json(payload), encoding="utf-8", newline="\n")
    else:
        path.write_text(str(payload), encoding="utf-8")


def test_load_proof_unparseable_json_message_names_recovery(tmp_path: Path) -> None:
    """Garbage JSON: error names ``sov end-round`` regenerate path."""
    path = tmp_path / "garbage.proof.json"
    path.write_text("not json{", encoding="utf-8")

    with pytest.raises(ProofFormatError) as exc_info:
        _load_proof(path)
    rendered = str(exc_info.value)
    assert "sov end-round" in rendered, (
        f"unparseable-JSON error must name recovery command; got: {rendered!r}"
    )


def test_load_proof_non_object_message_names_recovery(tmp_path: Path) -> None:
    """Top-level non-object: error names truncation/corruption + recovery."""
    path = tmp_path / "list.proof.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    with pytest.raises(ProofFormatError) as exc_info:
        _load_proof(path)
    rendered = str(exc_info.value)
    assert "sov end-round" in rendered, (
        f"non-object error must name recovery command; got: {rendered!r}"
    )


def test_load_proof_unknown_proof_version_message_names_recovery(tmp_path: Path) -> None:
    """Unknown proof_version: error names upgrade + regenerate paths."""
    path = tmp_path / "future.proof.json"
    _write(
        path,
        {
            "proof_version": 99,
            "round": 1,
            "game_id": "s42",
            "envelope_hash": "0" * 64,
        },
    )

    with pytest.raises(ProofFormatError) as exc_info:
        _load_proof(path)
    rendered = str(exc_info.value)
    assert "sov end-round" in rendered or "Upgrade sovereignty" in rendered, (
        f"unknown-version error must name recovery command; got: {rendered!r}"
    )


def test_load_proof_missing_field_message_names_recovery(tmp_path: Path) -> None:
    """Missing required field: error names ``sov end-round`` regenerate."""
    path = tmp_path / "incomplete.proof.json"
    _write(
        path,
        {
            "proof_version": 2,
            "round": 1,
            "game_id": "s42",
            # Notably: NO envelope_hash key.
        },
    )

    with pytest.raises(ProofFormatError) as exc_info:
        _load_proof(path)
    rendered = str(exc_info.value)
    assert "envelope_hash" in rendered, (
        f"missing-field error must name the field; got: {rendered!r}"
    )
    assert "sov end-round" in rendered, (
        f"missing-field error must name recovery command; got: {rendered!r}"
    )


def test_load_proof_envelope_hash_wrong_type_names_recovery(tmp_path: Path) -> None:
    """envelope_hash with non-string type: error names ``sov end-round``."""
    path = tmp_path / "wrong_type.proof.json"
    _write(
        path,
        {
            "proof_version": 2,
            "round": 1,
            "game_id": "s42",
            "envelope_hash": 12345,  # int, not str
        },
    )

    with pytest.raises(ProofFormatError) as exc_info:
        _load_proof(path)
    rendered = str(exc_info.value)
    assert "envelope_hash" in rendered
    assert "sov end-round" in rendered, (
        f"wrong-type error must name recovery command; got: {rendered!r}"
    )


# ---------------------------------------------------------------------------
# BACKEND-C-004 — relative-from-.sov path rendering
# ---------------------------------------------------------------------------


def test_render_proof_path_collapses_under_dot_sov(tmp_path: Path) -> None:
    """When the path lives under a ``.sov/`` ancestor, render it relative
    to the ancestor's parent so support-bundle messages don't leak the
    operator's home dir."""
    sov_root = tmp_path / ".sov"
    proof_path = sov_root / "games" / "s42" / "proofs" / "round_001.proof.json"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text("{}", encoding="utf-8")

    rendered = _render_proof_path(proof_path)
    # The rendered form starts at .sov/, not at tmp_path.
    assert rendered.endswith("round_001.proof.json")
    assert ".sov" in rendered
    assert str(tmp_path) not in rendered, (
        f"rendered path must not include the absolute prefix; got: {rendered!r}"
    )


def test_render_proof_path_falls_back_to_supplied_path(tmp_path: Path) -> None:
    """When the path does not live under a ``.sov/`` ancestor, the
    supplied path renders unchanged (best-effort fallback)."""
    proof_path = tmp_path / "loose.proof.json"
    proof_path.write_text("{}", encoding="utf-8")

    rendered = _render_proof_path(proof_path)
    # Either the absolute path or the str() of the input is acceptable;
    # the contract is "no exception, returns something usable".
    assert rendered, "rendering must return a non-empty string"
    assert "loose.proof.json" in rendered

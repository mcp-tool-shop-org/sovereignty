"""JOB-012: engine, CLI, and daemon share one anchors.json shape.

Canonical on-disk wrap is ``{"schema_version": 1, "entries": {round: txid}}``.
A round recorded by ``sov anchor`` must not show as missing on
``GET /games/{id}/anchor-status/{round}``, and a daemon flush must not
erase earlier txids.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sov_engine.io_utils import anchors_file, game_dir, proofs_dir

_HASH_A = "a" * 64
_TX_CLI = "TX-FROM-CLI"
_TX_DAEMON = "TX-FROM-DAEMON"


def _ensure_game_dir(game_id: str) -> None:
    game_dir(game_id).mkdir(parents=True, exist_ok=True)


def _write_proof_file(game_id: str, round_num: int, envelope_hash: str) -> Path:
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


def _write_cli_anchors(game_id: str, entries: dict[str, str]) -> Path:
    path = anchors_file(game_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"schema_version": 1, "entries": entries},
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_cli_entries_shape_is_visible_to_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CLI wrap uses ``entries``; engine used to look at ``anchors`` and
    report MISSING. Shared reader must see the CLI txid."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    _write_cli_anchors("s42", {"1": _TX_CLI})
    proof_path = _write_proof_file("s42", 1, _HASH_A)

    from sov_transport.xrpl_internals import ChainLookupResult

    transport = MagicMock()
    transport.is_anchored_on_chain.return_value = ChainLookupResult.FOUND

    from sov_engine.proof import AnchorStatus, proof_anchor_status

    status = proof_anchor_status(proof_path, transport)
    assert status == AnchorStatus.ANCHORED


def test_record_anchors_merges_without_dropping_prior_rounds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Shared writer overlays new rounds and keeps earlier txids."""
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    _write_cli_anchors("s42", {"1": _TX_CLI})

    from sov_engine.proof import record_anchors

    record_anchors("s42", {"2": _TX_DAEMON})

    raw = json.loads(anchors_file("s42").read_text(encoding="utf-8"))
    assert raw == {
        "schema_version": 1,
        "entries": {"1": _TX_CLI, "2": _TX_DAEMON},
    }


def test_daemon_read_sees_cli_entries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pytest.importorskip("starlette", reason="daemon extra not installed")
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    _write_cli_anchors("s42", {"1": _TX_CLI, "FINAL": "TX-FINAL"})

    from sov_daemon.server import _read_anchors

    assert _read_anchors("s42") == {"1": _TX_CLI, "FINAL": "TX-FINAL"}


def test_daemon_record_does_not_erase_cli_txids_or_write_bare_map(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A daemon flush used to read a wrapped CLI file as empty, then write
    a bare map. Shared writer must keep round 1 and persist ``entries``."""
    pytest.importorskip("starlette", reason="daemon extra not installed")
    monkeypatch.chdir(tmp_path)
    _ensure_game_dir("s42")
    _write_cli_anchors("s42", {"1": _TX_CLI})

    from sov_daemon.server import _record_anchors

    _record_anchors("s42", {"2": _TX_DAEMON})

    raw = json.loads(anchors_file("s42").read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert "entries" in raw
    assert "anchors" not in raw
    assert raw["entries"] == {"1": _TX_CLI, "2": _TX_DAEMON}

_FIXED_TOKEN = "test-token-fixed-for-tests"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}


def _seed_daemon_game(root: Path, game_id: str = "s42") -> None:
    game_dir_path = root / ".sov" / "games" / game_id
    proofs = game_dir_path / "proofs"
    proofs.mkdir(parents=True, exist_ok=True)
    (game_dir_path / "state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "game_id": game_id,
                "round": 0,
                "ruleset": "campfire_v1",
                "players": ["A", "B"],
                "rng_seed": "42",
            }
        ),
        encoding="utf-8",
    )
    (proofs / "round-1.json").write_text(
        json.dumps(
            {
                "proof_version": 2,
                "game_id": game_id,
                "round": 1,
                "envelope_hash": _HASH_A,
            }
        ),
        encoding="utf-8",
    )
    (game_dir_path / "pending-anchors.json").write_text(
        json.dumps({"pending": []}), encoding="utf-8"
    )


async def test_daemon_anchor_status_sees_cli_recorded_round(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GET anchor-status for a round already in CLI ``entries`` is not missing."""
    httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
    pytest.importorskip("starlette", reason="daemon extra not installed")
    from sov_daemon.server import DaemonConfig, build_app

    monkeypatch.chdir(tmp_path)
    _seed_daemon_game(tmp_path, "s42")
    _write_cli_anchors("s42", {"1": _TX_CLI})
    app = build_app(DaemonConfig(network="testnet", readonly=True, token=_FIXED_TOKEN))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/anchor-status/1", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body.get("anchor_status") == "anchored"
    assert body.get("txid") == _TX_CLI

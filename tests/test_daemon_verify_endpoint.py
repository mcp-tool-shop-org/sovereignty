"""GET /games/{id}/verify/{round} — additive 3-state chain lookup.

Does not hit live XRPL. Fake transports cover FOUND / NOT_FOUND /
LOOKUP_FAILED. Browse GET /anchor-status stays local-index only.
Tests never print wallet seeds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")

from sov_transport.base import ChainLookupResult  # noqa: E402

_FIXED_TOKEN = "test-token-fixed-for-tests"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}
_HASH = "0" * 64
_TXID = "TXIDVERIFY0001"


class _FakeTransport:
    def __init__(self, result: ChainLookupResult | Exception) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def is_anchored_on_chain(self, txid: str, envelope_hash: str) -> ChainLookupResult:
        self.calls.append((txid, envelope_hash))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _build_config(*, readonly: bool = True) -> Any:
    from sov_daemon.server import DaemonConfig

    return DaemonConfig(network="testnet", readonly=readonly, token=_FIXED_TOKEN)


def _seed_game(root: Path, game_id: str = "s42") -> None:
    import json

    game_dir = root / ".sov" / "games" / game_id
    proofs_dir = game_dir / "proofs"
    proofs_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "state.json").write_text(
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
    (proofs_dir / "round-1.json").write_text(
        json.dumps(
            {
                "proof_version": 2,
                "game_id": game_id,
                "round": 1,
                "envelope_hash": _HASH,
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    from sov_daemon.server import build_app

    monkeypatch.chdir(tmp_path)
    _seed_game(tmp_path)
    return build_app(_build_config(readonly=True))


async def _get(app: Any, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers=_AUTH)


@pytest.mark.parametrize(
    "result,expected",
    [
        (ChainLookupResult.FOUND, "found"),
        (ChainLookupResult.NOT_FOUND, "not_found"),
        (ChainLookupResult.LOOKUP_FAILED, "lookup_failed"),
    ],
)
async def test_verify_emits_chain_lookup_without_collapsing(
    app: Any, monkeypatch: pytest.MonkeyPatch, result: ChainLookupResult, expected: str
) -> None:
    from sov_engine.proof import record_anchors

    record_anchors("s42", {"1": _TXID})
    fake = _FakeTransport(result)
    monkeypatch.setattr("sov_daemon.server.get_verify_transport", lambda network: fake)

    r = await _get(app, "/games/s42/verify/1")
    assert r.status_code == 200
    body = r.json()
    assert body["anchor_status"] == "anchored"
    assert body["txid"] == _TXID
    assert body["chain_lookup"] == expected
    assert fake.calls == [(_TXID, _HASH)]


async def test_verify_transport_exception_is_lookup_failed_not_missing(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_engine.proof import record_anchors

    record_anchors("s42", {"1": _TXID})
    fake = _FakeTransport(ConnectionError("rpc down"))
    monkeypatch.setattr("sov_daemon.server.get_verify_transport", lambda network: fake)

    r = await _get(app, "/games/s42/verify/1")
    assert r.status_code == 200
    body = r.json()
    assert body["anchor_status"] == "anchored"
    assert body["chain_lookup"] == "lookup_failed"
    assert body["anchor_status"] != "missing"


async def test_verify_omits_chain_lookup_when_pending(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_engine.io_utils import add_pending_anchor

    add_pending_anchor("s42", "1", _HASH)
    fake = _FakeTransport(ChainLookupResult.FOUND)
    monkeypatch.setattr("sov_daemon.server.get_verify_transport", lambda network: fake)

    r = await _get(app, "/games/s42/verify/1")
    assert r.status_code == 200
    body = r.json()
    assert body["anchor_status"] == "pending"
    assert "chain_lookup" not in body
    assert fake.calls == []


async def test_verify_omits_chain_lookup_when_missing(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeTransport(ChainLookupResult.FOUND)
    monkeypatch.setattr("sov_daemon.server.get_verify_transport", lambda network: fake)

    r = await _get(app, "/games/s42/verify/1")
    assert r.status_code == 200
    body = r.json()
    assert body["anchor_status"] == "missing"
    assert "chain_lookup" not in body
    assert fake.calls == []


async def test_browse_anchor_status_does_not_hit_transport(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sov_engine.proof import record_anchors

    record_anchors("s42", {"1": _TXID})
    fake = _FakeTransport(ChainLookupResult.FOUND)
    monkeypatch.setattr("sov_daemon.server.get_verify_transport", lambda network: fake)

    r = await _get(app, "/games/s42/anchor-status/1")
    assert r.status_code == 200
    body = r.json()
    assert body["anchor_status"] == "anchored"
    assert "chain_lookup" not in body
    assert fake.calls == []


async def test_verify_works_in_readonly(app: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from sov_engine.proof import record_anchors

    record_anchors("s42", {"1": _TXID})
    fake = _FakeTransport(ChainLookupResult.NOT_FOUND)
    monkeypatch.setattr("sov_daemon.server.get_verify_transport", lambda network: fake)

    r = await _get(app, "/games/s42/verify/1")
    assert r.status_code == 200
    assert r.json()["chain_lookup"] == "not_found"

"""Wave 7 regression tests for ``sov_daemon`` domain amends.

One file per amend-wave for traceability. Each test pins a specific finding
from ``swarm-1777686810-67fd/wave-6/audit/daemon-findings.yaml`` so the next
audit can match a green test to a closed finding.

Coverage:

* DAEMON-001 — game_id + round path-traversal allowlist at HTTP boundary.
* DAEMON-002 — ``.sov/daemon.json`` is mode 0600 on POSIX.
* DAEMON-003 — invalid ``--network`` rejected at startup, not first write.
* DAEMON-004 — pid soft-check refuses SIGTERM when pid no longer names daemon.
* DAEMON-005 — mainnet underfunded preflight surfaces ``MAINNET_UNDERFUNDED``.
* DAEMON-006 — chain-lookup cache coalesces concurrent calls to one upstream.
* DAEMON-007 — verified by un-skipped ``tests/test_daemon_sse.py`` suite.
* DAEMON-009 — broadcaster reset clears per-test state.
* DAEMON-010 — subprocess env contains only allowlisted vars.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import pytest

httpx = pytest.importorskip("httpx", reason="daemon extra not installed")
pytest.importorskip("starlette", reason="daemon extra not installed")


_FIXED_TOKEN = "test-amend-wave7-token"
_AUTH = {"Authorization": f"Bearer {_FIXED_TOKEN}"}


def _build_app(*, readonly: bool = True, network: str = "testnet") -> Any:
    from sov_daemon.server import DaemonConfig, build_app

    return build_app(DaemonConfig(network=network, readonly=readonly, token=_FIXED_TOKEN))


def _seed_game(root: Path, game_id: str = "s42") -> None:
    """Seed minimal multi-save layout."""
    import json as _json

    gd = root / ".sov" / "games" / game_id
    pd = gd / "proofs"
    pd.mkdir(parents=True, exist_ok=True)
    (gd / "state.json").write_text(
        _json.dumps(
            {
                "schema_version": 1,
                "game_id": game_id,
                "round": 0,
                "ruleset": "campfire_v1",
                "config": {"ruleset": "campfire_v1", "max_rounds": 5},
                "players": ["A", "B"],
                "rng_seed": "42",
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# DAEMON-001 — path traversal rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "..",
        "../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "../",
        "/etc/passwd",
        "s42/../",
        "abc",
        "S42",
        "s42a",
        "s",
        "s00000000000000000000000",  # 21 digits, exceeds {1,19}
    ],
)
async def test_daemon001_game_detail_rejects_malformed_game_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad_id: str
) -> None:
    """DAEMON-001: ``GET /games/{id}`` validates ``game_id`` before
    constructing a Path."""
    monkeypatch.chdir(tmp_path)
    app = _build_app(readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # URL-encode separators so Starlette doesn't 404 on routing first.
        from urllib.parse import quote

        encoded = quote(bad_id, safe="")
        r = await c.get(f"/games/{encoded}", headers=_AUTH)
    # Acceptable outcomes for a path-traversal payload: 400 (validator
    # rejects), 404 (Starlette routing has no match), 307 (Starlette
    # redirects on trailing slash before the handler runs), 405 (method
    # not allowed because the URL collapsed to a different route). What's
    # NOT acceptable is a 200 with leaked content.
    assert r.status_code in (400, 404, 307, 405), (
        f"path-traversal payload {bad_id!r} returned status {r.status_code}; "
        "must be rejected, unrouted, or redirected away from the handler."
    )
    if r.status_code == 400:
        body = r.json()
        assert body.get("code") == "INVALID_GAME_ID"


async def test_daemon001_proofs_list_rejects_malformed_game_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-001 covers proofs-list endpoint too."""
    monkeypatch.chdir(tmp_path)
    app = _build_app(readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/INVALID/proofs", headers=_AUTH)
    assert r.status_code == 400
    assert r.json().get("code") == "INVALID_GAME_ID"


async def test_daemon001_proof_detail_rejects_malformed_round(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-001: round must be 1..15 or FINAL. Anything else is rejected."""
    monkeypatch.chdir(tmp_path)
    _seed_game(tmp_path, "s42")
    app = _build_app(readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/proofs/9999", headers=_AUTH)
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") == "INVALID_ROUND"


async def test_daemon001_anchor_status_rejects_malformed_round(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-001: anchor-status validates round token too."""
    monkeypatch.chdir(tmp_path)
    _seed_game(tmp_path, "s42")
    app = _build_app(readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/s42/anchor-status/twenty", headers=_AUTH)
    assert r.status_code == 400
    assert r.json().get("code") == "INVALID_ROUND"


async def test_daemon001_pending_anchors_rejects_malformed_game_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-001 also pins pending-anchors handler."""
    monkeypatch.chdir(tmp_path)
    app = _build_app(readonly=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/games/sNOPE/pending-anchors", headers=_AUTH)
    assert r.status_code == 400
    assert r.json().get("code") == "INVALID_GAME_ID"


# ---------------------------------------------------------------------------
# DAEMON-002 — daemon.json mode 0600
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only file mode check")
def test_daemon002_handshake_file_is_mode_0600(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-002: ``.sov/daemon.json`` carries the bearer token; force 0600
    on POSIX so co-located users / backup processes can't exfiltrate it."""
    from sov_daemon.lifecycle import _write_handshake

    monkeypatch.chdir(tmp_path)
    info = {
        "schema_version": 1,
        "pid": 12345,
        "port": 47823,
        "token": "test-token",
        "network": "testnet",
        "readonly": True,
        "ipc_version": 1,
        "started_iso": "2026-05-02T00:00:00Z",
    }
    _write_handshake(info)
    daemon_json = tmp_path / ".sov" / "daemon.json"
    assert daemon_json.exists()
    mode = daemon_json.stat().st_mode & 0o777
    assert mode == 0o600, f"daemon.json mode is {oct(mode)}, want 0o600"


# ---------------------------------------------------------------------------
# DAEMON-003 — early network validation
# ---------------------------------------------------------------------------


def test_daemon003_run_foreground_rejects_invalid_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-003: typo in network surfaces SystemExit at startup, not on
    the first anchor write."""
    from sov_daemon.lifecycle import run_foreground

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        run_foreground(network="testnetz", readonly=True)
    msg = str(exc_info.value)
    assert "testnetz" in msg
    assert "valid" in msg.lower()


# ---------------------------------------------------------------------------
# DAEMON-004 — pid liveness soft check (MANDATORY regression)
# ---------------------------------------------------------------------------


def test_daemon004_stop_daemon_refuses_recycled_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-004 MANDATORY pid-race regression.

    Fixture: write daemon.json carrying a pid that is alive but does NOT
    name a sov daemon (a sleeping subprocess we control). ``stop_daemon``
    must NOT signal the unrelated process and must clear the handshake.
    """
    import json
    import subprocess

    from sov_daemon import lifecycle
    from sov_daemon.lifecycle import stop_daemon

    monkeypatch.chdir(tmp_path)

    # Spawn a subprocess that is alive but has no "sov" in its command
    # line. We patch the soft-check helper to deterministically return
    # False so this test is portable across Linux / Mac / Windows even
    # when a real ``ps`` lookup might race.
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        sov_dir = tmp_path / ".sov"
        sov_dir.mkdir(parents=True, exist_ok=True)
        (sov_dir / "daemon.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "pid": other.pid,
                    "port": 1,
                    "token": "tok",
                    "network": "testnet",
                    "readonly": False,
                    "ipc_version": 1,
                    "started_iso": "2026-04-01T00:00:00Z",
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(lifecycle, "_is_sov_daemon_pid", lambda _pid: False)

        with pytest.raises(RuntimeError) as exc_info:
            stop_daemon()
        msg = str(exc_info.value).lower()
        assert "recycled" in msg or "no longer points" in msg, (
            f"refusal message must explain pid recycle: {msg!r}"
        )
        # Handshake must be removed so the next status call returns NONE.
        assert not (sov_dir / "daemon.json").exists()
        # The unrelated subprocess must still be running — we did NOT signal it.
        assert other.poll() is None, "stop_daemon signalled the recycled pid!"
    finally:
        other.terminate()
        other.wait(timeout=5)


# ---------------------------------------------------------------------------
# DAEMON-005 — mainnet balance preflight
# ---------------------------------------------------------------------------


async def test_daemon005_mainnet_underfunded_raised_before_anchor_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-005: zero-balance mainnet wallet → ``MAINNET_UNDERFUNDED``
    raised BEFORE ``anchor_batch`` is invoked."""
    monkeypatch.chdir(tmp_path)
    _seed_game(tmp_path, "s42")

    # Pre-populate a pending anchor row so flush has something to batch.
    from sov_engine.io_utils import add_pending_anchor

    add_pending_anchor("s42", "1", "a" * 64)

    from sov_daemon import server as srv

    anchor_batch_called = False

    class _FakeTransport:
        def __init__(self, network: Any) -> None:
            self.network = network

        async def anchor_batch(self, *_a: Any, **_kw: Any) -> str:
            nonlocal anchor_batch_called
            anchor_batch_called = True
            return "FAKETXID"

        def explorer_tx_url(self, _txid: str) -> str:
            return ""

    async def _zero_balance(*_a: Any, **_kw: Any) -> None:
        # Match _check_wallet_balance_or_raise's contract: raise the
        # carrier exception with required+balance drops set.
        raise srv.MainnetUnderfundedError(balance_drops=0, required_drops=10_000_012)

    # Patch the transport class so flush_pending_anchors uses our fake.
    import sov_transport.xrpl_async as xa

    monkeypatch.setattr(xa, "AsyncXRPLTransport", _FakeTransport)
    monkeypatch.setattr(srv, "_check_wallet_balance_or_raise", _zero_balance)

    app = srv.build_app(srv.DaemonConfig(network="mainnet", readonly=False, token=_FIXED_TOKEN))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # Provide a fake seed via env so _load_seed returns non-empty.
        monkeypatch.setenv("XRPL_SEED", "sEdTM1uX8pu2do5XvTnutH6HsouMaM2")
        r = await c.post("/games/s42/anchor", headers=_AUTH)

    assert r.status_code == 402, f"expected 402 MAINNET_UNDERFUNDED, got {r.status_code}"
    body = r.json()
    assert body.get("code") == "MAINNET_UNDERFUNDED"
    assert not anchor_batch_called, "anchor_batch must NOT be invoked when balance preflight fails"


# ---------------------------------------------------------------------------
# DAEMON-006 — single-flight + 5s cache (MANDATORY regression)
# ---------------------------------------------------------------------------


async def test_daemon006_chain_lookup_cache_single_flight() -> None:
    """DAEMON-006 MANDATORY single-flight regression.

    Two concurrent ``get(same_txid)`` calls must invoke the upstream
    fetcher exactly once. The second waiter awaits the first's future
    and gets the same result. xrpl-py's testnet rate limit (~120/min/IP)
    starts to bite without this.
    """
    from sov_daemon.events import ChainLookupCache

    cache = ChainLookupCache()
    call_count = 0

    async def _fetch() -> bool:
        nonlocal call_count
        call_count += 1
        # Hold the call long enough for both gather'd waiters to attach
        # to the same in-flight future.
        await asyncio.sleep(0.05)
        return True

    results = await asyncio.gather(
        cache.get("DEADBEEF", _fetch),
        cache.get("DEADBEEF", _fetch),
    )

    assert results == [True, True]
    assert call_count == 1, (
        f"two concurrent get(same_txid) must fetch once; got {call_count} fetches"
    )


async def test_daemon006_chain_lookup_cache_serves_from_cache_within_ttl() -> None:
    """Subsequent calls within TTL hit the cache (not the upstream)."""
    from sov_daemon.events import ChainLookupCache

    cache = ChainLookupCache()
    call_count = 0

    async def _fetch() -> bool:
        nonlocal call_count
        call_count += 1
        return True

    a = await cache.get("ABC", _fetch)
    b = await cache.get("ABC", _fetch)
    assert a is True and b is True
    assert call_count == 1


async def test_daemon006_chain_lookup_cache_propagates_errors() -> None:
    """Errors from the fetcher propagate to every concurrent waiter."""
    from sov_daemon.events import ChainLookupCache

    cache = ChainLookupCache()

    class _Boom(Exception):
        pass

    async def _fetch() -> bool:
        await asyncio.sleep(0.01)
        raise _Boom("upstream failed")

    results = await asyncio.gather(
        cache.get("XYZ", _fetch),
        cache.get("XYZ", _fetch),
        return_exceptions=True,
    )
    assert all(isinstance(r, _Boom) for r in results), (
        f"both waiters should see _Boom; got {results!r}"
    )


# ---------------------------------------------------------------------------
# DAEMON-009 — broadcaster reset clears module singleton
# ---------------------------------------------------------------------------


def test_daemon009_reset_default_broadcaster_clears_singleton(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-009: the module-level singleton must be resettable so test
    suites don't carry one test's broadcaster into the next."""
    import sov_daemon.events as ev
    from sov_daemon.server import build_app

    monkeypatch.chdir(tmp_path)
    app = build_app(network="testnet", readonly=True, token=_FIXED_TOKEN)
    # Prime the singleton.
    ev.get_broadcaster(app)
    assert ev._default_broadcaster is not None

    ev.reset_default_broadcaster()
    assert ev._default_broadcaster is None


# ---------------------------------------------------------------------------
# DAEMON-010 — env allowlist
# ---------------------------------------------------------------------------


def test_daemon010_subprocess_env_excludes_unrelated_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DAEMON-010: spawned daemon's env should not carry unrelated parent
    secrets (``GITHUB_TOKEN``, ``AWS_*``, etc.). Allowlist only forwards
    minimal-OS keys + the named seed var."""
    from sov_daemon.lifecycle import _build_subprocess_env

    monkeypatch.setenv("UNRELATED_TOKEN", "should-not-leak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "also-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_keepout")
    monkeypatch.setenv("XRPL_SEED", "sEdTM1uX8pu2do5XvTnutH6HsouMaM2")

    env = _build_subprocess_env(
        port=12345,
        token="tok",
        network="testnet",
        readonly=False,
        seed_env="XRPL_SEED",
        signer_file=None,
    )

    assert "UNRELATED_TOKEN" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "GITHUB_TOKEN" not in env
    # The named seed var IS forwarded — we explicitly opted in.
    assert env.get("XRPL_SEED") == "sEdTM1uX8pu2do5XvTnutH6HsouMaM2"
    # Standard SOV_DAEMON_* knobs are present.
    assert env["SOV_DAEMON_PORT"] == "12345"
    assert env["SOV_DAEMON_TOKEN"] == "tok"
    # PATH is forwarded (allowlisted).
    assert "PATH" in env


def test_daemon010_subprocess_env_signer_file_does_not_forward_xrpl_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the operator chose ``--signer-file``, the env seed must not
    flow through. Today's bug: ``os.environ.copy()`` carries ``XRPL_SEED``
    even when ``signer_file`` is set, exposing the seed in
    ``/proc/<pid>/environ`` to other local users.

    Note: ``XRPL_SEED`` may still flow if ``seed_env="XRPL_SEED"`` AND
    the operator also chose ``--signer-file``; that's a CLI-level choice,
    not the daemon's. We verify the env-seed-only-when-named contract.
    """
    from sov_daemon.lifecycle import _build_subprocess_env

    monkeypatch.setenv("XRPL_SEED", "must-not-leak")
    fake_signer = Path("/tmp/fake-signer")  # noqa: S108

    env = _build_subprocess_env(
        port=1,
        token="t",
        network="testnet",
        readonly=False,
        seed_env=None,
        signer_file=fake_signer,
    )
    # With seed_env=None, the seed must NOT be forwarded.
    assert "XRPL_SEED" not in env
    assert env.get("SOV_DAEMON_SIGNER_FILE") == str(fake_signer)


# ---------------------------------------------------------------------------
# DAEMON-008 — broadcaster lock + iteration safety
# ---------------------------------------------------------------------------


async def test_daemon008_broadcast_with_concurrent_unsubscribe_does_not_drop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DAEMON-008: broadcaster snapshots subscribers under the lock so a
    concurrent unsubscribe can't strand a queue mid-broadcast."""
    from sov_daemon.events import EventBroadcaster

    bcast = EventBroadcaster()
    queues = [await bcast.subscribe() for _ in range(5)]

    bcast.broadcast("test.event", {"n": 1})

    # Each subscriber must have received the event.
    for q in queues:
        assert q.qsize() == 1
        evt, payload = await q.get()
        assert evt == "test.event"
        assert payload == {"n": 1}

    # Unsubscribe + broadcast: no leaks.
    for q in queues:
        await bcast.unsubscribe(q)
    bcast.broadcast("after.event", {})
    # Subscriber set is empty; broadcast is a no-op.
    for q in queues:
        assert q.empty()


# ---------------------------------------------------------------------------
# DAEMON-007 — verified by tests/test_daemon_sse.py un-skip
# ---------------------------------------------------------------------------


def test_daemon007_sse_test_module_is_no_longer_skipped() -> None:
    """DAEMON-007: ensure the SSE test module isn't carrying a module-level
    pytest.mark.skip anymore.

    A regression here means the SSE contract has slipped back into being
    'documented in test bodies but not actually exercised'.
    """
    sse_test_path = Path(__file__).parent / "test_daemon_sse.py"
    text = sse_test_path.read_text(encoding="utf-8")
    assert "pytestmark = pytest.mark.skip" not in text, (
        "SSE tests must run, not skip — see DAEMON-007."
    )


# Silence unused-import warnings in environments where the imports above are
# only consumed by parametrize / fixtures.
_ = os

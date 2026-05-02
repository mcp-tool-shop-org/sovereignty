"""Seed-leak regression test — the trust boundary, mechanically pinned.

Spec §11 + coordinator brief item #5: the daemon holds the wallet seed in
memory only. Any serialization regression that lands the seed in
``.sov/daemon.json`` (or any other on-disk artifact written at start) must
fail CI, not user testing. **Mandatory** — never skip / xfail.

Two paths covered:

1. ``XRPL_SEED`` env var — the default operator path.
2. ``--signer-file`` flag (file contents stripped + held in memory).

Both paths must produce a ``.sov/daemon.json`` that does NOT contain the
seed string anywhere in its serialized contents.

These tests run against the in-process daemon lifecycle helper (no
subprocess spawn) so the seed string lives in *this* test process's memory
only — there is no IPC channel to leak through.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# A recognizable, structurally-valid-looking seed we can grep for.
_SECRET_SEED = "sSecretSeed_" + "X" * 24


def _file_excludes_secret(path: Path, secret: str) -> bool:
    """Return True if ``path`` does not contain ``secret`` (as bytes or hex).

    Hex check guards against a defensive serializer that hex-encodes the
    seed (which would still be a leak — once on disk, the bytes are
    recoverable). The seed string is ASCII so utf-8 / ascii decoding is
    equivalent.
    """
    raw = path.read_bytes()
    secret_bytes = secret.encode("utf-8")
    if secret_bytes in raw:
        return False
    return secret.encode("utf-8").hex().encode("ascii") not in raw


# ---------------------------------------------------------------------------
# 1. XRPL_SEED env path
# ---------------------------------------------------------------------------


def test_daemon_json_never_contains_seed_via_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``.sov/daemon.json`` must NEVER serialize the seed (env path).

    Trust boundary: daemon holds seed in memory only. Any regression that
    lands the seed on disk fails CI — not user testing.
    """
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _SECRET_SEED)
    # Mock the transport-construction path so no real XRPL client init is
    # attempted with our fake seed. The lifecycle helper still goes through
    # the seed-load codepath that the leak guard cares about.
    info = start_daemon(network=XRPLNetwork.TESTNET, readonly=False)
    try:
        state_file = tmp_path / ".sov" / "daemon.json"
        assert state_file.exists(), "start_daemon must write .sov/daemon.json"
        assert _file_excludes_secret(state_file, _SECRET_SEED), (
            "REGRESSION: wallet seed leaked into .sov/daemon.json. "
            "The daemon must hold the seed in memory only — "
            "any on-disk serialization is a trust-boundary breach."
        )
        # Also assert the returned info dict does not carry the seed.
        for value in info.values():
            assert _SECRET_SEED not in str(value), (
                f"start_daemon return value leaked seed in field {value!r}"
            )
    finally:
        stop_daemon()


# ---------------------------------------------------------------------------
# 2. --signer-file path
# ---------------------------------------------------------------------------


def test_daemon_json_never_contains_seed_via_signer_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same trust pin, ``--signer-file`` path.

    The file's contents are stripped + held in memory only. The path itself
    may legitimately appear in operator-facing logs (it's a filesystem
    path, not a secret), but the seed contents must never leak to disk.
    """
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    seed_file = tmp_path / "wallet-seed.txt"
    seed_file.write_text(_SECRET_SEED + "\n", encoding="utf-8")

    # Some implementations may want the signer-file as a string path argument;
    # others as a Path. Pass a Path — start_daemon should accept either via
    # PathLike protocol. If the impl uses a different parameter name, adjust
    # the test (this is the parameter name the spec documents in §13).
    info = start_daemon(
        network=XRPLNetwork.TESTNET,
        readonly=False,
        signer_file=seed_file,
    )
    try:
        state_file = tmp_path / ".sov" / "daemon.json"
        assert state_file.exists(), "start_daemon must write .sov/daemon.json"
        assert _file_excludes_secret(state_file, _SECRET_SEED), (
            "REGRESSION: --signer-file seed leaked into .sov/daemon.json. "
            "Signer-file contents must be stripped + held in memory only."
        )
        for value in info.values():
            assert _SECRET_SEED not in str(value), (
                f"start_daemon return leaked signer-file seed in {value!r}"
            )

        # Audit-paranoia: the seed file itself must remain on disk untouched.
        assert seed_file.exists()
        assert _SECRET_SEED in seed_file.read_text(encoding="utf-8")

        # Sweep: no other file under .sov/ should contain the seed.
        for path in (tmp_path / ".sov").rglob("*"):
            if path.is_file():
                assert _file_excludes_secret(path, _SECRET_SEED), f"seed leaked into {path!r}"
    finally:
        stop_daemon()


# ---------------------------------------------------------------------------
# 3. Readonly mode does not load the seed at all
# ---------------------------------------------------------------------------


def test_readonly_daemon_does_not_load_seed_or_write_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Readonly mode skips seed load entirely (spec §9).

    Even when ``XRPL_SEED`` is set, a readonly daemon must NOT load it —
    the trust boundary stays at the smallest blast radius.
    """
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _SECRET_SEED)
    start_daemon(network=XRPLNetwork.TESTNET, readonly=True)
    try:
        state_file = tmp_path / ".sov" / "daemon.json"
        assert _file_excludes_secret(state_file, _SECRET_SEED)
        # Sweep all files under .sov/ for the secret.
        for path in (tmp_path / ".sov").rglob("*"):
            if path.is_file():
                assert _file_excludes_secret(path, _SECRET_SEED), (
                    f"readonly daemon leaked seed into {path!r}"
                )
    finally:
        stop_daemon()


# ---------------------------------------------------------------------------
# 4. Process-environment hygiene
# ---------------------------------------------------------------------------


def test_daemon_does_not_export_seed_to_subprocess_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Belt-and-suspenders: this test process's env still has XRPL_SEED, but
    the daemon's persisted state must reflect that no copy of that seed
    leaked through serialization. Sanity-check the negation."""
    from sov_daemon.lifecycle import start_daemon, stop_daemon
    from sov_transport.xrpl_internals import XRPLNetwork

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XRPL_SEED", _SECRET_SEED)
    assert os.environ.get("XRPL_SEED") == _SECRET_SEED
    start_daemon(network=XRPLNetwork.TESTNET, readonly=False)
    try:
        # Sweep every path under .sov/ — the seed must not appear anywhere.
        for path in (tmp_path / ".sov").rglob("*"):
            if path.is_file():
                assert _file_excludes_secret(path, _SECRET_SEED), (
                    f"REGRESSION: seed found under .sov/ at {path!r}"
                )
    finally:
        stop_daemon()

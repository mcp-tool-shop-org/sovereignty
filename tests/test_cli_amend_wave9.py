"""Stage 7-B amend regression tests for the CLI domain (wave-9).

Pins the post-amend posture for:

* CLI-B-005: wallet_seed.txt writes mode 0o600.
* CLI-B-002 / B-003: anchors.json + season.json carry schema_version
  wrappers on write, but readers tolerate the v0 bare-dict shape so
  v2.0 → v2.1 in-place upgrades migrate on next write.
* CLI-B-006 / 007 / 008 / 009: ``sov doctor`` extensions land — daemon
  presence, multi-save layout, schema-version currency, [daemon] extra
  coherence.
* CLI-B-011: ``sov status --brief`` surfaces pending-anchors count.

Pattern matches tests/test_cli_integration.py — uses ``CliRunner`` +
``monkeypatch.chdir`` + a per-test ``.sov/`` tree built with the existing
``_seed_minimal_game`` helpers.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sov_cli.main import (
    ANCHORS_SCHEMA_VERSION,
    SEASON_SCHEMA_VERSION,
    _read_anchors_entries,
    _read_season_document,
    _record_anchor,
    _update_season,
    app,
)
from sov_engine.io_utils import (
    active_game_pointer_path,
    anchors_file,
    game_dir,
    rng_seed_file,
    state_file,
)
from sov_engine.rules.campfire import new_game
from sov_engine.serialize import canonical_json, game_state_snapshot

runner = CliRunner()


def _seed_minimal_game(cwd: Path, *, players: list[str] | None = None, seed: int = 42) -> None:
    """Mirror tests/test_cli_integration.py — write a v2 multi-save tree."""
    players = players or ["Alice", "Bob"]
    state, _ = new_game(seed, players)
    game_id = f"s{seed}"
    (cwd / ".sov").mkdir(parents=True, exist_ok=True)
    game_dir(game_id).mkdir(parents=True, exist_ok=True)
    snapshot = game_state_snapshot(state)
    state_file(game_id).write_text(
        canonical_json(snapshot),
        encoding="utf-8",
        newline="\n",
    )
    rng_seed_file(game_id).write_text(str(seed), encoding="utf-8")
    active_game_pointer_path().write_text(game_id, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI-B-005 — wallet_seed.txt mode 0o600
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes only")
def test_wallet_seed_writes_mode_0600(monkeypatch, tmp_path):
    """``sov wallet`` must persist the seed at 0o600 — the file is the
    bearer credential for an XRPL wallet, world-readable would leak it."""
    monkeypatch.chdir(tmp_path)

    # Stub fund_dev_wallet so the test doesn't hit the testnet faucet.
    from sov_transport import xrpl_testnet

    def _fake_fund(_network):
        return ("rXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", "sEdTESTSEEDTESTSEEDTESTSEEDTEST")

    monkeypatch.setattr(xrpl_testnet, "fund_dev_wallet", _fake_fund)
    monkeypatch.setattr("sov_cli.main.fund_dev_wallet", _fake_fund, raising=False)

    result = runner.invoke(app, ["wallet"])
    assert result.exit_code == 0, f"wallet command failed: {result.output!r}"

    wallet_file = tmp_path / ".sov" / "wallet_seed.txt"
    assert wallet_file.exists(), "wallet_seed.txt must be written"
    mode = stat.S_IMODE(wallet_file.stat().st_mode)
    # Owner-only: no group / other read or write bits.
    assert mode & 0o077 == 0, (
        f"wallet_seed.txt mode={oct(mode)} grants group/other access; "
        f"must be 0o600 (owner-only) — bearer credential leak risk."
    )


# ---------------------------------------------------------------------------
# CLI-B-002 / B-003 — anchors.json + season.json schema_version wrappers
# ---------------------------------------------------------------------------


def test_record_anchor_writes_v1_wrapped_shape(monkeypatch, tmp_path):
    """``_record_anchor`` writes ``{"schema_version": 1, "entries": ...}``
    so a v2.2 reader can detect the format unambiguously."""
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)

    _record_anchor("1", "DEADBEEF" * 8, "s42")

    anchor_file = anchors_file("s42")
    raw = json.loads(anchor_file.read_text(encoding="utf-8"))
    assert raw["schema_version"] == ANCHORS_SCHEMA_VERSION
    assert raw["entries"] == {"1": "DEADBEEF" * 8}


def test_record_anchor_migrates_v0_bare_dict_on_next_write(monkeypatch, tmp_path):
    """A pre-v2.1 ``anchors.json`` (bare-dict) must be readable AND get
    upgraded to the v1 wrapped shape on the next ``_record_anchor`` write.

    This is the v2.0 → v2.1 in-place upgrade path; without the
    migrate-on-read shim, a v2.1 binary reading a v2.0 anchors.json would
    silently treat the old txids as the v1 wrapper itself, losing all
    history.
    """
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)

    # Seed a v0 bare-dict anchors.json (pre-Stage-7-B shape).
    anchor_file = anchors_file("s42")
    anchor_file.parent.mkdir(parents=True, exist_ok=True)
    anchor_file.write_text(
        json.dumps({"1": "OLDTX1", "2": "OLDTX2"}, indent=2) + "\n",
        encoding="utf-8",
    )

    # Add a new anchor — should preserve the v0 entries AND write the
    # v1 wrapped shape going forward.
    _record_anchor("3", "NEWTX3", "s42")

    raw = json.loads(anchor_file.read_text(encoding="utf-8"))
    assert raw["schema_version"] == ANCHORS_SCHEMA_VERSION
    assert raw["entries"] == {"1": "OLDTX1", "2": "OLDTX2", "3": "NEWTX3"}


def test_read_anchors_entries_tolerates_v0_and_v1(tmp_path):
    """The reader returns the same map for both v0 (bare-dict) and v1
    (wrapped) on-disk shapes. Pinned so a future "drop v0 support"
    refactor either lands a forward-compat shim or this test fails."""
    v0 = tmp_path / "v0.json"
    v0.write_text(json.dumps({"1": "T1", "FINAL": "TF"}), encoding="utf-8")

    v1 = tmp_path / "v1.json"
    v1.write_text(
        json.dumps(
            {"schema_version": 1, "entries": {"1": "T1", "FINAL": "TF"}},
            indent=2,
        ),
        encoding="utf-8",
    )

    expected = {"1": "T1", "FINAL": "TF"}
    assert _read_anchors_entries(v0) == expected
    assert _read_anchors_entries(v1) == expected


def test_update_season_writes_v1_wrapped_shape(monkeypatch, tmp_path):
    """``_update_season`` writes ``{"schema_version": 1, "season": ...}``."""
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)
    state, _ = new_game(42, ["Alice", "Bob"])
    state.winner = "Alice"

    story_points = {
        "Alice": {
            "winner": 1,
            "promise_keeper": 0,
            "most_helpful": 0,
            "tables_choice": 0,
            "treaty_keeper": 0,
        },
        "Bob": {
            "winner": 0,
            "promise_keeper": 0,
            "most_helpful": 0,
            "tables_choice": 0,
            "treaty_keeper": 0,
        },
    }
    _update_season(state, story_points)

    season_file = tmp_path / ".sov" / "season.json"
    raw = json.loads(season_file.read_text(encoding="utf-8"))
    assert raw["schema_version"] == SEASON_SCHEMA_VERSION
    assert "season" in raw
    assert isinstance(raw["season"]["games"], list)
    assert len(raw["season"]["games"]) == 1


def test_read_season_document_tolerates_v0_bare_dict(monkeypatch, tmp_path):
    """A pre-v2.1 ``season.json`` (bare-dict ``{"games": [...],
    "standings": {...}}``) must read cleanly into the same shape the v1
    wrapper exposes."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sov").mkdir(parents=True, exist_ok=True)
    season_file = tmp_path / ".sov" / "season.json"
    season_file.write_text(
        json.dumps(
            {"games": [{"game_id": "s1"}], "standings": {"Alice": 3}},
            indent=2,
        ),
        encoding="utf-8",
    )

    season = _read_season_document()
    assert season["games"] == [{"game_id": "s1"}]
    assert season["standings"] == {"Alice": 3}


# ---------------------------------------------------------------------------
# CLI-B-006 / 007 / 008 / 009 — sov doctor extensions
# ---------------------------------------------------------------------------


def test_doctor_reports_multi_save_layout_when_active_game_extant(monkeypatch, tmp_path):
    """CLI-B-007: a pointed-at extant game surfaces an explicit
    "Multi-save layout valid" check (post-amend behavior)."""
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Multi-save layout valid" in result.output, (
        f"Multi-save layout check missing from doctor output:\n{result.output}"
    )


def test_doctor_warns_on_orphaned_active_game_pointer(monkeypatch, tmp_path):
    """CLI-B-007: a pointer to a non-existent game surfaces as warn."""
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path, seed=42)

    # Simulate an orphan: write a different pointer with no matching save.
    # We can't write a malformed-but-allowed value via set_active_game_id
    # (it validates), so we hand-build the layout: keep s42 saved but
    # point active-game at s99 which has no directory.
    active_game_pointer_path().write_text("s99", encoding="utf-8")

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    # Either the existing "pointer but state.json missing" check OR the
    # new "target game missing" check fires — both surface a warn.
    assert "s99" in result.output, f"Orphan pointer not surfaced in doctor output:\n{result.output}"


def test_doctor_includes_daemon_extra_coherence_check(monkeypatch, tmp_path):
    """CLI-B-009: when SOV_TAURI_SHELL=1 is set, doctor should emit the
    extra-coherence check (either OK if [daemon] is installed, or warn
    if it isn't)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SOV_TAURI_SHELL", "1")

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    output = result.output
    has_coherence = (
        "Tauri shell + [daemon] extra both present" in output
        or "Tauri shell present but [daemon] extra not installed" in output
    )
    assert has_coherence, f"Tauri/daemon coherence check missing from doctor output:\n{output}"


def test_doctor_schema_version_currency_passes_silently_on_clean(monkeypatch, tmp_path):
    """CLI-B-008: when every versioned file is current, doctor stays
    silent (no diagnostic noise on the green path)."""
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    # No "Schema version unrecognized" line on a clean tree.
    assert "Schema version unrecognized" not in result.output


def test_doctor_schema_version_currency_fails_on_unsupported(monkeypatch, tmp_path):
    """CLI-B-008: a non-active save with state.json declaring
    schema_version=999 must surface as a fail in doctor, not silently.

    Forward-bumping the ACTIVE game's state.json trips ``_load_game``'s
    own gate (which fails fast with the operator-friendly state-version
    error). The new currency check is for INACTIVE saves: a v2.2 save
    on disk that the user isn't currently playing — those slip through
    every other diagnostic.
    """
    from sov_engine.io_utils import pending_anchors_path

    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path, seed=42)
    _seed_minimal_game(tmp_path, seed=99)

    # Active game stays s42 (most-recent pointer wins). Forward-bump s99.
    # We can't forward-bump state.json because list_saved_games would drop
    # s99 from the listing — so use pending-anchors.json which the
    # currency check probes per-save.
    pa = pending_anchors_path("s99")
    pa.parent.mkdir(parents=True, exist_ok=True)
    pa.write_text(
        json.dumps({"schema_version": 999, "entries": {}}),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["doctor"])
    assert "Schema version unrecognized" in result.output, (
        f"Forward-bumped pending-anchors.json did not surface in doctor:\n{result.output}"
    )


def test_doctor_under_2s_wall_time_on_healthy_system(monkeypatch, tmp_path):
    """The doctor extensions must not blow the <2s budget on a typical
    healthy system. This test seeds 5 games + the new checks and asserts
    wall-clock < 2 seconds."""
    import time

    monkeypatch.chdir(tmp_path)
    for seed in (1, 2, 3, 4, 42):
        _seed_minimal_game(tmp_path, seed=seed)

    started = time.monotonic()
    result = runner.invoke(app, ["doctor"])
    elapsed = time.monotonic() - started
    assert result.exit_code == 0
    assert elapsed < 2.0, (
        f"sov doctor took {elapsed:.2f}s on a 5-save healthy tree; "
        f"<2s budget violated. Investigate the doctor extensions for "
        f"unintended I/O or HTTP."
    )


# ---------------------------------------------------------------------------
# CLI-B-011 — sov status --brief surfaces pending-anchors count
# ---------------------------------------------------------------------------


def test_status_brief_shows_pending_anchors_count(monkeypatch, tmp_path):
    """CLI-B-011: when pending-anchors are queued, ``sov status --brief``
    must surface the count + the actionable next step."""
    from sov_engine.io_utils import add_pending_anchor

    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)

    add_pending_anchor("s42", "1", "a" * 64)
    add_pending_anchor("s42", "2", "b" * 64)

    result = runner.invoke(app, ["status", "--brief"])
    assert result.exit_code == 0
    assert "2 pending anchors" in result.output, (
        f"pending count missing from --brief output:\n{result.output}"
    )
    assert "sov anchor" in result.output, (
        f"actionable next step missing from --brief output:\n{result.output}"
    )


def test_status_brief_silent_when_no_pending_anchors(monkeypatch, tmp_path):
    """No pending → no pending-anchor line. The brief surface stays lean
    when there's nothing to flush."""
    monkeypatch.chdir(tmp_path)
    _seed_minimal_game(tmp_path)

    result = runner.invoke(app, ["status", "--brief"])
    assert result.exit_code == 0
    assert "pending anchor" not in result.output, (
        f"--brief leaked a pending-anchor line on a clean tree:\n{result.output}"
    )

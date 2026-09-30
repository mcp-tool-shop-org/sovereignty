"""Behavioural tests for the CLI gameplay commands in ``sov_cli/main.py``.

Covers ``new`` / ``play`` / ``tutorial`` / ``status`` (human, ``--brief``,
``--json``) / ``turn`` / ``undo`` / ``end-round`` / ``promise`` / ``apologize``
/ ``offer`` / ``treaty`` / ``vote`` / ``toast`` / ``recap`` / ``board`` /
``market`` / ``upgrade`` plus the display helpers behind them (daemon status
view, market mood line, recipe filter, tier name).

Every test asserts the exit code AND either the rendered text, the structured
error code, or the state written to disk. Games are built through the CLI in a
``tmp_path`` cwd; scenario setup (coins, resources, rep, market supply) is done
by editing the saved ``state.json`` directly. Offline only: the daemon probe is
faked through ``sov_daemon.daemon_status`` / ``daemon_info`` and
``time.sleep`` is neutralised for the tutorial.

Local fast-check: ``uv run pytest tests/test_cli_gameplay_commands.py -v``.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sov_cli import main
from sov_cli.errors import SovError
from sov_cli.main import app
from sov_daemon import DaemonStatus
from sov_engine.io_utils import add_pending_anchor
from sov_engine.rules.campfire import CAMPFIRE_UPGRADE_HINT
from sov_engine.rules.town_hall import BUILDER_TOOLS_COST, WORKSHOP_WOOD_COST

runner = CliRunner()

GAME_ID = "s42"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run every test in a fresh cwd so ``.sov/`` is isolated."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def codes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record the ``SovError.code`` of every ``_fail`` call (then delegate)."""
    seen: list[str] = []
    original = main._fail

    def _recording_fail(err: SovError) -> Any:
        seen.append(err.code)
        return original(err)

    monkeypatch.setattr(main, "_fail", _recording_fail)
    return seen


@pytest.fixture
def log_text() -> Iterator[Callable[[], str]]:
    """Capture ``sov_cli`` logger output (it has propagate=False, so caplog is blind)."""
    records: list[logging.LogRecord] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Collector(level=logging.DEBUG)
    lg = logging.getLogger("sov_cli")
    old_level = lg.level
    lg.addHandler(handler)
    lg.setLevel(logging.DEBUG)
    try:
        yield lambda: " | ".join(r.getMessage() for r in records)
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)


def _flat(result: Any) -> str:
    """Whitespace-normalised output so Rich line-wrapping never breaks a match."""
    return " ".join(result.output.split())


def _sov(*args: str, input: str | None = None) -> Any:
    return runner.invoke(app, list(args), input=input)


def _new(
    *extra: str,
    players: tuple[str, ...] = ("Alice", "Bob"),
    seed: int = 42,
) -> Any:
    argv = ["new", "--seed", str(seed)]
    for p in players:
        argv += ["-p", p]
    argv += list(extra)
    res = runner.invoke(app, argv)
    assert res.exit_code == 0, res.output
    return res


def _state_path(cwd: Path, game_id: str = GAME_ID) -> Path:
    return cwd / ".sov" / "games" / game_id / "state.json"


def _read_state(cwd: Path) -> dict[str, Any]:
    return json.loads(_state_path(cwd).read_text(encoding="utf-8"))


def _edit_state(cwd: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = _state_path(cwd)
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _player(data: dict[str, Any], name: str) -> dict[str, Any]:
    return next(p for p in data["players"] if p["name"] == name)


@pytest.fixture
def fake_daemon(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    """Return a setter that fakes ``sov_daemon.daemon_status`` / ``daemon_info``."""
    import sov_daemon

    def _set(state: DaemonStatus, info: Any) -> None:
        monkeypatch.setattr(sov_daemon, "daemon_status", lambda: state)
        monkeypatch.setattr(sov_daemon, "daemon_info", lambda: info)

    yield _set


# ---------------------------------------------------------------------------
# new / play / tutorial
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tier", "label", "flavour"),
    [
        ("campfire", "Campfire", None),
        ("market-day", "Market Day", "fixed prices"),
        ("market_day", "Market Day", "fixed prices"),
        ("town-hall", "Town Hall", "scarcity"),
        ("townhall", "Town Hall", "scarcity"),
        ("treaty-table", "Treaty Table", "Treaties have teeth"),
        ("treaty_table", "Treaty Table", "Treaties have teeth"),
    ],
)
def test_new_tier_selection_writes_ruleset(
    _cwd: Path, tier: str, label: str, flavour: str | None
) -> None:
    res = _sov("new", "-p", "Alice", "-p", "Bob", "--tier", tier)
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert f"Sovereignty: {label}" in flat
    assert "Players: Alice, Bob" in flat
    if flavour:
        assert flavour in flat
    data = _read_state(_cwd)
    expected = {
        "Campfire": "campfire_v1",
        "Market Day": "market_day_v1",
        "Town Hall": "town_hall_v1",
        "Treaty Table": "treaty_table_v1",
    }[label]
    assert data["config"]["ruleset"] == expected
    assert (_cwd / ".sov" / "active-game").read_text(encoding="utf-8").strip() == GAME_ID


@pytest.mark.parametrize(
    ("players", "code"),
    [
        ((), "INPUT_PLAYERS"),
        (("A",), "INPUT_PLAYERS"),
        (("A", "B", "C", "D", "E"), "INPUT_PLAYERS"),
    ],
)
def test_new_rejects_bad_player_counts(
    players: tuple[str, ...], code: str, codes: list[str]
) -> None:
    argv = ["new"]
    for p in players:
        argv += ["-p", p]
    res = runner.invoke(app, argv)
    assert res.exit_code == 1
    assert codes == [code]
    assert "players" in _flat(res)
    assert not (Path(".sov") / "active-game").exists()


def test_new_rejects_malformed_share_code(codes: list[str]) -> None:
    res = _sov("new", "-p", "A", "-p", "B", "--code", "not-a-code")
    assert res.exit_code == 1
    assert codes == ["INPUT_SHARE_CODE"]
    assert "Invalid share code" in _flat(res)


def test_new_share_code_overrides_seed_tier_and_recipe(_cwd: Path) -> None:
    res = _sov(
        "new", "-p", "A", "-p", "B", "--code", "SOV|market-panic|town-hall|spicy|s77", "--seed", "1"
    )
    assert res.exit_code == 0, res.output
    assert "Sovereignty: Town Hall" in _flat(res)
    data = json.loads(_state_path(_cwd, "s77").read_text(encoding="utf-8"))
    assert data["config"]["ruleset"] == "town_hall_v1"
    assert data["config"]["seed"] == 77
    assert (_cwd / ".sov" / "games" / "s77" / "rng_seed.txt").read_text() == "77"
    assert any(
        line.startswith("Recipe: spicy") for line in [e.split(": ", 1)[-1] for e in data["log"]]
    )


def test_new_existing_game_declined_keeps_old_save(_cwd: Path) -> None:
    _new("--tier", "treaty-table")
    before = _state_path(_cwd).read_text(encoding="utf-8")
    res = _sov("new", "-p", "Xena", "-p", "Yuri", input="n\n")
    assert res.exit_code == 0
    assert "already exists. Overwrite?" in _flat(res)
    assert _state_path(_cwd).read_text(encoding="utf-8") == before


def test_new_existing_game_confirmed_overwrites(_cwd: Path) -> None:
    _new()
    res = _sov("new", "-p", "Xena", "-p", "Yuri", input="y\n")
    assert res.exit_code == 0, res.output
    names = [p["name"] for p in _read_state(_cwd)["players"]]
    assert names == ["Xena", "Yuri"]


@pytest.mark.parametrize("recipe", ["cozy", "spicy", "market", "promise"])
def test_new_recipe_note_and_log(_cwd: Path, recipe: str) -> None:
    res = _sov("new", "-p", "A", "-p", "B", "--recipe", recipe)
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert f"Recipe: {recipe}" in flat
    assert any(f"Recipe: {recipe}" in entry for entry in _read_state(_cwd)["log"])


def test_new_recipe_filters_deal_deck_when_enough_matches(_cwd: Path) -> None:
    """Some recipes leave enough tagged cards to actually narrow the decks."""
    filtered = 0
    for recipe in ("cozy", "spicy", "market", "promise"):
        res = _sov("new", "-p", "A", "-p", "B", "-r", recipe, input="y\n")
        assert res.exit_code == 0, res.output
        note = _flat(res)
        # "N events, M deals" (filtered) vs "all N events (too few ...)".
        if " deals" in note and "too few" not in note.split("Recipe:")[1]:
            filtered += 1
    assert filtered >= 1


def test_new_unknown_recipe_warns_but_still_creates_game(_cwd: Path) -> None:
    res = _sov("new", "-p", "A", "-p", "B", "--recipe", "sweet")
    assert res.exit_code == 0, res.output
    assert "Unknown recipe 'sweet'" in _flat(res)
    assert _state_path(_cwd).exists()


@pytest.mark.parametrize(
    ("ruleset", "expected"),
    [
        ("campfire_v1", "campfire_v1"),
        ("market_day_v1", "market_day_v1"),
        ("town-hall", "town_hall_v1"),
        ("treaty_table", "treaty_table_v1"),
        ("no-such-ruleset", "campfire_v1"),
    ],
)
def test_play_maps_ruleset_and_seats_you_and_rival(_cwd: Path, ruleset: str, expected: str) -> None:
    res = _sov("play", ruleset)
    assert res.exit_code == 0, res.output
    assert "Your turn next." in _flat(res)
    data = _read_state(_cwd)
    assert data["config"]["ruleset"] == expected
    assert [p["name"] for p in data["players"]] == ["You", "Rival"]


def _assert_tutorial_completed(res: Any, cwd: Path) -> None:
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    for marker in (
        "Learn by doing",
        "Step 1: Roll and move",
        "Step 2: The Promise",
        "Step 3: Friend's turn",
        "Step 4: End of round",
        "Receipt:",
        "You're ready",
    ):
        assert marker in flat
    # The demo game is saved as s1 and made active; the promise persisted.
    assert (cwd / ".sov" / "active-game").read_text(encoding="utf-8").strip() == "s1"
    data = json.loads(_state_path(cwd, "s1").read_text(encoding="utf-8"))
    assert [p["name"] for p in data["players"]] == ["You", "Friend"]
    assert _player(data, "You")["promises"] == ["help Friend next round"]
    # ...and the follow-up command the tutorial advertises actually works.
    follow = _sov("status", "--brief")
    assert follow.exit_code == 0
    assert "You:" in follow.output


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: tutorial step 4 splits one [dim]...[/dim] span across two console.print "
        "calls (main.py ~1826-1827) -> rich MarkupError, `sov tutorial` exits 1"
    ),
)
def test_tutorial_runs_to_completion(_cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.sleep", lambda _s: None)
    _assert_tutorial_completed(_sov("tutorial"), _cwd)


def test_tutorial_flow_with_markup_tolerant_console(
    _cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the whole walkthrough (save + closing panel) despite the markup bug above."""
    from rich.console import Console

    monkeypatch.setattr("time.sleep", lambda _s: None)
    monkeypatch.setattr(main, "console", Console(markup=False, highlight=False, width=100))
    _assert_tutorial_completed(_sov("tutorial"), _cwd)


# ---------------------------------------------------------------------------
# status (human / brief / json) and the daemon-status helpers
# ---------------------------------------------------------------------------


def test_status_without_game_fails(codes: list[str]) -> None:
    res = _sov("status")
    assert res.exit_code == 1
    assert codes == ["STATE_NO_GAME"]
    assert "No active game" in _flat(res)


def test_status_human_campfire_shows_table_and_turn_line() -> None:
    _new()
    res = _sov("status")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Round 1" in flat
    assert "Alice *" in flat
    assert "prosperity" in flat
    assert "Alice's turn next." in flat
    assert "Resources" not in flat  # campfire has no resource column


def test_status_human_town_hall_includes_resources_and_market(_cwd: Path) -> None:
    _new("--tier", "town-hall")
    _edit_state(
        _cwd, lambda d: _player(d, "Bob").update(resources={"food": 2, "wood": 0, "tools": 1})
    )
    res = _sov("status")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Resources" in flat
    assert "2F 1T" in flat
    assert "Market Board" in flat


def test_status_human_game_over_lines(_cwd: Path) -> None:
    _new()
    _edit_state(_cwd, lambda d: d.update(game_over=True, winner="Bob"))
    res = _sov("status")
    assert "Bob wins the game." in _flat(res)
    _edit_state(_cwd, lambda d: d.update(game_over=True, winner="You"))
    res = _sov("status")
    assert "You win the game." in _flat(res)


def test_status_brief_is_one_line_per_game(_cwd: Path) -> None:
    _new()
    res = _sov("status", "--brief")
    assert res.exit_code == 0
    assert "R1 | >Alice: 5c 3r 0u | Bob: 5c 3r 0u" in _flat(res)
    assert "pending anchor" not in res.output


@pytest.mark.parametrize(
    ("rounds", "phrase"), [(1, "1 pending anchor "), (2, "2 pending anchors ")]
)
def test_status_brief_reports_pending_anchors(rounds: int, phrase: str) -> None:
    _new()
    for r in range(rounds):
        add_pending_anchor(GAME_ID, str(r + 1), "a" * 64)
    res = _sov("status", "--brief")
    assert res.exit_code == 0
    flat = _flat(res)
    assert phrase in flat
    assert "run sov anchor to flush" in flat.replace("`", "")


def test_status_brief_survives_pending_probe_failure(
    monkeypatch: pytest.MonkeyPatch, log_text: Callable[[], str]
) -> None:
    _new()

    def _boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("pending index exploded")

    monkeypatch.setattr(main, "read_pending_anchors", _boom)
    res = _sov("status", "--brief")
    assert res.exit_code == 0
    assert "R1 |" in res.output
    assert "status.pending_probe.failed" in log_text()
    assert "pending anchor" not in res.output


def test_status_reports_running_daemon(fake_daemon: Callable[..., None]) -> None:
    _new()
    fake_daemon(
        DaemonStatus.RUNNING,
        {"port": 4711, "network": "testnet", "readonly": True, "pid": 99},
    )
    for argv in (["status"], ["status", "--brief"]):
        res = _sov(*argv)
        assert res.exit_code == 0
        assert "daemon: running (port 4711, network=testnet, readonly=true)" in _flat(res)


def test_status_reports_stale_daemon(fake_daemon: Callable[..., None]) -> None:
    _new()
    fake_daemon(DaemonStatus.STALE, {"pid": 12345})
    res = _sov("status")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "daemon: stale (last pid 12345" in flat
    assert "sov daemon start" in flat


def test_status_daemon_probe_failure_is_logged_not_fatal(
    monkeypatch: pytest.MonkeyPatch, log_text: Callable[[], str]
) -> None:
    _new()

    def _boom() -> Any:
        raise ValueError("bad daemon.json")

    monkeypatch.setattr(main, "_query_daemon_status", _boom)
    human = _sov("status")
    brief = _sov("status", "--brief")
    as_json = _sov("status", "--json")
    assert human.exit_code == 0 and brief.exit_code == 0 and as_json.exit_code == 0
    assert "daemon:" not in human.output
    assert "daemon:" not in brief.output
    assert json.loads(as_json.output)["daemon"] == {"state": "none"}
    assert log_text().count("status.daemon_probe.failed") == 3


def test_query_daemon_status_none_without_daemon_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "sov_daemon", None)  # import -> ImportError
    assert main._query_daemon_status() is None
    # A RUNNING status still renders (without handshake info) when the package is gone.
    assert main._daemon_status_view(DaemonStatus.RUNNING) == ("running", {})


def test_daemon_status_view_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    import sov_daemon

    assert main._daemon_status_view(None) == ("none", {})
    monkeypatch.setattr(sov_daemon, "daemon_info", lambda: None)  # non-dict -> {}
    assert main._daemon_status_view("stale") == ("stale", {})
    monkeypatch.setattr(sov_daemon, "daemon_info", lambda: {"pid": 7})
    assert main._daemon_status_view(DaemonStatus.STALE) == ("stale", {"pid": 7})


def test_daemon_status_human_line_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    import sov_daemon

    monkeypatch.setattr(sov_daemon, "daemon_info", lambda: {})
    assert main._daemon_status_human_line(DaemonStatus.RUNNING) == (
        "daemon: running (port ?, network=?, readonly=false)"
    )
    assert main._daemon_status_human_line(DaemonStatus.STALE).startswith(
        "daemon: stale (last pid ?"
    )
    assert main._daemon_status_human_line(DaemonStatus.NONE) == "daemon: none"


def test_daemon_status_json_field(monkeypatch: pytest.MonkeyPatch) -> None:
    import sov_daemon

    assert main._daemon_status_json_field(None) == {"state": "none"}
    monkeypatch.setattr(
        sov_daemon,
        "daemon_info",
        lambda: {
            "port": 1,
            "pid": 2,
            "network": "devnet",
            "readonly": False,
            "started_iso": "2026-01-01T00:00:00Z",
            "token": "must-not-leak",
        },
    )
    field = main._daemon_status_json_field(DaemonStatus.RUNNING)
    assert field == {
        "state": "running",
        "port": 1,
        "pid": 2,
        "network": "devnet",
        "readonly": False,
        "started_iso": "2026-01-01T00:00:00Z",
    }
    monkeypatch.setattr(sov_daemon, "daemon_info", lambda: {})
    assert main._daemon_status_json_field(DaemonStatus.STALE) == {"state": "stale"}


def test_status_json_shape_fresh_game() -> None:
    _new()
    res = _sov("status", "--json")
    assert res.exit_code == 0
    payload = json.loads(res.output)
    assert payload["command"] == "status"
    assert payload["status"] == "ok"
    assert payload["game_id"] == GAME_ID
    assert payload["current_round"] == 1
    assert payload["game_over"] is False
    assert payload["winner"] is None
    assert payload["rounds"] == []
    assert payload["pending_count"] == 0
    assert "anchor_pending" not in payload
    assert payload["players"][0] == {
        "name": "Alice",
        "coins": 5,
        "reputation": 3,
        "upgrades": 0,
        "is_current": True,
    }
    assert payload["players"][1]["is_current"] is False


def test_status_json_rounds_union_and_ordering(
    _cwd: Path, fake_daemon: Callable[..., None]
) -> None:
    _new()
    fake_daemon(
        DaemonStatus.RUNNING,
        {"port": 9, "pid": 4, "network": "testnet", "readonly": False, "started_iso": "t"},
    )
    assert _sov("end-round").exit_code == 0  # proof for round 1 + pending "1"
    gdir = _cwd / ".sov" / "games" / GAME_ID
    (gdir / "proofs" / "garbage.proof.json").write_text("{not json", encoding="utf-8")
    (gdir / "proofs" / "anchors.json").write_text(
        json.dumps({"FINAL": "TXF", "2": "TX2", "weird": "TXW"}), encoding="utf-8"
    )
    add_pending_anchor(GAME_ID, "FINAL", "b" * 64)
    add_pending_anchor(GAME_ID, "zzz", "c" * 64)

    payload = json.loads(_sov("status", "--json").output)
    rounds = payload["rounds"]
    keys = [r["round"] for r in rounds]
    # Numeric rounds, then FINAL, then unrecognised keys (all tie on the sort key, so their
    # relative order follows set iteration and is deliberately not asserted).
    assert keys[:3] == ["1", "2", "FINAL"]
    assert sorted(keys[3:]) == ["weird", "zzz"]
    by_key = {r["round"]: r for r in rounds}
    assert by_key["1"] == {"round": "1", "anchor_status": "pending"}
    assert by_key["2"] == {"round": "2", "anchor_status": "anchored", "txid": "TX2"}
    assert by_key["FINAL"]["anchor_status"] == "anchored"  # anchored wins over pending
    assert by_key["weird"]["txid"] == "TXW"
    assert by_key["zzz"]["anchor_status"] == "pending"
    assert payload["pending_count"] == 2  # healed: FINAL is already anchored
    pending = payload["anchor_pending"]
    assert pending["code"] == "ANCHOR_PENDING"
    assert pending["rounds"] == ["1", "zzz"]
    assert "sov anchor" in pending["hint"]
    assert payload["daemon"] == {
        "state": "running",
        "port": 9,
        "pid": 4,
        "network": "testnet",
        "readonly": False,
        "started_iso": "t",
    }


# ---------------------------------------------------------------------------
# turn / undo / end-round
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [["turn"], ["undo"], ["end-round"]])
def test_turn_undo_end_round_without_game(argv: list[str], codes: list[str]) -> None:
    res = _sov(*argv)
    assert res.exit_code == 1
    assert codes == ["STATE_NO_GAME"]


def test_turn_moves_current_player_and_advances() -> None:
    _new()
    res = _sov("turn")
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert "Alice, it's your turn. (Round 1)" in flat
    assert "You rolled a" in flat
    assert "You land on" in flat
    # Brief recap follows, with the turn passed to Bob.
    assert "Alice:" in flat and ">Bob:" in flat


def test_turn_on_finished_game_exits_zero_without_mutating(_cwd: Path) -> None:
    _new()
    _edit_state(_cwd, lambda d: d.update(game_over=True, winner="Alice"))
    before = _state_path(_cwd).read_text(encoding="utf-8")
    res = _sov("turn")
    assert res.exit_code == 0
    assert "The game is over. Alice won." in _flat(res)
    assert "sov game-end" in _flat(res)
    assert _state_path(_cwd).read_text(encoding="utf-8") == before


def test_turn_skipped_move_prints_stuck_message(_cwd: Path) -> None:
    _new()
    _edit_state(_cwd, lambda d: _player(d, "Alice").update(skip_next_move=True))
    res = _sov("turn")
    assert res.exit_code == 0
    assert "You're stuck. Road's out." in _flat(res)
    assert _player(_read_state(_cwd), "Alice")["skip_next_move"] is False


def test_turn_shows_promise_reminder_and_treaty_reminder(_cwd: Path) -> None:
    _new("--tier", "treaty-table")
    assert _sov("promise", "make", "share the fire").exit_code == 0
    made = _sov("treaty", "make", "mutual aid", "--with", "Bob", "--stake", "1 coins")
    assert made.exit_code == 0, made.output
    res = _sov("turn")
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert 'You promised: "share the fire"' in flat
    assert 'Treaty with Bob: "mutual aid" (due R4)' in flat


def test_turn_declares_winner_and_keeps_undo_checkpoint(_cwd: Path) -> None:
    _new()
    _edit_state(_cwd, lambda d: _player(d, "Alice").update(coins=40, win_condition="prosperity"))
    res = _sov("turn")
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert "Alice wins!" in flat
    assert "sov game-end" in flat
    data = _read_state(_cwd)
    assert data["game_over"] is True
    assert data["winner"] == "Alice"
    # keep_undo=True: the pre-turn checkpoint survives so `sov undo` can rewind the win.
    undone = _sov("undo")
    assert undone.exit_code == 0
    assert _read_state(_cwd)["game_over"] is False


@pytest.mark.parametrize("tier", ["campfire", "town-hall", "treaty-table"])
def test_turn_round_wrap_resets_market_and_settles_treaties(_cwd: Path, tier: str) -> None:
    _new("--tier", tier)
    if tier == "treaty-table":
        assert (
            _sov(
                "treaty", "make", "quick pact", "--with", "Bob", "--stake", "1 coins", "-d", "1"
            ).exit_code
            == 0
        )

        def _expire(d: dict[str, Any]) -> None:
            for p in d["players"]:
                for t in p["active_treaties"]:
                    t["deadline_round"] = 1

        _edit_state(_cwd, _expire)
    if tier == "town-hall":
        _edit_state(_cwd, lambda d: d["market_board"]["price_shifts"].update(food=2))
    _edit_state(_cwd, lambda d: d["market"].update(food=9, wood=9, tools=9))
    # Both players take a turn; nobody can win on 5 coins.
    _edit_state(_cwd, lambda d: [p.update(helped_last_round=True) for p in d["players"]])
    first = _sov("turn")
    second = _sov("turn")
    assert first.exit_code == 0 and second.exit_code == 0, second.output
    data = _read_state(_cwd)
    assert data["current_round"] == 2
    assert "Round 1 wraps up" in _flat(second)
    assert data["market"] == {"food": 1, "wood": 2, "tools": 3}
    assert all(p["helped_last_round"] is False for p in data["players"])
    if tier == "town-hall":
        assert data["market_board"]["price_shifts"]["food"] == 0
    if tier == "treaty-table":
        assert "honored" in _flat(second)


def test_undo_restores_pre_turn_state_once(_cwd: Path) -> None:
    _new()
    before = _read_state(_cwd)
    assert _sov("turn").exit_code == 0
    assert _read_state(_cwd)["current_player_index"] == 1
    res = _sov("undo")
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert "Undid the last turn." in flat
    assert "R1 | >Alice:" in flat
    after = _read_state(_cwd)
    assert after["current_player_index"] == before["current_player_index"] == 0
    assert after["players"] == before["players"]
    # One-shot: the buffer is gone, a second undo has nothing to do.
    again = _sov("undo")
    assert again.exit_code == 1
    assert "Nothing to undo" in _flat(again)


def test_undo_without_checkpoint_fails(codes: list[str]) -> None:
    _new()
    res = _sov("undo")
    assert res.exit_code == 1
    assert codes == ["STATE_NOTHING_TO_UNDO"]
    assert "sov turn" in _flat(res)


def test_end_round_writes_proof_and_queues_anchor(_cwd: Path) -> None:
    _new()
    res = _sov("end-round")
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert "Round Proof" in flat
    assert "Round: 1" in flat
    proof_path = _cwd / ".sov" / "games" / GAME_ID / "proofs" / "round_001.proof.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    assert proof["round"] == 1
    assert proof["envelope_hash"] in flat
    pending = json.loads(
        (_cwd / ".sov" / "games" / GAME_ID / "pending-anchors.json").read_text(encoding="utf-8")
    )
    assert "1" in json.dumps(pending)
    assert proof["envelope_hash"] in json.dumps(pending)


def test_end_round_clears_undo_checkpoint() -> None:
    _new()
    assert _sov("turn").exit_code == 0
    assert _sov("end-round").exit_code == 0
    res = _sov("undo")
    assert res.exit_code == 1
    assert "Nothing to undo" in _flat(res)


def test_end_round_custom_output_does_not_queue_anchor(_cwd: Path) -> None:
    _new()
    out = _cwd / "elsewhere"
    res = _sov("end-round", "--output", str(out))
    assert res.exit_code == 0, res.output
    assert (out / "round_001.proof.json").exists()
    assert not (_cwd / ".sov" / "games" / GAME_ID / "pending-anchors.json").exists()


# ---------------------------------------------------------------------------
# promise / apologize / offer / vote / toast
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["promise", "make", "x"],
        ["apologize", "Bob"],
        ["offer", "2 coins for 1 wood"],
        ["vote", "mvp", "Bob"],
        ["toast", "Bob"],
        ["recap"],
        ["board"],
        ["market"],
        ["treaty", "list"],
        ["upgrade", "workshop"],
    ],
)
def test_gameplay_commands_without_game_fail(argv: list[str], codes: list[str]) -> None:
    res = _sov(*argv)
    assert res.exit_code == 1
    assert codes == ["STATE_NO_GAME"]
    assert "sov new" in _flat(res)


def test_promise_make_keep_break_cycle(_cwd: Path) -> None:
    _new()
    made = _sov("promise", "make", "share the fire")
    assert made.exit_code == 0
    assert 'Alice promises: "share the fire"' in _flat(made)
    assert _player(_read_state(_cwd), "Alice")["promises"] == ["share the fire"]

    kept = _sov("promise", "keep", "share the fire")
    assert kept.exit_code == 0
    assert _player(_read_state(_cwd), "Alice")["promises"] == []

    _sov("promise", "make", "carry water")
    broken = _sov("promise", "break", "carry water")
    assert broken.exit_code == 0
    flat = _flat(broken)
    assert "broke their promise" in flat
    assert "Apologize once per game" in flat


def test_promise_break_after_apology_used_omits_apology_hint(_cwd: Path) -> None:
    _new()
    _edit_state(_cwd, lambda d: _player(d, "Alice").update(apology_used=True, promises=["x"]))
    res = _sov("promise", "break", "x")
    assert res.exit_code == 0
    assert "broke their promise" in _flat(res)
    assert "Apologize once per game" not in _flat(res)


def test_promise_for_named_player(_cwd: Path) -> None:
    _new()
    res = _sov("promise", "make", "pay up", "--player", "Bob")
    assert res.exit_code == 0
    assert _player(_read_state(_cwd), "Bob")["promises"] == ["pay up"]
    assert _player(_read_state(_cwd), "Alice")["promises"] == []


def test_promise_unknown_player_and_bad_action(codes: list[str]) -> None:
    _new()
    unknown = _sov("promise", "make", "x", "-p", "Zed")
    assert unknown.exit_code == 1
    assert "Player 'Zed' is not in this game." in _flat(unknown)
    bad = _sov("promise", "swear", "x")
    assert bad.exit_code == 1
    assert "Unknown action: 'swear'" in _flat(bad)
    assert codes == ["INPUT_PLAYER_NAME", "INPUT_ACTION"]


def test_apologize_pays_and_persists(_cwd: Path) -> None:
    _new()
    res = _sov("apologize", "Bob")
    assert res.exit_code == 0, res.output
    assert "Alice apologizes to Bob." in _flat(res)
    data = _read_state(_cwd)
    assert _player(data, "Alice")["apology_used"] is True


def test_apologize_second_time_is_refused_by_engine(_cwd: Path) -> None:
    _new()
    _sov("apologize", "Bob")
    coins_after_first = _player(_read_state(_cwd), "Bob")["coins"]
    res = _sov("apologize", "Bob")
    assert res.exit_code == 0
    assert "apologizes to Bob" not in _flat(res)
    assert _player(_read_state(_cwd), "Bob")["coins"] == coins_after_first


def test_apologize_explicit_source_player(_cwd: Path) -> None:
    _new()
    res = _sov("apologize", "Alice", "--player", "Bob")
    assert res.exit_code == 0
    assert "Bob apologizes to Alice." in _flat(res)


@pytest.mark.parametrize(
    "argv",
    [["apologize", "Zed"], ["apologize", "Bob", "-p", "Zed"]],
)
def test_apologize_unknown_names(argv: list[str], codes: list[str]) -> None:
    _new()
    res = _sov(*argv)
    assert res.exit_code == 1
    assert codes == ["INPUT_PLAYER_NAME"]
    assert "Player 'Zed' is not in this game." in _flat(res)


def test_offer_to_table_and_to_player_logs_entries(_cwd: Path) -> None:
    _new()
    table = _sov("offer", "2 coins for 1 wood")
    assert table.exit_code == 0
    assert 'Alice offers the table: "2 coins for 1 wood"' in _flat(table)
    assert "The table decides." in _flat(table)
    assert "One Offer per turn" not in table.output

    direct = _sov("offer", "a song for a coin", "--to", "Bob", "--player", "Bob")
    assert direct.exit_code == 0
    assert 'Bob offers Bob: "a song for a coin"' in _flat(direct)
    log = _read_state(_cwd)["log"]
    assert any('Alice offers the table: "2 coins for 1 wood"' in e for e in log)


def test_offer_second_in_a_round_nudges(_cwd: Path) -> None:
    _new()
    _sov("offer", "first")
    res = _sov("offer", "second", "--to", "Bob")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "One Offer per turn" in flat
    assert 'Alice offers Bob: "second"' in flat


def test_offer_unknown_player_errors(codes: list[str]) -> None:
    _new()
    assert _sov("offer", "x", "--to", "Zed").exit_code == 1
    assert _sov("offer", "x", "--player", "Zed").exit_code == 1
    assert codes == ["INPUT_PLAYER_NAME", "INPUT_PLAYER_NAME"]


@pytest.mark.parametrize(
    ("category", "value", "expected"),
    [
        ("mvp", "Bob", "Vote: Bob wins Table's Choice (MVP)"),
        ("MVP", "Alice", "Vote: Alice wins Table's Choice (MVP)"),
        ("chaos", "Bob", "Vote: Bob wins Chaos Gremlin"),
        ("promise", "Always share", 'Vote: Best Promise — "Always share"'),
    ],
)
def test_vote_categories_are_logged(_cwd: Path, category: str, value: str, expected: str) -> None:
    _new()
    res = _sov("vote", category, value)
    assert res.exit_code == 0, res.output
    assert expected in _flat(res)
    assert "The table decides. The console records it." in _flat(res)
    assert any(expected in e for e in _read_state(_cwd)["log"])


@pytest.mark.parametrize(
    ("argv", "code", "text"),
    [
        (["vote", "mvp", "Zed"], "INPUT_PLAYER_NAME", "Player 'Zed'"),
        (["vote", "chaos", "Zed"], "INPUT_PLAYER_NAME", "Player 'Zed'"),
        (["vote", "best", "Bob"], "INPUT_ACTION", "Unknown action: 'best'"),
    ],
)
def test_vote_errors(argv: list[str], code: str, text: str, codes: list[str]) -> None:
    _new()
    res = _sov(*argv)
    assert res.exit_code == 1
    assert codes == [code]
    assert text in _flat(res)


def test_toast_grants_rep_once_per_player(_cwd: Path) -> None:
    _new()
    res = _sov("toast", "Bob")
    assert res.exit_code == 0
    assert "The table toasts Bob! +1 Rep." in _flat(res)
    bob = _player(_read_state(_cwd), "Bob")
    assert bob["reputation"] == 4
    assert bob["toasted"] is True

    again = _sov("toast", "Bob")
    assert again.exit_code == 0
    assert "Bob has already been toasted this game." in _flat(again)
    assert _player(_read_state(_cwd), "Bob")["reputation"] == 4


def test_toast_unknown_player(codes: list[str]) -> None:
    _new()
    res = _sov("toast", "Zed")
    assert res.exit_code == 1
    assert codes == ["INPUT_PLAYER_NAME"]


# ---------------------------------------------------------------------------
# treaty
# ---------------------------------------------------------------------------


def test_treaty_requires_treaty_table_tier(codes: list[str]) -> None:
    _new()
    res = _sov("treaty", "list")
    assert res.exit_code == 1
    assert codes == ["INPUT_TREATY"]
    assert "Treaties require Treaty Table tier." in _flat(res)


def test_treaty_unknown_acting_player(codes: list[str]) -> None:
    _new("--tier", "treaty-table")
    res = _sov("treaty", "list", "--player", "Zed")
    assert res.exit_code == 1
    assert codes == ["INPUT_PLAYER_NAME"]


@pytest.mark.parametrize(
    ("argv", "code", "text"),
    [
        (["treaty", "make", "pact"], "INPUT_TREATY", "Use --with"),
        (
            ["treaty", "make", "pact", "--with", "Zed", "--stake", "1 coins"],
            "INPUT_PLAYER_NAME",
            "Player 'Zed'",
        ),
        (
            ["treaty", "make", "pact", "--with", "Bob"],
            "INPUT_TREATY",
            "At least one side must stake something",
        ),
        (
            ["treaty", "make", "pact", "--with", "Bob", "--stake", "banana"],
            "INPUT_TREATY",
            "",
        ),
        (
            [
                "treaty",
                "make",
                "pact",
                "--with",
                "Bob",
                "--stake",
                "1 coins",
                "--their-stake",
                "??",
            ],
            "INPUT_TREATY",
            "",
        ),
        (
            ["treaty", "make", "pact", "--with", "Bob", "--stake", "99 coins"],
            "INPUT_TREATY",
            "",
        ),
        (["treaty", "keep"], "INPUT_TREATY", "Specify the treaty ID"),
        (["treaty", "keep", "t_9999"], "INPUT_TREATY", "Treaty 't_9999' not found on Alice."),
        (["treaty", "break"], "INPUT_TREATY", "Specify the treaty ID"),
        (["treaty", "break", "t_9999"], "INPUT_TREATY", "Treaty 't_9999' not found on Alice."),
        (["treaty", "annul"], "INPUT_ACTION", "Unknown action: 'annul'"),
    ],
)
def test_treaty_error_exits(argv: list[str], code: str, text: str, codes: list[str]) -> None:
    _new("--tier", "treaty-table")
    res = _sov(*argv)
    assert res.exit_code == 1, res.output
    assert codes == [code]
    assert text in _flat(res)


def test_treaty_list_empty_state_names_recovery_command() -> None:
    _new("--tier", "treaty-table")
    res = _sov("treaty", "list")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Alice has no treaties." in flat
    assert "sov treaty make" in flat


def test_treaty_make_keep_list_lifecycle(_cwd: Path) -> None:
    _new("--tier", "treaty-table")
    made = _sov(
        "treaty",
        "make",
        "mutual aid",
        "--with",
        "Bob",
        "--stake",
        "2 coins",
        "--their-stake",
        "1 coins",
        "--duration",
        "2",
    )
    assert made.exit_code == 0, made.output
    flat = _flat(made)
    assert 'Treaty t_0001: Alice and Bob agree: "mutual aid"' in flat
    assert "Due round 3. Stakes in escrow." in flat
    data = _read_state(_cwd)
    assert _player(data, "Alice")["coins"] == 3
    assert _player(data, "Bob")["coins"] == 4

    listed = _sov("treaty", "list")
    assert listed.exit_code == 0
    lflat = _flat(listed)
    assert "t_0001" in lflat and "active" in lflat and "R3" in lflat
    assert "Alice: 2 coins" in lflat

    as_bob = _sov("treaty", "list", "--player", "Bob")
    assert "Bob's Treaties" in _flat(as_bob)

    kept = _sov("treaty", "keep", "t_0001")
    assert kept.exit_code == 0
    assert "Treaty t_0001 honored!" in _flat(kept)
    data = _read_state(_cwd)
    assert _player(data, "Alice")["coins"] == 5
    assert _player(data, "Alice")["reputation"] == 4

    after = _sov("treaty", "list")
    assert "kept" in _flat(after)


def test_treaty_break_transfers_stake_to_partner(_cwd: Path) -> None:
    _new("--tier", "treaty-table")
    assert (
        _sov(
            "treaty",
            "make",
            "pact",
            "--with",
            "Bob",
            "--stake",
            "2 coins",
            "--their-stake",
            "2 coins",
        ).exit_code
        == 0
    )
    res = _sov("treaty", "break", "t_0001")
    assert res.exit_code == 0, res.output
    assert "Treaty t_0001" in _flat(res)
    data = _read_state(_cwd)
    # Alice (the breaker) forfeits; Bob is made whole plus the escrowed stake.
    assert _player(data, "Bob")["coins"] > _player(data, "Alice")["coins"]
    listed = _sov("treaty", "list")
    assert "broken" in _flat(listed)


def test_treaty_break_can_name_the_breaker(_cwd: Path) -> None:
    _new("--tier", "treaty-table")
    assert (
        _sov(
            "treaty",
            "make",
            "pact",
            "--with",
            "Bob",
            "--stake",
            "2 coins",
            "--their-stake",
            "2 coins",
        ).exit_code
        == 0
    )
    res = _sov("treaty", "break", "t_0001", "--breaker", "Bob")
    assert res.exit_code == 0, res.output
    data = _read_state(_cwd)
    assert _player(data, "Alice")["coins"] > _player(data, "Bob")["coins"]


def test_treaty_make_unaffordable_second_stake_is_refused(_cwd: Path, codes: list[str]) -> None:
    """The engine refuses a stake the maker can no longer afford (INPUT_TREATY)."""
    _new("--tier", "treaty-table")
    first = _sov("treaty", "make", "pact", "--with", "Bob", "--stake", "4 coins")
    assert first.exit_code == 0, first.output
    second = _sov("treaty", "make", "pact2", "--with", "Bob", "--stake", "4 coins")
    assert second.exit_code == 1
    assert codes == ["INPUT_TREATY"]
    assert _player(_read_state(_cwd), "Alice")["coins"] == 1  # nothing further escrowed


# ---------------------------------------------------------------------------
# recap / board
# ---------------------------------------------------------------------------


def test_recap_empty_log_shows_empty_state(_cwd: Path) -> None:
    _new()
    _edit_state(_cwd, lambda d: d.update(log=[]))
    res = _sov("recap")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Nothing has happened yet." in flat
    assert "sov turn" in flat


def test_recap_lists_recent_entries_and_highlights(_cwd: Path) -> None:
    _new()
    _sov("promise", "make", "carry water")
    _sov("promise", "break", "carry water")
    _sov("apologize", "Bob")
    _edit_state(_cwd, lambda d: d["log"].append("R1: Bob helps Alice carry the wood."))
    res = _sov("recap")
    assert res.exit_code == 0, res.output
    flat = _flat(res)
    assert "What happened lately (Round 1)" in flat
    assert "- Alice promises:" in flat
    assert "Ouch: Alice broke their promise" in flat
    assert "Kind: Bob helps Alice carry the wood." in flat
    assert "Brave: Alice apologizes to Bob." in flat
    assert "Market's" not in flat  # campfire has no market line


def test_recap_without_highlights_has_no_highlight_labels() -> None:
    _new()
    res = _sov("recap")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Ouch:" not in flat and "Kind:" not in flat and "Brave:" not in flat


def test_recap_town_hall_appends_market_moment() -> None:
    _new("--tier", "town-hall")
    res = _sov("recap")
    assert res.exit_code == 0
    assert "Market's steady." in _flat(res)


def test_recap_skips_entries_outside_current_and_previous_round(_cwd: Path) -> None:
    _new()
    _edit_state(
        _cwd,
        lambda d: (
            d.update(current_round=5),
            d["log"].extend(["R1: ancient history", "R4: last round", "R5: this round"]),
        ),
    )
    flat = _flat(_sov("recap"))
    assert "ancient history" not in flat
    assert "last round" in flat and "this round" in flat


def test_board_marks_player_positions(_cwd: Path) -> None:
    _new()
    _edit_state(_cwd, lambda d: _player(d, "Bob").update(position=3))
    res = _sov("board")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Board" in flat
    assert "Campfire" in flat and "Alice" in flat  # both on space 0 initially / Alice at 0
    assert "Rumor" in flat
    # Bob moved off the Campfire row.
    rows = [line for line in res.output.splitlines() if "Bob" in line]
    assert rows and "Campfire" not in rows[0]


# ---------------------------------------------------------------------------
# market
# ---------------------------------------------------------------------------


def test_market_requires_a_market_tier(codes: list[str]) -> None:
    _new()
    res = _sov("market")
    assert res.exit_code == 1
    assert codes == ["INPUT_MARKET"]
    assert "Market Board requires Market Day or Town Hall." in _flat(res)


def test_market_show_town_hall_lists_prices_and_supply() -> None:
    _new("--tier", "town-hall")
    res = _sov("market", "show")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Market Board" in flat
    assert "Food" in flat and "available" in flat
    assert "fixed prices" not in flat


def test_market_show_market_day_is_fixed_price() -> None:
    _new("--tier", "market-day")
    res = _sov("market")
    assert res.exit_code == 0
    flat = _flat(res)
    assert "Market Board (fixed prices)" in flat
    assert "A shop, not a casino." in flat
    assert "Supply" not in flat


def test_market_buy_and_sell_round_trip(_cwd: Path) -> None:
    _new("--tier", "town-hall")
    bought = _sov("market", "buy", "food")
    assert bought.exit_code == 0, bought.output
    assert "Alice buys 1 food for 2 coins." in _flat(bought)
    data = _read_state(_cwd)
    assert _player(data, "Alice")["coins"] == 3
    assert _player(data, "Alice")["resources"]["food"] == 1
    assert data["market_board"]["supply"]["food"] == 7

    sold = _sov("market", "sell", "food")
    assert sold.exit_code == 0
    assert "Alice sells 1 food for 1 coins." in _flat(sold)
    data = _read_state(_cwd)
    assert _player(data, "Alice")["coins"] == 4
    assert data["market_board"]["supply"]["food"] == 8


def test_market_named_player_and_engine_messages(_cwd: Path) -> None:
    _new("--tier", "market-day")
    assert "Bob buys 1 wood" in _flat(_sov("market", "buy", "wood", "-p", "Bob"))
    nothing = _sov("market", "sell", "tools", "--player", "Bob")
    assert nothing.exit_code == 0
    assert "Bob has no tools to sell." in _flat(nothing)
    unknown = _sov("market", "buy", "gold")
    assert unknown.exit_code == 0
    assert "Unknown resource: gold." in _flat(unknown)


@pytest.mark.parametrize(
    ("argv", "code", "text"),
    [
        (["market", "buy"], "INPUT_MARKET", "Specify a resource"),
        (["market", "buy", "food", "-p", "Zed"], "INPUT_PLAYER_NAME", "Player 'Zed'"),
        (["market", "barter", "food"], "INPUT_ACTION", "Unknown action: 'barter'"),
    ],
)
def test_market_error_exits(argv: list[str], code: str, text: str, codes: list[str]) -> None:
    _new("--tier", "town-hall")
    res = _sov(*argv)
    assert res.exit_code == 1
    assert codes == [code]
    assert text in _flat(res)


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda mb: mb["supply"].update(food=0), "Market's dry: Food unavailable."),
        (
            lambda mb: mb["supply"].update(food=0, tools=0),
            "Market's dry: Food and Tools unavailable.",
        ),
        (lambda mb: mb["supply"].update(wood=2), "Market's tight: Wood is scarce (price 3)."),
        (
            lambda mb: mb["price_shifts"].update(tools=-1),
            "Market's kind: Tools is cheap (price 1).",
        ),
        (lambda mb: None, "Market's steady. Nothing scarce, nothing cheap."),
    ],
)
def test_market_moment_town_hall_moods(
    _cwd: Path, mutate: Callable[[dict[str, Any]], None], expected: str
) -> None:
    _new("--tier", "town-hall")
    _edit_state(_cwd, lambda d: mutate(d["market_board"]))
    res = _sov("recap")
    assert res.exit_code == 0, res.output
    assert expected in _flat(res)


def test_market_moment_market_day_and_none(_cwd: Path) -> None:
    _new("--tier", "market-day")
    res = _sov("recap")
    assert "Market's open. Fixed prices" in _flat(res)
    _new("--tier", "campfire", players=("Cara", "Dan"), seed=5)
    campfire = main._load_game()
    assert campfire is not None
    assert main._market_moment(campfire[0]) == ""


def test_print_market_marks_empty_and_scarce_rows(_cwd: Path) -> None:
    _new("--tier", "town-hall")
    _edit_state(_cwd, lambda d: d["market_board"]["supply"].update(food=0, wood=1))
    res = _sov("market")
    flat = _flat(res)
    assert "EMPTY" in flat
    assert "scarce (+1 price)" in flat
    assert "available" in flat  # tools untouched
    loaded = main._load_game()
    assert loaded is not None
    loaded[0].market_board = None
    main._print_market(loaded[0])  # market-less state is a silent no-op


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def test_upgrade_cost_table_mirrors_engine_constants() -> None:
    assert main._upgrade_cost_table("workshop") == (2, "wood", WORKSHOP_WOOD_COST)
    assert main._upgrade_cost_table("builder") == (3, "tools", BUILDER_TOOLS_COST)


def test_upgrade_bad_target_fails_before_loading_game(codes: list[str]) -> None:
    res = _sov("upgrade", "castle")
    assert res.exit_code == 1
    assert codes == ["INPUT_ACTION"]
    assert "Unknown action: 'castle'" in _flat(res)


def test_upgrade_on_campfire_is_unavailable_and_logs_hint(
    codes: list[str], log_text: Callable[[], str]
) -> None:
    _new()
    res = _sov("upgrade", "workshop")
    assert res.exit_code == 1
    assert codes == ["INPUT_UPGRADE"]
    assert CAMPFIRE_UPGRADE_HINT in log_text()
    assert "Campfire" in _flat(res)


@pytest.mark.parametrize("tier", ["town-hall", "treaty-table", "market-day"])
def test_upgrade_dry_run_describes_cost(tier: str) -> None:
    _new("--tier", tier)
    workshop = _sov("upgrade", "workshop", "--dry-run")
    assert workshop.exit_code == 0
    flat = _flat(workshop)
    assert "Dry run: upgrade workshop" in flat
    assert "Cost: 2 coins + 1 wood" in flat
    assert "Alice has: 5 coins, 0 wood, Rep 3" in flat
    builder = _sov("upgrade", "builder", "-p", "Bob", "--dry-run")
    bflat = _flat(builder)
    assert "Cost: 3 coins + 1 tools (requires Rep >= 3)" in bflat
    assert "Bob has: 5 coins, 0 tools, Rep 3" in bflat


def test_upgrade_dry_run_spends_nothing(_cwd: Path) -> None:
    _new("--tier", "town-hall")
    before = _state_path(_cwd).read_text(encoding="utf-8")
    assert _sov("upgrade", "workshop", "--dry-run").exit_code == 0
    assert _state_path(_cwd).read_text(encoding="utf-8") == before


def test_upgrade_unknown_player(codes: list[str]) -> None:
    _new("--tier", "town-hall")
    res = _sov("upgrade", "workshop", "-p", "Zed")
    assert res.exit_code == 1
    assert codes == ["INPUT_PLAYER_NAME"]


def test_upgrade_builder_requires_rep(_cwd: Path, codes: list[str]) -> None:
    _new("--tier", "town-hall")
    _edit_state(
        _cwd,
        lambda d: _player(d, "Alice").update(
            reputation=2, coins=9, resources={"food": 0, "wood": 0, "tools": 2}
        ),
    )
    res = _sov("upgrade", "builder")
    assert res.exit_code == 1
    assert codes == ["INPUT_UPGRADE"]
    flat = _flat(res)
    assert "Rep" in flat
    assert "sov promise keep" in flat


@pytest.mark.parametrize(
    ("target", "coins", "resources", "expected"),
    [
        (
            "workshop",
            5,
            {"food": 0, "wood": 0, "tools": 0},
            "Pick up 1 wood via sov market buy wood.",
        ),
        (
            "workshop",
            1,
            {"food": 0, "wood": 1, "tools": 0},
            "Earn 1 more coin via sov market sell.",
        ),
        (
            "workshop",
            0,
            {"food": 0, "wood": 1, "tools": 0},
            "Earn 2 more coins via sov market sell.",
        ),
        (
            "builder",
            1,
            {"food": 0, "wood": 0, "tools": 0},
            "Earn 2 more coins via sov market sell, then pick up 1 tools via sov market buy tools.",
        ),
    ],
)
def test_upgrade_shortfall_hints(
    _cwd: Path,
    codes: list[str],
    target: str,
    coins: int,
    resources: dict[str, int],
    expected: str,
) -> None:
    _new("--tier", "town-hall")
    _edit_state(_cwd, lambda d: _player(d, "Alice").update(coins=coins, resources=resources))
    res = _sov("upgrade", target)
    assert res.exit_code == 1
    assert codes == ["INPUT_UPGRADE"]
    flat = _flat(res).replace("`", "")
    assert expected in flat
    assert f"Cannot upgrade {target}" in flat


@pytest.mark.parametrize(
    ("target", "resource", "coin_cost"), [("workshop", "wood", 2), ("builder", "tools", 3)]
)
def test_upgrade_success_spends_and_persists(
    _cwd: Path, target: str, resource: str, coin_cost: int
) -> None:
    _new("--tier", "treaty-table")
    _edit_state(
        _cwd,
        lambda d: _player(d, "Alice").update(coins=8, resources={"food": 0, "wood": 1, "tools": 1}),
    )
    res = _sov("upgrade", target.upper())  # case-insensitive
    assert res.exit_code == 0, res.output
    alice = _player(_read_state(_cwd), "Alice")
    assert alice["upgrades"] == 1
    assert alice["coins"] == 8 - coin_cost
    assert alice["resources"][resource] == 0


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tier", "label"),
    [
        ("campfire", "Campfire"),
        ("market-day", "Market Day"),
        ("town-hall", "Town Hall"),
        ("treaty-table", "Treaty Table"),
    ],
)
def test_tier_name_per_ruleset(tier: str, label: str) -> None:
    _new("--tier", tier)
    loaded = main._load_game()
    assert loaded is not None
    assert main._tier_name(loaded[0]) == label


def test_apply_recipe_unknown_returns_warning_and_leaves_state_alone() -> None:
    _new()
    loaded = main._load_game()
    assert loaded is not None
    state = loaded[0]
    events_before = len(state.event_deck.draw_pile)
    note = main._apply_recipe(state, "SWEET")
    assert "Unknown recipe 'SWEET'" in note
    assert len(state.event_deck.draw_pile) == events_before
    assert not any("Recipe:" in e for e in state.log)


def test_apply_recipe_is_case_insensitive_and_logs() -> None:
    _new()
    loaded = main._load_game()
    assert loaded is not None
    state = loaded[0]
    note = main._apply_recipe(state, "CoZy")
    assert "Recipe: cozy" in note
    assert "Recipe: cozy" in state.log[-1]


def test_apply_recipe_too_few_events_keeps_full_deck() -> None:
    _new()
    loaded = main._load_game()
    assert loaded is not None
    state = loaded[0]
    state.event_deck.draw_pile = state.event_deck.draw_pile[:3]
    note = main._apply_recipe(state, "cozy")
    assert "all 3 events (too few 'cozy' events to filter)" in note
    assert len(state.event_deck.draw_pile) == 3


def test_status_omits_daemon_line_when_probe_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _new()
    monkeypatch.setattr(main, "_query_daemon_status", lambda: None)
    for argv in (["status"], ["status", "--brief"]):
        res = _sov(*argv)
        assert res.exit_code == 0
        assert "daemon:" not in res.output


def test_status_json_marks_unqueued_proof_as_missing(_cwd: Path) -> None:
    from sov_engine.io_utils import clear_pending_anchors

    _new()
    assert _sov("end-round").exit_code == 0
    clear_pending_anchors(GAME_ID, ["1"])
    payload = json.loads(_sov("status", "--json").output)
    assert payload["rounds"] == [{"round": "1", "anchor_status": "missing"}]
    assert payload["pending_count"] == 0
    assert "anchor_pending" not in payload

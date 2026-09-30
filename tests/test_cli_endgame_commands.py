"""CLI end-of-game and content commands in ``sov_cli/main.py``.

Coverage-90 Phase 1 (part B). Exercises through Typer's ``CliRunner``:

* ``sov postcard`` (all styles, proof + anchor lines, market lines)
* ``sov game-end`` (Story Points, season file, FINAL proof, ``--anchor`` paths)
* ``sov season-postcard`` (empty states, champion / tie, award totals, votes)
* ``sov scenario`` (list / code / lint and every error exit)
* ``sov games`` / ``sov resume`` / ``sov feedback``
* the pure helpers behind them (``_calc_story_points``, ``_read_season_document``,
  ``_update_season``, ``_postcard_highlights``, ``_lint_scenario``,
  ``_parse_share_code``, ``_build_share_code``, ``_summary_to_dict``,
  ``_format_last_played``).

Everything is offline: the XRPL transport is stubbed at the import boundary
(``sov_transport.xrpl.XRPLTransport``), exactly as ``tests/test_anchor_cli.py``
does, so nothing touches the network.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sov_cli import main as cli_main
from sov_cli.main import app
from sov_engine.io_utils import (
    active_game_pointer_path,
    add_pending_anchor,
    anchors_file,
    game_dir,
    pending_anchors_path,
    proofs_dir,
    rng_seed_file,
    state_file,
)
from sov_engine.models import GameState
from sov_engine.proof import record_anchors
from sov_engine.rules.campfire import new_game
from sov_engine.rules.market_day import new_market_day_game
from sov_engine.rules.town_hall import new_town_hall_game
from sov_engine.rules.treaty_table import new_treaty_table_game
from sov_engine.serialize import canonical_json, game_state_snapshot

runner = CliRunner()

_HASH = "c" * 64
_TEST_SEED = "sEdXXXXXXXXXXXXXXXXXXXXXXX"
_BOX_CHARS = re.compile(r"[│╭╮╰╯─┃┏┓┗┛━┡┩╇┳┻╈┼┠┨┯┷┿╂┌┐└┘├┤┬┴┼]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    """Strip Rich box-drawing glyphs and collapse whitespace.

    Rich wraps long lines at 80 columns inside panels and tables; normalising
    lets assertions match a phrase regardless of where the wrap fell.
    """
    return " ".join(_BOX_CHARS.sub(" ", text).split())


def _make_state(
    tier: str = "campfire",
    seed: int = 42,
    players: list[str] | None = None,
) -> GameState:
    names = players or ["Alice", "Bob"]
    factories: dict[str, Callable[[int, list[str]], Any]] = {
        "campfire": new_game,
        "market-day": new_market_day_game,
        "town-hall": new_town_hall_game,
        "treaty-table": new_treaty_table_game,
    }
    state, _ = factories[tier](seed, names)
    return state


def _plant(state: GameState, cwd: Path) -> str:
    """Persist ``state`` as the active game under ``cwd/.sov``. Returns the game-id."""
    seed = state.config.seed
    game_id = f"s{seed}"
    (cwd / ".sov").mkdir(parents=True, exist_ok=True)
    game_dir(game_id).mkdir(parents=True, exist_ok=True)
    state_file(game_id).write_text(
        canonical_json(game_state_snapshot(state)), encoding="utf-8", newline="\n"
    )
    rng_seed_file(game_id).write_text(str(seed), encoding="utf-8")
    active_game_pointer_path().write_text(game_id, encoding="utf-8")
    return game_id


def _write_proof(game_id: str, round_num: int, *, name: str | None = None) -> Path:
    pdir = proofs_dir(game_id)
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / (name or f"round_{round_num:02d}.proof.json")
    path.write_text(
        json.dumps({"round": round_num, "envelope_hash": _HASH}) + "\n", encoding="utf-8"
    )
    return path


def _transport_factory(txids: list[list[str]] | None = None) -> MagicMock:
    """Mock ``XRPLTransport`` class; ``anchor_batch`` returns each txid list in turn."""
    transport = MagicMock()
    if txids is None:
        transport.anchor_batch.return_value = ["FINALTX"]
    else:
        transport.anchor_batch.side_effect = txids
    transport.explorer_tx_url.side_effect = lambda t: f"https://explorer.example/{t}"
    return MagicMock(return_value=transport)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every test runs in an empty cwd with no ambient wallet / network config."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XRPL_SEED", raising=False)
    monkeypatch.delenv("SOV_XRPL_NETWORK", raising=False)


# ---------------------------------------------------------------------------
# postcard
# ---------------------------------------------------------------------------


def test_postcard_no_game_fails_with_hint() -> None:
    result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "No active game found" in out
    assert "sov new -p Alice -p Bob" in out


def test_postcard_fresh_campfire_shows_scoreboard_and_no_proof(tmp_path: Path) -> None:
    _plant(_make_state(), tmp_path)
    result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Campfire Postcard" in out
    assert "Sovereignty: Campfire" in out
    assert "Alice, Bob" in out
    assert "Alice: 5c 3r 0u" in out and "Bob: 5c 3r 0u" in out
    assert "no proof yet" in out
    assert "sov postcard --style all" in out
    assert "Anchored:" not in out


def test_postcard_scoreboard_lists_positive_resources(tmp_path: Path) -> None:
    state = _make_state("town-hall", players=["Alice", "Bob", "Cara"])
    state.players[0].resources["wood"] = 2
    state.players[0].resources["food"] = 1
    _plant(state, tmp_path)
    result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Town Hall Postcard" in out
    # Only non-zero resources are listed, keyed by first letter.
    assert "1F 2W" in out or "2W 1F" in out
    assert "0T" not in out
    assert "Market's" in out  # market line comes from _market_moment


def test_postcard_market_day_line(tmp_path: Path) -> None:
    _plant(_make_state("market-day"), tmp_path)
    result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Market Day Postcard" in out
    assert "Fixed prices" in out


def test_postcard_treaty_table_title(tmp_path: Path) -> None:
    _plant(_make_state("treaty-table"), tmp_path)
    result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 0, result.output
    assert "Treaty Table Postcard" in _norm(result.output)


def test_postcard_shows_latest_proof_hash(tmp_path: Path) -> None:
    game_id = _plant(_make_state(), tmp_path)
    _write_proof(game_id, 1)
    result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert _HASH in out.replace(" ", "")
    assert "no proof yet" not in out
    assert "Anchored:" not in out  # no anchors.json


def test_postcard_shows_anchor_url_for_latest_round(tmp_path: Path) -> None:
    game_id = _plant(_make_state(), tmp_path)
    _write_proof(game_id, 3)
    record_anchors(game_id, {"3": "TXROUND3"})
    assert anchors_file(game_id).exists()
    factory = _transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 0, result.output
    assert "Anchored:" in _norm(result.output)
    assert "https://explorer.example/TXROUND3" in result.output.replace("\n", "").replace(
        " ", ""
    ).replace("│", "")
    factory.return_value.explorer_tx_url.assert_called_once_with("TXROUND3")


def test_postcard_anchors_file_without_matching_round_omits_anchor_line(
    tmp_path: Path,
) -> None:
    game_id = _plant(_make_state(), tmp_path)
    _write_proof(game_id, 3)
    record_anchors(game_id, {"1": "OTHERROUND"})
    factory = _transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["postcard"])
    assert result.exit_code == 0, result.output
    assert "Anchored:" not in _norm(result.output)
    factory.return_value.explorer_tx_url.assert_not_called()


@pytest.mark.parametrize(
    ("style", "expected", "absent"),
    [
        ("cozy", "Kind: Alice helps Bob", "Trade:"),
        ("spicy", "Ouch: Bob broke their promise", "Kind:"),
        ("economic", "Buy: Alice buys wood", "Kind:"),
        ("all", "Kind: Alice helps Bob", None),
        ("nonsense", "Kind: Alice helps Bob", "Trade:"),  # unknown style falls back to cozy
    ],
)
def test_postcard_style_filters_highlights(
    tmp_path: Path, style: str, expected: str, absent: str | None
) -> None:
    state = _make_state()
    state.add_log("Alice helps Bob")
    state.add_log("Bob broke their promise")
    state.add_log("Alice buys wood")
    _plant(state, tmp_path)
    result = runner.invoke(app, ["postcard", "--style", style])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert expected in out
    if absent:
        assert absent not in out
    assert f"sov postcard --style {style}" in out


def test_postcard_caps_highlights_at_three(tmp_path: Path) -> None:
    state = _make_state()
    for i in range(5):
        state.add_log(f"Alice helps friend{i}")
    _plant(state, tmp_path)
    result = runner.invoke(app, ["postcard", "-s", "cozy"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert out.count("Kind:") == 3
    assert "friend0" in out and "friend2" in out
    assert "friend3" not in out


# ---------------------------------------------------------------------------
# _postcard_highlights
# ---------------------------------------------------------------------------


def test_postcard_highlights_includes_previous_round_only_after_round_one() -> None:
    state = _make_state()
    state.log = [
        "R1T0: Alice helps Bob",
        "R2T0: Bob apologizes to Alice",
        "R3T0: Alice toasts Bob",
    ]
    round_two = cli_main._postcard_highlights(state, 2, "all")
    assert round_two == [
        "[green]Kind:[/green] Alice helps Bob",
        "[blue]Brave:[/blue] Bob apologizes to Alice",
    ]
    round_one = cli_main._postcard_highlights(state, 1, "all")
    assert round_one == ["[green]Kind:[/green] Alice helps Bob"]


@pytest.mark.parametrize(
    ("style", "line", "label"),
    [
        ("all", "Alice offers a trade", "[cyan]Trade:[/cyan]"),
        ("all", "Bob toasts Alice", "[yellow]Toast:[/yellow]"),
        ("all", "Treaty t_0001 BROKEN by Bob", "[red]Treaty broken:[/red]"),
        ("all", "Alice wins by prosperity!", "[bold green]"),
        ("cozy", "Bob toasts Alice", "[yellow]Toast:[/yellow]"),
        ("cozy", "Bob kept their promise", "[green]Kept:[/green]"),
        ("spicy", "Alice offers a trade", "[cyan]Trade:[/cyan]"),
        ("spicy", "Bob defaults on a deal", "[red]Default:[/red]"),
        ("spicy", "Treaty BROKEN", "[red]Treaty broken:[/red]"),
        ("economic", "Bob sells food", "[cyan]Sell:[/cyan]"),
        ("economic", "Market shifted", "[dim]Market:[/dim]"),
    ],
)
def test_postcard_highlights_label_per_pattern(style: str, line: str, label: str) -> None:
    state = _make_state()
    state.log = [f"R1T0: {line}"]
    assert cli_main._postcard_highlights(state, 1, style) == [f"{label} {line}"]


def test_postcard_highlights_all_style_labels_honored_treaties() -> None:
    # Regression: the matcher was the regex "Treaty.*honored" compared with
    # `in`, so "Treaty kept" never appeared (fixed 2.3.3).
    state = _make_state()
    state.log = ["R1T0: Treaty t_0001 honored"]
    assert cli_main._postcard_highlights(state, 1, "all") == [
        "[green]Treaty kept:[/green] Treaty t_0001 honored"
    ]


def test_postcard_highlights_ignores_unmatched_and_other_rounds() -> None:
    state = _make_state()
    state.log = ["R1T0: Nothing notable here", "R5T0: Alice helps Bob"]
    assert cli_main._postcard_highlights(state, 1, "all") == []


# ---------------------------------------------------------------------------
# _calc_story_points
# ---------------------------------------------------------------------------


def test_calc_story_points_awards_every_category() -> None:
    state = _make_state(players=["Alice", "Bob", "Cara"])
    state.winner = "Alice"
    state.log = [
        "R1T0: Alice kept their promise: share",
        "R1T1: Alice kept their promise: lend",
        "R1T2: Bob kept their promise: wave",
        "R2T0: Bob helps Cara",
        "R2T1: Cara helps Bob",
        "R2T2: Cara helps Alice",
        "R3T0: Table's Choice (MVP): Vote: Cara",
        "R3T1: Treaty t_0001 honored by Bob",
        "R3T2: Treaty t_0002 honored by Bob",
    ]
    points = cli_main._calc_story_points(state)
    assert points["Alice"] == {
        "winner": 1,
        "promise_keeper": 1,
        "most_helpful": 0,
        "tables_choice": 0,
        "treaty_keeper": 0,
    }
    assert points["Bob"]["promise_keeper"] == 0  # 1 kept vs Alice's 2
    assert points["Bob"]["treaty_keeper"] == 1
    assert points["Cara"]["most_helpful"] == 1  # 2 helps vs Bob's 1
    assert points["Cara"]["tables_choice"] == 1
    assert points["Cara"]["winner"] == 0


def test_calc_story_points_ties_share_the_award() -> None:
    state = _make_state()
    state.log = ["R1T0: Alice helps Bob", "R1T1: Bob helps Alice"]
    points = cli_main._calc_story_points(state)
    assert points["Alice"]["most_helpful"] == 1
    assert points["Bob"]["most_helpful"] == 1


def test_calc_story_points_empty_log_and_unknown_winner_award_nothing() -> None:
    state = _make_state()
    state.winner = "Nobody"
    points = cli_main._calc_story_points(state)
    assert all(sum(a.values()) == 0 for a in points.values())


# ---------------------------------------------------------------------------
# season document helpers
# ---------------------------------------------------------------------------


def _season_path(tmp_path: Path) -> Path:
    return tmp_path / ".sov" / "season.json"


def _write_season(tmp_path: Path, payload: object) -> Path:
    path = _season_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    path.write_text(text, encoding="utf-8")
    return path


def test_read_season_document_missing_file_is_empty_skeleton() -> None:
    assert cli_main._read_season_document() == {"games": [], "standings": {}}


@pytest.mark.parametrize("raw", ["{not json", "[1, 2, 3]", '"a string"'])
def test_read_season_document_malformed_or_non_dict_is_empty(tmp_path: Path, raw: str) -> None:
    _write_season(tmp_path, raw)
    assert cli_main._read_season_document() == {"games": [], "standings": {}}


def test_read_season_document_unreadable_path_is_empty(tmp_path: Path) -> None:
    # A directory where the file should be: exists() is True, read_text raises OSError.
    _season_path(tmp_path).mkdir(parents=True)
    assert cli_main._read_season_document() == {"games": [], "standings": {}}


# strict=True is the doctor's read: corruption raises instead of reading empty.


def test_read_season_document_strict_missing_file_is_still_empty() -> None:
    assert cli_main._read_season_document(strict=True) == {"games": [], "standings": {}}


@pytest.mark.parametrize(
    ("raw", "detail"),
    [
        ("{not json", "JSONDecodeError"),
        ("[1, 2, 3]", "not an object"),
        ('{"schema_version": 1, "season": []}', "`season` is not an object"),
        ('{"games": {}, "standings": {}}', "`games` is missing or not a list"),
        ('{"standings": {}}', "`games` is missing or not a list"),
    ],
)
def test_read_season_document_strict_raises_on_corruption(
    tmp_path: Path, raw: str, detail: str
) -> None:
    _write_season(tmp_path, raw)
    with pytest.raises(cli_main.SeasonDocumentError, match=re.escape(detail)):
        cli_main._read_season_document(strict=True)


def test_read_season_document_strict_raises_on_unreadable_path(tmp_path: Path) -> None:
    _season_path(tmp_path).mkdir(parents=True)
    with pytest.raises(cli_main.SeasonDocumentError):
        cli_main._read_season_document(strict=True)


def test_read_season_document_strict_accepts_both_valid_shapes(tmp_path: Path) -> None:
    _write_season(tmp_path, {"games": [{"id": "s1"}], "standings": {}})
    assert cli_main._read_season_document(strict=True)["games"] == [{"id": "s1"}]
    _write_season(tmp_path, {"schema_version": 1, "season": {"games": [], "standings": {}}})
    assert cli_main._read_season_document(strict=True) == {"games": [], "standings": {}}


def test_read_season_document_wrapped_form_returns_inner_season(tmp_path: Path) -> None:
    inner = {"games": [{"game_id": "s1"}], "standings": {"Alice": 2}}
    _write_season(tmp_path, {"schema_version": 1, "season": inner})
    assert cli_main._read_season_document() == inner


def test_read_season_document_wrapped_with_bad_inner_is_empty(tmp_path: Path) -> None:
    _write_season(tmp_path, {"schema_version": 1, "season": ["nope"]})
    assert cli_main._read_season_document() == {"games": [], "standings": {}}


def test_read_season_document_bare_v0_form_is_returned_as_is(tmp_path: Path) -> None:
    bare = {"games": [{"game_id": "s9"}], "standings": {"Bob": 1}}
    _write_season(tmp_path, bare)
    assert cli_main._read_season_document() == bare


def test_update_season_migrates_bare_dict_to_wrapped_form(tmp_path: Path) -> None:
    _write_season(tmp_path, {"games": [{"game_id": "s9"}], "standings": {"Alice": 3}})
    state = _make_state()
    state.winner = "Alice"
    state.log = [
        "R1T0: Table's Choice (MVP): Vote: Bob",
        "R1T1: Chaos Gremlin: Vote: Alice",
        "R1T2: Best Promise: Vote: Bob",
    ]
    points = cli_main._calc_story_points(state)
    season = cli_main._update_season(state, points)

    on_disk = json.loads(_season_path(tmp_path).read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == 1
    assert on_disk["season"] == season
    assert [g["game_id"] for g in season["games"]] == ["s9", "s42"]
    record = season["games"][-1]
    assert record["winner"] == "Alice"
    assert record["ruleset"] == "campfire_v1"
    assert record["votes"] == {
        "mvp": "Table's Choice (MVP): Vote: Bob",
        "chaos": "Chaos Gremlin: Vote: Alice",
        "promise": "Best Promise: Vote: Bob",
    }
    # Alice: winner(1) + Bob: tables_choice(1); standings accumulate across games.
    assert season["standings"] == {"Alice": 4, "Bob": 1}


def test_update_season_without_games_key_resets_skeleton(tmp_path: Path) -> None:
    _write_season(tmp_path, {"unrelated": True})
    state = _make_state()
    season = cli_main._update_season(state, cli_main._calc_story_points(state))
    assert [g["game_id"] for g in season["games"]] == ["s42"]
    assert season["standings"] == {"Alice": 0, "Bob": 0}


# ---------------------------------------------------------------------------
# game-end
# ---------------------------------------------------------------------------


def test_game_end_no_game_fails_with_hint() -> None:
    result = runner.invoke(app, ["game-end"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "No active game found" in out
    assert "sov new -p Alice -p Bob" in out


def test_game_end_finished_game_records_points_season_and_final_proof(tmp_path: Path) -> None:
    state = _make_state(players=["Alice", "Bob", "Cara"])
    state.game_over = True
    state.winner = "Alice"
    state.log = [
        "R1T0: Bob kept their promise: wave",
        "R2T0: Cara helps Bob",
        "R3T0: Table's Choice (MVP): Vote: Cara",
    ]
    game_id = _plant(state, tmp_path)

    result = runner.invoke(app, ["game-end"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Final Scores — Campfire" in out
    assert "Alice wins!" in out
    assert "Story Points" in out
    assert "Promise Keeper Bob" in out
    assert "Most Helpful Cara" in out
    assert "Table's Choice Cara" in out
    assert "Treaty Keeper" in out  # row present, no winner
    assert "Alice: 1 Story Points" in out
    assert "Cara: 2 Story Points" in out
    assert "Final proof:" in out
    assert "That's a wrap" in out
    assert "Season Standings" not in out  # first game of the season

    final = proofs_dir(game_id) / "final.proof.json"
    proof = json.loads(final.read_text(encoding="utf-8"))
    assert proof["final"] is True
    assert proof["envelope_hash"] in out.replace(" ", "")

    season = json.loads(_season_path(tmp_path).read_text(encoding="utf-8"))
    assert season["schema_version"] == 1
    assert season["season"]["standings"] == {"Alice": 1, "Bob": 1, "Cara": 2}

    pending = json.loads(pending_anchors_path(game_id).read_text(encoding="utf-8"))
    assert pending["entries"]["FINAL"]["envelope_hash"] == proof["envelope_hash"]


def test_game_end_prints_votes_from_log(tmp_path: Path) -> None:
    state = _make_state()
    state.game_over = True
    state.winner = "Bob"
    state.log = ["R2T0: Chaos Gremlin: Vote: Alice"]
    _plant(state, tmp_path)
    result = runner.invoke(app, ["game-end"])
    assert result.exit_code == 0, result.output
    assert "Vote: Alice" in _norm(result.output)


def test_game_end_unfinished_game_is_ended_by_tiebreak(tmp_path: Path) -> None:
    state = _make_state()
    state.players[1].coins = 9  # Bob leads on combined score, nobody has hit a win condition
    game_id = _plant(state, tmp_path)
    result = runner.invoke(app, ["game-end"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Bob wins!" in out
    saved = json.loads(state_file(game_id).read_text(encoding="utf-8"))
    assert saved["game_over"] is True
    assert saved["winner"] == "Bob"
    assert any("wins by tiebreak" in entry for entry in saved["log"])


def test_game_end_unfinished_game_with_win_condition_met(tmp_path: Path) -> None:
    state = _make_state()
    state.players[0].coins = 25  # PROSPERITY threshold is 20
    game_id = _plant(state, tmp_path)
    result = runner.invoke(app, ["game-end"])
    assert result.exit_code == 0, result.output
    assert "Alice wins!" in _norm(result.output)
    saved = json.loads(state_file(game_id).read_text(encoding="utf-8"))
    assert saved["winner"] == "Alice"
    assert any("wins by" in e and "tiebreak" not in e for e in saved["log"])


def test_game_end_town_hall_shows_resource_column(tmp_path: Path) -> None:
    state = _make_state("town-hall", players=["Alice", "Bob", "Cara"])
    state.game_over = True
    state.winner = "Alice"
    state.players[0].resources["wood"] = 3
    state.players[0].resources["tools"] = 1
    _plant(state, tmp_path)
    result = runner.invoke(app, ["game-end"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Final Scores — Town Hall" in out
    assert "Resources" in out
    assert "3W 1T" in out
    assert " - " in out  # players without resources render a dash


def test_game_end_second_game_shows_season_standings(tmp_path: Path) -> None:
    first = _make_state(seed=1)
    first.game_over = True
    first.winner = "Alice"
    _plant(first, tmp_path)
    assert runner.invoke(app, ["game-end"]).exit_code == 0

    second = _make_state(seed=2)
    second.game_over = True
    second.winner = "Alice"
    _plant(second, tmp_path)
    result = runner.invoke(app, ["game-end"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Season Standings (Game 2)" in out
    assert "Alice 2" in out  # winner point from both games
    season = json.loads(_season_path(tmp_path).read_text(encoding="utf-8"))["season"]
    assert [g["game_id"] for g in season["games"]] == ["s1", "s2"]
    assert season["standings"]["Alice"] == 2


def test_game_end_anchor_without_wallet_seed_explains_options(tmp_path: Path) -> None:
    state = _make_state()
    state.game_over = True
    state.winner = "Alice"
    game_id = _plant(state, tmp_path)
    factory = _transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["game-end", "--anchor"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "No wallet seed found for anchoring" in out
    assert "`sov wallet`" in out or "sov wallet" in out
    assert "The final proof is already saved locally" in out
    factory.return_value.anchor_batch.assert_not_called()
    assert (proofs_dir(game_id) / "final.proof.json").is_file()


def test_game_end_anchor_flushes_final_in_one_tx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    state = _make_state()
    state.game_over = True
    state.winner = "Alice"
    game_id = _plant(state, tmp_path)
    factory = _transport_factory([["FINALTX"]])
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["game-end", "--anchor"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Anchoring 1 pending round..." in out
    assert "Anchored. TX: FINALTX" in out
    assert "https://explorer.example/FINALTX" in out

    (call,) = factory.return_value.anchor_batch.call_args_list
    entries, seed = call.args
    assert seed == _TEST_SEED
    assert [e["round_key"] for e in entries] == ["FINAL"]
    assert entries[0]["game_id"] == game_id
    assert entries[0]["ruleset"] == "campfire_v1"

    anchors = json.loads(anchors_file(game_id).read_text(encoding="utf-8"))
    assert anchors["entries"]["FINAL"] == "FINALTX"
    pending = json.loads(pending_anchors_path(game_id).read_text(encoding="utf-8"))
    assert pending["entries"] == {}


def test_game_end_anchor_chunks_rounds_and_orders_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    state = _make_state()
    state.game_over = True
    state.winner = "Alice"
    game_id = _plant(state, tmp_path)
    for n in range(1, 9):  # rounds 1..8 + FINAL + one odd key = 10 entries -> 2 chunks
        add_pending_anchor(game_id, str(n), _HASH)
    add_pending_anchor(game_id, "weird", _HASH)

    factory = _transport_factory([["TXCHUNK1"], ["TXCHUNK2"]])
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["game-end", "--anchor"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Anchoring 10 pending rounds..." in out
    assert "Anchored across 2 txs" in out
    assert "TX 1/2: TXCHUNK1" in out
    assert "TX 2/2: TXCHUNK2" in out

    first, second = factory.return_value.anchor_batch.call_args_list
    first_keys = [e["round_key"] for e in first.args[0]]
    second_keys = [e["round_key"] for e in second.args[0]]
    # ints ascending, then FINAL, then unparseable keys last.
    assert first_keys == ["1", "2", "3", "4", "5", "6", "7", "8"]
    assert second_keys == ["FINAL", "weird"]


def test_game_end_anchor_with_nothing_pending(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    state = _make_state()
    state.game_over = True
    state.winner = "Alice"
    game_id = _plant(state, tmp_path)
    # FINAL is already recorded on chain, so heal-on-read drops it from pending.
    record_anchors(game_id, {"FINAL": "PRIORTX"})
    factory = _transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["game-end", "--anchor"])
    assert result.exit_code == 0, result.output
    assert "No pending anchors to flush." in _norm(result.output)
    factory.return_value.anchor_batch.assert_not_called()


def test_game_end_anchor_failure_exits_one_and_keeps_local_proof(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XRPL_SEED", _TEST_SEED)
    state = _make_state()
    state.game_over = True
    state.winner = "Alice"
    game_id = _plant(state, tmp_path)
    factory = _transport_factory()
    factory.return_value.anchor_batch.side_effect = RuntimeError("ledger unreachable")
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["game-end", "--anchor"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "Anchor submission failed: ledger unreachable" in out
    assert "Retry with sov anchor" in out
    assert "That's a wrap" not in out
    assert (proofs_dir(game_id) / "final.proof.json").is_file()
    pending = json.loads(pending_anchors_path(game_id).read_text(encoding="utf-8"))
    assert "FINAL" in pending["entries"]  # not cleared, so a retry can submit it


# ---------------------------------------------------------------------------
# season-postcard
# ---------------------------------------------------------------------------


def _game_record(
    n: int,
    winner: str,
    *,
    awards: dict[str, dict[str, int]] | None = None,
    votes: dict[str, str] | None = None,
    ruleset: str = "campfire_v1",
) -> dict[str, Any]:
    return {
        "game_id": f"s{n}",
        "ruleset": ruleset,
        "players": ["Alice", "Bob"],
        "winner": winner,
        "rounds": 10 + n,
        "awards": awards or {},
        "votes": votes or {},
    }


def test_season_postcard_without_file_shows_empty_state() -> None:
    result = runner.invoke(app, ["season-postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "No season yet." in out
    assert "sov game-end" in out


def test_season_postcard_file_with_no_games_shows_empty_state(tmp_path: Path) -> None:
    _write_season(tmp_path, {"schema_version": 1, "season": {"games": [], "standings": {}}})
    result = runner.invoke(app, ["season-postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "No games recorded yet." in out
    assert "sov game-end" in out


def test_season_postcard_malformed_file_is_treated_as_empty(tmp_path: Path) -> None:
    _write_season(tmp_path, "{broken")
    result = runner.invoke(app, ["season-postcard"])
    assert result.exit_code == 0, result.output
    assert "No games recorded yet." in _norm(result.output)


def test_season_postcard_single_game_has_no_champion(tmp_path: Path) -> None:
    season = {
        "games": [_game_record(1, "Alice", ruleset="town_hall_v1")],
        "standings": {"Alice": 2, "Bob": 1},
    }
    _write_season(tmp_path, {"schema_version": 1, "season": season})
    result = runner.invoke(app, ["season-postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Season Standings (1 game)" in out
    assert "Season Champion" not in out
    assert "Game 1: Town Hall — Alice won (round 11)" in out
    assert "Season Postcard" in out


def test_season_postcard_three_games_names_champion_awards_and_votes(tmp_path: Path) -> None:
    awards = {
        "Alice": {"winner": 1, "promise_keeper": 1, "most_helpful": 0, "tables_choice": 0},
        "Bob": {"winner": 0, "promise_keeper": 0, "most_helpful": 1, "tables_choice": 1},
    }
    season = {
        "games": [
            _game_record(1, "Alice", awards=awards, votes={"mvp": "MVP vote: Bob"}),
            _game_record(2, "Alice", awards=awards, ruleset="market_day_v1"),
            _game_record(3, "Bob", awards=awards, votes={"chaos": "Chaos vote: Alice"}),
        ],
        "standings": {"Bob": 3, "Alice": 6},
    }
    _write_season(tmp_path, season)  # bare v0 shape is accepted too
    result = runner.invoke(app, ["season-postcard"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Season Standings (3 games)" in out
    assert "Season Champion: Alice" in out
    assert "Award Totals" in out
    # Alice: 3 wins/3 promise; Bob: 3 helpful/3 MVP across the three games.
    assert re.search(r"Alice 3 3 0 0", out)
    assert re.search(r"Bob 0 0 3 3", out)
    assert "Game 2: Market Day — Alice won (round 12)" in out
    assert "Game 3: Campfire — Bob won (round 13)" in out
    assert "MVP vote: Bob" in out and "Chaos vote: Alice" in out


def test_season_postcard_tied_champions(tmp_path: Path) -> None:
    season = {
        "games": [_game_record(1, "Alice"), _game_record(2, "Bob"), _game_record(3, "Alice")],
        "standings": {"Alice": 4, "Bob": 4},
    }
    _write_season(tmp_path, {"schema_version": 1, "season": season})
    result = runner.invoke(app, ["season-postcard"])
    assert result.exit_code == 0, result.output
    assert "Tied for Season Champion: Alice, Bob" in _norm(result.output)


def test_season_postcard_tolerates_sparse_game_records(tmp_path: Path) -> None:
    season = {"games": [{}], "standings": {"Alice": 1}}
    _write_season(tmp_path, season)
    result = runner.invoke(app, ["season-postcard"])
    assert result.exit_code == 0, result.output
    assert "Game 1: ? — ? won (round ?)" in _norm(result.output)


# ---------------------------------------------------------------------------
# share codes
# ---------------------------------------------------------------------------


def test_build_share_code_uses_dash_for_empty_recipe() -> None:
    assert cli_main._build_share_code("cozy-night", "campfire", "cozy", 7) == (
        "SOV|cozy-night|campfire|cozy|s7"
    )
    assert cli_main._build_share_code("custom", "town-hall", "", 9) == "SOV|custom|town-hall|-|s9"


def test_parse_share_code_round_trips_and_normalises_dash_recipe() -> None:
    parsed = cli_main._parse_share_code("  SOV|custom|town-hall|-|s9  ")
    assert parsed == {"slug": "custom", "tier": "town-hall", "recipe": "", "seed": "9"}
    code = cli_main._build_share_code("cozy-night", "campfire", "cozy", 1234)
    assert cli_main._parse_share_code(code) == {
        "slug": "cozy-night",
        "tier": "campfire",
        "recipe": "cozy",
        "seed": "1234",
    }


@pytest.mark.parametrize(
    ("code", "fragment"),
    [
        ("garbage", "Invalid share code"),
        ("SOV|a|b|c", "Invalid share code"),
        ("XYZ|a|b|c|s1", "Invalid share code"),
        ("SOV|a|b|c|42", "Invalid seed in share code: '42'"),
        ("SOV|a|b|c|sabc", "Invalid seed in share code: 'sabc'"),
        ("SOV|a|b|c|s", "Invalid seed in share code: 's'"),
    ],
)
def test_parse_share_code_rejects_bad_codes(code: str, fragment: str) -> None:
    parsed = cli_main._parse_share_code(code)
    assert isinstance(parsed, str)
    assert fragment in parsed


# ---------------------------------------------------------------------------
# scenario
# ---------------------------------------------------------------------------


def test_scenario_list_shows_all_packs() -> None:
    result = runner.invoke(app, ["scenario", "list"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Scenario Packs" in out
    for name in ("Cozy Night", "Market Panic", "Promises Matter", "Treaty Night"):
        assert name in out
    assert "docs/scenarios/<name>.md" in out


def test_scenario_code_known_slug_prints_share_code() -> None:
    result = runner.invoke(app, ["scenario", "code", "cozy-night", "--seed", "7"])
    assert result.exit_code == 0, result.output
    assert "SOV|cozy-night|campfire|cozy|s7" in result.output
    assert 'sov new --code "SOV|cozy-night|campfire|cozy|s7"' in _norm(result.output)


def test_scenario_code_defaults_to_seed_42_and_dash_recipe() -> None:
    result = runner.invoke(app, ["scenario", "code", "treaty-night"])
    assert result.exit_code == 0, result.output
    assert "SOV|treaty-night|treaty-table|-|s42" in result.output


def test_scenario_code_custom_with_tier_and_recipe() -> None:
    result = runner.invoke(
        app,
        ["scenario", "code", "custom", "-t", "town-hall", "-r", "spicy", "-s", "5"],
    )
    assert result.exit_code == 0, result.output
    assert "SOV|custom|town-hall|spicy|s5" in result.output


def test_scenario_code_generated_code_is_accepted_by_new() -> None:
    generated = runner.invoke(app, ["scenario", "code", "market-panic", "--seed", "11"])
    code = re.search(r"SOV\|[^\s\[]+", generated.output)
    assert code is not None
    started = runner.invoke(app, ["new", "--code", code.group(0), "-p", "A", "-p", "B", "-p", "C"])
    assert started.exit_code == 0, started.output
    assert state_file("s11").is_file()


def test_scenario_code_requires_name() -> None:
    result = runner.invoke(app, ["scenario", "code"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "Usage: sov scenario code <name> --seed N" in out
    assert "sov scenario list" in out


def test_scenario_code_custom_requires_tier() -> None:
    result = runner.invoke(app, ["scenario", "code", "custom"])
    assert result.exit_code == 1
    assert "Custom codes need --tier." in _norm(result.output)


def test_scenario_code_unknown_name_lists_known_slugs() -> None:
    result = runner.invoke(app, ["scenario", "code", "nope"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "Unknown scenario 'nope'" in out
    assert "cozy-night" in out and "custom" in out


def test_scenario_unknown_action_exits_one() -> None:
    result = runner.invoke(app, ["scenario", "frobnicate"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "Unknown action: 'frobnicate'." in out
    assert "scenario list/code/lint" in out


_GOOD_SCENARIO = """# Test Scenario

> A long enough vibe intro that reads like a real scenario blurb for players.

| Setting | Value |
|---------|-------|
| Tier | Campfire |
| Recipe | cozy |
| Players | 2-4 |
| Rounds | 8-10 |
| Time | 30-45 min |

## What to expect

Stuff happens.

## Start command

```bash
sov new -p A -p B
```

## What success feels like

Good.

## After the game

Postcard.

## Table norms

Be kind.
"""


def _write_scenario(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_lint_scenario_good_file_has_no_issues(tmp_path: Path) -> None:
    path = _write_scenario(tmp_path, "good.md", _GOOD_SCENARIO)
    assert cli_main._lint_scenario(str(path)) == []


def test_lint_scenario_missing_file(tmp_path: Path) -> None:
    missing = str(tmp_path / "nope.md")
    assert cli_main._lint_scenario(missing) == [("error", f"File not found: {missing}")]


def test_lint_scenario_empty_file_reports_every_structural_error(tmp_path: Path) -> None:
    path = _write_scenario(tmp_path, "empty.md", "")
    issues = cli_main._lint_scenario(str(path))
    errors = [m for lvl, m in issues if lvl == "error"]
    warns = [m for lvl, m in issues if lvl == "warn"]
    assert "Missing: H1 heading (scenario name)" in errors
    assert "Missing: Block quote (vibe intro)" in errors
    assert "Missing: ## What to expect" in errors
    assert "Missing: ## Start command" in errors
    assert any(m.startswith("Settings table missing rows:") for m in errors)
    assert warns == [
        "Missing: ## What success feels like",
        "Missing: ## After the game",
        "Missing: ## Table norms",
    ]


def test_lint_scenario_start_command_without_code_block(tmp_path: Path) -> None:
    text = _GOOD_SCENARIO.replace("```bash\nsov new -p A -p B\n```", "just words")
    path = _write_scenario(tmp_path, "nocode.md", text)
    assert ("error", "Start command section has no code block") in cli_main._lint_scenario(
        str(path)
    )


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("| Tier | Campfire |", "| Tier | Dungeon |", 'Invalid tier: "Dungeon"'),
        ("| Recipe | cozy |", "| Recipe | bland |", 'Invalid recipe: "bland"'),
        ("| Players | 2-4 |", "| Players | many |", 'Invalid players format: "many"'),
        ("| Time | 30-45 min |", "| Time | 2 hours |", "Invalid time"),
    ],
)
def test_lint_scenario_invalid_field_values(
    tmp_path: Path, old: str, new: str, fragment: str
) -> None:
    path = _write_scenario(tmp_path, "bad.md", _GOOD_SCENARIO.replace(old, new))
    errors = [m for lvl, m in cli_main._lint_scenario(str(path)) if lvl == "error"]
    assert any(fragment in m for m in errors), errors


def test_lint_scenario_vibe_intro_length_warnings(tmp_path: Path) -> None:
    short = _GOOD_SCENARIO.replace(
        "> A long enough vibe intro that reads like a real scenario blurb for players.",
        "> Too short.",
    )
    long_ = _GOOD_SCENARIO.replace(
        "> A long enough vibe intro that reads like a real scenario blurb for players.",
        "> " + "word " * 120,
    )
    short_warns = [
        m for lvl, m in cli_main._lint_scenario(str(_write_scenario(tmp_path, "s.md", short)))
    ]
    long_warns = [
        m for lvl, m in cli_main._lint_scenario(str(_write_scenario(tmp_path, "l.md", long_)))
    ]
    assert any(m.startswith("Vibe intro too short (") for m in short_warns)
    assert any(m.startswith("Vibe intro too long (") for m in long_warns)


def test_lint_scenario_recipe_with_thin_deck_warns(tmp_path: Path) -> None:
    from sov_engine.content import build_deal_deck, build_event_deck

    events, deals = build_event_deck(), build_deal_deck()
    thin = [
        tag
        for tag in ("cozy", "spicy", "market", "promise")
        if sum(tag in e.tags for e in events) < 5 or sum(tag in d.tags for d in deals) < 3
    ]
    if not thin:
        pytest.skip("every recipe has a full deck in this content pack")
    tag = thin[0]
    text = _GOOD_SCENARIO.replace("| Recipe | cozy |", f"| Recipe | {tag} |")
    warns = [m for lvl, m in cli_main._lint_scenario(str(_write_scenario(tmp_path, "t.md", text)))]
    assert any(m.startswith(f"Recipe '{tag}': only ") for m in warns)


def test_lint_scenario_recipe_deck_warnings_from_small_content_pack(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import sov_engine.content as content

    monkeypatch.setattr(content, "build_event_deck", lambda: [])
    monkeypatch.setattr(content, "build_deal_deck", lambda: [])
    path = _write_scenario(tmp_path, "g.md", _GOOD_SCENARIO)
    issues = cli_main._lint_scenario(str(path))
    assert ("warn", "Recipe 'cozy': only 0 matching events (< 5, full deck will be used)") in issues
    assert ("warn", "Recipe 'cozy': only 0 matching deals (< 3, full deck will be used)") in issues


def test_scenario_lint_named_file_passes(tmp_path: Path) -> None:
    path = _write_scenario(tmp_path, "good.md", _GOOD_SCENARIO)
    result = runner.invoke(app, ["scenario", "lint", str(path)])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Structure OK" in out
    assert "1 file(s) checked, 1 passed, 0 failed." in out


def test_scenario_lint_named_file_fails_with_errors_and_warnings(tmp_path: Path) -> None:
    text = _GOOD_SCENARIO.replace("| Tier | Campfire |", "| Tier | Dungeon |").replace(
        "## Table norms", "## Something else"
    )
    path = _write_scenario(tmp_path, "bad.md", text)
    result = runner.invoke(app, ["scenario", "lint", str(path)])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert 'FAIL Invalid tier: "Dungeon"' in out
    assert "WARN Missing: ## Table norms" in out
    assert "1 file(s) checked, 0 passed, 1 failed." in out


def test_scenario_lint_missing_named_file_counts_as_failure(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scenario", "lint", str(tmp_path / "ghost.md")])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "File not found:" in out
    assert "0 passed, 1 failed" in out


def test_scenario_lint_without_directory_fails(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scenario", "lint"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "docs/scenarios/ not found." in out
    assert "sov scenario list" in out


def test_scenario_lint_directory_with_only_excluded_files_fails(tmp_path: Path) -> None:
    scenarios = tmp_path / "docs" / "scenarios"
    scenarios.mkdir(parents=True)
    for name in ("README.md", "CANON.md", "_TEMPLATE.md"):
        (scenarios / name).write_text("# ignored\n", encoding="utf-8")
    result = runner.invoke(app, ["scenario", "lint"])
    assert result.exit_code == 1
    assert "No scenario files found." in _norm(result.output)


def test_scenario_lint_directory_lints_every_scenario_but_skips_excluded(
    tmp_path: Path,
) -> None:
    scenarios = tmp_path / "docs" / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "a.md").write_text(_GOOD_SCENARIO, encoding="utf-8")
    (scenarios / "b.md").write_text(_GOOD_SCENARIO, encoding="utf-8")
    (scenarios / "README.md").write_text("not a scenario", encoding="utf-8")
    result = runner.invoke(app, ["scenario", "lint"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "2 file(s) checked, 2 passed, 0 failed." in out
    assert "README.md" not in out


# ---------------------------------------------------------------------------
# games / resume helpers
# ---------------------------------------------------------------------------


def _plant_v2(seed: int, *, ruleset: str = "campfire_v1", round_: int = 1) -> str:
    game_id = f"s{seed}"
    game_dir(game_id).mkdir(parents=True, exist_ok=True)
    state_file(game_id).write_text(
        json.dumps(
            {
                "config": {"seed": seed, "ruleset": ruleset, "max_rounds": 15},
                "current_round": round_,
                "players": [{"name": "Alice"}, {"name": "Bob"}],
                "schema_version": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rng_seed_file(game_id).write_text(str(seed), encoding="utf-8")
    return game_id


def test_summary_to_dict_shape() -> None:
    from sov_engine.io_utils import GameSummary

    summary = GameSummary(
        game_id="s3",
        ruleset="campfire_v1",
        current_round=4,
        max_rounds=15,
        players=("Alice", "Bob"),
        last_modified_iso="2026-01-02T03:04:05Z",
    )
    assert cli_main._summary_to_dict(summary) == {
        "game_id": "s3",
        "ruleset": "campfire_v1",
        "current_round": 4,
        "max_rounds": 15,
        "players": ["Alice", "Bob"],
        "last_modified_iso": "2026-01-02T03:04:05Z",
    }


@pytest.mark.parametrize(
    ("iso", "expected"),
    [
        ("2026-01-02T03:04:05Z", "2026-01-02 03:04 UTC"),
        ("yesterday-ish", "yesterday-ish"),
        ("", ""),
    ],
)
def test_format_last_played(iso: str, expected: str) -> None:
    assert cli_main._format_last_played(iso) == expected


def test_format_last_played_none_falls_back_to_input() -> None:
    assert cli_main._format_last_played(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# games
# ---------------------------------------------------------------------------


def test_games_empty_shows_recovery_hint() -> None:
    result = runner.invoke(app, ["games"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "No saved games." in out
    assert "sov tutorial" in out and "sov play campfire_v1" in out


def test_games_empty_json_is_empty_list() -> None:
    result = runner.invoke(app, ["games", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []


def test_games_json_marks_active_game(tmp_path: Path) -> None:
    _plant_v2(1)
    _plant_v2(2, ruleset="town_hall_v1", round_=3)
    active_game_pointer_path().write_text("s2", encoding="utf-8")
    result = runner.invoke(app, ["games", "--json"])
    assert result.exit_code == 0, result.output
    payload = {entry["game_id"]: entry for entry in json.loads(result.output)}
    assert set(payload) == {"s1", "s2"}
    assert payload["s2"]["active"] is True
    assert payload["s1"]["active"] is False
    assert payload["s2"]["ruleset"] == "town_hall_v1"
    assert payload["s2"]["current_round"] == 3
    assert payload["s2"]["players"] == ["Alice", "Bob"]


def test_games_table_lists_rounds_players_and_active_marker(tmp_path: Path) -> None:
    _plant_v2(1, round_=4)
    _plant_v2(2)
    active_game_pointer_path().write_text("s1", encoding="utf-8")
    result = runner.invoke(app, ["games"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Saved Games" in out
    assert re.search(r"s1 campfire_v1 4/15 Alice, Bob \d{4}-\d\d-\d\d \d\d:\d\d UTC \*", out)
    assert "s2" in out
    assert "No active game pointer" not in out


def test_games_without_active_pointer_prompts_resume(tmp_path: Path) -> None:
    _plant_v2(1)
    _plant_v2(2)  # two games, no pointer
    result = runner.invoke(app, ["games"])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "No active game pointer." in out
    assert "sov resume <game-id>" in out


def test_games_ignores_junk_directories(tmp_path: Path) -> None:
    _plant_v2(1)
    (tmp_path / ".sov" / "games" / "not-a-game").mkdir(parents=True)
    (tmp_path / ".sov" / "games" / "s9").mkdir(parents=True)  # no state.json
    result = runner.invoke(app, ["games", "--json"])
    assert result.exit_code == 0, result.output
    assert [e["game_id"] for e in json.loads(result.output)] == ["s1"]


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["s17/../s42", "..", "42", "s", "sabc", "s1\\s2"])
def test_resume_rejects_malformed_game_id(tmp_path: Path, bad: str) -> None:
    _plant_v2(42)
    result = runner.invoke(app, ["resume", bad])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "Invalid game-id:" in out
    assert "sov games" in out
    assert not active_game_pointer_path().exists()


def test_resume_unknown_game_points_at_games_listing() -> None:
    result = runner.invoke(app, ["resume", "s404"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "No saved game with id 's404'." in out
    assert "sov games" in out


def test_resume_switches_active_pointer_and_reports_state() -> None:
    _plant_v2(1)
    _plant_v2(2, ruleset="town_hall_v1", round_=6)
    result = runner.invoke(app, ["resume", "s2"])
    assert result.exit_code == 0, result.output
    assert "Switched to game s2 (round 6/15, ruleset town_hall_v1)." in _norm(result.output)
    assert active_game_pointer_path().read_text(encoding="utf-8").strip() == "s2"


def test_resume_with_unreadable_state_still_switches_pointer(tmp_path: Path) -> None:
    game_id = _plant_v2(5)
    state_file(game_id).write_text("{ this is not json", encoding="utf-8")
    result = runner.invoke(app, ["resume", game_id])
    assert result.exit_code == 0, result.output
    out = _norm(result.output)
    assert "Switched to game s5." in out
    assert "round" not in out
    assert active_game_pointer_path().read_text(encoding="utf-8").strip() == "s5"


def test_resume_with_non_object_state_still_switches_pointer(tmp_path: Path) -> None:
    # Regression: a list-shaped state.json raised AttributeError on .get()
    # and crashed resume after the pointer moved (fixed 2.3.3).
    game_id = _plant_v2(6)
    state_file(game_id).write_text("[]", encoding="utf-8")
    result = runner.invoke(app, ["resume", game_id])
    assert result.exit_code == 0, result.output
    assert "Switched to game s6." in _norm(result.output)
    assert active_game_pointer_path().read_text(encoding="utf-8").strip() == "s6"


# ---------------------------------------------------------------------------
# feedback
# ---------------------------------------------------------------------------


def test_feedback_no_game_fails_with_hint() -> None:
    result = runner.invoke(app, ["feedback"])
    assert result.exit_code == 1
    out = _norm(result.output)
    assert "No active game found" in out
    assert "sov new -p Alice -p Bob" in out


def test_feedback_minimal_report_for_fresh_game(tmp_path: Path) -> None:
    _plant(_make_state(), tmp_path)
    result = runner.invoke(app, ["feedback"])
    assert result.exit_code == 0, result.output
    out = result.output
    assert "## Sovereignty Play Report" in out
    assert "| Tier | Campfire |" in out
    assert "| Recipe | — |" in out
    assert "| Seed | 42 |" in out
    assert "| Players | 2 |" in out
    assert "| Rounds | 1 |" in out
    assert "| Winner | (in progress) |" in out
    assert "### Awards" not in out
    assert "### Notable moments" not in out
    assert "No proof generated." in out
    assert f"*Generated by `sov feedback` v{cli_main._resolve_version()}*" in out


def test_feedback_full_report_awards_notable_and_proof(tmp_path: Path) -> None:
    state = _make_state("town-hall", players=["Alice", "Bob", "Cara"])
    state.game_over = True
    state.winner = "Alice"
    state.log = [
        "R1T0: Recipe: cozy (12 events, 5 deals)",
        "R1T1: Bob kept their promise: wave",
        "R2T0: Cara helps Bob",
        "R2T1: nothing to see",
    ]
    game_id = _plant(state, tmp_path)
    _write_proof(game_id, 2)
    record_anchors(game_id, {"2": "TXFEEDBACK"})
    factory = _transport_factory()
    with patch("sov_transport.xrpl.XRPLTransport", factory):
        result = runner.invoke(app, ["feedback"])
    assert result.exit_code == 0, result.output
    out = result.output
    assert "| Tier | Town Hall |" in out
    assert "| Recipe | cozy |" in out
    assert "| Winner | Alice |" in out
    assert "### Awards" in out
    assert "- Winner: Alice" in out
    assert "- Promise Keeper: Bob" in out
    assert "- Most Helpful: Cara" in out
    assert "### Notable moments" in out
    assert "- R1T1: Bob kept their promise: wave" in out
    assert "nothing to see" not in out
    assert f"`{_HASH}`" in out
    # Rich wraps the 80-column line, so compare with whitespace collapsed.
    assert "[XRPL TX](https://explorer.example/TXFEEDBACK)" in " ".join(out.split())


def test_feedback_keeps_only_last_ten_notable_moments(tmp_path: Path) -> None:
    state = _make_state()
    state.log = [f"R1T{i}: Alice helps friend{i}" for i in range(13)]
    _plant(state, tmp_path)
    result = runner.invoke(app, ["feedback"])
    assert result.exit_code == 0, result.output
    bullets = [ln for ln in result.output.splitlines() if ln.startswith("- R1T")]
    assert len(bullets) == 10
    assert bullets[0].endswith("friend3")
    assert bullets[-1].endswith("friend12")


def test_feedback_uses_last_proof_without_anchor_link(tmp_path: Path) -> None:
    game_id = _plant(_make_state(), tmp_path)
    _write_proof(game_id, 1, name="final.proof.json")
    result = runner.invoke(app, ["feedback"])
    assert result.exit_code == 0, result.output
    assert f"`{_HASH}`" in result.output
    assert "XRPL TX" not in result.output

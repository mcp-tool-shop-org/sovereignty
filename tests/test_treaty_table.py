"""Tests for Treaty Table (Tier 4) mechanics."""

from __future__ import annotations

import json

from sov_engine.models import (
    STAKE_CAP_COINS,
    STAKE_CAP_RESOURCES,
    TREATY_REP_BONUS,
    TREATY_REP_PENALTY,
    Stake,
    Treaty,
    TreatyStatus,
)
from sov_engine.rules.treaty_table import (
    check_treaty_deadlines,
    new_treaty_table_game,
    parse_stake,
    treaty_break,
    treaty_keep,
    treaty_make,
)
from sov_engine.serialize import canonical_json, game_state_snapshot


def test_new_treaty_table_game_setup():
    state, rng = new_treaty_table_game(42, ["Alice", "Bob", "Carol"])
    assert state.config.ruleset == "treaty_table_v1"
    assert state.market_board is not None
    assert len(state.players) == 3
    for p in state.players:
        assert p.active_treaties == []
        assert p.resources == {"food": 0, "wood": 0, "tools": 0}


def test_treaty_make_coins():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players

    result = treaty_make(
        state, alice, bob, "help each other",
        Stake(coins=2), Stake(coins=1),
    )
    assert isinstance(result, Treaty)
    assert result.treaty_id == "t_0001"
    assert result.status == TreatyStatus.ACTIVE
    assert alice.coins == 3  # 5 - 2
    assert bob.coins == 4  # 5 - 1
    assert len(alice.active_treaties) == 1
    assert len(bob.active_treaties) == 1
    # Both share the same Treaty object
    assert alice.active_treaties[0] is bob.active_treaties[0]


def test_treaty_make_resource_stake():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    alice.resources["food"] = 3
    bob.resources["wood"] = 2

    result = treaty_make(
        state, alice, bob, "trade pact",
        Stake(resources={"food": 2}), Stake(resources={"wood": 1}),
    )
    assert isinstance(result, Treaty)
    assert alice.resources["food"] == 1  # 3 - 2
    assert bob.resources["wood"] == 1  # 2 - 1


def test_treaty_make_mixed_stakes():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    bob.resources["tools"] = 2

    result = treaty_make(
        state, alice, bob, "alliance",
        Stake(coins=3), Stake(resources={"tools": 1}),
    )
    assert isinstance(result, Treaty)
    assert alice.coins == 2  # 5 - 3
    assert bob.resources["tools"] == 1  # 2 - 1


def test_treaty_keep_returns_stakes():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    old_rep_a, old_rep_b = alice.reputation, bob.reputation

    t = treaty_make(
        state, alice, bob, "help",
        Stake(coins=2), Stake(coins=1),
    )
    assert isinstance(t, Treaty)

    msg = treaty_keep(state, t)
    assert "honored" in msg
    assert t.status == TreatyStatus.KEPT
    assert alice.coins == 5  # 3 + 2 returned
    assert bob.coins == 5  # 4 + 1 returned
    assert alice.reputation == old_rep_a + TREATY_REP_BONUS
    assert bob.reputation == old_rep_b + TREATY_REP_BONUS


def test_treaty_break_transfers_stake():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    old_rep = alice.reputation

    t = treaty_make(
        state, alice, bob, "pact",
        Stake(coins=3), Stake(coins=2),
    )
    assert isinstance(t, Treaty)
    assert alice.coins == 2  # 5 - 3
    assert bob.coins == 3  # 5 - 2

    msg = treaty_break(state, t, "Alice")
    assert "BROKEN" in msg
    assert t.status == TreatyStatus.BROKEN
    # Alice's 3 coins go to Bob, Bob gets his 2 back
    assert bob.coins == 3 + 3 + 2  # had 3, gets alice's 3 + own 2
    # Alice loses rep
    assert alice.reputation == old_rep + TREATY_REP_PENALTY


def test_treaty_break_penalty_bigger_than_promise():
    assert abs(TREATY_REP_PENALTY) > 2  # promise break is -2


def test_treaty_max_active_limit():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    alice.coins = 20  # plenty to stake

    t1 = treaty_make(state, alice, bob, "pact 1", Stake(coins=1), Stake())
    assert isinstance(t1, Treaty)
    t2 = treaty_make(state, alice, bob, "pact 2", Stake(coins=1), Stake())
    assert isinstance(t2, Treaty)
    # Third should fail
    result = treaty_make(state, alice, bob, "pact 3", Stake(coins=1), Stake())
    assert isinstance(result, str)
    assert "already has 2" in result


def test_treaty_stake_cap():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    alice.coins = 20

    result = parse_stake(f"{STAKE_CAP_COINS + 1} coins")
    assert isinstance(result, str)
    assert "Max" in result

    over_res = f"1 food, 1 wood, 1 tools, {STAKE_CAP_RESOURCES} food"
    result2 = parse_stake(over_res)
    assert isinstance(result2, str)
    assert "Max" in result2


def test_treaty_cant_afford():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    assert alice.coins == 5

    result = treaty_make(
        state, alice, bob, "impossible",
        Stake(coins=STAKE_CAP_COINS), Stake(),  # 5 coins, alice has 5 — OK
    )
    assert isinstance(result, Treaty)

    # Now alice has 0 coins — test with a fresh game
    # (Alice already has 2 active treaties above, so limit would fire first)
    state2, _ = new_treaty_table_game(99, ["X", "Y"])
    x, y = state2.players
    x.coins = 0
    result3 = treaty_make(state2, x, y, "nope", Stake(coins=1), Stake())
    assert isinstance(result3, str)
    assert "can't afford" in result3


def test_treaty_empty_stake_rejected():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players

    result = treaty_make(state, alice, bob, "handshake", Stake(), Stake())
    assert isinstance(result, str)
    assert "must stake something" in result.lower()


def test_treaty_one_sided_stake_ok():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players

    result = treaty_make(state, alice, bob, "one sided", Stake(coins=2), Stake())
    assert isinstance(result, Treaty)
    assert alice.coins == 3  # 5 - 2
    assert bob.coins == 5  # unchanged


def test_treaty_deadline_auto_keeps():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players

    t = treaty_make(
        state, alice, bob, "short pact",
        Stake(coins=1), Stake(coins=1), duration_rounds=1,
    )
    assert isinstance(t, Treaty)
    assert alice.coins == 4
    assert bob.coins == 4

    # Advance past deadline
    state.current_round = state.current_round + 2

    msgs = check_treaty_deadlines(state)
    assert len(msgs) == 1
    assert "honored" in msgs[0]
    assert t.status == TreatyStatus.KEPT
    assert alice.coins == 5  # returned
    assert bob.coins == 5  # returned


def test_treaty_already_resolved():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players

    t = treaty_make(state, alice, bob, "done", Stake(coins=1), Stake())
    assert isinstance(t, Treaty)
    treaty_keep(state, t)

    # Trying again should fail
    msg = treaty_keep(state, t)
    assert "already" in msg
    msg2 = treaty_break(state, t, "Alice")
    assert "already" in msg2


def test_treaty_serialization_roundtrip():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    alice.resources["food"] = 3

    treaty_make(
        state, alice, bob, "serialize me",
        Stake(coins=2, resources={"food": 1}), Stake(coins=1),
    )

    snapshot = game_state_snapshot(state)
    json_str = canonical_json(snapshot)
    data = json.loads(json_str)

    # Check treaties appear in both player snapshots
    alice_data = data["players"][0]
    bob_data = data["players"][1]
    assert len(alice_data["active_treaties"]) == 1
    assert len(bob_data["active_treaties"]) == 1

    t_data = alice_data["active_treaties"][0]
    assert t_data["treaty_id"].startswith("t_")
    assert t_data["text"] == "serialize me"
    assert t_data["status"] == "active"
    assert "Alice" in t_data["stakes"]
    assert t_data["stakes"]["Alice"]["coins"] == 2
    assert t_data["stakes"]["Alice"]["resources"]["food"] == 1


def test_treaty_deterministic_hash():
    def play_game(seed: int) -> str:
        state, _ = new_treaty_table_game(seed, ["A", "B"])
        a, b = state.players
        a.resources["food"] = 3
        treaty_make(state, a, b, "pact", Stake(coins=1), Stake())
        snap = game_state_snapshot(state)
        return canonical_json(snap)

    j1 = play_game(42)
    j2 = play_game(42)
    assert j1 == j2


def test_parse_stake_coins():
    result = parse_stake("2 coins")
    assert isinstance(result, Stake)
    assert result.coins == 2
    assert result.resources == {}


def test_parse_stake_resources():
    result = parse_stake("1 food, 1 wood")
    assert isinstance(result, Stake)
    assert result.coins == 0
    assert result.resources == {"food": 1, "wood": 1}


def test_parse_stake_mixed():
    result = parse_stake("3 coins, 1 tools")
    assert isinstance(result, Stake)
    assert result.coins == 3
    assert result.resources == {"tools": 1}


def test_parse_stake_invalid():
    result = parse_stake("lots of money")
    assert isinstance(result, str)  # error message

    result2 = parse_stake("-1 coins")
    assert isinstance(result2, str)

    result3 = parse_stake("1 diamonds")
    assert isinstance(result3, str)


def test_treaty_escrow_prevents_overspend():
    state, _ = new_treaty_table_game(42, ["Alice", "Bob"])
    alice, bob = state.players
    assert alice.coins == 5

    treaty_make(state, alice, bob, "locked", Stake(coins=4), Stake())
    assert alice.coins == 1  # only 1 left

    # Can't stake more than she has left
    state2, _ = new_treaty_table_game(99, ["X", "Y"])
    x, y = state2.players
    treaty_make(state2, x, y, "first", Stake(coins=4), Stake())
    result = treaty_make(state2, x, y, "second", Stake(coins=2), Stake())
    assert isinstance(result, str)
    assert "can't afford" in result

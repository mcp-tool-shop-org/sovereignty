"""Tests for game engine rules."""

from sov_engine.rules.campfire import (
    apologize,
    break_promise,
    keep_promise,
    make_promise,
    new_game,
    resolve_help_desk,
    resolve_space,
    roll_and_move,
)


def test_new_game_setup():
    state, rng = new_game(42, ["Alice", "Bob"])
    assert len(state.players) == 2
    assert len(state.board) == 16
    assert state.current_round == 1
    assert state.players[0].name == "Alice"
    assert state.players[1].name == "Bob"
    assert all(p.coins == 5 for p in state.players)
    assert all(p.reputation == 3 for p in state.players)


def test_new_game_rejects_bad_player_count():
    import pytest
    with pytest.raises(ValueError, match="2-4"):
        new_game(1, ["Solo"])
    with pytest.raises(ValueError, match="2-4"):
        new_game(1, ["A", "B", "C", "D", "E"])


def test_roll_and_move_deterministic():
    state1, rng1 = new_game(99, ["Alice", "Bob"])
    state2, rng2 = new_game(99, ["Alice", "Bob"])

    roll1 = roll_and_move(state1, rng1)
    roll2 = roll_and_move(state2, rng2)

    assert roll1 == roll2
    assert state1.players[0].position == state2.players[0].position


def test_campfire_board_setup():
    state, rng = new_game(42, ["Alice", "Bob"])
    assert state.board[0].name == "Campfire"
    assert len(state.board) == 16


def test_resolve_space_mint():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 8  # Mint
    old_coins = state.players[0].coins
    resolve_space(state, rng)
    assert state.players[0].coins == old_coins + 2


def test_resolve_space_faucet():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 11  # Faucet
    old_coins = state.players[0].coins
    resolve_space(state, rng)
    assert state.players[0].coins == old_coins + 1


def test_resolve_space_workshop_can_afford():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 1  # Workshop
    state.players[0].coins = 5
    resolve_space(state, rng)
    assert state.players[0].coins == 3
    assert state.players[0].upgrades == 1


def test_resolve_space_workshop_cant_afford():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 1  # Workshop
    state.players[0].coins = 1
    resolve_space(state, rng)
    assert state.players[0].coins == 1
    assert state.players[0].upgrades == 0


def test_resolve_space_builder_needs_rep():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 10  # Builder
    state.players[0].coins = 10
    state.players[0].reputation = 2  # too low
    resolve_space(state, rng)
    assert state.players[0].upgrades == 0
    assert state.players[0].coins == 10  # no charge


def test_resolve_space_taxman():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 13  # Taxman
    state.players[0].coins = 3
    resolve_space(state, rng)
    assert state.players[0].coins == 2


def test_resolve_space_taxman_no_coins():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 13
    state.players[0].coins = 0
    state.players[0].reputation = 5
    resolve_space(state, rng)
    assert state.players[0].reputation == 4


def test_resolve_space_trouble():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.players[0].position = 6  # Trouble
    state.players[0].coins = 3
    old_rep = state.players[0].reputation
    resolve_space(state, rng)
    assert state.players[0].coins == 2  # pays coin
    assert state.players[0].reputation == old_rep  # rep unchanged


def test_help_desk():
    state, rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    bob = state.players[1]
    alice.coins = 3

    resolve_help_desk(state, alice, bob)
    assert alice.coins == 2
    assert bob.coins == 6  # was 5, got 1
    assert alice.reputation == 4  # was 3, +1
    assert bob.reputation == 4
    assert alice.helped_last_round is True


def test_help_desk_sets_helped_flag():
    state, _ = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    assert alice.helped_last_round is False
    resolve_help_desk(state, alice, bob)
    assert alice.helped_last_round is True


def test_promise_make_keep():
    state, _ = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    make_promise(state, alice, "help Bob")
    assert "help Bob" in alice.promises
    keep_promise(state, alice, "help Bob")
    assert "help Bob" not in alice.promises
    assert alice.reputation == 4  # 3 + 1


def test_promise_break():
    state, _ = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    make_promise(state, alice, "help Bob")
    break_promise(state, alice, "help Bob")
    assert "help Bob" not in alice.promises
    assert alice.reputation == 1  # 3 - 2


def test_apology():
    state, _ = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    alice.reputation = 2  # pretend she broke a promise
    msg = apologize(state, alice, bob)
    assert alice.coins == 4  # 5 - 1
    assert bob.coins == 6  # 5 + 1
    assert alice.reputation == 3  # 2 + 1
    assert alice.apology_used is True
    assert "apologizes" in msg


def test_apology_once_per_game():
    state, _ = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    apologize(state, alice, bob)
    msg = apologize(state, alice, bob)
    assert "already used" in msg


def test_skip_next_move():
    state, rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    alice.skip_next_move = True
    roll = roll_and_move(state, rng)
    assert roll == 0
    assert alice.skip_next_move is False


def test_game_advance_turn_wraps():
    state, rng = new_game(42, ["Alice", "Bob"])
    assert state.current_player_index == 0
    assert state.current_round == 1

    state.advance_turn()
    assert state.current_player_index == 1
    assert state.current_round == 1

    state.advance_turn()
    assert state.current_player_index == 0
    assert state.current_round == 2


def test_tiebreak_after_max_rounds():
    state, rng = new_game(42, ["Alice", "Bob"])
    state.current_round = 15  # max
    state.players[0].coins = 10
    state.players[1].coins = 20

    state.advance_turn()  # Bob's turn
    state.advance_turn()  # wraps to Alice, round becomes 16 → tiebreak

    assert state.game_over
    assert state.winner is not None

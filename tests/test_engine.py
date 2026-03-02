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


def test_toast():
    state, rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    old_rep = alice.reputation

    assert alice.toasted is False
    alice.toasted = True
    alice.adjust_rep(1)
    assert alice.reputation == old_rep + 1
    assert alice.toasted is True


def test_toast_once_per_game():
    state, rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]

    alice.toasted = True
    alice.adjust_rep(1)
    # Second toast should be blocked (CLI enforces, model just tracks)
    assert alice.toasted is True


def test_content_tags_on_events():
    from sov_engine.content import build_event_deck

    events = build_event_deck()
    # Every event should have at least one tag
    for evt in events:
        assert evt.tags, f"Event {evt.id} ({evt.name}) has no tags"
    # Verify specific tags
    by_id = {e.id: e for e in events}
    assert "market" in by_id["evt_01"].tags  # Supply Delay
    assert "cozy" in by_id["evt_02"].tags  # Boom Town
    assert "spicy" in by_id["evt_03"].tags  # Storm
    assert "help" in by_id["evt_11"].tags  # Lost Wallet
    assert "market" in by_id["evt_21"].tags  # Bumper Harvest


def test_content_tags_on_deals():
    from sov_engine.content import build_deal_deck

    cards = build_deal_deck()
    for card in cards:
        assert card.tags, f"Card {card.id} ({card.name}) has no tags"
    by_id = {c.id: c for c in cards}
    assert "promise" in by_id["deal_01"].tags  # Supply Run
    assert "help" in by_id["deal_03"].tags  # Generosity Pledge
    assert "market" in by_id["deal_04"].tags  # Market Watcher
    assert "promise" in by_id["vouch_01"].tags  # Small Loan


def test_story_points_winner():
    """Story Points: winner gets +1."""
    state, _ = new_game(42, ["Alice", "Bob"])
    state.game_over = True
    state.winner = "Alice"

    from sov_cli.main import _calc_story_points

    points = _calc_story_points(state)
    assert points["Alice"]["winner"] == 1
    assert points["Bob"]["winner"] == 0


def test_story_points_promise_keeper():
    """Story Points: most promises kept gets +1, ties share."""
    state, _ = new_game(42, ["Alice", "Bob"])
    state.game_over = True
    state.winner = "Bob"
    # Simulate promise-keeping in log
    state.add_log("Alice kept their promise: help Bob")
    state.add_log("Alice kept their promise: share coins")
    state.add_log("Bob kept their promise: trade fair")

    from sov_cli.main import _calc_story_points

    points = _calc_story_points(state)
    assert points["Alice"]["promise_keeper"] == 1
    assert points["Bob"]["promise_keeper"] == 0  # Alice had more


def test_story_points_promise_keeper_tie():
    """Story Points: tied promise keepers both get +1."""
    state, _ = new_game(42, ["Alice", "Bob"])
    state.game_over = True
    state.winner = "Alice"
    state.add_log("Alice kept their promise: help Bob")
    state.add_log("Bob kept their promise: trade fair")

    from sov_cli.main import _calc_story_points

    points = _calc_story_points(state)
    assert points["Alice"]["promise_keeper"] == 1
    assert points["Bob"]["promise_keeper"] == 1


def test_story_points_most_helpful():
    """Story Points: most Help Desk visits gets +1."""
    state, _ = new_game(42, ["Alice", "Bob"])
    state.game_over = True
    state.winner = "Alice"
    state.add_log("Alice helps Bob at Help Desk")
    state.add_log("Alice helps Bob at Help Desk")

    from sov_cli.main import _calc_story_points

    points = _calc_story_points(state)
    assert points["Alice"]["most_helpful"] == 1
    assert points["Bob"]["most_helpful"] == 0


def test_story_points_tables_choice():
    """Story Points: MVP vote gives +1."""
    state, _ = new_game(42, ["Alice", "Bob"])
    state.game_over = True
    state.winner = "Alice"
    state.add_log("Vote: Bob wins Table's Choice (MVP)")

    from sov_cli.main import _calc_story_points

    points = _calc_story_points(state)
    assert points["Bob"]["tables_choice"] == 1
    assert points["Alice"]["tables_choice"] == 0


def test_story_points_totals():
    """Story Points: total is sum of all awards."""
    state, _ = new_game(42, ["Alice", "Bob"])
    state.game_over = True
    state.winner = "Alice"
    state.add_log("Alice kept their promise: help")
    state.add_log("Alice helps Bob at Help Desk")
    state.add_log("Vote: Alice wins Table's Choice (MVP)")

    from sov_cli.main import _calc_story_points

    points = _calc_story_points(state)
    # Alice: winner(1) + promise_keeper(1) + most_helpful(1) + tables_choice(1) = 4
    total = sum(points["Alice"].values())
    assert total == 4


def test_recipe_cozy_filters_events():
    """Recipe filter reduces event deck to matching tags."""
    state, _ = new_game(42, ["Alice", "Bob"])
    original_count = len(state.event_deck.draw_pile)

    from sov_cli.main import _apply_recipe

    _apply_recipe(state, "cozy")
    filtered_count = len(state.event_deck.draw_pile)
    assert filtered_count < original_count
    # All remaining events should have the cozy tag
    for card in state.event_deck.draw_pile:
        assert "cozy" in card.tags


def test_recipe_spicy_filters_events():
    """Recipe filter works for spicy too."""
    state, _ = new_game(42, ["Alice", "Bob"])

    from sov_cli.main import _apply_recipe

    _apply_recipe(state, "spicy")
    for card in state.event_deck.draw_pile:
        assert "spicy" in card.tags


def test_recipe_invalid_tag():
    """Invalid recipe tag returns a warning, doesn't filter."""
    state, _ = new_game(42, ["Alice", "Bob"])
    original_events = len(state.event_deck.draw_pile)

    from sov_cli.main import _apply_recipe

    result = _apply_recipe(state, "chaos")
    assert "Unknown recipe" in result
    assert len(state.event_deck.draw_pile) == original_events


def test_recipe_promise_filters():
    """Promise recipe filters events and deals to commitment-heavy cards."""
    state, _ = new_game(42, ["Alice", "Bob"])
    original_events = len(state.event_deck.draw_pile)

    from sov_cli.main import _apply_recipe

    _apply_recipe(state, "promise")
    # Events should be filtered (5 promise events >= threshold)
    filtered_events = len(state.event_deck.draw_pile)
    assert filtered_events < original_events
    assert filtered_events >= 5
    for card in state.event_deck.draw_pile:
        assert "promise" in card.tags
    # Deals should also be filtered (many vouchers + deals tagged promise)
    for card in state.deal_deck.draw_pile:
        assert "promise" in card.tags


def test_recipe_preserves_small_decks():
    """If filtered set is too small, keep the full deck."""
    state, _ = new_game(42, ["Alice", "Bob"])

    from sov_cli.main import _apply_recipe

    # "market" has 1 deal (deal_04) — too few to filter deals
    original_deals = len(state.deal_deck.draw_pile)
    _apply_recipe(state, "market")
    # Events should be filtered (12 market events >= 5)
    for card in state.event_deck.draw_pile:
        assert "market" in card.tags
    # Deals: market has deal_04 + vouch_04 = 2, below threshold of 3
    # So full deck should be preserved
    assert len(state.deal_deck.draw_pile) == original_deals


# ---------------------------------------------------------------------------
# Share code tests
# ---------------------------------------------------------------------------


def test_parse_share_code_valid():
    from sov_cli.main import _parse_share_code

    result = _parse_share_code("SOV|cozy-night|campfire|cozy|s42")
    assert isinstance(result, dict)
    assert result["slug"] == "cozy-night"
    assert result["tier"] == "campfire"
    assert result["recipe"] == "cozy"
    assert result["seed"] == "42"


def test_parse_share_code_no_recipe():
    from sov_cli.main import _parse_share_code

    result = _parse_share_code("SOV|treaty-night|treaty-table|-|s99")
    assert isinstance(result, dict)
    assert result["recipe"] == ""
    assert result["seed"] == "99"


def test_parse_share_code_invalid():
    from sov_cli.main import _parse_share_code

    result = _parse_share_code("NOT|a|valid|code")
    assert isinstance(result, str)  # error message

    result2 = _parse_share_code("SOV|slug|tier|recipe|bad")
    assert isinstance(result2, str)  # bad seed


def test_build_share_code():
    from sov_cli.main import _build_share_code

    code = _build_share_code("cozy-night", "campfire", "cozy", 42)
    assert code == "SOV|cozy-night|campfire|cozy|s42"

    code2 = _build_share_code("treaty-night", "treaty-table", "", 99)
    assert code2 == "SOV|treaty-night|treaty-table|-|s99"


def test_share_code_roundtrip():
    from sov_cli.main import _build_share_code, _parse_share_code

    code = _build_share_code("market-panic", "town-hall", "market", 7)
    parsed = _parse_share_code(code)
    assert isinstance(parsed, dict)
    assert parsed["slug"] == "market-panic"
    assert parsed["tier"] == "town-hall"
    assert parsed["recipe"] == "market"
    assert parsed["seed"] == "7"

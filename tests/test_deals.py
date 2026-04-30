"""Tests for the Campfire deal subsystem.

Covers ``accept_deal``, ``complete_deal``, and ``check_deal_deadlines`` in
``sov_engine.rules.campfire``. The module-level ``_deal_counter`` is reset
between tests by the autouse fixture in ``tests/conftest.py``.
"""

from __future__ import annotations

from sov_engine.models import (
    ActiveDeal,
    CardType,
    DealCard,
    DealStatus,
)
from sov_engine.rules.campfire import (
    accept_deal,
    check_deal_deadlines,
    complete_deal,
    new_game,
)


def _supply_run_template() -> DealCard:
    return DealCard(
        id="deal_test_supply",
        name="Supply Run (test)",
        card_type=CardType.DEAL,
        description="Deliver something within 2 rounds.",
        reward_coins=2,
        reward_rep=1,
        penalty_rep=1,
        deadline_rounds=2,
    )


# ---------------------------------------------------------------------------
# accept_deal
# ---------------------------------------------------------------------------


def test_accept_deal_creates_active_deal_with_correct_fields():
    """``accept_deal`` returns an ActiveDeal with the correct deadline and
    rewards copied from the template."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    template = _supply_run_template()

    deal = accept_deal(state, alice, template)

    assert isinstance(deal, ActiveDeal)
    assert deal.player == "Alice"
    assert deal.template_id == "deal_test_supply"
    assert deal.status == DealStatus.ACTIVE
    assert deal.reward_coins == 2
    assert deal.reward_rep == 1
    assert deal.penalty_rep == 1
    # deadline = current_round (1) + deadline_rounds (2) = 3
    assert deal.deadline_round == state.current_round + 2
    assert deal in alice.active_deals


def test_accept_deal_id_format_and_uniqueness():
    """``deal_id`` is ``d_NNNN`` zero-padded and increments across calls.

    Counter is reset by conftest, so this test always sees d_0001, d_0002.
    """
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    template = _supply_run_template()

    d1 = accept_deal(state, alice, template)
    d2 = accept_deal(state, alice, template)

    assert d1.deal_id == "d_0001"
    assert d2.deal_id == "d_0002"
    assert d1.deal_id != d2.deal_id
    # Counter lives on GameState post-W5 (parking F-432101-006 migration).
    assert state.next_deal_id == 2


# ---------------------------------------------------------------------------
# complete_deal — happy path and double-complete
# ---------------------------------------------------------------------------


def test_complete_deal_awards_rewards():
    """Successful completion grants reward_coins and reward_rep."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    template = _supply_run_template()
    deal = accept_deal(state, alice, template)

    coins_before = alice.coins
    rep_before = alice.reputation

    msg = complete_deal(state, alice, deal)

    assert deal.status == DealStatus.COMPLETED
    assert alice.coins == coins_before + 2
    assert alice.reputation == rep_before + 1
    assert "completes deal" in msg.lower() or "complet" in msg.lower()


def test_complete_deal_already_completed_returns_already_message():
    """Re-completing a deal returns the 'already' message and does not
    double-award the reward."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    deal = accept_deal(state, alice, _supply_run_template())

    complete_deal(state, alice, deal)
    coins_after_first = alice.coins
    rep_after_first = alice.reputation

    msg = complete_deal(state, alice, deal)

    assert "already" in msg.lower()
    assert alice.coins == coins_after_first
    assert alice.reputation == rep_after_first


def test_complete_deal_already_failed_returns_already_message():
    """A deal that was failed (e.g. by deadline sweep) cannot be retroactively
    completed."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    deal = accept_deal(state, alice, _supply_run_template())
    deal.status = DealStatus.FAILED

    coins_before = alice.coins
    msg = complete_deal(state, alice, deal)

    assert "already" in msg.lower()
    assert alice.coins == coins_before


# ---------------------------------------------------------------------------
# check_deal_deadlines
# ---------------------------------------------------------------------------


def test_check_deal_deadlines_fails_expired_deals_and_applies_penalty():
    """Expired active deals are marked FAILED and the player loses
    ``penalty_rep``."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    template = _supply_run_template()  # penalty_rep=1
    deal = accept_deal(state, alice, template)

    rep_before = alice.reputation
    state.current_round = deal.deadline_round + 1

    messages = check_deal_deadlines(state)

    assert len(messages) == 1
    assert deal.status == DealStatus.FAILED
    assert alice.reputation == rep_before - 1
    assert "expired" in messages[0].lower() or "fails" in messages[0].lower()


def test_check_deal_deadlines_skips_active_within_deadline():
    """Deals still within their deadline remain ACTIVE."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    deal = accept_deal(state, alice, _supply_run_template())

    state.current_round = deal.deadline_round  # exactly on the deadline, not past
    rep_before = alice.reputation

    messages = check_deal_deadlines(state)

    assert messages == []
    assert deal.status == DealStatus.ACTIVE
    assert alice.reputation == rep_before


def test_check_deal_deadlines_skips_completed_deals():
    """Completed deals are not penalized post-hoc by the deadline sweep."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice = state.players[0]
    deal = accept_deal(state, alice, _supply_run_template())
    complete_deal(state, alice, deal)

    state.current_round = deal.deadline_round + 5
    rep_after_complete = alice.reputation

    messages = check_deal_deadlines(state)

    assert messages == []
    assert deal.status == DealStatus.COMPLETED
    assert alice.reputation == rep_after_complete


def test_check_deal_deadlines_handles_multiple_players():
    """The sweep iterates across all players, not just the current one."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    d_alice = accept_deal(state, alice, _supply_run_template())
    d_bob = accept_deal(state, bob, _supply_run_template())

    state.current_round = max(d_alice.deadline_round, d_bob.deadline_round) + 1

    messages = check_deal_deadlines(state)

    assert len(messages) == 2
    assert d_alice.status == DealStatus.FAILED
    assert d_bob.status == DealStatus.FAILED

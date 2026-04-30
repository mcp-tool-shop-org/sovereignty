"""Tests for the Campfire voucher subsystem.

Covers ``issue_voucher``, ``redeem_voucher``, and ``check_voucher_deadlines``
in ``sov_engine.rules.campfire``. The module-level ``_voucher_counter`` is
reset between tests by the autouse fixture in ``tests/conftest.py``.
"""

from __future__ import annotations

from sov_engine.models import (
    CardType,
    Voucher,
    VoucherCard,
    VoucherStatus,
)
from sov_engine.rules.campfire import (
    check_voucher_deadlines,
    issue_voucher,
    new_game,
    redeem_voucher,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _small_loan_template() -> VoucherCard:
    """A non-negotiable face-value-2 voucher template, due in 3 rounds."""
    return VoucherCard(
        id="vouch_test_small",
        name="Small Loan (test)",
        card_type=CardType.VOUCHER,
        description="I owe you 2 coins.",
        face_value=2,
        deadline_rounds=3,
        default_penalty_rep=2,
    )


def _negotiable_template() -> VoucherCard:
    """A negotiable template — caller supplies face_value and deadline."""
    return VoucherCard(
        id="vouch_test_blank",
        name="Blank Voucher (test)",
        card_type=CardType.VOUCHER,
        description="Negotiable.",
        face_value=0,
        deadline_rounds=0,
        default_penalty_rep=0,
        negotiable=True,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_issue_voucher_happy_path():
    """Issuer with rep >= 2 can issue a voucher; voucher is wired into both
    issuer.vouchers_issued and holder.vouchers_held."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    template = _small_loan_template()

    v = issue_voucher(state, alice, bob, template)

    assert isinstance(v, Voucher)
    assert v.issuer == "Alice"
    assert v.holder == "Bob"
    assert v.face_value == 2
    assert v.status == VoucherStatus.ACTIVE
    assert v.deadline_round == state.current_round + 3
    assert v in alice.vouchers_issued
    assert v in bob.vouchers_held


def test_redeem_voucher_normal_payment():
    """Redemption from a non-trusted issuer pays exactly the face value."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    template = _small_loan_template()

    v = issue_voucher(state, alice, bob, template)
    assert isinstance(v, Voucher)

    alice_before = alice.coins
    bob_before = bob.coins

    msg = redeem_voucher(state, v)

    assert v.status == VoucherStatus.REDEEMED
    assert alice.coins == alice_before - 2
    assert bob.coins == bob_before + 2
    assert "redeemed" in msg.lower()


# ---------------------------------------------------------------------------
# Trusted-issuer bonus (rep >= 5 adds +1 to the redemption payment)
# ---------------------------------------------------------------------------


def test_redeem_voucher_trusted_issuer_bonus():
    """Issuer with rep >= 5 pays face_value + 1 on redemption."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    alice.reputation = 5  # trusted issuer
    alice.coins = 10
    template = _small_loan_template()  # face_value=2

    v = issue_voucher(state, alice, bob, template)
    assert isinstance(v, Voucher)

    alice_before = alice.coins
    bob_before = bob.coins

    redeem_voucher(state, v)

    assert v.status == VoucherStatus.REDEEMED
    # face_value 2 + trusted bonus 1 = 3 paid
    assert alice.coins == alice_before - 3
    assert bob.coins == bob_before + 3


# ---------------------------------------------------------------------------
# Issue blocked when issuer rep < 2
# ---------------------------------------------------------------------------


def test_issue_voucher_blocked_when_rep_too_low():
    """Issuer with rep < 2 cannot issue a voucher; returns an error string."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    alice.reputation = 1  # below threshold
    template = _small_loan_template()

    result = issue_voucher(state, alice, bob, template)

    assert isinstance(result, str)
    assert "can't issue" in result.lower()
    assert alice.vouchers_issued == []
    assert bob.vouchers_held == []


# ---------------------------------------------------------------------------
# Defaulted redemption (issuer can't pay)
# ---------------------------------------------------------------------------


def test_redeem_voucher_defaults_when_issuer_cant_pay():
    """When the issuer doesn't have enough coins to pay face value, the
    voucher is marked DEFAULTED and the issuer takes a rep penalty equal to
    ``max(1, (face_value + 1) // 2)``."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    template = VoucherCard(
        id="vouch_test_big",
        name="Big Loan (test)",
        card_type=CardType.VOUCHER,
        description="I owe you 4 coins.",
        face_value=4,
        deadline_rounds=3,
        default_penalty_rep=2,
    )

    v = issue_voucher(state, alice, bob, template)
    assert isinstance(v, Voucher)

    # Drain Alice's coins so she cannot pay.
    alice.coins = 0
    alice.reputation = 5  # plenty of rep to take a penalty hit
    bob_before_coins = bob.coins
    alice_rep_before = alice.reputation

    msg = redeem_voucher(state, v)

    expected_penalty = max(1, (4 + 1) // 2)  # = 2
    assert v.status == VoucherStatus.DEFAULTED
    assert alice.coins == 0
    assert bob.coins == bob_before_coins  # holder gets nothing
    assert alice.reputation == alice_rep_before - expected_penalty
    assert "default" in msg.lower()


def test_default_penalty_minimum_is_one():
    """For a face_value-1 voucher, ``max(1, (1+1)//2) == 1``."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    template = VoucherCard(
        id="vouch_test_tiny",
        name="Tiny Loan (test)",
        card_type=CardType.VOUCHER,
        description="I owe you 1 coin.",
        face_value=1,
        deadline_rounds=3,
        default_penalty_rep=1,
    )

    v = issue_voucher(state, alice, bob, template)
    assert isinstance(v, Voucher)

    alice.coins = 0
    rep_before = alice.reputation
    redeem_voucher(state, v)

    assert v.status == VoucherStatus.DEFAULTED
    assert alice.reputation == rep_before - 1


# ---------------------------------------------------------------------------
# Deadline expiry
# ---------------------------------------------------------------------------


def test_check_voucher_deadlines_auto_defaults_expired():
    """``check_voucher_deadlines`` auto-defaults vouchers whose deadline
    round has passed and applies the penalty."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    # _small_loan_template has default_penalty_rep=2 (non-negotiable). Post-W5
    # parking F-005 fix, Voucher.penalty_rep is set from default_penalty_rep at
    # issue time and used by check_voucher_deadlines instead of the dead
    # max(1, (face_value+1)//2) recompute branch.
    template = _small_loan_template()

    v = issue_voucher(state, alice, bob, template)
    assert isinstance(v, Voucher)

    # Fast-forward past the deadline.
    state.current_round = v.deadline_round + 1
    rep_before = alice.reputation

    messages = check_voucher_deadlines(state)

    assert len(messages) == 1
    assert v.status == VoucherStatus.DEFAULTED
    assert alice.reputation == rep_before - 2  # template.default_penalty_rep
    assert "expired" in messages[0].lower()


def test_check_voucher_deadlines_skips_active_within_deadline():
    """Vouchers still within their deadline are not affected."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]

    v = issue_voucher(state, alice, bob, _small_loan_template())
    assert isinstance(v, Voucher)

    # Deadline is current_round + 3. Stay before it.
    state.current_round = v.deadline_round  # current == deadline, NOT past
    messages = check_voucher_deadlines(state)

    assert messages == []
    assert v.status == VoucherStatus.ACTIVE


def test_check_voucher_deadlines_skips_already_redeemed():
    """Already-redeemed vouchers are not re-defaulted by the sweep."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]

    v = issue_voucher(state, alice, bob, _small_loan_template())
    assert isinstance(v, Voucher)
    redeem_voucher(state, v)
    assert v.status == VoucherStatus.REDEEMED

    state.current_round = v.deadline_round + 5
    rep_before = alice.reputation
    messages = check_voucher_deadlines(state)

    assert messages == []
    assert v.status == VoucherStatus.REDEEMED
    assert alice.reputation == rep_before


# ---------------------------------------------------------------------------
# voucher_id format and uniqueness (counter reset is verified via conftest)
# ---------------------------------------------------------------------------


def test_voucher_id_format_and_uniqueness():
    """voucher_id is ``v_NNNN`` zero-padded and increments across calls."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    template = _small_loan_template()

    v1 = issue_voucher(state, alice, bob, template)
    v2 = issue_voucher(state, alice, bob, template)
    v3 = issue_voucher(state, alice, bob, template)

    assert isinstance(v1, Voucher)
    assert isinstance(v2, Voucher)
    assert isinstance(v3, Voucher)

    # Conftest resets the counter to 0 before each test, so this run starts
    # at v_0001.
    assert v1.voucher_id == "v_0001"
    assert v2.voucher_id == "v_0002"
    assert v3.voucher_id == "v_0003"

    ids = {v1.voucher_id, v2.voucher_id, v3.voucher_id}
    assert len(ids) == 3, "voucher_ids must be unique within a run"


def test_voucher_counter_lives_on_state_post_w5():
    """Counter migrated from module global into GameState (W5 parking F-006).

    Each new_game() seeds next_voucher_id=0, so test isolation is automatic
    via fresh state per test rather than the conftest autouse fixture (now
    a no-op kept as a hook for future test isolation needs)."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    assert state.next_voucher_id == 0  # fresh game starts at 0
    v = issue_voucher(state, alice, bob, _small_loan_template())
    assert isinstance(v, Voucher)
    assert v.voucher_id == "v_0001"
    assert state.next_voucher_id == 1  # incremented after issue


# ---------------------------------------------------------------------------
# Negotiable vouchers honor caller-supplied face_value and deadline
# ---------------------------------------------------------------------------


def test_negotiable_voucher_uses_overrides():
    """For a negotiable template, caller can override face_value and deadline."""
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    template = _negotiable_template()

    v = issue_voucher(state, alice, bob, template, face_value=5, deadline_rounds=2)

    assert isinstance(v, Voucher)
    assert v.face_value == 5
    assert v.deadline_round == state.current_round + 2


# ---------------------------------------------------------------------------
# Defensive: redeeming a defaulted voucher is a no-op
# ---------------------------------------------------------------------------


def test_redeem_already_defaulted_voucher_is_noop():
    state, _rng = new_game(42, ["Alice", "Bob"])
    alice, bob = state.players[0], state.players[1]
    v = issue_voucher(state, alice, bob, _small_loan_template())
    assert isinstance(v, Voucher)
    v.status = VoucherStatus.DEFAULTED

    msg = redeem_voucher(state, v)
    assert "already" in msg.lower()

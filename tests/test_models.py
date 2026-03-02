"""Tests for core game models."""

from sov_engine.models import PlayerState, WinCondition


def test_player_starting_state():
    p = PlayerState(name="Alice")
    assert p.coins == 5
    assert p.reputation == 3
    assert p.upgrades == 0
    assert p.position == 0


def test_adjust_coins_cant_go_negative():
    p = PlayerState(name="Bob", coins=2)
    actual = p.adjust_coins(-5)
    assert p.coins == 0
    assert actual == -2  # only lost 2


def test_adjust_coins_positive():
    p = PlayerState(name="Carol", coins=5)
    actual = p.adjust_coins(3)
    assert p.coins == 8
    assert actual == 3


def test_adjust_rep_clamped():
    p = PlayerState(name="Dave", reputation=9)
    actual = p.adjust_rep(3)
    assert p.reputation == 10
    assert actual == 1

    actual = p.adjust_rep(-15)
    assert p.reputation == 0
    assert actual == -10


def test_rep_gates():
    p = PlayerState(name="Eve", reputation=1)
    assert not p.can_issue_voucher()
    assert not p.can_use_builder()
    assert not p.is_trusted_issuer()

    p.reputation = 2
    assert p.can_issue_voucher()
    assert not p.can_use_builder()

    p.reputation = 3
    assert p.can_use_builder()

    p.reputation = 5
    assert p.is_trusted_issuer()


def test_win_conditions():
    p = PlayerState(name="Frank", win_condition=WinCondition.PROSPERITY, coins=19)
    assert not p.has_won()
    p.coins = 20
    assert p.has_won()

    p2 = PlayerState(name="Grace", win_condition=WinCondition.BELOVED, reputation=9)
    assert not p2.has_won()
    p2.reputation = 10
    assert p2.has_won()

    p3 = PlayerState(name="Hank", win_condition=WinCondition.BUILDER, upgrades=3)
    assert not p3.has_won()
    p3.upgrades = 4
    assert p3.has_won()

"""Canonical serialization for deterministic hashing."""

from __future__ import annotations

import json
from typing import Any

from sov_engine.models import (
    GameState,
    PlayerState,
    Stake,
    Treaty,
    Voucher,
)


def _stake_snapshot(s: Stake) -> dict[str, Any]:
    result: dict[str, Any] = {"coins": s.coins}
    if s.resources:
        result["resources"] = dict(sorted(s.resources.items()))
    return result


def _treaty_snapshot(t: Treaty) -> dict[str, Any]:
    return {
        "created_round": t.created_round,
        "deadline_round": t.deadline_round,
        "parties": sorted(t.parties),
        "stakes": {
            name: _stake_snapshot(stake)
            for name, stake in sorted(t.stakes.items())
        },
        "status": t.status.value,
        "text": t.text,
        "treaty_id": t.treaty_id,
    }


def _player_snapshot(p: PlayerState) -> dict[str, Any]:
    """Canonical player state snapshot."""
    snapshot: dict[str, Any] = {
        "active_deals": [
            {
                "deal_id": d.deal_id,
                "deadline_round": d.deadline_round,
                "status": d.status.value,
                "template_id": d.template_id,
            }
            for d in sorted(p.active_deals, key=lambda d: d.deal_id)
        ],
        "active_treaties": [
            _treaty_snapshot(t)
            for t in sorted(p.active_treaties, key=lambda t: t.treaty_id)
        ],
        "apology_used": p.apology_used,
        "coins": p.coins,
        "helped_last_round": p.helped_last_round,
        "name": p.name,
        "position": p.position,
        "promises": sorted(p.promises),
        "reputation": p.reputation,
        "skip_next_move": p.skip_next_move,
        "toasted": p.toasted,
        "upgrades": p.upgrades,
        "vouchers_held": [
            _voucher_snapshot(v)
            for v in sorted(p.vouchers_held, key=lambda v: v.voucher_id)
        ],
        "vouchers_issued": [
            _voucher_snapshot(v)
            for v in sorted(p.vouchers_issued, key=lambda v: v.voucher_id)
        ],
        "win_condition": p.win_condition.value,
    }
    if p.resources:
        snapshot["resources"] = dict(sorted(p.resources.items()))
    return snapshot


def _voucher_snapshot(v: Voucher) -> dict[str, Any]:
    return {
        "deadline_round": v.deadline_round,
        "face_value": v.face_value,
        "holder": v.holder,
        "issuer": v.issuer,
        "status": v.status.value,
        "template_id": v.template_id,
        "voucher_id": v.voucher_id,
    }


def game_state_snapshot(state: GameState) -> dict[str, Any]:
    """Produce a canonical, hashable snapshot of the full game state."""
    snapshot: dict[str, Any] = {
        "config": {
            "board_size": state.config.board_size,
            "max_players": state.config.max_players,
            "max_rounds": state.config.max_rounds,
            "ruleset": state.config.ruleset,
            "seed": state.config.seed,
        },
        "current_player_index": state.current_player_index,
        "current_round": state.current_round,
        "game_over": state.game_over,
        "log": list(state.log),
        "market": {
            "food": state.market.food,
            "tools": state.market.tools,
            "wood": state.market.wood,
        },
        "players": [_player_snapshot(p) for p in state.players],
        "turn_in_round": state.turn_in_round,
        "winner": state.winner,
    }
    # Include market board state for Market Day / Town Hall
    mb = state.market_board
    if mb is not None:
        snapshot["market_board"] = {
            "base_prices": dict(sorted(mb.base_prices.items())),
            "fixed_prices": mb.fixed_prices,
            "price_shifts": dict(sorted(mb.price_shifts.items())),
            "supply": dict(sorted(mb.supply.items())),
        }
    return snapshot


def canonical_json(data: dict[str, Any]) -> str:
    """Produce canonical JSON: sorted keys, no trailing whitespace, LF line endings."""
    return json.dumps(
        data,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        separators=(",", ": "),
    ).replace("\r\n", "\n") + "\n"

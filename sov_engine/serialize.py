"""Canonical serialization for deterministic hashing."""

from __future__ import annotations

import json
from typing import Any

from sov_engine.models import (
    GameState,
    PlayerState,
    Voucher,
)


def _player_snapshot(p: PlayerState) -> dict[str, Any]:
    """Canonical player state snapshot."""
    return {
        "active_deals": [
            {
                "deal_id": d.deal_id,
                "deadline_round": d.deadline_round,
                "status": d.status.value,
                "template_id": d.template_id,
            }
            for d in sorted(p.active_deals, key=lambda d: d.deal_id)
        ],
        "coins": p.coins,
        "name": p.name,
        "position": p.position,
        "reputation": p.reputation,
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
    return {
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
        "market": {
            "food": state.market.food,
            "tools": state.market.tools,
            "wood": state.market.wood,
        },
        "players": [_player_snapshot(p) for p in state.players],
        "turn_in_round": state.turn_in_round,
        "winner": state.winner,
    }


def canonical_json(data: dict[str, Any]) -> str:
    """Produce canonical JSON: sorted keys, no trailing whitespace, LF line endings."""
    return json.dumps(
        data,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        separators=(",", ": "),
    ).replace("\r\n", "\n") + "\n"

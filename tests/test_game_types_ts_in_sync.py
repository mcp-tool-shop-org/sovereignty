"""Pin doc↔code consistency: game state field names from
sov_engine/models.py must appear in app/src/types/game.ts.

UI-consumed subset only — gameplay internals (helped_last_round,
skip_next_move, apology_used, toasted, position, win_condition,
vouchers_issued, promises) are deliberately not in the UI; the
type-sync test does not pin them so schema additions to non-UI
fields don't break CI."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TYPES_TS = REPO_ROOT / "app" / "src" / "types" / "game.ts"

# UI-consumed subset (spec §7 — Wave 5 amendment A from Mike's brief).
GAME_STATE_FIELDS = {
    # GameConfig
    "seed",
    "ruleset",
    "max_players",
    "max_rounds",
    "board_size",
    # GameState top-level
    "config",
    "players",
    "current_round",
    "game_over",
    "winner",
    # PlayerState (UI-consumed subset)
    "name",
    "coins",
    "reputation",
    "upgrades",
    "vouchers_held",
    "active_deals",
    "active_treaties",
    "resources",
}


@pytest.mark.parametrize("field_name", sorted(GAME_STATE_FIELDS))
def test_game_ts_contains_field(field_name: str) -> None:
    """Every UI-consumed game state field must appear in app/src/types/game.ts.

    Tolerates either a TS string literal ("field_name") or an interface field
    (`field_name:`) — both forms are valid mirroring patterns.
    """
    if not TYPES_TS.exists():
        pytest.skip("app/src/types/game.ts not present (pre-Wave-5)")
    text = TYPES_TS.read_text(encoding="utf-8")
    found = (
        f'"{field_name}"' in text
        or f"'{field_name}'" in text
        or f"{field_name}:" in text
        or f"{field_name} " in text
        or f"{field_name}\n" in text
    )
    assert found, (
        f"missing field {field_name!r} in {TYPES_TS} — "
        f"sov_engine/models.py defines it as part of the UI-consumed "
        f"PlayerState/GameState/GameConfig subset; types/game.ts must mirror"
    )

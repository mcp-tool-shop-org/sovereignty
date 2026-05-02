// Game state types — UI-consumed subset of sov_engine/models.py.
// Manual mirror per docs/v2.1-views.md §6. The type-sync test
// (tests/test_game_types_ts_in_sync.py, docs domain) pins ~18 field names
// as TS string literals OR interface fields.
//
// Schema additions to non-UI fields (helped_last_round, skip_next_move,
// apology_used, toasted, position, win_condition, vouchers_issued, promises)
// must NOT break the type-sync test — they live in the engine schema but
// the UI deliberately does not consume them.

export interface GameConfig {
  seed: number;
  ruleset: string;
  max_players: number;
  max_rounds: number;
  board_size: number;
}

// Voucher / ActiveDeal / Treaty: minimal shapes covering count-rendering only.
// Detail rendering is v2.2 scope.
export interface Voucher {
  id: number;
}

export interface ActiveDeal {
  id: number;
}

export interface Treaty {
  id: number;
}

export interface PlayerState {
  name: string;
  coins: number;
  reputation: number;
  upgrades: number;
  vouchers_held: Voucher[];
  active_deals: ActiveDeal[];
  active_treaties: Treaty[];
  resources: Record<string, number>; // food/wood/tools — Town Hall only, may be empty
}

export interface GameState {
  config: GameConfig;
  players: PlayerState[];
  current_round: number;
  game_over: boolean;
  winner: string | null;
}

/** Town Hall ruleset gate — controls resources row rendering on PlayerCard. */
export function isTownHall(ruleset: string): boolean {
  return ruleset.startsWith("town_hall");
}

/** Round key used by anchor endpoints. Numbered rounds + literal "FINAL". */
export type RoundKey = string;

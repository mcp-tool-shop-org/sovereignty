# Multi-save model

Starting in v2.1, sovereignty's persistence layer is plural. Multiple saved games coexist under `.sov/games/<game-id>/`, with a pointer file tracking which one is active. Switch between them with `sov resume <game-id>`; list them with `sov games`.

## Overview

v2.0.x stored one implicit game at `.sov/game_state.json`. Starting a new game silently overwrote the old one. v2.1 makes the layout plural so the audit viewer (Wave 5) can render multiple games and the game shell can switch between saves without manual file shuffling.

The change is on-disk layout only. State `schema_version` stays `1` — the contents of `state.json` are unchanged.

## Layout

### v2.1 on-disk tree

```
.sov/
  active-game            # single-line file: the active game-id
  wallet_seed.txt        # cross-game secret (unchanged location)
  season.json            # cross-game season record (unchanged location)
  games/
    <game-id>/           # game-id format: "s{seed}"
      state.json         # was .sov/game_state.json
      rng_seed.txt       # was .sov/rng_seed.txt
      proofs/
        round_*.proof.json
        final.proof.json
        anchors.json
```

### Per-game files (under `.sov/games/<game-id>/`)

| File | Purpose |
|---|---|
| ``state.json`` | Game state snapshot (schema_version=1) |
| ``rng_seed.txt`` | Deterministic RNG seed for replay |
| ``proofs/round_*.proof.json`` | Per-round proofs |
| ``proofs/final.proof.json`` | End-of-game proof |
| ``proofs/anchors.json`` | Index of XRPL anchor txids |

### Cross-game files (stay at `.sov/` root)

| File | Purpose |
|---|---|
| ``wallet_seed.txt`` | XRPL Testnet wallet seed (one wallet, all games) |
| ``season.json`` | Season standings across multiple games |
| ``active-game`` | Pointer file containing the current game-id |

## Commands

### `sov games`

Lists every saved game with ruleset, round progress, players, and last-modified time.

```
$ sov games
GAME-ID  RULESET       ROUND  PLAYERS                LAST PLAYED
s42      campfire_v1   3/15   Alice, Bob, Charlie    2026-04-30 14:22 UTC
s17      town_hall_v1  8/15   Dora, Eve              2026-04-29 09:11 UTC
```

`sov games --json` emits a `GameSummary[]` for tooling:

```json
[
  {"game_id": "s42", "ruleset": "campfire_v1", "current_round": 3, "max_rounds": 15, "players": ["Alice", "Bob", "Charlie"], "last_modified_iso": "2026-04-30T14:22:00Z"}
]
```

If `.sov/games/` is empty or missing, `sov games` prints a hint and exits 0 (not an error):

```
No saved games. Run `sov new` to start one.
```

### `sov resume <game-id>`

Switches the active game. Updates `.sov/active-game` to the chosen id and prints a one-line confirmation:

```
$ sov resume s42
Switched to game s42 (round 3/15, ruleset campfire_v1).
```

If the game-id doesn't exist, exits 1 with a hint pointing at `sov games`.

### `sov new`

Starts a fresh game. Writes per-game files to `.sov/games/<game-id>/` and sets the active-game pointer to the new id. The previous active game stays on disk — `sov resume` can switch back to it.

## Active-game resolution

When any command needs to know which save to operate on, it resolves the active game in this order:

1. **v1 layout detected** → run auto-migration (see below), then use the migrated id.
2. **`.sov/active-game` exists and is non-empty** → use that game-id.
3. **`.sov/games/` contains exactly one game** → auto-select it and write the pointer.
4. **Otherwise** → fail with a clear error:

   > No active game. Run `sov games` to list saved games, then `sov resume <game-id>` to pick one. Or `sov new` to start fresh.

Rule 3 keeps single-game workflows frictionless: if there's only one save, you don't need to `sov resume` it explicitly.

## Migrating from v2.0.x

v2.1 auto-migrates v1 layouts on first command invocation. There is nothing to do as an operator — the migration runs once and is transparent.

What happens internally:

1. Detects `.sov/game_state.json` present and `.sov/games/` absent.
2. Reads `state.json` and derives `game_id = s{seed}`.
3. Creates `.sov/games/<game-id>/`.
4. Moves `.sov/game_state.json` → `.sov/games/<game-id>/state.json`, `.sov/rng_seed.txt` → `.sov/games/<game-id>/rng_seed.txt`, and the entire `.sov/proofs/` directory → `.sov/games/<game-id>/proofs/`.
5. Writes `.sov/active-game` containing the game-id.
6. Prints a one-line stderr notice:

   ```
   [multi-save] migrated v1 layout → .sov/games/<game-id>/
   ```

The migration is one-way and one-shot. After it runs, the v1 paths no longer exist. `.sov/wallet_seed.txt` and `.sov/season.json` are not moved — they stay at `.sov/` root because they were always cross-game state.

If you mistakenly run a v2.0.x binary against a migrated tree, it will see `.sov/game_state.json` missing and fail its existing `STATE_FILE.exists()` checks gracefully (no data loss; just upgrade to v2.1 to use the tree again).

## Game-id format

Game-ids are the string `s{seed}` (matching the existing convention from `sov_engine/hashing.py`). For example, a game with seed `42` has id `s42`. The id is stable for the life of the game — derived from the seed at `sov new` time, never regenerated.

## See also

- [CHANGELOG.md](../CHANGELOG.md) for the v2.1.0 release notes
- [docs/v2.1-roadmap.md](v2.1-roadmap.md) for the full v2.1 scope
- [CLAUDE.md](../CLAUDE.md) for the persistence layer's place in the codebase

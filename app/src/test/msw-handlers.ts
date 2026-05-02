// Default msw handlers for daemon endpoints. Tests can override per-test
// via server.use(...). Endpoint shapes mirror docs/v2.1-daemon-ipc.md §4.
//
// Stage 7-B (WEB-UI MED — msw fixtures match wire): every handler returns
// what the daemon ACTUALLY emits, not what the TS interface used to claim.
// The Stage A miss class was "msw fixture matches the (wrong) TS interface,
// so unit tests pass while real-daemon traffic 404s/400s/renders-as-missing."
// If a future test deliberately simplifies the wire shape (e.g., for unit-
// test isolation), tag with `// SIMPLIFIED FROM WIRE — see daemon spec`.

import { http, HttpResponse } from "msw";
import type { GameState } from "../types/game";

const PORT = 47823;
const BASE = `http://127.0.0.1:${PORT}`;

export function makeGameState(overrides?: Partial<GameState>): GameState {
  return {
    config: {
      seed: 42,
      ruleset: "campfire_v1",
      max_players: 4,
      max_rounds: 15,
      board_size: 16,
    },
    players: [],
    current_round: 1,
    game_over: false,
    winner: null,
    ...overrides,
  };
}

export const defaultHandlers = [
  http.get(`${BASE}/health`, () =>
    HttpResponse.json({
      status: "ok",
      version: "2.1.0",
      network: "testnet",
      readonly: false,
      ipc_version: 1,
      uptime_seconds: 1,
    }),
  ),

  http.get(`${BASE}/games`, () =>
    HttpResponse.json([
      {
        game_id: "s42",
        ruleset: "campfire_v1",
        current_round: 3,
        max_rounds: 15,
        players: ["alice", "bob"],
        last_modified_iso: "2026-05-02T00:01:00Z",
      },
    ]),
  ),

  http.get(`${BASE}/games/s42`, () =>
    HttpResponse.json(
      makeGameState({
        current_round: 3,
        players: [
          {
            name: "alice",
            coins: 5,
            reputation: 3,
            upgrades: 0,
            vouchers_held: [],
            active_deals: [],
            active_treaties: [],
            resources: {},
          },
          {
            name: "bob",
            coins: 7,
            reputation: 4,
            upgrades: 1,
            vouchers_held: [{ id: 1 }],
            active_deals: [],
            active_treaties: [],
            resources: {},
          },
        ],
      }),
    ),
  ),

  // GET /games/{id}/proofs — wire shape per sov_daemon/server.py:439-446.
  // Each entry is `{round, envelope_hash, final, path}` (NOT bare round-key
  // strings, as the type previously claimed). Stage 7-B WEB-UI-B-004 fix.
  http.get(`${BASE}/games/s42/proofs`, () =>
    HttpResponse.json([
      {
        round: 1,
        envelope_hash: "a".repeat(64),
        final: false,
        path: "/tmp/.sov/games/s42/proofs/round_001.proof.json",
      },
      {
        round: 2,
        envelope_hash: "b".repeat(64),
        final: false,
        path: "/tmp/.sov/games/s42/proofs/round_002.proof.json",
      },
      {
        round: 3,
        envelope_hash: "c".repeat(64),
        final: false,
        path: "/tmp/.sov/games/s42/proofs/round_003.proof.json",
      },
    ]),
  ),

  // GET /games/{id}/anchor-status/{round} — wire shape per
  // sov_daemon/server.py:486-539 (anchor_status_handler). Daemon emits
  // `{round, anchor_status, envelope_hash, txid?}` — NOT `{game_id, round,
  // status, txid?, explorer_url?}` as the type previously claimed.
  // Stage 7-B WEB-UI-B-003 fix.
  http.get(`${BASE}/games/s42/anchor-status/:round`, ({ params }) =>
    HttpResponse.json({
      round: params.round,
      anchor_status: "anchored",
      envelope_hash: "a".repeat(64),
      txid: "ABC123DEF",
    }),
  ),

  http.get(`${BASE}/games/s42/pending-anchors`, () => HttpResponse.json({})),
];

export const PORT_FOR_TESTS = PORT;

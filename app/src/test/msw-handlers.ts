// Default msw handlers for daemon endpoints. Tests can override per-test
// via server.use(...). Endpoint shapes mirror docs/v2.1-daemon-ipc.md §4.

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

  http.get(`${BASE}/games/s42/proofs`, () => HttpResponse.json(["1", "2", "3"])),

  http.get(`${BASE}/games/s42/anchor-status/:round`, ({ params }) =>
    HttpResponse.json({
      game_id: "s42",
      round: params.round,
      status: "anchored",
      txid: "ABC123DEF",
      explorer_url: "https://testnet.xrpl.org/transactions/ABC123DEF",
    }),
  ),

  http.get(`${BASE}/games/s42/pending-anchors`, () => HttpResponse.json({})),
];

export const PORT_FOR_TESTS = PORT;

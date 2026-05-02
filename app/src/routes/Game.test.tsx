import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  daemonStatus: vi.fn(),
  daemonStart: vi.fn(),
  daemonStop: vi.fn(),
  getDaemonConfig: vi.fn(),
}));

vi.mock("../lib/invoke", () => ({
  daemonStatus: mocks.daemonStatus,
  daemonStart: mocks.daemonStart,
  daemonStop: mocks.daemonStop,
  getDaemonConfig: mocks.getDaemonConfig,
}));

import { MemoryRouter } from "react-router-dom";
import { DaemonProvider } from "../hooks/useDaemon";
import Game from "./Game";

const cfg = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: false,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function makeFetch({
  games,
  state,
}: {
  games: unknown[];
  state?: unknown;
}) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.endsWith("/games")) return jsonResponse(games);
    if (url.includes("/games/") && state && !url.includes("/proofs") && !url.includes("/anchor")) {
      return jsonResponse(state);
    }
    if (url.endsWith("/events")) return new Response(null, { status: 200 });
    return new Response(JSON.stringify({}), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  });
}

function renderGame() {
  return render(
    <MemoryRouter>
      <DaemonProvider>
        <Game />
      </DaemonProvider>
    </MemoryRouter>,
  );
}

describe("Game /game route", () => {
  beforeEach(() => {
    mocks.daemonStatus.mockResolvedValue({ state: "running", config: cfg });
    mocks.getDaemonConfig.mockResolvedValue(cfg);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("renders empty state when no games", async () => {
    vi.stubGlobal("fetch", makeFetch({ games: [] }));
    renderGame();
    await waitFor(() => {
      expect(screen.getByText(/No active game/i)).toBeTruthy();
    });
  });

  it("renders game header + player cards + timeline when game is active", async () => {
    const games = [
      {
        game_id: "s42",
        ruleset: "campfire_v1",
        current_round: 7,
        max_rounds: 15,
        players: [],
        last_modified_iso: "2026-05-02T00:00:00Z",
      },
    ];
    const state = {
      config: { seed: 42, ruleset: "campfire_v1", max_players: 4, max_rounds: 15, board_size: 16 },
      players: [
        {
          name: "Renna",
          coins: 4,
          reputation: 7,
          upgrades: 1,
          vouchers_held: [],
          active_deals: [],
          active_treaties: [],
          resources: {},
        },
      ],
      current_round: 7,
      game_over: false,
      winner: null,
    };
    vi.stubGlobal("fetch", makeFetch({ games, state }));
    renderGame();

    await waitFor(() => {
      expect(screen.getByText("Renna")).toBeTruthy();
    });
    expect(screen.getByText(/Round 7 of 15/i)).toBeTruthy();
    expect(screen.getByText("coins")).toBeTruthy();
    // Campfire ruleset → no resources row.
    expect(screen.queryByText("food")).toBeNull();
  });

  it("daemon-down empty state names `sov daemon start` (WEB-UI-C-002)", async () => {
    mocks.daemonStatus.mockResolvedValue({ state: "none" });
    mocks.daemonStart.mockRejectedValue(new Error("daemon start failed"));
    vi.stubGlobal("fetch", makeFetch({ games: [] }));
    renderGame();
    await waitFor(() => {
      expect(screen.getByText("Daemon not running")).toBeTruthy();
    });
    expect(screen.getByText("sov daemon start")).toBeTruthy();
  });

  it("nav uses aria-current='page' for /game", async () => {
    vi.stubGlobal("fetch", makeFetch({ games: [] }));
    renderGame();
    await waitFor(() => {
      const link = screen.getAllByRole("link").find((l) => l.textContent === "Game");
      expect(link?.getAttribute("aria-current")).toBe("page");
    });
  });

  it("renders resources row for town_hall_v1 ruleset", async () => {
    const games = [
      {
        game_id: "s42",
        ruleset: "town_hall_v1",
        current_round: 1,
        max_rounds: 15,
        players: [],
        last_modified_iso: "2026-05-02T00:00:00Z",
      },
    ];
    const state = {
      config: { seed: 42, ruleset: "town_hall_v1", max_players: 4, max_rounds: 15, board_size: 16 },
      players: [
        {
          name: "Voss",
          coins: 6,
          reputation: 5,
          upgrades: 2,
          vouchers_held: [],
          active_deals: [],
          active_treaties: [],
          resources: { food: 2, wood: 1, tools: 0 },
        },
      ],
      current_round: 1,
      game_over: false,
      winner: null,
    };
    vi.stubGlobal("fetch", makeFetch({ games, state }));
    renderGame();
    await waitFor(() => {
      expect(screen.getByText("Voss")).toBeTruthy();
    });
    expect(screen.getByText("food")).toBeTruthy();
  });
});

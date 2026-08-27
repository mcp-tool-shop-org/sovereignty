import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { GameSummary } from "../types/daemon";
import type { GameState } from "../types/game";

const mockConfig = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: false,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

vi.mock("./useDaemon", () => ({
  useDaemon: () => ({
    status: "running",
    config: mockConfig,
    error: null,
    startDaemon: vi.fn(),
    stopDaemon: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("./useDaemonEvents", () => ({
  useDaemonEvents: () => {},
}));

import { pickActiveGame, useGameState } from "./useGameState";

describe("pickActiveGame", () => {
  function summary(id: string, isoSuffix: string): GameSummary {
    return {
      game_id: id,
      ruleset: "campfire_v1",
      current_round: 1,
      max_rounds: 15,
      players: [],
      last_modified_iso: `2026-05-02T${isoSuffix}`,
    };
  }

  it("returns null for empty list", () => {
    expect(pickActiveGame([])).toBeNull();
  });

  it("returns the only game when one exists", () => {
    expect(pickActiveGame([summary("s1", "00:00:00Z")])).toBe("s1");
  });

  it("returns the most-recently-modified game", () => {
    const games = [
      summary("old", "00:00:00Z"),
      summary("newest", "12:00:00Z"),
      summary("middle", "06:00:00Z"),
    ];
    expect(pickActiveGame(games)).toBe("newest");
  });

  it("breaks ties deterministically (lexical)", () => {
    const games = [summary("s2", "10:00:00Z"), summary("s1", "10:00:00Z")];
    const result = pickActiveGame(games);
    expect(["s1", "s2"]).toContain(result);
  });
});

describe("useGameState.refresh (F-1098ef9e)", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  function jsonResponse(body: unknown): Response {
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }

  function listing(id: string, iso: string): GameSummary {
    return {
      game_id: id,
      ruleset: "campfire_v1",
      current_round: 1,
      max_rounds: 15,
      players: [],
      last_modified_iso: iso,
    };
  }

  function state(over: boolean): GameState {
    return {
      config: {
        seed: 1,
        ruleset: "campfire_v1",
        max_players: 4,
        max_rounds: 15,
        board_size: 16,
      },
      players: [],
      current_round: 1,
      game_over: over,
      winner: over ? "alice" : null,
    };
  }

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("skips a finished newest game and selects the next-newest in-progress id", async () => {
    // Listing order is oldest-first (NOT recency). Newest is game_over;
    // two older games are in progress. Must pick the next-most-recent
    // in-progress id, not games[0] from the original listing.
    const games = [
      listing("s_old_in_progress", "2026-05-01T00:00:00Z"),
      listing("s_newer_in_progress", "2026-05-02T06:00:00Z"),
      listing("s_newest_over", "2026-05-02T12:00:00Z"),
    ];
    fetchMock.mockImplementation((url: string) => {
      if (url.endsWith("/games")) return Promise.resolve(jsonResponse(games));
      if (url.endsWith("/games/s_newest_over")) return Promise.resolve(jsonResponse(state(true)));
      if (url.endsWith("/games/s_newer_in_progress"))
        return Promise.resolve(jsonResponse(state(false)));
      if (url.endsWith("/games/s_old_in_progress"))
        return Promise.resolve(jsonResponse(state(false)));
      return Promise.reject(new Error(`unhandled ${url}`));
    });

    const { result } = renderHook(() => useGameState());
    await act(async () => {
      await result.current.refresh();
    });
    await waitFor(() => {
      expect(result.current.activeGameId).toBe("s_newer_in_progress");
    });
    expect(result.current.state?.game_over).toBe(false);
  });
});

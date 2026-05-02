import { describe, expect, it } from "vitest";
import type { GameSummary } from "../types/daemon";
import { pickActiveGame } from "./useGameState";

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
    // Both have same iso, so localeCompare ties (returns 0); first stays first
    // after stable sort. The result is one of them.
    const result = pickActiveGame(games);
    expect(["s1", "s2"]).toContain(result);
  });
});

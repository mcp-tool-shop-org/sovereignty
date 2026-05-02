import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PlayerState } from "../types/game";
import { PlayerCard } from "./PlayerCard";

const basePlayer: PlayerState = {
  name: "Renna",
  coins: 4,
  reputation: 7,
  upgrades: 1,
  vouchers_held: [{ id: 1 }, { id: 2 }],
  active_deals: [{ id: 1 }],
  active_treaties: [{ id: 1 }],
  resources: { food: 2, wood: 1, tools: 0 },
};

describe("PlayerCard", () => {
  it("renders the player name", () => {
    render(<PlayerCard player={basePlayer} ruleset="campfire_v1" />);
    expect(screen.getByText("Renna")).toBeTruthy();
  });

  it("renders coins primitive (NOT votes)", () => {
    render(<PlayerCard player={basePlayer} ruleset="campfire_v1" />);
    expect(screen.getByText("coins")).toBeTruthy();
    expect(screen.queryByText("votes")).toBeNull();
  });

  it("renders reputation, upgrades, vouchers, deals, treaties counts", () => {
    render(<PlayerCard player={basePlayer} ruleset="campfire_v1" />);
    expect(screen.getByText("reputation")).toBeTruthy();
    expect(screen.getByText("upgrades")).toBeTruthy();
    expect(screen.getByText("vouchers")).toBeTruthy();
    expect(screen.getByText("deals")).toBeTruthy();
    expect(screen.getByText("treaties")).toBeTruthy();
    // counts:
    expect(screen.getByText("2")).toBeTruthy(); // vouchers
  });

  it("OMITS resources row for campfire ruleset (spec §3)", () => {
    render(<PlayerCard player={basePlayer} ruleset="campfire_v1" />);
    expect(screen.queryByLabelText("resources")).toBeNull();
    expect(screen.queryByText("food")).toBeNull();
  });

  it("RENDERS resources row for town_hall ruleset (spec §3)", () => {
    render(<PlayerCard player={basePlayer} ruleset="town_hall_v1" />);
    expect(screen.getByLabelText("resources")).toBeTruthy();
    expect(screen.getByText("food")).toBeTruthy();
    expect(screen.getByText("wood")).toBeTruthy();
    expect(screen.getByText("tools")).toBeTruthy();
  });

  it("renders aria-label='Player <name>'", () => {
    render(<PlayerCard player={basePlayer} ruleset="campfire_v1" />);
    expect(screen.getByLabelText("Player Renna")).toBeTruthy();
  });
});

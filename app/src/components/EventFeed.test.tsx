import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EventFeed, type FeedEntry, formatEventSummary } from "./EventFeed";

describe("EventFeed", () => {
  it("renders empty text when no events", () => {
    render(<EventFeed events={[]} emptyText="(nothing)" />);
    expect(screen.getByText("(nothing)")).toBeTruthy();
  });

  it("renders ul with aria-live='polite' (spec §1)", () => {
    const entries: FeedEntry[] = [
      {
        ts: Date.parse("2026-05-02T12:34:56Z"),
        event: { type: "anchor.pending_added", data: { round: "3" } },
      },
    ];
    const { container } = render(<EventFeed events={entries} />);
    const ul = container.querySelector("ul");
    expect(ul?.getAttribute("aria-live")).toBe("polite");
  });

  it("limits visible items to last N", () => {
    const entries: FeedEntry[] = Array.from({ length: 30 }, (_, i) => ({
      ts: 1_000_000 + i,
      event: { type: "anchor.pending_added", data: { round: String(i) } },
    }));
    const { container } = render(<EventFeed events={entries} limit={5} />);
    expect(container.querySelectorAll("li").length).toBe(5);
  });
});

describe("formatEventSummary", () => {
  it("formats anchor.pending_added", () => {
    const out = formatEventSummary({
      type: "anchor.pending_added",
      data: { round: "5" },
    });
    expect(out).toBe("round 5");
  });

  it("formats anchor.batch_complete with txid abbrev", () => {
    const out = formatEventSummary({
      type: "anchor.batch_complete",
      data: { rounds: ["1", "2", "3"], txid: "ABCDEF1234567890" },
    });
    expect(out).toContain("rounds 1–3");
    expect(out).toContain("ABCD");
  });

  it("formats game.state_changed", () => {
    const out = formatEventSummary({
      type: "game.state_changed",
      data: { game_id: "s42" },
    });
    expect(out).toBe("game s42 update");
  });

  it("formats error events", () => {
    const out = formatEventSummary({
      type: "error",
      data: { level: "warn", message: "transport unreachable" },
    });
    expect(out).toContain("warn");
    expect(out).toContain("transport unreachable");
  });
});

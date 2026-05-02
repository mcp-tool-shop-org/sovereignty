import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DisconnectedPlugGlyph, EmptyBoxGlyph, EmptyState, PausedGameGlyph } from "./EmptyState";

describe("EmptyState", () => {
  it("renders title", () => {
    render(<EmptyState title="No games yet" />);
    expect(screen.getByText("No games yet")).toBeTruthy();
  });

  it("renders body when given", () => {
    render(<EmptyState title="Empty" body="some prose" />);
    expect(screen.getByText("some prose")).toBeTruthy();
  });

  it("renders cta when given", () => {
    render(<EmptyState title="Empty" cta={<a href="/audit">Open</a>} />);
    expect(screen.getByText("Open")).toBeTruthy();
  });

  it("uses aria-label='empty state' on the section", () => {
    render(<EmptyState title="No games" />);
    expect(screen.getByLabelText("empty state")).toBeTruthy();
  });

  // ── Stage 9-D Theme 4 (WEB-UI-D-013) ──────────────────────────────────
  it("WEB-UI-D-013: renders optional glyph slot above the title", () => {
    render(
      <EmptyState
        glyph={<svg role="img" aria-label="test glyph" data-testid="glyph" />}
        title="Test"
      />,
    );
    expect(screen.getByLabelText("test glyph")).toBeTruthy();
  });

  it("WEB-UI-D-013: omits glyph slot when not provided (no extra DOM)", () => {
    render(<EmptyState title="No glyph" />);
    expect(screen.queryByRole("img")).toBeNull();
  });
});

describe("EmptyState glyphs (Stage 9-D inline-SVG only — Mike's lock #5)", () => {
  it("EmptyBoxGlyph renders with role='img' + aria-label", () => {
    render(<EmptyBoxGlyph />);
    expect(screen.getByLabelText("empty box")).toBeTruthy();
  });

  it("PausedGameGlyph renders with role='img' + aria-label", () => {
    render(<PausedGameGlyph />);
    expect(screen.getByLabelText("paused game")).toBeTruthy();
  });

  it("DisconnectedPlugGlyph renders with role='img' + aria-label", () => {
    render(<DisconnectedPlugGlyph />);
    expect(screen.getByLabelText("disconnected")).toBeTruthy();
  });

  it("Glyphs use currentColor for theme alignment (no hardcoded hex)", () => {
    const { container } = render(<EmptyBoxGlyph />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute("stroke")).toBe("currentColor");
  });
});

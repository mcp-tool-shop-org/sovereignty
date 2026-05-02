import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./EmptyState";

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
});

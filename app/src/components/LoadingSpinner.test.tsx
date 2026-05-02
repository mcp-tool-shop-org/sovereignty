import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LoadingSpinner } from "./LoadingSpinner";

describe("LoadingSpinner", () => {
  it("renders default label", () => {
    render(<LoadingSpinner />);
    expect(screen.getByText(/Loading…/)).toBeTruthy();
  });

  it("renders custom label", () => {
    render(<LoadingSpinner label="Fetching games" />);
    expect(screen.getByText(/Fetching games…/)).toBeTruthy();
  });

  it("uses role='status' with aria-busy=true", () => {
    render(<LoadingSpinner label="Working" />);
    const el = screen.getByRole("status");
    expect(el.getAttribute("aria-busy")).toBe("true");
    expect(el.getAttribute("aria-label")).toBe("Working");
  });
});

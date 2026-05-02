import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Pill } from "./Pill";

describe("Pill", () => {
  it("renders children", () => {
    render(<Pill>running</Pill>);
    expect(screen.getByText("running")).toBeTruthy();
  });

  it("uses role='status' when live=true (spec §1)", () => {
    render(<Pill live>live</Pill>);
    const el = screen.getByRole("status");
    expect(el.textContent).toBe("live");
  });

  it("does NOT use role='status' when live is unset", () => {
    render(<Pill>quiet</Pill>);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("applies title attribute", () => {
    render(<Pill title="hover text">x</Pill>);
    const el = screen.getByText("x");
    expect(el.getAttribute("title")).toBe("hover text");
  });
});

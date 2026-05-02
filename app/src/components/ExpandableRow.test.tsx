import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExpandableRow } from "./ExpandableRow";

describe("ExpandableRow", () => {
  it("uses native <details><summary> elements (spec §1)", () => {
    const { container } = render(<ExpandableRow summary="head">body</ExpandableRow>);
    expect(container.querySelector("details")).not.toBeNull();
    expect(container.querySelector("summary")).not.toBeNull();
  });

  it("renders summary content", () => {
    render(<ExpandableRow summary="game s42">body</ExpandableRow>);
    expect(screen.getByText("game s42")).toBeTruthy();
  });

  it("renders body content", () => {
    render(<ExpandableRow summary="head">expanded body</ExpandableRow>);
    expect(screen.getByText("expanded body")).toBeTruthy();
  });

  it("starts open when defaultOpen=true", () => {
    const { container } = render(
      <ExpandableRow summary="h" defaultOpen>
        b
      </ExpandableRow>,
    );
    const details = container.querySelector("details");
    expect(details?.hasAttribute("open")).toBe(true);
  });

  it("calls onToggle when toggled", () => {
    const onToggle = vi.fn();
    const { container } = render(
      <ExpandableRow summary="h" onToggle={onToggle}>
        b
      </ExpandableRow>,
    );
    const details = container.querySelector("details") as HTMLDetailsElement;
    details.open = true;
    fireEvent(details, new Event("toggle"));
    expect(onToggle).toHaveBeenCalledWith(true);
  });
});

import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RoundTimeline } from "./RoundTimeline";

describe("RoundTimeline", () => {
  it("renders one dot per round", () => {
    const { container } = render(<RoundTimeline total={15} current={1} />);
    const dots = container.querySelectorAll("[data-kind]");
    expect(dots.length).toBe(15);
  });

  it("marks rounds before current as complete", () => {
    const { container } = render(<RoundTimeline total={5} current={3} />);
    const completeDots = container.querySelectorAll('[data-kind="complete"]');
    expect(completeDots.length).toBe(2); // rounds 1, 2
  });

  it("marks current round as active", () => {
    const { container } = render(<RoundTimeline total={5} current={3} />);
    const activeDots = container.querySelectorAll('[data-kind="active"]');
    expect(activeDots.length).toBe(1);
  });

  it("marks all rounds complete when gameOver=true", () => {
    const { container } = render(<RoundTimeline total={5} current={3} gameOver />);
    const completeDots = container.querySelectorAll('[data-kind="complete"]');
    expect(completeDots.length).toBe(5);
  });

  it("uses role='img' with descriptive aria-label", () => {
    const { container } = render(<RoundTimeline total={15} current={7} />);
    const img = container.querySelector('[role="img"]');
    expect(img?.getAttribute("aria-label")).toMatch(/Round 7 of 15/);
  });
});

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

  // ── Stage 9-D Theme 2 (WEB-UI-D-002 .. D-005) ─────────────────────────

  it("WEB-UI-D-024: live pill carries the .live className for the pulsing dot", () => {
    render(<Pill live>live</Pill>);
    const el = screen.getByRole("status");
    expect(el.className).toMatch(/live/);
  });

  it("WEB-UI-D-024: non-live pill does NOT carry the .live className", () => {
    render(<Pill>quiet</Pill>);
    const el = screen.getByText("quiet");
    expect(el.className).not.toMatch(/\blive\b/);
  });

  it("WEB-UI-D-002: variant classes apply across success / warn / error / accent", () => {
    const { rerender } = render(<Pill variant="success">ok</Pill>);
    expect(screen.getByText("ok").className).toMatch(/success/);
    rerender(<Pill variant="warn">warn</Pill>);
    expect(screen.getByText("warn").className).toMatch(/warn/);
    rerender(<Pill variant="error">err</Pill>);
    expect(screen.getByText("err").className).toMatch(/error/);
    rerender(<Pill variant="accent">accent</Pill>);
    expect(screen.getByText("accent").className).toMatch(/accent/);
  });

  it("WEB-UI-D-027: title is mirrored into aria-label for SR accessibility", () => {
    render(<Pill title="verification failed: not on chain">x</Pill>);
    const el = screen.getByText("x");
    expect(el.getAttribute("aria-label")).toBe("verification failed: not on chain");
  });
});

describe("Pill — token sweep snapshot (Stage 9-D Theme 2)", () => {
  // Snapshot tests pin the fact that `.success/.warn/.error/.accent` classes
  // are applied; the actual color tokens are asserted at the CSS module level
  // (drift would change which token name the class references; the test
  // exists to fail loud on rename).
  it("token sweep — colored pills carry their semantic class", () => {
    const variants = ["success", "warn", "error", "accent"] as const;
    for (const v of variants) {
      const { container, unmount } = render(<Pill variant={v}>{v}</Pill>);
      const span = container.querySelector("span");
      expect(span).not.toBeNull();
      expect(span?.className).toMatch(new RegExp(v));
      unmount();
    }
  });
});

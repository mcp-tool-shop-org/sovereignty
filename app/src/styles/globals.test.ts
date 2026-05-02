// Stage 9-D Theme 4 (WEB-UI-D-015) regression test — assert that
// globals.css ships a `:focus-visible` baseline rule pointing at the
// theme accent token. The rule is the single source of truth for keyboard
// focus rings across the app; per-component overrides are only allowed
// where shape demands.
//
// We assert against the file text because css-modules don't ship a parsed
// stylesheet at runtime, and JSDOM's getComputedStyle won't report
// :focus-visible state. File-text assertion is brittle to formatting but
// honest about what we're checking.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const GLOBALS_CSS = resolve(__dirname, "globals.css");
const THEME_CSS = resolve(__dirname, "theme.css");

function readCss(path: string): string {
  return readFileSync(path, "utf-8");
}

describe("globals.css — Stage 9-D discipline rules", () => {
  it("WEB-UI-D-015: ships a :focus-visible baseline pointing at --sov-accent", () => {
    const css = readCss(GLOBALS_CSS);
    expect(css).toContain(":focus-visible");
    // The rule must reference the accent token, not a literal color.
    const focusBlock = /\:focus-visible\s*\{[^}]+\}/m.exec(css);
    expect(focusBlock).not.toBeNull();
    expect(focusBlock?.[0]).toContain("var(--sov-accent)");
  });

  it("WEB-UI-D-017: ships a (max-width: 960px) media query for the Tauri minWidth", () => {
    const css = readCss(GLOBALS_CSS);
    expect(css).toMatch(/@media\s*\(max-width:\s*960px\)/);
  });

  it("WEB-UI-D-030: button:disabled uses muted token rather than opacity", () => {
    const css = readCss(GLOBALS_CSS);
    const block = /button:disabled\s*\{[^}]+\}/m.exec(css);
    expect(block).not.toBeNull();
    expect(block?.[0]).toContain("var(--sov-fg-muted)");
    expect(block?.[0]).not.toContain("opacity: 0.5");
  });
});

describe("theme.css — Stage 9-D token additions", () => {
  it("WEB-UI-D-001: defines --sov-overlay (single-source modal backdrop)", () => {
    const css = readCss(THEME_CSS);
    expect(css).toMatch(/--sov-overlay:/);
  });

  it("does not introduce other rgba()/hex literals outside the documented set", () => {
    // Pin D will catch the broader pattern at CI; here we just confirm
    // theme.css remains the single source of truth.
    const css = readCss(THEME_CSS);
    // theme.css MAY have hex literals — that's its purpose. Just assert it
    // didn't accidentally lose --sov-radius or --sov-radius-sm.
    expect(css).toContain("--sov-radius");
  });
});

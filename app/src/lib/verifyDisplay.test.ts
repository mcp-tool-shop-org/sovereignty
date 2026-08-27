import { describe, expect, it } from "vitest";
import { anchorStatusDisplay, verifyFailureDisplay } from "./verifyDisplay";

describe("anchorStatusDisplay (WEB-UI-C-005 / F-7f7091d3)", () => {
  it("maps each AnchorStatus value to local-index vocabulary", () => {
    expect(anchorStatusDisplay("anchored")).toBe("Anchored");
    expect(anchorStatusDisplay("pending")).toBe("Pending");
    expect(anchorStatusDisplay("missing")).toBe("No local anchor");
  });
});

describe("verifyFailureDisplay (WEB-UI-C-005 + C-006)", () => {
  it("returns short label + recovery detail for envelope_mismatch", () => {
    const d = verifyFailureDisplay("envelope_mismatch");
    expect(d.short).toBe("envelope mismatch");
    expect(d.detail).toMatch(/proof/i);
  });

  it("returns short label + recovery detail for not_on_chain", () => {
    const d = verifyFailureDisplay("not_on_chain");
    expect(d.short).toBe("not on chain");
    expect(d.detail).toMatch(/sov anchor/);
  });

  it("daemon_unreachable copy points at sov daemon status (C-006 split)", () => {
    const d = verifyFailureDisplay("daemon_unreachable");
    expect(d.short).toBe("daemon unreachable");
    expect(d.detail).toMatch(/sov daemon status/);
  });

  it("chain_unreachable copy is distinct from daemon_unreachable (C-006 split)", () => {
    const daemon = verifyFailureDisplay("daemon_unreachable");
    const chain = verifyFailureDisplay("chain_unreachable");
    expect(daemon.short).not.toBe(chain.short);
    expect(daemon.detail).not.toBe(chain.detail);
    expect(chain.detail).toMatch(/sov verify/);
  });
});

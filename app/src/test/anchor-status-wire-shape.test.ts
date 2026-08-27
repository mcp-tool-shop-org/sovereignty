// Real-fixture wire-shape regression test for the anchor-status endpoint.
//
// Stage 7-B WEB-UI-B-003 (Stage A miss → Path 2 bundle).
// F-bdddd7f6: fixtures assign to AnchorStatusResponse without `as` so
// object-literal assignability + excess-property checks are real. A
// compile-time forbidden-key pin fails tsc if `status` / `game_id` /
// `explorer_url` return. Audit browse branches are driven off the real
// module export, not a copied ternary.

import { describe, expect, it } from "vitest";
import { auditBrowseAnchorParts } from "../routes/Audit";
import type { AnchorStatusResponse } from "../types/daemon";

type _Forbidden = Extract<keyof AnchorStatusResponse, "status" | "game_id" | "explorer_url">;
const _pin: [_Forbidden] extends [never] ? true : never = true;
void _pin;

describe("AnchorStatusResponse wire-shape regression (WEB-UI-B-003)", () => {
  const anchoredFixture: AnchorStatusResponse = {
    round: "3",
    anchor_status: "anchored",
    envelope_hash: "deadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00d",
    txid: "ABCDEF0123456789",
  };

  const pendingFixture: AnchorStatusResponse = {
    round: "5",
    anchor_status: "pending",
    envelope_hash: "00000000000000000000000000000000000000000000000000000000000abcde",
  };

  const missingFixture: AnchorStatusResponse = {
    round: "FINAL",
    anchor_status: "missing",
    envelope_hash: null,
  };

  it("anchored fixture parses cleanly through TS interface", () => {
    expect(anchoredFixture.anchor_status).toBe("anchored");
    expect(anchoredFixture.round).toBe("3");
    expect(anchoredFixture.txid).toBe("ABCDEF0123456789");
  });

  it("pending fixture parses without txid", () => {
    expect(pendingFixture.anchor_status).toBe("pending");
    expect(pendingFixture.txid).toBeUndefined();
  });

  it("missing fixture handles null envelope_hash", () => {
    expect(missingFixture.anchor_status).toBe("missing");
    expect(missingFixture.envelope_hash).toBeNull();
    expect(missingFixture.txid).toBeUndefined();
  });

  it("rejects pre-fix legacy shape `{game_id, round, status, ...}`", () => {
    for (const fixture of [anchoredFixture, pendingFixture, missingFixture]) {
      expect("status" in fixture).toBe(false);
      expect("game_id" in fixture).toBe(false);
      expect("explorer_url" in fixture).toBe(false);
      expect("anchor_status" in fixture).toBe(true);
    }
  });

  it("Audit.tsx browse branches read anchor_status via auditBrowseAnchorParts", () => {
    const branches = [anchoredFixture, pendingFixture, missingFixture].map((fix) => {
      const parts = auditBrowseAnchorParts(fix);
      return { round: fix.round, icon: parts.icon, variant: parts.variant };
    });
    expect(branches).toEqual([
      { round: "3", icon: "✓", variant: "success" },
      { round: "5", icon: "⊘", variant: "warn" },
      { round: "FINAL", icon: "✗", variant: "error" },
    ]);
  });
});

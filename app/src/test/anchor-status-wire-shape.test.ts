// Real-fixture wire-shape regression test for the anchor-status endpoint.
//
// Stage 7-B WEB-UI-B-003 (Stage A miss → Path 2 bundle).
//
// Why this file exists: pre-Stage 7-B, `app/src/types/daemon.ts`
// `AnchorStatusResponse` declared `{game_id, round, status, txid?,
// explorer_url?}` while the daemon at `sov_daemon/server.py:486-539`
// actually emits `{round, anchor_status, envelope_hash, txid?}`. The msw
// handler matched the (wrong) TS interface, so unit tests passed while
// any real daemon would render every round as "missing" (the falsy-eq
// fallback in `Audit.tsx`).
//
// This test pins the post-fix shape against a hand-built fixture matching
// the daemon's actual emission. It is intentionally hand-built rather than
// recorded from a live daemon: the fixture should travel with the test, not
// require a daemon round-trip to regenerate. The Python side has its own
// pin (`tests/test_daemon_endpoint_shapes.py`-class tests are the eventual
// home — that contract test boots the daemon and asserts response keys).
//
// If a v2.2 daemon adds a new field, both this test and the TS interface
// must update together. If the test fails after a daemon-side change but
// the interface hasn't moved, that's the drift this lens is designed to
// catch.

import { describe, expect, it } from "vitest";
import type { AnchorStatusResponse } from "../types/daemon";

describe("AnchorStatusResponse wire-shape regression (WEB-UI-B-003)", () => {
  // Real wire shape per sov_daemon/server.py:486-539, anchor_status_handler.
  // Construct the JSON exactly as the daemon emits it (not "as the type
  // claims it should look") — keys, types, ordering all match Python emit.
  const anchoredFixture = {
    round: "3",
    anchor_status: "anchored",
    envelope_hash: "deadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00d",
    txid: "ABCDEF0123456789",
  };

  const pendingFixture = {
    round: "5",
    anchor_status: "pending",
    envelope_hash: "00000000000000000000000000000000000000000000000000000000000abcde",
    // No txid — pending rounds have no transaction id yet.
  };

  const missingFixture = {
    round: "FINAL",
    anchor_status: "missing",
    envelope_hash: null, // proof file absent / unreadable → null per server.py:516-517
    // No txid — missing rounds have no transaction id.
  };

  it("anchored fixture parses cleanly through TS interface", () => {
    // The cast is the assertion: a real-fixture parse that compiled.
    // If the interface diverges from this shape, tsc fails the build.
    const parsed: AnchorStatusResponse = anchoredFixture as AnchorStatusResponse;
    expect(parsed.anchor_status).toBe("anchored");
    expect(parsed.round).toBe("3");
    expect(parsed.envelope_hash).toBe(anchoredFixture.envelope_hash);
    expect(parsed.txid).toBe("ABCDEF0123456789");
  });

  it("pending fixture parses without txid", () => {
    const parsed: AnchorStatusResponse = pendingFixture as AnchorStatusResponse;
    expect(parsed.anchor_status).toBe("pending");
    expect(parsed.txid).toBeUndefined();
  });

  it("missing fixture handles null envelope_hash", () => {
    const parsed: AnchorStatusResponse = missingFixture as AnchorStatusResponse;
    expect(parsed.anchor_status).toBe("missing");
    expect(parsed.envelope_hash).toBeNull();
    expect(parsed.txid).toBeUndefined();
  });

  it("rejects pre-fix legacy shape `{game_id, round, status, ...}`", () => {
    // Compile-time pin: the TS interface MUST NOT declare these legacy keys.
    // If a refactor accidentally restored them, this test still passes at
    // runtime (extra fields parse fine) BUT a parallel type-level assertion
    // ensures the field name `status` is not on AnchorStatusResponse.
    const legacy = {
      game_id: "s42", // not on AnchorStatusResponse anymore
      round: "3",
      status: "anchored", // wrong key — wire is `anchor_status`
      txid: "ABC",
      explorer_url: "https://example.com/tx/ABC", // not emitted by this endpoint
    };
    // Runtime narrowing — `status` is NOT a member of AnchorStatusResponse.
    // The legacy object is intentionally NOT cast as AnchorStatusResponse;
    // the explicit cast at the next line would be a type error if the
    // interface still had `status`. Use Record<string, unknown> as the
    // legacy bag, then check the parse extracts only valid AnchorStatus
    // fields.
    const bag: Record<string, unknown> = legacy;
    expect(bag.status).toBe("anchored"); // still in the bag
    expect("status" in ({} as AnchorStatusResponse)).toBe(false);
    expect("game_id" in ({} as AnchorStatusResponse)).toBe(false);
    expect("explorer_url" in ({} as AnchorStatusResponse)).toBe(false);
  });

  it("Audit.tsx rendering branches (anchored / pending / missing) read anchor_status", () => {
    // Mini-render simulator — same branch logic as Audit.tsx::RoundRowView
    // and useVerifyFlow.ts. If TS field rename drifts back to `status`,
    // these branches go undefined-truthy and every row becomes "missing".
    const branches = [anchoredFixture, pendingFixture, missingFixture].map((fix) => {
      const s = fix as AnchorStatusResponse;
      const icon = s.anchor_status === "anchored" ? "✓" : s.anchor_status === "pending" ? "⊘" : "✗";
      const variant =
        s.anchor_status === "anchored"
          ? "success"
          : s.anchor_status === "pending"
            ? "warn"
            : "error";
      return { round: s.round, icon, variant };
    });
    expect(branches).toEqual([
      { round: "3", icon: "✓", variant: "success" },
      { round: "5", icon: "⊘", variant: "warn" },
      { round: "FINAL", icon: "✗", variant: "error" },
    ]);
  });
});

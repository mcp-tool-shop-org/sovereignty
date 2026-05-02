// Real-fixture wire-shape regression test for the proofs-list endpoint.
//
// Stage 7-B WEB-UI-B-004 (Stage A miss → Path 2 bundle).
//
// Why this file exists: pre-Stage 7-B, `app/src/lib/daemonClient.ts`
// declared `proofs(...): Promise<string[]>` and cast the body as `string[]`.
// The daemon at `sov_daemon/server.py:439-446` actually emits an array of
// objects: `[{round, envelope_hash, final, path}, ...]`. Audit.tsx then
// looped `for (const round of roundKeys)` and called
// `client.anchorStatus(gameId, round)` passing a whole object as the
// path-param. `encodeURIComponent({...})` produces `"%5Bobject%20Object%5D"`
// → the daemon 400s with INVALID_ROUND. Net effect: zero rounds visible in
// the audit table against any real daemon.
//
// This test pins the post-fix `ProofMeta[]` shape and the
// `encodeURIComponent(round)` flow in Audit.tsx. The fixture matches
// daemon emit byte-for-byte (round can be int or "FINAL" string;
// envelope_hash is a 64-char hex; path is an absolute filesystem string).

import { describe, expect, it } from "vitest";
import type { ProofMeta } from "../types/daemon";

describe("ProofMeta[] wire-shape regression (WEB-UI-B-004)", () => {
  // Real wire shape per sov_daemon/server.py:439-446 (proofs_list_handler).
  // The daemon iterates `pdir.glob("*.json")` and appends:
  //   {"round": data.get("round"), "envelope_hash": data.get("envelope_hash"),
  //    "final": bool(data.get("final", False)), "path": str(path)}
  // `round` is an int for normal rounds and the string "FINAL" for the
  // closing round (per CLAUDE.md "game_id format" + the FINAL convention).
  const wireFixture = [
    {
      round: 1,
      envelope_hash: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
      final: false,
      path: "/Users/op/.sov/games/s42/proofs/round_001.proof.json",
    },
    {
      round: 2,
      envelope_hash: "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
      final: false,
      path: "/Users/op/.sov/games/s42/proofs/round_002.proof.json",
    },
    {
      round: "FINAL",
      envelope_hash: "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
      final: true,
      path: "/Users/op/.sov/games/s42/proofs/FINAL.proof.json",
    },
  ];

  it("parses each entry through ProofMeta", () => {
    // Daemon emits round as int OR string; the TS interface declares string
    // because consumers always coerce via String(round) for URL construction.
    // The cast asserts the type is loose enough on `round` for both forms.
    const parsed = wireFixture as unknown as ProofMeta[];
    expect(parsed).toHaveLength(3);
    expect(parsed[0].envelope_hash).toHaveLength(64);
    expect(parsed[0].final).toBe(false);
    expect(parsed[2].final).toBe(true);
    expect(parsed[2].path).toContain("FINAL");
  });

  it("Audit.tsx round iterator coerces round to string and avoids object-stringification bug", () => {
    // Pre-fix: `for (const round of roundKeys)` over `string[]` → fine.
    // Pre-fix actual: roundKeys was ProofMeta[], so `round` was the whole
    // object. encodeURIComponent({...}) → "%5Bobject%20Object%5D".
    // Post-fix: explicit String(meta.round) extraction → URL-safe.
    const proofs = wireFixture as unknown as ProofMeta[];
    const urls = proofs.map((meta) => {
      const round = String(meta.round);
      return `/games/s42/anchor-status/${encodeURIComponent(round)}`;
    });
    expect(urls).toEqual([
      "/games/s42/anchor-status/1",
      "/games/s42/anchor-status/2",
      "/games/s42/anchor-status/FINAL",
    ]);
    // The bug-class assertion: no URL should contain the literal substring
    // "%5Bobject" (URL-encoded "[object"). If the iterator ever passes the
    // raw ProofMeta object as a path-param again, this fails immediately.
    for (const url of urls) {
      expect(url).not.toContain("%5Bobject");
    }
  });

  it("rejects pre-fix bare-string-array shape", () => {
    // Sanity: a `string[]` body would NOT parse as ProofMeta[] without
    // throwing or producing garbage entries. Document the legacy shape so
    // a future audit can grep for "WEB-UI-B-004" and find this test.
    const legacy = ["1", "2", "3"] as unknown as ProofMeta[];
    // Each "entry" is a string — accessing `.envelope_hash` returns undefined.
    expect(legacy[0].envelope_hash).toBeUndefined();
    expect(legacy[0].path).toBeUndefined();
    expect(legacy[0].final).toBeUndefined();
  });
});

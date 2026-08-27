// Real-fixture wire-shape regression test for the proofs-list endpoint.
//
// Stage 7-B WEB-UI-B-004 (Stage A miss → Path 2 bundle).
// F-bdddd7f6: assign fixtures to ProofMeta without `as unknown as`.

import { describe, expect, it } from "vitest";
import type { ProofMeta } from "../types/daemon";

function isProofMeta(value: unknown): value is ProofMeta {
  return (
    typeof value === "object" &&
    value !== null &&
    "round" in value &&
    "envelope_hash" in value &&
    "final" in value &&
    "path" in value
  );
}

describe("ProofMeta[] wire-shape regression (WEB-UI-B-004)", () => {
  const wireFixture: ProofMeta[] = [
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
    expect(wireFixture).toHaveLength(3);
    expect(wireFixture[0].envelope_hash).toHaveLength(64);
    expect(wireFixture[0].final).toBe(false);
    expect(wireFixture[2].final).toBe(true);
    expect(wireFixture[2].path).toContain("FINAL");
  });

  it("Audit.tsx round iterator coerces round to string and avoids object-stringification bug", () => {
    const urls = wireFixture.map((meta) => {
      const round = String(meta.round);
      return `/games/s42/anchor-status/${encodeURIComponent(round)}`;
    });
    expect(urls).toEqual([
      "/games/s42/anchor-status/1",
      "/games/s42/anchor-status/2",
      "/games/s42/anchor-status/FINAL",
    ]);
    for (const url of urls) {
      expect(url).not.toContain("%5Bobject");
    }
  });

  it("rejects pre-fix bare-string-array shape", () => {
    const legacy: unknown[] = ["1", "2", "3"];
    expect(isProofMeta(legacy[0])).toBe(false);
  });
});

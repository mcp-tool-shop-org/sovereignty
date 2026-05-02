import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { canonicalJson, sha256Hex, useVerifyFlow } from "./useVerifyFlow";

// Mock the daemon context provider — return a stable config.
const mockConfig = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: false,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

vi.mock("./useDaemon", () => ({
  useDaemon: () => ({
    status: "running",
    config: mockConfig,
    error: null,
    startDaemon: vi.fn(),
    stopDaemon: vi.fn(),
    refresh: vi.fn(),
  }),
}));

describe("canonicalJson", () => {
  // Source of truth: sov_engine/serialize.py::canonical_json
  //   json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False,
  //              separators=(",", ": ")).replace("\r\n", "\n") + "\n"
  // Multi-line pretty-printed, 2-space indent, space after `:`, trailing LF.

  it("emits indent=2 + sorted keys + trailing LF for simple objects", () => {
    const out = canonicalJson({ b: 2, a: 1 });
    expect(out).toBe('{\n  "a": 1,\n  "b": 2\n}\n');
  });

  it("recursively sorts nested keys", () => {
    const out = canonicalJson({ z: { y: 1, x: 2 } });
    expect(out).toBe('{\n  "z": {\n    "x": 2,\n    "y": 1\n  }\n}\n');
  });

  it("preserves array order", () => {
    const out = canonicalJson({ list: [3, 1, 2] });
    expect(out).toBe('{\n  "list": [\n    3,\n    1,\n    2\n  ]\n}\n');
  });

  it("handles strings, booleans, null", () => {
    const out = canonicalJson({ s: "x", b: true, n: null });
    expect(out).toBe('{\n  "b": true,\n  "n": null,\n  "s": "x"\n}\n');
  });

  it("keeps empty containers on one line (matches Python's indent= behavior)", () => {
    expect(canonicalJson({ a: [], b: {} })).toBe('{\n  "a": [],\n  "b": {}\n}\n');
  });

  it("ensure_ascii=False — non-ASCII passes through as raw UTF-8", () => {
    const out = canonicalJson({ note: "éclat" });
    // Must NOT escape to "éclat" — Python uses ensure_ascii=False.
    expect(out).toBe('{\n  "note": "éclat"\n}\n');
  });

  it("regression: matches Python-generated proof bytes byte-for-byte", () => {
    // MANDATORY regression per Wave 7 amend brief: real Python proof fixture
    // round-tripped through browser canonicalJson must produce identical bytes
    // and identical SHA-256 hash. Without this, verify-all-rounds fails every
    // round (the v2.1 differentiator feature).
    const proofText = readFileSync(
      join(__dirname, "..", "test", "fixtures", "proof.real.json"),
      "utf-8",
    );
    const expectedCanonical = readFileSync(
      join(__dirname, "..", "test", "fixtures", "proof.real.canonical.txt"),
      "utf-8",
    );
    const proof = JSON.parse(proofText) as Record<string, unknown>;
    // Strip envelope_hash before canonicalizing — same shape useVerifyFlow uses.
    const { envelope_hash: _omit, ...envelope } = proof;
    expect(canonicalJson(envelope)).toBe(expectedCanonical);
  });
});

describe("verify-all-rounds regression — real proof", () => {
  it("browser-recomputed envelope_hash matches the Python-recorded hash", async () => {
    const proofText = readFileSync(
      join(__dirname, "..", "test", "fixtures", "proof.real.json"),
      "utf-8",
    );
    const proof = JSON.parse(proofText) as Record<string, unknown>;
    const declaredHash = String(proof.envelope_hash ?? "").toLowerCase();
    const { envelope_hash: _omit, ...envelope } = proof;
    const recomputed = await sha256Hex(canonicalJson(envelope));
    expect(recomputed).toBe(declaredHash);
  });
});

describe("sha256Hex", () => {
  it("computes known SHA-256 of empty string", async () => {
    const hex = await sha256Hex("");
    // SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    expect(hex).toBe("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
  });

  it("computes known SHA-256 of 'abc'", async () => {
    const hex = await sha256Hex("abc");
    expect(hex).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });
});

describe("useVerifyFlow", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("transitions idle → verifying → verified on a clean round", async () => {
    // Build a tiny envelope, hash it, then mock proof + anchor-status accordingly.
    const envelope = { game_id: "s42", round: "1" };
    const canon = canonicalJson(envelope);
    const expectedHash = await sha256Hex(canon);
    const proof = { ...envelope, envelope_hash: expectedHash };

    fetchMock.mockImplementation((url: string) => {
      if (url.includes("/proofs/1")) {
        return Promise.resolve(
          new Response(JSON.stringify(proof), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }
      if (url.includes("/anchor-status/1")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              round: "1",
              anchor_status: "anchored",
              envelope_hash: "a".repeat(64),
              txid: "ABC",
            }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          ),
        );
      }
      return Promise.reject(new Error("unexpected URL"));
    });

    const { result } = renderHook(() => useVerifyFlow());
    expect(result.current.isRunning).toBe(false);

    await act(async () => {
      await result.current.start("s42", ["1"]);
    });

    await waitFor(() => {
      expect(result.current.perRound.get("1")).toEqual({ kind: "verified" });
    });
    expect(result.current.isRunning).toBe(false);
  });

  it("transitions to failed:envelope_mismatch when local hash diverges", async () => {
    const proof = {
      game_id: "s42",
      round: "1",
      envelope_hash: "deadbeef".repeat(8), // wrong hash
    };

    fetchMock.mockImplementation((url: string) => {
      if (url.includes("/proofs/1")) {
        return Promise.resolve(
          new Response(JSON.stringify(proof), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }
      return Promise.reject(new Error("should not reach anchor-status"));
    });

    const { result } = renderHook(() => useVerifyFlow());

    await act(async () => {
      await result.current.start("s42", ["1"]);
    });

    const state = result.current.perRound.get("1");
    expect(state?.kind).toBe("failed");
    if (state?.kind === "failed") {
      expect(state.reason).toBe("envelope_mismatch");
    }
  });

  it("transitions to failed:not_on_chain when anchor-status returns non-anchored", async () => {
    const envelope = { game_id: "s42", round: "1" };
    const expectedHash = await sha256Hex(canonicalJson(envelope));
    const proof = { ...envelope, envelope_hash: expectedHash };

    fetchMock.mockImplementation((url: string) => {
      if (url.includes("/proofs/1")) {
        return Promise.resolve(
          new Response(JSON.stringify(proof), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }
      if (url.includes("/anchor-status/1")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              round: "1",
              anchor_status: "missing",
              envelope_hash: "a".repeat(64),
            }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          ),
        );
      }
      return Promise.reject(new Error("unexpected"));
    });

    const { result } = renderHook(() => useVerifyFlow());
    await act(async () => {
      await result.current.start("s42", ["1"]);
    });

    const state = result.current.perRound.get("1");
    expect(state?.kind).toBe("failed");
    if (state?.kind === "failed") {
      expect(state.reason).toBe("not_on_chain");
    }
  });

  it("transitions to failed:unreachable when proof fetch errors", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useVerifyFlow());
    await act(async () => {
      await result.current.start("s42", ["1"]);
    });

    const state = result.current.perRound.get("1");
    expect(state?.kind).toBe("failed");
    if (state?.kind === "failed") {
      expect(state.reason).toBe("unreachable");
    }
  });

  it("cancel mid-flight retains already-completed results", async () => {
    // First round completes successfully, then we cancel before the second runs.
    const envelope1 = { game_id: "s42", round: "1" };
    const hash1 = await sha256Hex(canonicalJson(envelope1));

    let secondCallSeen = false;
    fetchMock.mockImplementation((url: string) => {
      if (url.includes("/proofs/2")) {
        secondCallSeen = true;
      }
      if (url.includes("/proofs/1")) {
        return Promise.resolve(
          new Response(JSON.stringify({ ...envelope1, envelope_hash: hash1 }), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }
      if (url.includes("/anchor-status/1")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              round: "1",
              anchor_status: "anchored",
              envelope_hash: "a".repeat(64),
              txid: "ABC",
            }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          ),
        );
      }
      return Promise.reject(new Error("unexpected"));
    });

    const { result } = renderHook(() => useVerifyFlow());

    // Run sequentially; cancel happens after the first completes (synchronous
    // because we cancel before the second iteration).
    const startPromise = act(async () => {
      const p = result.current.start("s42", ["1", "2"]);
      // Cancel as soon as the loop starts the next iteration.
      result.current.cancel();
      await p;
    });
    await startPromise;

    expect(result.current.perRound.get("1")).toBeDefined();
    // Second round should not have been started after cancel.
    expect(secondCallSeen).toBe(false);
  });

  it("reset() clears state", async () => {
    const { result } = renderHook(() => useVerifyFlow());
    await act(async () => {
      result.current.reset();
    });
    expect(result.current.perRound.size).toBe(0);
    expect(result.current.isRunning).toBe(false);
  });

  it("cancel() aborts in-flight fetch via AbortController signal", async () => {
    let abortFired = false;
    fetchMock.mockImplementation((_url: string, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        const sig = init?.signal;
        if (sig) {
          sig.addEventListener("abort", () => {
            abortFired = true;
            reject(new DOMException("aborted", "AbortError"));
          });
        }
      });
    });

    const { result } = renderHook(() => useVerifyFlow());

    await act(async () => {
      const startPromise = result.current.start("s42", ["1"]);
      // Allow microtasks so start() actually issues the fetch + signal subscription.
      await Promise.resolve();
      result.current.cancel();
      await startPromise;
    });

    expect(abortFired).toBe(true);
  });
});

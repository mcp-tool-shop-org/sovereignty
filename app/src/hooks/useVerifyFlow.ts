// useVerifyFlow — sequential per-round verify state machine.
//
// Per spec §2: verify-all-rounds is sequential, not concurrent (XRPL rate limits).
// For each round:
//   1. Fetch proof contents.
//   2. Recompute envelope_hash via canonical JSON + SHA-256 (Web Crypto).
//   3. Compare to proof's envelope_hash. If mismatch → failed:envelope_mismatch.
//   4. Otherwise GET anchor-status. If anchored → verified.
//      Else → failed:not_on_chain or unreachable.
//
// Cancel sets a flag the loop checks each iteration; in-flight rounds keep
// completed results.

import { useCallback, useRef, useState } from "react";
import { DaemonClient } from "../lib/daemonClient";
import { useDaemon } from "./useDaemon";

export type RoundVerifyState =
  | { kind: "idle" }
  | { kind: "verifying" }
  | { kind: "verified" }
  | {
      kind: "failed";
      reason: "envelope_mismatch" | "not_on_chain" | "unreachable";
      detail?: string;
    };

export interface UseVerifyFlow {
  perRound: Map<string, RoundVerifyState>;
  isRunning: boolean;
  /** Currently-resolving round (for aria-live progress). */
  currentRound: string | null;
  start: (gameId: string, rounds: string[]) => Promise<void>;
  cancel: () => void;
  reset: () => void;
}

/** Canonical JSON serialization matching sov_engine/serialize.py::canonical_json:
 *  json.dumps(obj, sort_keys=True, separators=(",", ":")).
 *  Exported for testing. */
export function canonicalJson(value: unknown): string {
  return canonicalize(value);
}

function canonicalize(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("Cannot canonicalize non-finite number");
    }
    return JSON.stringify(value);
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return `[${value.map(canonicalize).join(",")}]`;
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    const pairs = keys.map((k) => `${JSON.stringify(k)}:${canonicalize(obj[k])}`);
    return `{${pairs.join(",")}}`;
  }
  throw new Error(`Cannot canonicalize value of type ${typeof value}`);
}

/** SHA-256 hex digest of a UTF-8 string via Web Crypto. */
export async function sha256Hex(text: string): Promise<string> {
  const buf = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function useVerifyFlow(): UseVerifyFlow {
  const { config } = useDaemon();
  const [perRound, setPerRound] = useState<Map<string, RoundVerifyState>>(new Map());
  const [isRunning, setIsRunning] = useState(false);
  const [currentRound, setCurrentRound] = useState<string | null>(null);
  const cancelledRef = useRef(false);

  const setRoundState = useCallback((round: string, st: RoundVerifyState) => {
    setPerRound((prev) => {
      const next = new Map(prev);
      next.set(round, st);
      return next;
    });
  }, []);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
  }, []);

  const reset = useCallback(() => {
    cancelledRef.current = false;
    setPerRound(new Map());
    setIsRunning(false);
    setCurrentRound(null);
  }, []);

  const start = useCallback(
    async (gameId: string, rounds: string[]) => {
      if (!config) return;
      cancelledRef.current = false;
      setIsRunning(true);
      const client = new DaemonClient(config);

      try {
        for (const round of rounds) {
          if (cancelledRef.current) break;
          setCurrentRound(round);
          setRoundState(round, { kind: "verifying" });

          // 1. Fetch proof contents.
          let proof: Record<string, unknown>;
          try {
            proof = (await client.proof(gameId, round)) as Record<string, unknown>;
          } catch (e) {
            setRoundState(round, {
              kind: "failed",
              reason: "unreachable",
              detail: String(e),
            });
            continue;
          }

          // 2. Local envelope-hash recompute. Strip the envelope_hash field
          // itself before canonicalizing — it's the output, not part of the input.
          const declaredHash = String(proof.envelope_hash ?? "").toLowerCase();
          // Strip the envelope_hash field — it's the output, not part of the input.
          const { envelope_hash: _omit, ...envelope } = proof;
          // proof_version field is part of the envelope; signature/extras stay.
          let recomputed: string;
          try {
            const canon = canonicalJson(envelope);
            recomputed = await sha256Hex(canon);
          } catch (e) {
            setRoundState(round, {
              kind: "failed",
              reason: "envelope_mismatch",
              detail: String(e),
            });
            continue;
          }

          if (recomputed !== declaredHash) {
            setRoundState(round, { kind: "failed", reason: "envelope_mismatch" });
            continue;
          }

          // 3. Chain lookup via daemon.
          if (cancelledRef.current) break;
          try {
            const status = await client.anchorStatus(gameId, round);
            if (status.status === "anchored") {
              setRoundState(round, { kind: "verified" });
            } else {
              setRoundState(round, { kind: "failed", reason: "not_on_chain" });
            }
          } catch (e) {
            setRoundState(round, {
              kind: "failed",
              reason: "unreachable",
              detail: String(e),
            });
          }
        }
      } finally {
        setIsRunning(false);
        setCurrentRound(null);
      }
    },
    [config, setRoundState],
  );

  return { perRound, isRunning, currentRound, start, cancel, reset };
}

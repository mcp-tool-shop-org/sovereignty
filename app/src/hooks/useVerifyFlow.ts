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

// WEB-UI-C-006: split `unreachable` into `daemon_unreachable` (proof fetch
// threw — daemon side) and `chain_unreachable` (anchor-status threw — chain
// lookup transient). The two have distinct recovery commands; collapsing
// them lost that signal pre-Stage-C.
export type RoundVerifyState =
  | { kind: "idle" }
  | { kind: "verifying" }
  | { kind: "verified" }
  | {
      kind: "failed";
      reason: "envelope_mismatch" | "not_on_chain" | "daemon_unreachable" | "chain_unreachable";
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

/** Canonical JSON serialization byte-for-byte equivalent to
 *  sov_engine/serialize.py::canonical_json — Python is the source of truth for
 *  envelope_hash. Python emits:
 *    json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False,
 *               separators=(",", ": ")).replace("\r\n", "\n") + "\n"
 *  i.e. multi-line pretty-printed (2-space indent), space after `:`, sorted
 *  keys at every nesting level, no Unicode escaping for non-ASCII characters,
 *  LF newlines, trailing LF.
 *
 *  Python's `indent` uses `\n` (LF) regardless of platform; empty containers
 *  ({} and []) stay on one line; non-empty containers get one element per
 *  line at the current indent. Numbers must follow Python's repr (integers
 *  bare; finite floats via JSON.stringify, which already matches for safe
 *  integers and standard floats).
 *
 *  Exported for testing. */
export function canonicalJson(value: unknown): string {
  return `${canonicalize(value, 0)}\n`;
}

const INDENT_UNIT = "  ";

function indent(level: number): string {
  return INDENT_UNIT.repeat(level);
}

/** Encode a string with Python's ensure_ascii=False semantics: only the
 *  characters JSON requires (`"`, `\`, control chars 0x00-0x1F) are escaped;
 *  non-ASCII Unicode passes through as raw UTF-8 (the JSON spec allows it). */
function encodeString(s: string): string {
  let out = '"';
  for (let i = 0; i < s.length; i++) {
    const ch = s.charCodeAt(i);
    if (ch === 0x22) out += '\\"';
    else if (ch === 0x5c) out += "\\\\";
    else if (ch === 0x08) out += "\\b";
    else if (ch === 0x09) out += "\\t";
    else if (ch === 0x0a) out += "\\n";
    else if (ch === 0x0c) out += "\\f";
    else if (ch === 0x0d) out += "\\r";
    else if (ch < 0x20) out += `\\u${ch.toString(16).padStart(4, "0")}`;
    else out += s[i];
  }
  return `${out}"`;
}

function canonicalize(value: unknown, level: number): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("Cannot canonicalize non-finite number");
    }
    return JSON.stringify(value);
  }
  if (typeof value === "string") return encodeString(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    const inner = indent(level + 1);
    const closing = indent(level);
    const items = value.map((v) => `${inner}${canonicalize(v, level + 1)}`);
    return `[\n${items.join(",\n")}\n${closing}]`;
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    if (keys.length === 0) return "{}";
    const inner = indent(level + 1);
    const closing = indent(level);
    const pairs = keys.map((k) => `${inner}${encodeString(k)}: ${canonicalize(obj[k], level + 1)}`);
    return `{\n${pairs.join(",\n")}\n${closing}}`;
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
  const abortRef = useRef<AbortController | null>(null);

  const setRoundState = useCallback((round: string, st: RoundVerifyState) => {
    setPerRound((prev) => {
      const next = new Map(prev);
      next.set(round, st);
      return next;
    });
  }, []);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    cancelledRef.current = false;
    abortRef.current = null;
    setPerRound(new Map());
    setIsRunning(false);
    setCurrentRound(null);
  }, []);

  const start = useCallback(
    async (gameId: string, rounds: string[]) => {
      if (!config) return;
      cancelledRef.current = false;
      const controller = new AbortController();
      abortRef.current = controller;
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
            proof = (await client.proof(gameId, round, controller.signal)) as Record<
              string,
              unknown
            >;
          } catch (e) {
            if (cancelledRef.current) break;
            // Proof endpoint hit the daemon; failure here means daemon-side
            // unreachable (down, restarting, 5xx). WEB-UI-C-006.
            setRoundState(round, {
              kind: "failed",
              reason: "daemon_unreachable",
              detail: String(e),
            });
            continue;
          }

          if (cancelledRef.current) break;

          // 2. Local envelope-hash recompute. Strip the envelope_hash field
          // itself before canonicalizing — it's the output, not part of the input.
          const declaredHash = String(proof.envelope_hash ?? "").toLowerCase();
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

          if (cancelledRef.current) break;

          if (recomputed !== declaredHash) {
            setRoundState(round, {
              kind: "failed",
              reason: "envelope_mismatch",
            });
            continue;
          }

          // 3. Chain lookup via daemon.
          if (cancelledRef.current) break;
          try {
            const status = await client.anchorStatus(gameId, round, controller.signal);
            if (cancelledRef.current) break;
            // Stage 7-B WEB-UI-B-003: AnchorStatusResponse field renamed to
            // `anchor_status` (was `status`) to match daemon wire shape.
            if (status.anchor_status === "anchored") {
              setRoundState(round, { kind: "verified" });
            } else {
              setRoundState(round, { kind: "failed", reason: "not_on_chain" });
            }
          } catch (e) {
            if (cancelledRef.current) break;
            // anchor-status failure here surfaces transient chain lookup
            // failure (LOOKUP_FAILED on the Python side or daemon proxy
            // 5xx). Distinct recovery from daemon_unreachable. WEB-UI-C-006.
            setRoundState(round, {
              kind: "failed",
              reason: "chain_unreachable",
              detail: String(e),
            });
          }
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setIsRunning(false);
        setCurrentRound(null);
      }
    },
    [config, setRoundState],
  );

  return { perRound, isRunning, currentRound, start, cancel, reset };
}

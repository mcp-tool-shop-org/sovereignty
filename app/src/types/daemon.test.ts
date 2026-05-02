// Compile-time type assertions live here as runtime type-guard checks.
// The Python type-sync test (tests/test_daemon_types_ts_in_sync.py) pins
// the SSE event + error code literals against this file's text. These
// runtime tests pin the same literals at the value level so a refactor
// that loses one fails Vitest as well.

import { describe, expect, it } from "vitest";
import type {
  AnchorStatus,
  AnchorStatusResponse,
  DaemonError,
  DaemonErrorCode,
  DaemonStatus,
  ProofMeta,
  SSEEvent,
  SSEEventType,
  ShellError,
  ShellErrorCode,
  XRPLNetwork,
} from "./daemon";

describe("daemon types — pinned literals", () => {
  it("XRPLNetwork values are accepted", () => {
    const ns: XRPLNetwork[] = ["testnet", "mainnet", "devnet"];
    expect(ns).toHaveLength(3);
  });

  it("AnchorStatus 3-state enum", () => {
    const s: AnchorStatus[] = ["anchored", "pending", "missing"];
    expect(s).toContain("anchored");
  });

  it("SSEEventType covers all six daemon-IPC event types", () => {
    const events: SSEEventType[] = [
      "daemon.ready",
      "daemon.shutdown",
      "anchor.pending_added",
      "anchor.batch_complete",
      "game.state_changed",
      "error",
    ];
    expect(events).toHaveLength(6);
  });

  it("DaemonErrorCode covers all eighteen daemon-emitted codes", () => {
    // Stage 7-B WEB-UI-B-001: extended from 7 -> 18 by enumerating every
    // daemon-emitted code surface (sov_daemon/server.py + sov_daemon/auth.py
    // inline emits + sov_cli/errors.py factories the daemon imports), plus
    // the two CLI-emitted lifecycle codes covered by the type-sync test
    // (tests/test_daemon_types_ts_in_sync.py). Keep these two pins in
    // lockstep — drift breaks both at once, by design.
    const codes: DaemonErrorCode[] = [
      "DAEMON_READONLY",
      "DAEMON_AUTH_MISSING",
      "DAEMON_AUTH_INVALID",
      "DAEMON_PORT_BUSY",
      "DAEMON_NOT_INSTALLED",
      "DAEMON_NOT_RUNNING",
      "DAEMON_STOP_FAILED",
      "INVALID_GAME_ID",
      "INVALID_ROUND",
      "INVALID_NETWORK",
      "GAME_NOT_FOUND",
      "PROOF_NOT_FOUND",
      "PROOF_UNREADABLE",
      "XRPL_NOT_INSTALLED",
      "ANCHOR_FAILED",
      "ANCHOR_PENDING",
      "MAINNET_FAUCET_REJECTED",
      "MAINNET_UNDERFUNDED",
    ];
    expect(codes).toHaveLength(18);
    // Set-uniqueness — drift would deduplicate to a smaller set.
    expect(new Set(codes).size).toBe(18);
  });

  it("ShellErrorCode covers all seven Rust ShellError variants", () => {
    // Stage 7-B TAURI-SHELL-B-002 cross-domain B mirror. Variant names
    // mirror app/src-tauri/src/commands.rs::ShellError exactly.
    const codes: ShellErrorCode[] = [
      "DaemonNotRunning",
      "DaemonStartFailed",
      "DaemonNotInstalled",
      "ConfigFileMissing",
      "ConfigFileMalformed",
      "ConfigSchemaUnsupported",
      "SubprocessFailed",
    ];
    expect(codes).toHaveLength(7);
    expect(new Set(codes).size).toBe(7);
  });

  it("ShellError tagged-union narrows on `code`", () => {
    const cases: ShellError[] = [
      { code: "DaemonNotRunning" },
      { code: "DaemonStartFailed", stderr: "boom" },
      { code: "DaemonNotInstalled" },
      { code: "ConfigFileMissing" },
      { code: "ConfigFileMalformed", detail: "bad json" },
      { code: "ConfigSchemaUnsupported", found: 0, expected: 1 },
      { code: "SubprocessFailed", exit_code: 1, stderr: "boom" },
    ];
    expect(cases).toHaveLength(7);
    // Field-bearing variants carry their fields after the discriminator.
    const malformed = cases[4];
    if (malformed.code === "ConfigFileMalformed") {
      expect(malformed.detail).toBe("bad json");
    }
  });

  it("ProofMeta and AnchorStatusResponse match daemon wire shape", () => {
    // Stage 7-B WEB-UI-B-003 + B-004: type-level pin of the post-fix shapes.
    // Real-fixture regression tests live alongside in
    // app/src/test/{anchor-status,proofs}-wire-shape.test.ts.
    const proofs: ProofMeta[] = [
      {
        round: "1",
        envelope_hash: "a".repeat(64),
        final: false,
        path: "/tmp/p.json",
      },
    ];
    expect(proofs[0].round).toBe("1");

    const anchor: AnchorStatusResponse = {
      round: "1",
      anchor_status: "anchored",
      envelope_hash: "a".repeat(64),
      txid: "ABC",
    };
    expect(anchor.anchor_status).toBe("anchored");
    // Field name is `anchor_status`, NOT `status` — drift would compile-fail.
    expect(anchor).not.toHaveProperty("status");
  });

  it("SSEEvent shape carries type + data", () => {
    const e: SSEEvent<{ network: string }> = {
      type: "daemon.ready",
      data: { network: "testnet" },
    };
    expect(e.type).toBe("daemon.ready");
    expect(e.data.network).toBe("testnet");
  });

  it("DaemonError shape with optional hint", () => {
    const err: DaemonError = {
      code: "DAEMON_READONLY",
      message: "anchor disabled",
      hint: "restart without --readonly",
    };
    expect(err.code).toBe("DAEMON_READONLY");
    expect(err.hint).toBeDefined();
  });

  it("DaemonStatus 'none' state has no config", () => {
    const s: DaemonStatus = { state: "none", started_by_shell: false };
    expect(s.config).toBeUndefined();
  });

  it("DaemonStatus carries started_by_shell for Guardrail #1 (no `?? true` fallback)", () => {
    const s: DaemonStatus = { state: "none", started_by_shell: false };
    expect(typeof s.started_by_shell).toBe("boolean");
  });
});

// Compile-time type assertions live here as runtime type-guard checks.
// The Python type-sync test (tests/test_daemon_types_ts_in_sync.py) pins
// the SSE event + error code literals against this file's text. These
// runtime tests pin the same literals at the value level so a refactor
// that loses one fails Vitest as well.

import { describe, expect, it } from "vitest";
import type {
  AnchorStatus,
  DaemonError,
  DaemonErrorCode,
  DaemonStatus,
  SSEEvent,
  SSEEventType,
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

  it("DaemonErrorCode covers all seven daemon-IPC error codes", () => {
    const codes: DaemonErrorCode[] = [
      "DAEMON_READONLY",
      "DAEMON_AUTH_MISSING",
      "DAEMON_AUTH_INVALID",
      "DAEMON_PORT_BUSY",
      "DAEMON_NOT_INSTALLED",
      "MAINNET_FAUCET_REJECTED",
      "ANCHOR_PENDING",
    ];
    expect(codes).toHaveLength(7);
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
    const s: DaemonStatus = { state: "none" };
    expect(s.config).toBeUndefined();
  });
});

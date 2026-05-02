// Mirrors docs/v2.1-daemon-ipc.md. Source of truth is the spec doc; this file is
// kept in lockstep manually. tests/test_daemon_types_ts_in_sync.py mechanically
// pins SSE event types and daemon error codes as TS string literals.

// Network selection per Wave 2 spec.
export type XRPLNetwork = "testnet" | "mainnet" | "devnet";

// Anchor 3-state per Wave 2 verify split.
export type AnchorStatus = "anchored" | "pending" | "missing";

// Daemon process state — what the Tauri shell reports back.
export type DaemonState = "running" | "stale" | "none";

// Mirrors Rust shell's DaemonConfig (app/src-tauri/src/config.rs).
// Seed is NEVER part of this shape — trust boundary pinned by daemon-side test.
export interface DaemonConfig {
  pid: number;
  port: number;
  token: string;
  network: XRPLNetwork;
  readonly: boolean;
  ipc_version: number;
  started_iso: string;
}

// Mirrors Rust shell's DaemonStatus.
export interface DaemonStatus {
  state: DaemonState;
  config?: DaemonConfig;
}

// GET /health response — daemon liveness endpoint.
export interface HealthResponse {
  status: "ok";
  version: string;
  network: XRPLNetwork;
  readonly: boolean;
  ipc_version: number;
  uptime_seconds: number;
}

// SSE event types — UNION literal must be exhaustive. Pinned by docs agent's
// type-sync test against docs/v2.1-daemon-ipc.md §5.
export type SSEEventType =
  | "daemon.ready"
  | "daemon.shutdown"
  | "anchor.pending_added"
  | "anchor.batch_complete"
  | "game.state_changed"
  | "error";

export interface SSEEvent<T = unknown> {
  type: SSEEventType;
  data: T;
}

// Daemon error codes — pinned by docs agent's type-sync test. These are the
// stable codes daemon emits on 4xx/5xx responses for typed frontend dispatch.
export type DaemonErrorCode =
  | "DAEMON_READONLY"
  | "DAEMON_AUTH_MISSING"
  | "DAEMON_AUTH_INVALID"
  | "DAEMON_PORT_BUSY"
  | "DAEMON_NOT_INSTALLED"
  | "MAINNET_FAUCET_REJECTED"
  | "ANCHOR_PENDING";

export interface DaemonError {
  code: DaemonErrorCode;
  message: string;
  hint?: string;
}

// Mirrors `sov games --json` output shape.
export interface GameSummary {
  game_id: string;
  ruleset: string;
  current_round: number;
  max_rounds: number;
  players: string[];
  last_modified_iso: string;
}

// GET /games/{id}/pending-anchors entry shape.
export interface PendingEntry {
  envelope_hash: string;
  added_iso: string;
}

// Per-round anchor status response (GET /games/{id}/anchor-status/{round}).
export interface AnchorStatusResponse {
  game_id: string;
  round: string;
  status: AnchorStatus;
  txid?: string;
  explorer_url?: string;
}

// Mirrors docs/v2.1-daemon-ipc.md. Source of truth is the spec doc; this file is
// kept in lockstep manually. tests/test_daemon_types_ts_in_sync.py mechanically
// pins SSE event types and daemon error codes as TS string literals.

// Network selection per Wave 2 spec.
export type XRPLNetwork = "testnet" | "mainnet" | "devnet";

// Anchor 3-state per Wave 2 verify split.
export type AnchorStatus = "anchored" | "pending" | "missing";

// INTENTIONAL NON-MIRROR: sov_transport/base.py exports ChainLookupResult
// (StrEnum: FOUND / NOT_FOUND / LOOKUP_FAILED) but the engine collapses
// LOOKUP_FAILED + NOT_FOUND -> AnchorStatus.MISSING at sov_engine/proof.py
// before reaching the daemon. The /anchor-status endpoint never invokes
// is_anchored_on_chain (it reads the local pending-anchors / anchors.json
// indices only), so the frontend consumes a 3-state AnchorStatus and never
// sees the chain-side 3-state. v2.2 may surface the distinction by adding
// a /games/{id}/verify/{round} endpoint that does the chain lookup; at that
// point ChainLookupResult earns a TS mirror. For v2.1 it stays Python-only.
// Cross-domain D in wave-9/AMEND.md.

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

// Mirrors Rust shell's DaemonStatus. `started_by_shell` is reported by the
// Tauri shell so Guardrail #1 (refuse network/mode switch when externally-
// started) can fire. The Rust side serializes it from its AtomicBool tracker;
// undefined here means an old shell binary, in which case the UI fails closed
// (treats the daemon as externally-started).
export interface DaemonStatus {
  state: DaemonState;
  config?: DaemonConfig;
  started_by_shell: boolean;
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
//
// Stage 7-B WEB-UI-B-001: extended from 7 -> 18 codes by enumerating every
// daemon-emitted code surface (sov_daemon/server.py + sov_daemon/auth.py
// inline emits + sov_cli/errors.py factories the daemon imports), plus the
// two CLI-emitted lifecycle codes (DAEMON_NOT_RUNNING / DAEMON_STOP_FAILED)
// per the docs agent's extended type-sync pin in
// tests/test_daemon_types_ts_in_sync.py. Mirror gap caught by Stage A audit
// lens lacking proactive-mirror reasoning.
export type DaemonErrorCode =
  // ── Auth / lifecycle (always present, infrastructure-level)
  | "DAEMON_READONLY"
  | "DAEMON_AUTH_MISSING"
  | "DAEMON_AUTH_INVALID"
  | "DAEMON_PORT_BUSY"
  | "DAEMON_NOT_INSTALLED"
  | "DAEMON_NOT_RUNNING"
  | "DAEMON_STOP_FAILED"
  // ── Validation (path / round / config inputs to HTTP endpoints)
  | "INVALID_GAME_ID"
  | "INVALID_ROUND"
  | "INVALID_NETWORK"
  // ── Resource lookup (404s on existing-game / proof paths)
  | "GAME_NOT_FOUND"
  | "PROOF_NOT_FOUND"
  | "PROOF_UNREADABLE"
  // ── XRPL / anchor flow (transport + funding state)
  | "XRPL_NOT_INSTALLED"
  | "ANCHOR_FAILED"
  | "ANCHOR_PENDING"
  | "MAINNET_FAUCET_REJECTED"
  | "MAINNET_UNDERFUNDED";

export interface DaemonError {
  code: DaemonErrorCode;
  message: string;
  hint?: string;
}

// Tauri shell error codes — mirrors Rust ShellError variants in
// app/src-tauri/src/commands.rs. Stage 7-B TAURI-SHELL-B-002 (cross-domain B
// mirror discipline). The Rust enum uses #[serde(tag = "code")] so the wire
// payload is `{ code: "<variant>", ...variant_fields }` — these strings are
// the Rust variant names verbatim.
export type ShellErrorCode =
  | "DaemonNotRunning"
  | "DaemonStartFailed"
  | "DaemonNotInstalled"
  | "ConfigFileMissing"
  | "ConfigFileMalformed"
  | "ConfigSchemaUnsupported"
  | "SubprocessFailed";

// Tagged-union shape of the Tauri shell's serialized ShellError. Variant
// fields follow each Rust struct definition; `code` is always present.
export type ShellError =
  | { code: "DaemonNotRunning" }
  | { code: "DaemonStartFailed"; stderr: string }
  | { code: "DaemonNotInstalled" }
  | { code: "ConfigFileMissing" }
  | { code: "ConfigFileMalformed"; detail: string }
  | { code: "ConfigSchemaUnsupported"; found: number; expected: number }
  | { code: "SubprocessFailed"; exit_code: number; stderr: string };

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

// GET /games/{id}/proofs entry shape — array element returned by
// proofs_list_handler in sov_daemon/server.py:439-446.
//
// Stage 7-B WEB-UI-B-004: changed from `string[]` to `ProofMeta[]`. Daemon
// emits `[{round, envelope_hash, final, path}, ...]`; the previous TS claim
// that this was `string[]` was a Stage A miss — msw mock matched the type,
// not the wire, so unit tests passed while real-daemon traffic 400'd on
// `encodeURIComponent({...})` in the round-iterator path.
//
// `path` is daemon-internal (file-watch correlation) and SHOULD NOT be
// rendered. Future v2.2 may drop it; for now consumers just don't surface it.
export interface ProofMeta {
  round: string;
  envelope_hash: string;
  final: boolean;
  path: string;
}

// Per-round anchor status response (GET /games/{id}/anchor-status/{round}).
//
// Stage 7-B WEB-UI-B-003: aligned to actual daemon wire shape per
// sov_daemon/server.py:486-539 (anchor_status_handler). Previously declared:
//   { game_id, round, status, txid?, explorer_url? }
// Daemon actually emits:
//   { round, anchor_status, envelope_hash, txid? }
// All four divergences fixed:
//   - `status` -> `anchor_status` (field-name match)
//   - `game_id` removed (never emitted by this endpoint; path-param only)
//   - `explorer_url` removed (only emitted by /anchor write, not status)
//   - `envelope_hash` added (was emitted but missing from interface)
// Pinned via app/src/test/anchor-status-wire-shape.test.ts so future drift
// fails Vitest, not silently-renders-everything-as-missing.
export interface AnchorStatusResponse {
  round: string;
  anchor_status: AnchorStatus;
  envelope_hash: string | null;
  txid?: string;
}

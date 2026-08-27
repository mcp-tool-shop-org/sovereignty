// Fetch wrapper for daemon HTTP surface. Direct webview → daemon at
// 127.0.0.1:<port> with bearer-token auth (locked topology — Tauri shell
// does NOT proxy daemon calls). See docs/v2.1-tauri-shell.md §2.
//
// Wave 4 ships the wrapper shell + minimal coverage. Wave 5 expands as the
// audit viewer + game shell pull on more endpoints.

import type {
  AnchorStatusResponse,
  DaemonConfig,
  GameSummary,
  HealthResponse,
  PendingEntry,
  ProofMeta,
  VerifyRoundResponse,
} from "../types/daemon";
import type { GameState } from "../types/game";

export class DaemonClient {
  constructor(private readonly config: DaemonConfig) {}

  /** Build absolute URL for a daemon endpoint path. */
  url(path: string): string {
    return `http://127.0.0.1:${this.config.port}${path}`;
  }

  /** Authorization headers — bearer-token gate per daemon-IPC spec §7. */
  headers(extra?: HeadersInit): HeadersInit {
    return {
      Authorization: `Bearer ${this.config.token}`,
      ...(extra ?? {}),
    };
  }

  async health(): Promise<HealthResponse> {
    const r = await fetch(this.url("/health"), { headers: this.headers() });
    if (!r.ok) throw new Error(`health: ${r.status}`);
    return (await r.json()) as HealthResponse;
  }

  async games(): Promise<GameSummary[]> {
    const r = await fetch(this.url("/games"), { headers: this.headers() });
    if (!r.ok) throw new Error(`games: ${r.status}`);
    return (await r.json()) as GameSummary[];
  }

  async game(gameId: string): Promise<GameState> {
    const r = await fetch(this.url(`/games/${encodeURIComponent(gameId)}`), {
      headers: this.headers(),
    });
    if (!r.ok) throw new Error(`game ${gameId}: ${r.status}`);
    return (await r.json()) as GameState;
  }

  /** GET /games/{id}/proofs — list of proof metadata entries.
   *
   * Stage 7-B WEB-UI-B-004: return shape changed from `string[]` to
   * `ProofMeta[]`. Daemon emits `[{round, envelope_hash, final, path}, ...]`
   * per `sov_daemon/server.py:439-446`. The previous `string[]` claim was
   * a Stage A miss — msw mock matched the type, not the wire, so the round
   * iterator in `Audit.tsx` would `encodeURIComponent({...})` against a real
   * daemon and 400 every round. Pinned by `proofs-wire-shape.test.ts`.
   *
   * `path` is daemon-internal (file-watch correlation) and SHOULD NOT be
   * rendered. Consumers extract `round` for display + as the URL path-param. */
  async proofs(gameId: string): Promise<ProofMeta[]> {
    const r = await fetch(this.url(`/games/${encodeURIComponent(gameId)}/proofs`), {
      headers: this.headers(),
    });
    if (!r.ok) throw new Error(`proofs ${gameId}: ${r.status}`);
    return (await r.json()) as ProofMeta[];
  }

  /** GET /games/{id}/proofs/{round} — full proof envelope contents.
   * Accepts an optional AbortSignal so callers (e.g. useVerifyFlow) can cancel
   * in-flight verification. */
  async proof(gameId: string, round: string, signal?: AbortSignal): Promise<unknown> {
    const r = await fetch(
      this.url(`/games/${encodeURIComponent(gameId)}/proofs/${encodeURIComponent(round)}`),
      { headers: this.headers(), signal },
    );
    if (!r.ok) throw new Error(`proof ${gameId}/${round}: ${r.status}`);
    return r.json();
  }

  async pendingAnchors(gameId: string): Promise<Record<string, PendingEntry>> {
    const r = await fetch(this.url(`/games/${encodeURIComponent(gameId)}/pending-anchors`), {
      headers: this.headers(),
    });
    if (!r.ok) throw new Error(`pending-anchors ${gameId}: ${r.status}`);
    const body: unknown = await r.json();
    return unwrapPendingAnchors(body);
  }

  async anchorStatus(
    gameId: string,
    round: string,
    signal?: AbortSignal,
  ): Promise<AnchorStatusResponse> {
    const r = await fetch(
      this.url(`/games/${encodeURIComponent(gameId)}/anchor-status/${encodeURIComponent(round)}`),
      { headers: this.headers(), signal },
    );
    if (!r.ok) throw new Error(`anchor-status ${gameId}/${round}: ${r.status}`);
    return (await r.json()) as AnchorStatusResponse;
  }

  /** GET /games/{id}/verify/{round} — local indices plus chain lookup.
   * Browse continues to use anchorStatus(); Verify-all-rounds uses this. */
  async verifyRound(
    gameId: string,
    round: string,
    signal?: AbortSignal,
  ): Promise<VerifyRoundResponse> {
    const r = await fetch(
      this.url(`/games/${encodeURIComponent(gameId)}/verify/${encodeURIComponent(round)}`),
      { headers: this.headers(), signal },
    );
    if (!r.ok) throw new Error(`verify ${gameId}/${round}: ${r.status}`);
    return (await r.json()) as VerifyRoundResponse;
  }
}

/** Daemon GET /pending-anchors emits `{ pending: string[], entries: {round: PendingEntry} }`.
 *  Consumers count entries, never Object.keys(wrapper). Empty index is
 *  `{ pending: [], entries: {} }` — two wrapper keys, zero pending rounds.
 *  F-ae4241e2. */
export function unwrapPendingAnchors(body: unknown): Record<string, PendingEntry> {
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return {};
  }
  const rec = body as Record<string, unknown>;
  if (rec.entries !== undefined) {
    if (rec.entries !== null && typeof rec.entries === "object" && !Array.isArray(rec.entries)) {
      return rec.entries as Record<string, PendingEntry>;
    }
    return {};
  }
  // Legacy flat map (no wrap). Reject the wrap's `pending` array key as entries.
  if ("pending" in rec && Array.isArray(rec.pending)) {
    return {};
  }
  return rec as Record<string, PendingEntry>;
}

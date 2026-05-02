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

  /** GET /games/{id}/proofs — list of round keys with proofs on disk. */
  async proofs(gameId: string): Promise<string[]> {
    const r = await fetch(this.url(`/games/${encodeURIComponent(gameId)}/proofs`), {
      headers: this.headers(),
    });
    if (!r.ok) throw new Error(`proofs ${gameId}: ${r.status}`);
    return (await r.json()) as string[];
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
    return (await r.json()) as Record<string, PendingEntry>;
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
}

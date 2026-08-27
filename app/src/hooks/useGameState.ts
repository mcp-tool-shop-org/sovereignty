// useGameState — active-game selection + state fetch.
// Per spec §3: active game id derived from /games listing (most-recently-modified
// game whose state.game_over === false). Single re-fetch on game.state_changed
// SSE event for the active game.

import { useCallback, useEffect, useRef, useState } from "react";
import { DaemonClient } from "../lib/daemonClient";
import type { GameSummary, SSEEvent } from "../types/daemon";
import type { GameState } from "../types/game";
import { useDaemon } from "./useDaemon";
import { useDaemonEvents } from "./useDaemonEvents";

export interface UseGameStateResult {
  /** Resolved active game id, or null if none. */
  activeGameId: string | null;
  /** Last fetched state, or null if not yet loaded. */
  state: GameState | null;
  /** Loading on initial fetch only — not on re-fetches. */
  loading: boolean;
  /** Surfaced fetch error, or null. */
  error: string | null;
  /** Manual reload trigger. */
  refresh: () => Promise<void>;
}

/** Pick the most-recently-modified non-game-over game from a games list.
 * Exported for testing. */
export function pickActiveGame(games: GameSummary[]): string | null {
  if (games.length === 0) return null;
  // GameSummary doesn't carry game_over — daemon already filters in /games.
  // Sort by last_modified_iso descending and pick first.
  const sorted = [...games].sort((a, b) => b.last_modified_iso.localeCompare(a.last_modified_iso));
  return sorted[0]?.game_id ?? null;
}

export function useGameState(): UseGameStateResult {
  const { config, status } = useDaemon();
  const [activeGameId, setActiveGameId] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Stable client reference — recreated only when config changes.
  const clientRef = useRef<DaemonClient | null>(null);
  if (config) {
    clientRef.current = new DaemonClient(config);
  } else {
    clientRef.current = null;
  }

  const refresh = useCallback(async () => {
    const client = clientRef.current;
    if (!client) return;
    try {
      const games = await client.games();
      // Walk last_modified_iso descending and skip game_over. Listing order
      // is not recency; the previous fallback used the unsorted remainder
      // and could pick an older in-progress game. F-1098ef9e.
      const sorted = [...games].sort((a, b) =>
        b.last_modified_iso.localeCompare(a.last_modified_iso),
      );
      let resolvedId: string | null = null;
      let resolvedState: GameState | null = null;
      for (const g of sorted) {
        const s = await client.game(g.game_id);
        if (!s.game_over) {
          resolvedId = g.game_id;
          resolvedState = s;
          break;
        }
      }
      setActiveGameId(resolvedId);
      setState(resolvedState);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch when daemon comes up.
  useEffect(() => {
    if (status !== "running" || !config) {
      setLoading(false);
      return;
    }
    setLoading(true);
    void refresh();
  }, [status, config, refresh]);

  // SSE: re-fetch on game.state_changed for active game (single fetch per spec §8).
  // Other events are payload-driven; do NOT re-fetch on anchor.batch_complete.
  const handler = useCallback(
    (event: SSEEvent) => {
      if (event.type !== "game.state_changed") return;
      const data = event.data as { game_id?: string } | undefined;
      if (!data?.game_id) return;
      if (data.game_id !== activeGameId) return;
      void refresh();
    },
    [activeGameId, refresh],
  );
  useDaemonEvents(handler);

  return { activeGameId, state, loading, error, refresh };
}

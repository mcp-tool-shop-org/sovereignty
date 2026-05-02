// EventFeed — <ul aria-live="polite"> rendering last N SSE events.
// Spec §1 requires aria-live region for SSE event feed.

import type { SSEEvent } from "../types/daemon";
import styles from "./EventFeed.module.css";

export interface FeedEntry {
  /** Wall-clock timestamp when received (ms). */
  ts: number;
  event: SSEEvent;
}

export interface EventFeedProps {
  events: FeedEntry[];
  /** Max number to render (oldest dropped on overflow handled by caller). */
  limit?: number;
  emptyText?: string;
}

/** Format an SSE event payload to a short summary string per spec §3 table. */
export function formatEventSummary(event: SSEEvent): string {
  const data = (event.data ?? {}) as Record<string, unknown>;
  switch (event.type) {
    case "daemon.ready":
      return `network: ${data.network ?? "?"}, ipc_version: ${data.ipc_version ?? "?"}`;
    case "daemon.shutdown":
      return `reason: ${data.reason ?? "?"}`;
    case "anchor.pending_added":
      return `round ${data.round ?? "?"}`;
    case "anchor.batch_complete": {
      const rounds = (data.rounds as string[] | undefined) ?? [];
      const first = rounds[0] ?? "?";
      const last = rounds[rounds.length - 1] ?? first;
      const txid = (data.txid as string | undefined) ?? "?";
      const txidShort = txid.length > 8 ? `${txid.slice(0, 4)}…${txid.slice(-2)}` : txid;
      return `rounds ${first}–${last} → ${txidShort}`;
    }
    case "game.state_changed":
      return `game ${data.game_id ?? "?"} update`;
    case "error":
      return `${data.level ?? "error"}: ${data.message ?? "?"}`;
    default:
      return "";
  }
}

function formatHHMMSS(ts: number): string {
  const d = new Date(ts);
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export function EventFeed({ events, limit = 20, emptyText = "No events yet." }: EventFeedProps) {
  const items = events.slice(-limit);
  if (items.length === 0) {
    return <p className={styles.empty}>{emptyText}</p>;
  }
  return (
    <ul className={styles.feed} aria-live="polite" aria-relevant="additions">
      {items.map((entry, idx) => {
        const isError = entry.event.type === "error";
        return (
          <li key={`${entry.ts}-${idx}`} className={`${styles.row} ${isError ? styles.error : ""}`}>
            <span className={styles.time}>{formatHHMMSS(entry.ts)}</span>
            <span className={styles.type}>{entry.event.type}</span>
            <span className={styles.summary}>{formatEventSummary(entry.event)}</span>
          </li>
        );
      })}
    </ul>
  );
}

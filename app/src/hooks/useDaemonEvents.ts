// SSE subscription per docs/v2.1-tauri-shell.md §8.
//
// EventSource doesn't support custom request headers in the WHATWG spec, so
// to send the bearer token we use fetch + ReadableStream + manual SSE frame
// parse. v2.1 daemon contract is fire-and-forget (no Last-Event-ID buffer);
// caller refetches state on reconnect if missed events matter.
//
// Reconnect: bounded exponential backoff (1s → 30s, capped at 6 attempts =
// ~63s total wait). After the cap, the connection is reported as lost via
// the `daemonConnectionLost` event; consuming routes can surface a banner.
//
// Handler stability: `handler` is held in a ref so consumers don't tear down
// and reopen the SSE connection on every render (fixes the audit churn the
// audit-viewer hit when expanding rows).

import { useEffect, useRef } from "react";
import type { SSEEvent, SSEEventType } from "../types/daemon";
import { useDaemon } from "./useDaemon";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30_000;

export function useDaemonEvents(handler: (event: SSEEvent) => void): void {
  const { config, status } = useDaemon();
  // Hold the handler in a ref so its identity changes don't re-effect the
  // SSE setup. Without this, every render where the caller passes a fresh
  // closure (very common — Audit.tsx's onEvent depends on `expanded`) would
  // tear down and reopen the connection, dropping events in the gap.
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    if (status !== "running" || !config) return;
    const controller = new AbortController();
    const url = `http://127.0.0.1:${config.port}/events`;
    let attempt = 0;
    let stopped = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = async (): Promise<void> => {
      try {
        const response = await fetch(url, {
          headers: { Authorization: `Bearer ${config.token}` },
          signal: controller.signal,
        });
        if (!response.ok || !response.body) {
          throw new Error(`SSE non-ok status: ${response.status}`);
        }
        // Successful frame parses reset the retry budget (proves the daemon
        // is alive, not just listening).
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const event = parseSSEFrame(frame);
            if (event) {
              attempt = 0;
              handlerRef.current(event);
            }
          }
        }
        // Stream closed cleanly — fall through to reconnect logic below.
      } catch (e) {
        if (controller.signal.aborted || stopped) return;
        // fall through to reconnect
      }

      if (controller.signal.aborted || stopped) return;

      if (attempt >= MAX_RETRIES) {
        // Surface the give-up state for routes that want a banner.
        try {
          window.dispatchEvent(new CustomEvent("daemonConnectionLost"));
        } catch {
          // SSR / non-window envs — no-op.
        }
        return;
      }
      const delay = Math.min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** attempt);
      attempt += 1;
      retryTimer = setTimeout(() => {
        if (!stopped) void connect();
      }, delay);
    };

    void connect();

    return () => {
      stopped = true;
      controller.abort();
      if (retryTimer !== null) clearTimeout(retryTimer);
    };
  }, [config, status]);
}

/** Parse a single SSE frame ("event: ...\ndata: ..." separated by `\n\n`).
 * Exported for testing. Returns `null` if the frame has no `event:` line or
 * malformed JSON in `data:`. */
export function parseSSEFrame(frame: string): SSEEvent | null {
  let type = "";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) type = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!type) return null;
  const joined = dataLines.join("").trim();
  try {
    const data = joined === "" ? {} : JSON.parse(joined);
    return { type: type as SSEEventType, data };
  } catch {
    return null;
  }
}

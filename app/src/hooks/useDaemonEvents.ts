// SSE subscription per docs/v2.1-tauri-shell.md §8.
//
// EventSource doesn't support custom request headers in the WHATWG spec, so
// to send the bearer token we use fetch + ReadableStream + manual SSE frame
// parse. v2.1 daemon contract is fire-and-forget (no Last-Event-ID buffer);
// caller refetches state on reconnect if missed events matter.

import { useEffect } from "react";
import type { SSEEvent, SSEEventType } from "../types/daemon";
import { useDaemon } from "./useDaemon";

export function useDaemonEvents(handler: (event: SSEEvent) => void): void {
  const { config, status } = useDaemon();

  useEffect(() => {
    if (status !== "running" || !config) return;
    const controller = new AbortController();
    const url = `http://127.0.0.1:${config.port}/events`;

    (async () => {
      try {
        const response = await fetch(url, {
          headers: { Authorization: `Bearer ${config.token}` },
          signal: controller.signal,
        });
        if (!response.ok || !response.body) return;
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
            if (event) handler(event);
          }
        }
      } catch {
        // Aborts and stream errors are expected on unmount + daemon restart.
        // No reconnect logic — clients re-fetch state if they care about
        // missed events (per Wave 3 spec §5 fire-and-forget contract).
      }
    })();

    return () => controller.abort();
  }, [config, status, handler]);
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

// Hook-level tests for useDaemonEvents — reconnect on stream end, handler-
// identity stability (no fetch churn on caller re-renders), and AbortError
// behavior. Pure-frame parsing is covered in useDaemonEvents.test.ts.

import { act, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  daemonStatus: vi.fn(),
  daemonStart: vi.fn(),
  daemonStop: vi.fn(),
  getDaemonConfig: vi.fn(),
}));

vi.mock("../lib/invoke", () => ({
  daemonStatus: mocks.daemonStatus,
  daemonStart: mocks.daemonStart,
  daemonStop: mocks.daemonStop,
  getDaemonConfig: mocks.getDaemonConfig,
}));

import { DaemonProvider } from "./useDaemon";
import { useDaemonEvents } from "./useDaemonEvents";

const runningConfig = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: false,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

function makeReadableBody(frames: string[], delayMs = 0): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  let i = 0;
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      if (i >= frames.length) {
        controller.close();
        return;
      }
      if (delayMs > 0) {
        await new Promise((r) => setTimeout(r, delayMs));
      }
      // Frames in SSE wire format separated by `\n\n`.
      controller.enqueue(enc.encode(`${frames[i]}\n\n`));
      i += 1;
    },
  });
}

interface ConsumerProps {
  handler: (e: { type: string; data: unknown }) => void;
}

function Consumer({ handler }: ConsumerProps) {
  // useDaemonEvents typed handler — cast for loose test setup.
  useDaemonEvents(handler as Parameters<typeof useDaemonEvents>[0]);
  return null;
}

describe("useDaemonEvents — connection lifetime", () => {
  beforeEach(() => {
    mocks.daemonStatus.mockReset();
    mocks.getDaemonConfig.mockReset();
    mocks.daemonStatus.mockResolvedValue({
      state: "running",
      config: runningConfig,
      started_by_shell: true,
    });
    mocks.getDaemonConfig.mockResolvedValue(runningConfig);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("does NOT tear down + reopen on handler-identity churn (ref pattern)", async () => {
    let openCount = 0;
    const fetchMock = vi.fn(async () => {
      openCount += 1;
      return new Response(makeReadableBody(['event: daemon.ready\ndata: {"network":"testnet"}']), {
        status: 200,
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const handler1 = vi.fn();
    const handler2 = vi.fn();

    const { rerender } = render(
      <DaemonProvider>
        <Consumer handler={handler1} />
      </DaemonProvider>,
    );

    await waitFor(() => {
      expect(openCount).toBeGreaterThanOrEqual(1);
    });
    const initialOpens = openCount;

    // Simulate caller passing a fresh closure on every render — the audit-
    // viewer pattern when `expanded` changes.
    rerender(
      <DaemonProvider>
        <Consumer handler={handler2} />
      </DaemonProvider>,
    );
    rerender(
      <DaemonProvider>
        <Consumer handler={vi.fn()} />
      </DaemonProvider>,
    );

    // Give effects a moment to run.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    // handler-identity churn must NOT have caused new fetch calls beyond the
    // unrelated DaemonProvider re-fetches. The SSE-side count should match.
    // We only assert that at least one fetch happened and we did not get a
    // wave of new SSE opens. Allow at most one extra (in case DaemonProvider
    // mounts/unmounts twice).
    expect(openCount - initialOpens).toBeLessThanOrEqual(1);
  });

  it("reconnects with exponential backoff after stream end", async () => {
    let openCount = 0;
    const fetchMock = vi.fn(async () => {
      openCount += 1;
      // Empty body → stream closes immediately → reconnect path engaged.
      return new Response(makeReadableBody([]), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <DaemonProvider>
        <Consumer handler={vi.fn()} />
      </DaemonProvider>,
    );

    // First connect happens immediately; second after BASE_DELAY=1000ms.
    await waitFor(
      () => {
        expect(openCount).toBeGreaterThanOrEqual(1);
      },
      { timeout: 500 },
    );

    // Wait long enough for first retry (delay = 1s, allow some slack).
    await waitFor(
      () => {
        expect(openCount).toBeGreaterThanOrEqual(2);
      },
      { timeout: 2500 },
    );
  });

  it("does not reconnect after AbortController.abort (clean unmount)", async () => {
    let openCount = 0;
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      openCount += 1;
      return new Promise<Response>((_resolve, reject) => {
        const sig = init?.signal;
        if (sig) {
          sig.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        }
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(
      <DaemonProvider>
        <Consumer handler={vi.fn()} />
      </DaemonProvider>,
    );

    await waitFor(() => {
      expect(openCount).toBeGreaterThanOrEqual(1);
    });

    unmount();
    const afterUnmount = openCount;

    // Wait through what would otherwise be a retry window.
    await new Promise((r) => setTimeout(r, 1500));
    expect(openCount).toBe(afterUnmount);
  });
});

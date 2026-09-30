// Global test setup — intercept daemon SSE endpoint so useDaemonEvents doesn't
// ECONNREFUSE against 127.0.0.1:47823 in every test that mounts DaemonProvider
// with status === "running". Tests that vi.stubGlobal("fetch", ...) override
// this wrapper for their own scope; the wrapper delegates non-/events URLs to
// the real fetch.

const _originalFetch = globalThis.fetch;

globalThis.fetch = async (...args: Parameters<typeof fetch>): Promise<Response> => {
  const [input] = args;
  const url = typeof input === "string" ? input : input.toString();
  if (url.endsWith("/events")) {
    // Return a minimal SSE comment frame (ignored by parseSSEFrame) then close.
    // This prevents ECONNREFUSED stderr noise while still exercising the hook's
    // normal read → parse → reconnect path. Reconnects are bounded by test
    // runtime; component unmount aborts the in-flight fetch via AbortController.
    return new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(":ok\n\n"));
          controller.close();
        },
      }),
      { status: 200, headers: { "content-type": "text/event-stream" } },
    );
  }
  return _originalFetch(...args);
};

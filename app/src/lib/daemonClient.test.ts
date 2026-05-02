import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DaemonConfig } from "../types/daemon";
import { DaemonClient } from "./daemonClient";

const cfg: DaemonConfig = {
  pid: 12345,
  port: 47823,
  token: "test-token-abc",
  network: "testnet",
  readonly: false,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("DaemonClient", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds URLs against 127.0.0.1:port", () => {
    const c = new DaemonClient(cfg);
    expect(c.url("/health")).toBe("http://127.0.0.1:47823/health");
    expect(c.url("/games/s42")).toBe("http://127.0.0.1:47823/games/s42");
  });

  it("injects bearer Authorization header", () => {
    const c = new DaemonClient(cfg);
    const headers = c.headers() as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-token-abc");
  });

  it("merges extra headers without dropping Authorization", () => {
    const c = new DaemonClient(cfg);
    const headers = c.headers({ "X-Trace": "abc" }) as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-token-abc");
    expect(headers["X-Trace"]).toBe("abc");
  });

  it("health() parses HealthResponse and sends Authorization", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        status: "ok",
        version: "2.1.0",
        network: "testnet",
        readonly: false,
        ipc_version: 1,
        uptime_seconds: 142,
      }),
    );
    const c = new DaemonClient(cfg);
    const result = await c.health();
    expect(result.status).toBe("ok");
    expect(result.version).toBe("2.1.0");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:47823/health",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token-abc",
        }),
      }),
    );
  });

  it("games() returns array shape", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse([
        {
          game_id: "s42",
          ruleset: "campfire",
          current_round: 3,
          max_rounds: 10,
          players: ["alice", "bob"],
          last_modified_iso: "2026-05-02T00:01:00Z",
        },
      ]),
    );
    const c = new DaemonClient(cfg);
    const games = await c.games();
    expect(games).toHaveLength(1);
    expect(games[0].game_id).toBe("s42");
  });

  it("throws on non-2xx for health", async () => {
    fetchMock.mockResolvedValue(new Response("nope", { status: 401 }));
    const c = new DaemonClient(cfg);
    await expect(c.health()).rejects.toThrow(/health: 401/);
  });

  it("throws on non-2xx for games", async () => {
    fetchMock.mockResolvedValue(new Response("nope", { status: 500 }));
    const c = new DaemonClient(cfg);
    await expect(c.games()).rejects.toThrow(/games: 500/);
  });

  it("anchorStatus URL-encodes round id and parses wire shape", async () => {
    // Stage 7-B WEB-UI-B-003: wire shape is `{round, anchor_status,
    // envelope_hash, txid?}` per sov_daemon/server.py:486-539.
    fetchMock.mockResolvedValue(
      jsonResponse({
        round: "3",
        anchor_status: "anchored",
        envelope_hash: "a".repeat(64),
        txid: "ABC",
      }),
    );
    const c = new DaemonClient(cfg);
    const status = await c.anchorStatus("s42", "3");
    const call = fetchMock.mock.calls[0]?.[0] as string;
    expect(call).toBe("http://127.0.0.1:47823/games/s42/anchor-status/3");
    expect(status.anchor_status).toBe("anchored");
    expect(status.round).toBe("3");
    expect(status.envelope_hash).toBe("a".repeat(64));
    expect(status.txid).toBe("ABC");
  });

  it("proofs() returns ProofMeta[] (wire shape, not bare round-key strings)", async () => {
    // Stage 7-B WEB-UI-B-004: wire shape is `[{round, envelope_hash, final,
    // path}, ...]` per sov_daemon/server.py:439-446. Previously this method
    // claimed `Promise<string[]>` which masked a 100% audit-viewer breakage
    // against any real daemon (encodeURIComponent({...}) on object → 400).
    fetchMock.mockResolvedValue(
      jsonResponse([
        {
          round: 1,
          envelope_hash: "a".repeat(64),
          final: false,
          path: "/tmp/r1.json",
        },
        {
          round: 2,
          envelope_hash: "b".repeat(64),
          final: false,
          path: "/tmp/r2.json",
        },
      ]),
    );
    const c = new DaemonClient(cfg);
    const proofs = await c.proofs("s42");
    expect(proofs).toHaveLength(2);
    expect(proofs[0].envelope_hash).toBe("a".repeat(64));
    expect(proofs[0].final).toBe(false);
    expect(typeof proofs[0].path).toBe("string");
  });

  it("pendingAnchors fetches the right path", async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    const c = new DaemonClient(cfg);
    const result = await c.pendingAnchors("s42");
    expect(result).toEqual({});
    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://127.0.0.1:47823/games/s42/pending-anchors");
  });
});

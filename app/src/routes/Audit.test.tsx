import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

import { MemoryRouter } from "react-router-dom";
import { DaemonProvider } from "../hooks/useDaemon";
import Audit from "./Audit";

const cfg = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: false,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

function fetchMockFor(games: unknown[], extras: Record<string, unknown> = {}) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.endsWith("/games")) return jsonResponse(games);
    if (url.endsWith("/events")) return new Response(null, { status: 200 });
    for (const [path, body] of Object.entries(extras)) {
      if (url.endsWith(path)) return jsonResponse(body);
    }
    if (url.includes("/anchor-status/")) {
      const m = url.match(/\/anchor-status\/(.+)$/);
      return jsonResponse({
        game_id: "s42",
        round: m?.[1] ?? "?",
        status: "anchored",
        txid: "ABC123DEF",
        explorer_url: "https://testnet.xrpl.org/x/ABC123DEF",
      });
    }
    return new Response("not found", { status: 404 });
  });
}

function renderAudit() {
  return render(
    <MemoryRouter>
      <DaemonProvider>
        <Audit />
      </DaemonProvider>
    </MemoryRouter>,
  );
}

describe("Audit /audit route", () => {
  beforeEach(() => {
    mocks.daemonStatus.mockResolvedValue({ state: "running", config: cfg });
    mocks.getDaemonConfig.mockResolvedValue(cfg);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("renders empty state when no games", async () => {
    vi.stubGlobal("fetch", fetchMockFor([]));
    renderAudit();
    await waitFor(() => {
      expect(screen.getByText(/No games yet/i)).toBeTruthy();
    });
  });

  it("renders games list using semantic <details> per row", async () => {
    vi.stubGlobal(
      "fetch",
      fetchMockFor([
        {
          game_id: "s42",
          ruleset: "campfire_v1",
          current_round: 5,
          max_rounds: 15,
          players: [],
          last_modified_iso: "2026-05-02T00:00:00Z",
        },
      ]),
    );
    const { container } = renderAudit();
    await waitFor(() => {
      expect(screen.getByText("s42")).toBeTruthy();
    });
    expect(container.querySelectorAll("details").length).toBeGreaterThan(0);
    expect(screen.getByText(/network: testnet/)).toBeTruthy();
  });

  it("sorts games by last_modified_iso descending", async () => {
    vi.stubGlobal(
      "fetch",
      fetchMockFor([
        {
          game_id: "s_old",
          ruleset: "campfire_v1",
          current_round: 1,
          max_rounds: 15,
          players: [],
          last_modified_iso: "2026-01-01T00:00:00Z",
        },
        {
          game_id: "s_new",
          ruleset: "campfire_v1",
          current_round: 1,
          max_rounds: 15,
          players: [],
          last_modified_iso: "2026-05-02T00:00:00Z",
        },
      ]),
    );
    const { container } = renderAudit();
    await waitFor(() => {
      expect(screen.getByText("s_new")).toBeTruthy();
    });
    const ids = Array.from(container.querySelectorAll("summary")).map((s) => s.textContent ?? "");
    const newIdx = ids.findIndex((t) => t.includes("s_new"));
    const oldIdx = ids.findIndex((t) => t.includes("s_old"));
    expect(newIdx).toBeGreaterThanOrEqual(0);
    expect(newIdx).toBeLessThan(oldIdx);
  });

  it("nav uses aria-current='page' for /audit", async () => {
    vi.stubGlobal("fetch", fetchMockFor([]));
    renderAudit();
    await waitFor(() => {
      const link = screen.getAllByRole("link").find((l) => l.textContent === "Audit");
      expect(link?.getAttribute("aria-current")).toBe("page");
    });
  });

  it("expanding a row fetches proofs + statuses (rounds table)", async () => {
    vi.stubGlobal(
      "fetch",
      fetchMockFor(
        [
          {
            game_id: "s42",
            ruleset: "campfire_v1",
            current_round: 3,
            max_rounds: 15,
            players: [],
            last_modified_iso: "2026-05-02T00:00:00Z",
          },
        ],
        {
          "/games/s42/proofs": ["1", "2", "3"],
        },
      ),
    );
    const { container } = renderAudit();
    await waitFor(() => {
      expect(screen.getByText("s42")).toBeTruthy();
    });
    const details = container.querySelector("details") as HTMLDetailsElement;
    details.open = true;
    fireEvent(details, new Event("toggle"));

    await waitFor(() => {
      expect(screen.getByText(/Verify all rounds/i)).toBeTruthy();
    });
  });
});

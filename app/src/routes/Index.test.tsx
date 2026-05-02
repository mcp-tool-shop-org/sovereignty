import { render, screen, waitFor } from "@testing-library/react";
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
import Index from "./Index";

const cfg = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: true,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

function makeFetch(games: unknown[]) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.endsWith("/games")) {
      return new Response(JSON.stringify(games), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    return new Response(null, { status: 200 });
  });
}

function renderIndex() {
  return render(
    <MemoryRouter>
      <DaemonProvider>
        <Index />
      </DaemonProvider>
    </MemoryRouter>,
  );
}

describe("Index /", () => {
  beforeEach(() => {
    mocks.daemonStatus.mockResolvedValue({ state: "running", config: cfg });
    mocks.getDaemonConfig.mockResolvedValue(cfg);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("renders welcome empty state when no games", async () => {
    vi.stubGlobal("fetch", makeFetch([]));
    renderIndex();
    await waitFor(() => {
      expect(screen.getByText("Welcome")).toBeTruthy();
    });
  });

  it("renders game count when games exist", async () => {
    vi.stubGlobal(
      "fetch",
      makeFetch([
        {
          game_id: "s42",
          ruleset: "campfire_v1",
          current_round: 3,
          max_rounds: 15,
          players: [],
          last_modified_iso: "2026-05-02T00:00:00Z",
        },
      ]),
    );
    renderIndex();
    await waitFor(() => {
      expect(screen.getByText(/1 game/)).toBeTruthy();
    });
  });

  it("nav links to audit, game, settings", async () => {
    vi.stubGlobal("fetch", makeFetch([]));
    renderIndex();
    await waitFor(() => {
      expect(screen.getAllByRole("link").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("Audit Viewer")).toBeTruthy();
    expect(screen.getByText("Active Game")).toBeTruthy();
    expect(screen.getByText("Settings")).toBeTruthy();
  });

  it("renders status pill with role='status'", async () => {
    vi.stubGlobal("fetch", makeFetch([]));
    renderIndex();
    await waitFor(() => {
      expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
    });
  });
});

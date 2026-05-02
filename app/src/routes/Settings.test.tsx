import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the lib/invoke module — Settings reads daemon_status to derive started_by_shell.
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
import Settings from "./Settings";

const runningConfig = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: true,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

function makeFetchMock(opts: { pendingByGame?: Record<string, number> } = {}) {
  return vi.fn((url: string) => {
    if (typeof url !== "string") {
      // Could be a Request — we ignore.
      return Promise.reject(new Error("non-string url"));
    }
    if (url.endsWith("/games")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            {
              game_id: "s42",
              ruleset: "campfire_v1",
              current_round: 3,
              max_rounds: 15,
              players: [],
              last_modified_iso: "2026-05-02T00:00:00Z",
            },
          ]),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );
    }
    if (url.includes("/pending-anchors")) {
      const m = url.match(/\/games\/([^/]+)\/pending-anchors/);
      const gid = m?.[1] ?? "";
      const count = opts.pendingByGame?.[gid] ?? 0;
      const body: Record<string, unknown> = {};
      for (let i = 0; i < count; i++) {
        body[String(i)] = { envelope_hash: "deadbeef", added_iso: "2026-05-02T00:00:00Z" };
      }
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    }
    return Promise.reject(new Error(`unhandled URL: ${url}`));
  });
}

function renderSettings() {
  return render(
    <MemoryRouter>
      <DaemonProvider>
        <Settings />
      </DaemonProvider>
    </MemoryRouter>,
  );
}

describe("Settings — network switcher guardrails (spec §4)", () => {
  beforeEach(() => {
    mocks.daemonStatus.mockReset();
    mocks.daemonStart.mockReset();
    mocks.daemonStop.mockReset();
    mocks.getDaemonConfig.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("disables Apply when daemon was started externally (started_by_shell=false)", async () => {
    mocks.daemonStatus.mockResolvedValue({
      state: "running",
      config: runningConfig,
      started_by_shell: false,
    });
    mocks.getDaemonConfig.mockResolvedValue(runningConfig);
    vi.stubGlobal("fetch", makeFetchMock());

    renderSettings();

    await waitFor(() => {
      expect(screen.getByText(/started externally/i)).toBeTruthy();
    });
    const apply = screen.getByText(/Apply/i) as HTMLButtonElement;
    // Change select target to mainnet.
    const select = screen.getByLabelText(/Target network/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "mainnet" } });
    expect(apply.disabled).toBe(true);
  });

  it("disables Apply when active game has pending anchors", async () => {
    mocks.daemonStatus.mockResolvedValue({
      state: "running",
      config: runningConfig,
      started_by_shell: true,
    });
    mocks.getDaemonConfig.mockResolvedValue(runningConfig);
    vi.stubGlobal("fetch", makeFetchMock({ pendingByGame: { s42: 3 } }));

    renderSettings();

    await waitFor(() => {
      expect(screen.getByText(/Pending anchors target/i)).toBeTruthy();
    });
    const select = screen.getByLabelText(/Target network/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "devnet" } });
    const apply = screen.getByText(/Apply/i) as HTMLButtonElement;
    expect(apply.disabled).toBe(true);
  });

  it("opens confirm dialog when switching to mainnet (clean guardrails)", async () => {
    mocks.daemonStatus.mockResolvedValue({
      state: "running",
      config: runningConfig,
      started_by_shell: true,
    });
    mocks.getDaemonConfig.mockResolvedValue(runningConfig);
    vi.stubGlobal("fetch", makeFetchMock());

    // jsdom/happy-dom doesn't implement HTMLDialogElement.showModal — stub it.
    const showModalSpy = vi
      .spyOn(HTMLDialogElement.prototype, "showModal")
      .mockImplementation(function (this: HTMLDialogElement) {
        this.setAttribute("open", "");
      });
    const closeSpy = vi.spyOn(HTMLDialogElement.prototype, "close").mockImplementation(function (
      this: HTMLDialogElement,
    ) {
      this.removeAttribute("open");
    });

    renderSettings();

    await waitFor(() => {
      expect(screen.getByText(/Switch XRPL network/i)).toBeTruthy();
    });
    const select = screen.getByLabelText(/Target network/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "mainnet" } });
    const apply = screen.getByText(/Apply/i) as HTMLButtonElement;
    expect(apply.disabled).toBe(false);
    fireEvent.click(apply);

    await waitFor(() => {
      expect(showModalSpy).toHaveBeenCalled();
    });
    expect(screen.getByText(/cost real XRP/i)).toBeTruthy();

    showModalSpy.mockRestore();
    closeSpy.mockRestore();
  });

  it("does NOT prompt for mainnet confirm when switching testnet → devnet", async () => {
    mocks.daemonStatus.mockResolvedValueOnce({
      state: "running",
      config: runningConfig,
      started_by_shell: true,
    });
    mocks.daemonStatus.mockResolvedValue({
      state: "none",
    });
    mocks.getDaemonConfig.mockResolvedValue(runningConfig);
    mocks.daemonStop.mockResolvedValue(undefined);
    mocks.daemonStart.mockResolvedValue({ ...runningConfig, network: "devnet" });
    vi.stubGlobal("fetch", makeFetchMock());

    const showModalSpy = vi
      .spyOn(HTMLDialogElement.prototype, "showModal")
      .mockImplementation(() => {});

    renderSettings();

    await waitFor(() => {
      expect(screen.getByText(/Switch XRPL network/i)).toBeTruthy();
    });
    const select = screen.getByLabelText(/Target network/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "devnet" } });
    const apply = screen.getByText(/Apply/i) as HTMLButtonElement;
    fireEvent.click(apply);

    // No modal should open for testnet→devnet.
    expect(showModalSpy).not.toHaveBeenCalled();
    showModalSpy.mockRestore();
  });
});

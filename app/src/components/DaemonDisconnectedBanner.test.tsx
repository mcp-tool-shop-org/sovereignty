import { fireEvent, render, screen } from "@testing-library/react";
import { act } from "react";
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

import { DaemonProvider } from "../hooks/useDaemon";
import { DaemonDisconnectedBanner } from "./DaemonDisconnectedBanner";

const cfg = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: true,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

describe("DaemonDisconnectedBanner (WEB-UI-C-004)", () => {
  beforeEach(() => {
    mocks.daemonStatus.mockResolvedValue({ state: "running", config: cfg });
    mocks.getDaemonConfig.mockResolvedValue(cfg);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing by default", () => {
    render(
      <DaemonProvider autoStart={false}>
        <DaemonDisconnectedBanner />
      </DaemonProvider>,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("surfaces the recovery banner when `daemonConnectionLost` is dispatched", () => {
    render(
      <DaemonProvider autoStart={false}>
        <DaemonDisconnectedBanner />
      </DaemonProvider>,
    );
    act(() => {
      window.dispatchEvent(new CustomEvent("daemonConnectionLost"));
    });
    // Recovery copy must be present verbatim — the SSE silent-death gap.
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText(/Lost connection to daemon/i)).toBeTruthy();
    expect(screen.getByText("sov daemon start")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Reconnect/i })).toBeTruthy();
  });

  it("dismisses on Reconnect click", () => {
    render(
      <DaemonProvider autoStart={false}>
        <DaemonDisconnectedBanner />
      </DaemonProvider>,
    );
    act(() => {
      window.dispatchEvent(new CustomEvent("daemonConnectionLost"));
    });
    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Reconnect/i }));
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the lib/invoke module so the provider effects don't reach Tauri.
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

import { DaemonProvider, useDaemon } from "./useDaemon";

function StatusProbe() {
  const { status, config, error } = useDaemon();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="port">{config?.port ?? ""}</span>
      <span data-testid="error">{error ?? ""}</span>
    </div>
  );
}

const runningConfig = {
  pid: 1,
  port: 47823,
  token: "tok",
  network: "testnet" as const,
  readonly: true,
  ipc_version: 1,
  started_iso: "2026-05-02T00:00:00Z",
};

describe("DaemonProvider + useDaemon", () => {
  beforeEach(() => {
    mocks.daemonStatus.mockReset();
    mocks.daemonStart.mockReset();
    mocks.daemonStop.mockReset();
    mocks.getDaemonConfig.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("attaches when daemon is already running", async () => {
    mocks.daemonStatus.mockResolvedValue({
      state: "running",
      config: runningConfig,
    });
    mocks.getDaemonConfig.mockResolvedValue(runningConfig);

    render(
      <DaemonProvider>
        <StatusProbe />
      </DaemonProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("running");
    });
    expect(screen.getByTestId("port").textContent).toBe("47823");
    expect(mocks.daemonStart).not.toHaveBeenCalled();
  });

  it("auto-starts with --readonly when state is 'none'", async () => {
    mocks.daemonStatus.mockResolvedValue({ state: "none" });
    mocks.daemonStart.mockResolvedValue(runningConfig);

    render(
      <DaemonProvider>
        <StatusProbe />
      </DaemonProvider>,
    );

    await waitFor(() => {
      expect(mocks.daemonStart).toHaveBeenCalledWith(true, undefined);
    });
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("running");
    });
  });

  it("auto-starts when state is 'stale'", async () => {
    mocks.daemonStatus.mockResolvedValue({ state: "stale" });
    mocks.daemonStart.mockResolvedValue(runningConfig);

    render(
      <DaemonProvider>
        <StatusProbe />
      </DaemonProvider>,
    );

    await waitFor(() => {
      expect(mocks.daemonStart).toHaveBeenCalledTimes(1);
    });
  });

  it("surfaces errors when daemon_status throws", async () => {
    mocks.daemonStatus.mockRejectedValue(new Error("daemon not installed"));

    render(
      <DaemonProvider>
        <StatusProbe />
      </DaemonProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("error");
    });
    expect(screen.getByTestId("error").textContent).toMatch(/daemon not installed/);
  });

  it("throws when useDaemon is called outside provider", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<StatusProbe />)).toThrow(/inside <DaemonProvider>/);
    consoleSpy.mockRestore();
  });

  it("autoStart=false leaves status loading and skips status calls", async () => {
    mocks.daemonStatus.mockResolvedValue({ state: "running", config: runningConfig });

    render(
      <DaemonProvider autoStart={false}>
        <StatusProbe />
      </DaemonProvider>,
    );

    // Give effects a tick.
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("status").textContent).toBe("loading");
    expect(mocks.daemonStatus).not.toHaveBeenCalled();
  });
});

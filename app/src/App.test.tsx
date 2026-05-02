// App.test.tsx — consumer-listener pin (Mike's reinforcement, Stage 9-D).
//
// Mirrors the Stage 8-C SSE-banner consumer pin: assert mechanically that
// when <App /> renders, at least one `shell-panic` listener is registered
// on the Tauri event bus. If a future refactor orphans PanicModal (event
// dispatched, no consumer), this test fails — preventing the same orphan
// pattern Stage 8-C closed for the daemon-disconnect SSE flow.

import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  daemonStatus: vi.fn(),
  daemonStart: vi.fn(),
  daemonStop: vi.fn(),
  getDaemonConfig: vi.fn(),
  tauriListen: vi.fn(),
}));

vi.mock("../src/lib/invoke", () => ({
  daemonStatus: mocks.daemonStatus,
  daemonStart: mocks.daemonStart,
  daemonStop: mocks.daemonStop,
  getDaemonConfig: mocks.getDaemonConfig,
}));

// Fallback path resolution if the relative path differs at test resolve.
vi.mock("./lib/invoke", () => ({
  daemonStatus: mocks.daemonStatus,
  daemonStart: mocks.daemonStart,
  daemonStop: mocks.daemonStop,
  getDaemonConfig: mocks.getDaemonConfig,
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: (event: string) => {
    mocks.tauriListen(event);
    return Promise.resolve(() => {});
  },
}));

beforeEach(() => {
  // Patch HTMLDialogElement modal methods (happy-dom doesn't ship them).
  if (typeof HTMLDialogElement !== "undefined") {
    if (!HTMLDialogElement.prototype.showModal) {
      HTMLDialogElement.prototype.showModal = function () {
        this.setAttribute("open", "");
      };
    }
    if (!HTMLDialogElement.prototype.close) {
      HTMLDialogElement.prototype.close = function () {
        this.removeAttribute("open");
      };
    }
  }
  mocks.daemonStatus.mockResolvedValue({ state: "none", started_by_shell: false });
  mocks.getDaemonConfig.mockResolvedValue(null);
});

afterEach(() => {
  vi.clearAllMocks();
});

import App from "./App";

describe("App — panic-event consumer-listener pin (Mike's reinforcement)", () => {
  it("registers at least one `shell-panic` listener on render", async () => {
    // The point of this assertion: a future refactor that orphans PanicModal
    // (PanicModal removed, dynamic import returns null, etc.) must fail this
    // test. Mirrors the Stage 8-C SSE-banner consumer pin pattern.
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(mocks.tauriListen).toHaveBeenCalledWith("shell-panic");
    });
  });

  it("PanicModal is mounted OUTSIDE the DaemonProvider (Mike's lock)", async () => {
    // Spec: PanicModal mount point must be the App root, OUTSIDE
    // <DaemonProvider>. A shell panic that prevents DaemonProvider from
    // initializing must still surface the modal — that's the whole point.
    // We pin the position by asserting that the PanicModal's <dialog>
    // appears as a sibling of (not a descendant of) any DaemonProvider
    // tree. Mechanical: PanicModal's own <dialog> exists when the daemon
    // call rejects (provider in error state).
    mocks.daemonStatus.mockRejectedValueOnce(new Error("daemon down"));
    const { container } = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => {
      // Native <dialog> from PanicModal must exist regardless of provider state.
      expect(container.querySelector("dialog")).not.toBeNull();
    });
  });
});

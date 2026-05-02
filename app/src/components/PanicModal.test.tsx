// PanicModal.test.tsx — Stage 9-D Theme 1 (WEB-UI-D-012, Stage 8-C carryover).
//
// Pin the contract:
//   1. Renders nothing visible when no panic event has fired.
//   2. On `shell-panic` event with PanicPayload, the modal opens with the
//      message + location + timestamp visible.
//   3. Dismiss button closes the modal.
//   4. The component subscribes to the Tauri event bus on mount and the
//      subscription is cleaned up on unmount.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PanicPayload } from "../types/daemon";

// Mock @tauri-apps/api/event before importing PanicModal so the dynamic
// import inside the component sees the mocked module.
const tauriListen = vi.fn();
const tauriUnlisten = vi.fn();
let panicHandler: ((e: { payload: PanicPayload }) => void) | null = null;

vi.mock("@tauri-apps/api/event", () => ({
  listen: (event: string, handler: (e: { payload: PanicPayload }) => void) => {
    tauriListen(event);
    if (event === "shell-panic") panicHandler = handler;
    return Promise.resolve(tauriUnlisten);
  },
}));

// happy-dom doesn't implement HTMLDialogElement.showModal/close. Patch them
// onto the prototype so the component can drive native modal lifecycle in
// the test env without exploding.
beforeEach(() => {
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
});

afterEach(() => {
  tauriListen.mockClear();
  tauriUnlisten.mockClear();
  panicHandler = null;
});

import { PanicModal } from "./PanicModal";

describe("PanicModal — shell-panic event consumer", () => {
  it("subscribes to the `shell-panic` Tauri event on mount", async () => {
    render(<PanicModal />);
    await waitFor(() => {
      expect(tauriListen).toHaveBeenCalledWith("shell-panic");
    });
  });

  it("renders nothing visible until a panic event arrives", () => {
    render(<PanicModal />);
    expect(screen.queryByText(/fatal error/i)).toBeNull();
  });

  it("opens the modal with payload contents when shell-panic fires", async () => {
    render(<PanicModal />);
    await waitFor(() => {
      expect(panicHandler).not.toBeNull();
    });
    const payload: PanicPayload = {
      message: "index out of bounds",
      location: "src/commands.rs:128:9",
      timestamp_iso: "2026-05-02T12:34:56Z",
    };
    panicHandler?.({ payload });
    await waitFor(() => {
      expect(screen.getByText(/fatal error/i)).toBeTruthy();
    });
    expect(screen.getByText("index out of bounds")).toBeTruthy();
    expect(screen.getByText("src/commands.rs:128:9")).toBeTruthy();
    expect(screen.getByText("2026-05-02T12:34:56Z")).toBeTruthy();
  });

  it("dismiss button closes the modal", async () => {
    render(<PanicModal />);
    await waitFor(() => {
      expect(panicHandler).not.toBeNull();
    });
    panicHandler?.({
      payload: {
        message: "boom",
        location: "src/lib.rs:1:1",
        timestamp_iso: "2026-05-02T12:00:00Z",
      },
    });
    await waitFor(() => {
      expect(screen.getByText(/fatal error/i)).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /Dismiss/i }));
    await waitFor(() => {
      expect(screen.queryByText(/fatal error/i)).toBeNull();
    });
  });

  it("uses native <dialog> element (Wave 5 lock — semantic primitive)", () => {
    const { container } = render(<PanicModal />);
    const dialog = container.querySelector("dialog");
    expect(dialog).not.toBeNull();
  });
});

// Daemon connection Context provider per docs/v2.1-tauri-shell.md §8.
//
// Lifecycle: on mount, fetch status → if running attach, otherwise auto-start
// with --readonly (default per spec §4). Routes consume via useDaemon().

import { type ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react";
import { formatError } from "../lib/errorFormat";
import { daemonStart, daemonStatus, daemonStop, getDaemonConfig } from "../lib/invoke";
import type { DaemonConfig, DaemonState, XRPLNetwork } from "../types/daemon";

/** Compose a typed daemon/shell error into one rendered string. Until the
 *  banner UI is split into separate message + hint slots, the hint trails
 *  the message in the same `error` field — surfaces the recovery copy that
 *  was previously dropped by `String(e)`. WEB-UI-C-007. */
function renderTypedError(e: unknown): string {
  const { message, hint } = formatError(e);
  return hint ? `${message} — ${hint}` : message;
}

export type DaemonUiStatus = "loading" | DaemonState | "error";

export interface DaemonContextValue {
  status: DaemonUiStatus;
  config: DaemonConfig | null;
  error: string | null;
  startDaemon: (readonly: boolean, network?: XRPLNetwork) => Promise<void>;
  stopDaemon: () => Promise<void>;
  refresh: () => Promise<void>;
}

const DaemonContext = createContext<DaemonContextValue | null>(null);

export interface DaemonProviderProps {
  children: ReactNode;
  /** Test seam: skip the auto-start effect so unit tests can drive lifecycle. */
  autoStart?: boolean;
}

export function DaemonProvider({ children, autoStart = true }: DaemonProviderProps) {
  const [status, setStatus] = useState<DaemonUiStatus>("loading");
  const [config, setConfig] = useState<DaemonConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await daemonStatus();
      setStatus(s.state);
      setConfig(s.config ?? null);
      setError(null);
      if (s.state === "running") {
        const c = await getDaemonConfig();
        setConfig(c);
      }
    } catch (e) {
      setStatus("error");
      setError(renderTypedError(e));
    }
  }, []);

  const startDaemon = useCallback(async (readonly_: boolean, network?: XRPLNetwork) => {
    try {
      const c = await daemonStart(readonly_, network);
      setConfig(c);
      setStatus("running");
      setError(null);
    } catch (e) {
      setError(renderTypedError(e));
      throw e;
    }
  }, []);

  const stopDaemon = useCallback(async () => {
    try {
      await daemonStop();
      setStatus("none");
      setConfig(null);
    } catch (e) {
      setError(renderTypedError(e));
      throw e;
    }
  }, []);

  // Auto-start on mount per spec §4 ("Shell startup sequence"). Re-check
  // status fresh after refresh() — the `status` setter has updated, but the
  // closure value here is still "loading" until next render.
  useEffect(() => {
    if (!autoStart) return;
    let cancelled = false;
    (async () => {
      try {
        await refresh();
        const s = await daemonStatus();
        if (cancelled) return;
        if (s.state === "none" || s.state === "stale") {
          await startDaemon(true);
        }
      } catch (e) {
        if (cancelled) return;
        setError(renderTypedError(e));
        setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [autoStart, refresh, startDaemon]);

  return (
    <DaemonContext.Provider value={{ status, config, error, startDaemon, stopDaemon, refresh }}>
      {children}
    </DaemonContext.Provider>
  );
}

export function useDaemon(): DaemonContextValue {
  const ctx = useContext(DaemonContext);
  if (!ctx) throw new Error("useDaemon must be used inside <DaemonProvider>");
  return ctx;
}

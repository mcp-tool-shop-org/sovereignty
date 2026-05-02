// Typed wrappers around Tauri's invoke() — the 4 commands listed in
// docs/v2.1-tauri-shell.md §3. Anything not in this file is not a daemon
// IPC call; gameplay verbs go via CLI subprocess (Wave 3 spec §10).

import { invoke as tauriInvoke } from "@tauri-apps/api/core";
import type { DaemonConfig, DaemonStatus, XRPLNetwork } from "../types/daemon";

export async function daemonStatus(): Promise<DaemonStatus> {
  return tauriInvoke<DaemonStatus>("daemon_status");
}

export async function daemonStart(
  readonly_: boolean,
  network?: XRPLNetwork,
): Promise<DaemonConfig> {
  return tauriInvoke<DaemonConfig>("daemon_start", {
    readonly: readonly_,
    network,
  });
}

export async function daemonStop(): Promise<void> {
  return tauriInvoke<void>("daemon_stop");
}

export async function getDaemonConfig(): Promise<DaemonConfig> {
  return tauriInvoke<DaemonConfig>("get_daemon_config");
}

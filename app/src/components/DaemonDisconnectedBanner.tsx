// DaemonDisconnectedBanner — top-of-app banner that surfaces the give-up
// state from useDaemonEvents.ts after the SSE retry budget is exhausted
// (~63s of failed reconnects). Wires the `daemonConnectionLost` CustomEvent
// the hook dispatches: prior to this component the event was dispatched but
// no consumer listened, so the SSE silently died. WEB-UI-C-004 (Stage A miss).
//
// Mounting: the banner is rendered at the App layout root inside the
// DaemonProvider so every route inherits it. On Reconnect it bumps an
// internal token that consumers re-key against; the existing useDaemon
// `refresh()` re-establishes status, and useDaemonEvents re-mounts the SSE
// loop on its own when status flips back to "running".
//
// Stage 9-D Theme 3 (WEB-UI-D-008/D-009/D-010):
//   - sticky-top + z-index 100 (CSS) so the banner doesn't scroll out
//   - auto-dismiss when daemon status flips back to "running"
//   - explicit close (×) button preserved as redundant escape
//   - slide-in + fade animation via CSS, prefers-reduced-motion honored

import { useCallback, useEffect, useState } from "react";
import { useDaemon } from "../hooks/useDaemon";
import styles from "./DaemonDisconnectedBanner.module.css";

export function DaemonDisconnectedBanner() {
  const { refresh, status } = useDaemon();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handler = () => setVisible(true);
    window.addEventListener("daemonConnectionLost", handler);
    return () => {
      window.removeEventListener("daemonConnectionLost", handler);
    };
  }, []);

  // WEB-UI-D-009: auto-dismiss on reconnect. When the daemon SSE re-establishes
  // the provider's status flips back to "running" — the banner is no longer
  // useful, so unmount it. Manual dismiss (Reconnect / ×) preserved as
  // redundant escape.
  useEffect(() => {
    if (status === "running" && visible) setVisible(false);
  }, [status, visible]);

  const onReconnect = useCallback(() => {
    setVisible(false);
    void refresh();
  }, [refresh]);

  const onDismiss = useCallback(() => {
    setVisible(false);
  }, []);

  if (!visible) return null;

  return (
    <div className={styles.banner} role="alert" aria-live="assertive">
      <p className={styles.message}>
        Lost connection to daemon. Run <code>sov daemon start</code> to reconnect, then refresh.
      </p>
      <button type="button" className={styles.button} onClick={onReconnect}>
        Reconnect
      </button>
      <button
        type="button"
        className={styles.dismiss}
        onClick={onDismiss}
        aria-label="Dismiss banner"
      >
        ×
      </button>
    </div>
  );
}

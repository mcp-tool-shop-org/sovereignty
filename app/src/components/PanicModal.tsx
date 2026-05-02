// PanicModal — surfaces shell-level panics emitted by the Tauri panic hook.
//
// Stage 9-D Theme 1 (WEB-UI-D-012, Stage 8-C carryover):
//   - The Rust panic hook in app/src-tauri/src/lib.rs emits a `shell-panic`
//     Tauri event with payload `{ message, location, timestamp_iso }`.
//     PanicModal listens for that event and renders an unrecoverable-error
//     <dialog> with the payload + a Dismiss action.
//   - Mike's lock (AMEND.md): mounted at App ROOT, OUTSIDE <DaemonProvider>.
//     A shell panic that prevents DaemonProvider from initializing must
//     still surface this modal — that's the whole point. Mounting inside
//     the provider would couple panic visibility to daemon state.
//   - Dismiss closes the modal but does NOT auto-restart the shell.
//     Operator decides whether to relaunch.
//   - Consumer-listener pin (Mike's reinforcement): App.test.tsx asserts a
//     `shell-panic` listener is registered on render. Mirrors Stage 8-C's
//     SSE-banner consumer pin so a future refactor that orphans this
//     component fails the test mechanically.

import { useEffect, useRef, useState } from "react";
import type { PanicPayload } from "../types/daemon";
import styles from "./PanicModal.module.css";

interface TauriEventApi {
  listen: <T>(event: string, handler: (e: { payload: T }) => void) => Promise<() => void>;
}

/** Lazy-load @tauri-apps/api/event so vitest (jsdom / happy-dom) doesn't
 *  try to resolve the Tauri runtime. The import is cached after the first
 *  call. Returns `null` outside a Tauri webview where the import is
 *  unavailable — falls back to a no-op listener so the component renders
 *  cleanly under test. */
async function loadTauriEvents(): Promise<TauriEventApi | null> {
  try {
    const mod = await import("@tauri-apps/api/event");
    return mod as unknown as TauriEventApi;
  } catch {
    return null;
  }
}

export function PanicModal() {
  const [panic, setPanic] = useState<PanicPayload | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;

    void (async () => {
      const events = await loadTauriEvents();
      if (!events || cancelled) return;
      try {
        unlisten = await events.listen<PanicPayload>("shell-panic", (e) => {
          setPanic(e.payload);
        });
      } catch {
        // The webview is alive but listen() failed — no consumer wiring
        // available; rely on the structured log trail.
      }
    })();

    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  // Promote to native modal when panic arrives. Native ESC + the Dismiss
  // button both close the dialog. We retain the payload state so a re-open
  // is not possible without a fresh event (operator would relaunch).
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (panic && !dialog.open) dialog.showModal();
    else if (!panic && dialog.open) dialog.close();
  }, [panic]);

  const onDismiss = () => setPanic(null);

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      onClose={onDismiss}
      aria-labelledby="panic-modal-title"
    >
      {panic ? (
        <>
          <h2 id="panic-modal-title" className={styles.title}>
            Sovereignty has encountered a fatal error
          </h2>
          <p className={styles.body}>
            The desktop shell hit an unrecoverable error. Dismiss this dialog and relaunch the app
            to continue. If the error recurs, file an issue with the details below.
          </p>
          <dl className={styles.payload}>
            <dt>Message</dt>
            <dd>{panic.message}</dd>
            <dt>Location</dt>
            <dd>{panic.location}</dd>
            <dt>Timestamp</dt>
            <dd>{panic.timestamp_iso}</dd>
          </dl>
          <div className={styles.actions}>
            <button type="button" className={styles.dismiss} onClick={onDismiss}>
              Dismiss
            </button>
          </div>
        </>
      ) : null}
    </dialog>
  );
}

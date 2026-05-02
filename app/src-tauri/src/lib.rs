//! Sovereignty Tauri 2 shell.
//!
//! Thin window manager + 4-command bridge for daemon discovery / lifecycle.
//! The webview talks to the Sovereignty daemon directly over HTTP/SSE on
//! `127.0.0.1:<port>` (per Wave 3 contract). The Rust shell never proxies
//! daemon requests — it only owns daemon-discovery + lifecycle, plus a
//! `started_by_shell` flag used to scope auto-stop on window close.

pub mod commands;
pub mod config;
pub mod daemon;

use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, RunEvent, WindowEvent};

/// Payload emitted on the `shell-panic` Tauri event when the Rust shell
/// panics. The frontend `PanicModal` (web-ui scope) listens via
/// `@tauri-apps/api/event::listen<PanicPayload>("shell-panic", ...)` and
/// renders the structured fields. Field names are part of the cross-domain
/// contract — the TS mirror in `app/src/types/daemon.ts` mirrors them as
/// `{ message: string; location: string; timestamp_iso: string }`.
///
/// Stable across releases — Stage 8-C carryover, completed in Wave 9.
#[derive(Clone, Debug, Serialize)]
pub struct PanicPayload {
    pub message: String,
    pub location: String,
    pub timestamp_iso: String,
}

/// Process-lifetime state for the shell. `started_by_shell` is `true` iff the
/// daemon was started by the shell itself via `daemon_start`. On window close
/// the shell only stops daemons it started; externally-started daemons stay
/// alive (the user controls them via CLI).
///
/// `AtomicBool` over `Mutex<bool>`: the flag never gates any other shared
/// state, so a single atomic load/store is exactly the right primitive — no
/// poison semantics, no allocation, no `Result` wrapping. `Ordering::SeqCst`
/// is the safe default and the cost is negligible at this surface.
pub struct ShellState {
    pub started_by_shell: AtomicBool,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize structured logging. Default level is `warn` so the shell is
    // silent in normal use; operators set `RUST_LOG=sov_tauri_shell=debug` to
    // see the full close-handler / subprocess trail. `try_init` because tests
    // (or a future second `run()` invocation in process) must not panic on a
    // duplicate global subscriber.
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "warn".into()),
        )
        .try_init();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(ShellState {
            started_by_shell: AtomicBool::new(false),
        })
        .invoke_handler(tauri::generate_handler![
            commands::daemon_status,
            commands::daemon_start,
            commands::daemon_stop,
            commands::get_daemon_config,
        ])
        .on_window_event(handle_window_event)
        .build(tauri::generate_context!())
        .expect("error while building Sovereignty Tauri shell");

    // TAURI-SHELL-C-008 + Stage 8-C carryover (Wave 9): install a panic hook
    // so the shell emits a structured event instead of hitting the user with a
    // raw Rust traceback. The hook (a) logs a `shell.panic` tracing event for
    // `sov doctor` and the structured-log trail, AND (b) emits a Tauri
    // `shell-panic` event so the frontend's `PanicModal` can render a
    // user-facing crash banner. Installed AFTER `build()` so we can capture
    // an `AppHandle` for the emit; the previous panic hook is preserved so
    // test harnesses (which install their own hooks for `should_panic`) keep
    // working.
    install_panic_hook(app.handle().clone());

    app.run(|_app_handle, _event| {
        // Reserved for future RunEvent hooks; currently a no-op so we keep the
        // lifecycle surface explicit.
        let _ = RunEvent::Ready;
    });
}

/// Format a panic location into a stable `file:line:col` string. Returns
/// `"<unknown>"` when the panic info has no location attached (rare, but
/// possible for panics that originate outside Rust source — e.g. an FFI
/// boundary). Lifted out of the panic-hook closure so tests can pin the
/// payload shape without spawning a panicking thread.
pub(crate) fn format_panic_location(info: &std::panic::PanicHookInfo<'_>) -> String {
    info.location()
        .map(|l| format!("{}:{}:{}", l.file(), l.line(), l.column()))
        .unwrap_or_else(|| "<unknown>".to_string())
}

/// Format a panic payload into a stable string. Panics carry a `&'static str`
/// or a `String` payload in the common case; anything else surfaces as a
/// generic placeholder so the panic-hook payload is always a printable
/// string. Lifted out for test parity with [`format_panic_location`].
pub(crate) fn format_panic_payload(info: &std::panic::PanicHookInfo<'_>) -> String {
    let payload = info.payload();
    if let Some(s) = payload.downcast_ref::<&'static str>() {
        (*s).to_string()
    } else if let Some(s) = payload.downcast_ref::<String>() {
        s.clone()
    } else {
        "(non-string panic payload)".to_string()
    }
}

/// Format a `SystemTime` as RFC 3339 / ISO 8601 in UTC (`YYYY-MM-DDTHH:MM:SSZ`).
///
/// Implemented inline against `std::time` to avoid pulling `chrono` or `time`
/// as a direct dependency just for one timestamp string. Uses the civil-calendar
/// algorithm from Howard Hinnant (`days_from_civil` inverse), valid for all
/// proleptic Gregorian dates. Matches the `timestamp_iso` shape the structured
/// daemon-logging contract uses elsewhere (`sov_daemon/log_fields.py`).
pub(crate) fn format_iso_utc(now: SystemTime) -> String {
    let secs_since_epoch = now
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);

    // Split into days-since-epoch and seconds-of-day. Floor division for
    // negative epoch values (pre-1970), though we never expect them here.
    let days = secs_since_epoch.div_euclid(86_400);
    let secs_of_day = secs_since_epoch.rem_euclid(86_400);
    let h = secs_of_day / 3600;
    let m = (secs_of_day % 3600) / 60;
    let s = secs_of_day % 60;

    // Hinnant civil_from_days: convert days-since-1970-01-01 to (y, m, d).
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = y + if month <= 2 { 1 } else { 0 };

    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        year, month, d, h, m, s
    )
}

/// Install a panic hook that (a) logs a structured `shell.panic` tracing event
/// and (b) emits a Tauri `shell-panic` event the frontend can listen to.
///
/// TAURI-SHELL-C-008 + Stage 8-C carryover (Wave 9): a raw Rust traceback is a
/// developer-grade error surface; the user-facing path is twofold —
///
/// 1. The same tracing subscriber the rest of the shell uses (for `sov doctor`
///    + support bundles).
/// 2. A Tauri `shell-panic` event with a stable [`PanicPayload`] (for the
///    frontend `PanicModal`, web-ui scope).
///
/// The hook calls back into the previous panic hook so test harnesses (which
/// install their own hooks for `should_panic` machinery) keep working.
///
/// The hook does NOT crash the process — Rust's default behavior of aborting
/// on an unhandled panic still applies after the hook returns. The emit is
/// best-effort: a panic during shutdown (when the AppHandle has nothing to
/// dispatch to) silently swallows the event rather than re-panic in the hook.
fn install_panic_hook(app_handle: AppHandle) {
    let prev = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        let location = format_panic_location(info);
        let message = format_panic_payload(info);
        let timestamp_iso = format_iso_utc(SystemTime::now());

        tracing::error!(
            event = "shell.panic",
            location = %location,
            payload = %message,
            timestamp_iso = %timestamp_iso,
            "shell panicked; see structured log for context"
        );

        // Best-effort emit to the frontend so `PanicModal` can render a
        // structured crash banner. Errors are swallowed: if the AppHandle
        // can't dispatch (e.g. teardown in progress) we still want the
        // tracing log + the previous hook to run.
        let _ = app_handle.emit(
            "shell-panic",
            PanicPayload {
                message,
                location,
                timestamp_iso,
            },
        );

        prev(info);
    }));
}

/// Handle window events. Specifically: on close, if the shell started the
/// daemon, fire a best-effort `daemon stop` so the user doesn't have to clean
/// up stray processes.
///
/// Structured log events emitted from this surface (TAURI-SHELL-B-006):
/// - `shell.daemon_stop_on_close_failed` — best-effort stop returned an error;
///   the user may have a stale daemon process. Operators should run
///   `sov daemon stop` manually or `sov doctor` to confirm.
fn handle_window_event(window: &tauri::Window, event: &WindowEvent) {
    if let WindowEvent::CloseRequested { .. } = event {
        let state = window.state::<ShellState>();
        let started = state.started_by_shell.load(Ordering::SeqCst);
        if started {
            // Best-effort: errors are not propagated up — the user is closing
            // the window; do not block on a stubborn daemon. We DO emit a
            // structured warn event so operators (and `sov doctor` later) have
            // a breadcrumb trail when a stale daemon survives a close.
            if let Err(e) = daemon::stop_blocking() {
                tracing::warn!(
                    event = "shell.daemon_stop_on_close_failed",
                    error = %e,
                    "best-effort daemon stop on window close failed; user may have a stale daemon"
                );
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tauri_conf_csp_is_locked_to_localhost() {
        // TAURI-SHELL-001: the CSP must be a non-null string that locks the
        // webview to self + localhost. A regression to `null` (or any value
        // missing the localhost connect-src) re-opens the threat model.
        let raw = include_str!("../tauri.conf.json");
        let value: serde_json::Value =
            serde_json::from_str(raw).expect("tauri.conf.json must be valid JSON");
        let csp = value
            .get("app")
            .and_then(|a| a.get("security"))
            .and_then(|s| s.get("csp"));
        let csp_str = csp
            .and_then(|c| c.as_str())
            .expect("app.security.csp must be a non-null string");
        assert!(
            csp_str.contains("default-src 'self'"),
            "csp missing default-src: {csp_str}"
        );
        assert!(
            csp_str.contains("connect-src"),
            "csp missing connect-src: {csp_str}"
        );
        assert!(
            csp_str.contains("http://127.0.0.1:*"),
            "csp must allow daemon on 127.0.0.1: {csp_str}"
        );
        assert!(
            csp_str.contains("http://localhost:*"),
            "csp must allow Vite dev server on localhost: {csp_str}"
        );
        assert!(
            csp_str.contains("script-src 'self'"),
            "csp must lock scripts to self: {csp_str}"
        );
    }

    #[test]
    fn shell_state_default_started_by_shell_is_false() {
        let s = ShellState {
            started_by_shell: AtomicBool::new(false),
        };
        assert!(!s.started_by_shell.load(Ordering::SeqCst));
    }

    #[test]
    fn shell_state_flag_can_be_toggled() {
        let s = ShellState {
            started_by_shell: AtomicBool::new(false),
        };
        s.started_by_shell.store(true, Ordering::SeqCst);
        assert!(s.started_by_shell.load(Ordering::SeqCst));
        s.started_by_shell.store(false, Ordering::SeqCst);
        assert!(!s.started_by_shell.load(Ordering::SeqCst));
    }

    #[test]
    fn panic_hook_formatters_handle_str_payload() {
        // TAURI-SHELL-C-008: the payload formatter must turn a `&'static str`
        // payload into a printable string. We can't easily synthesize a
        // `PanicHookInfo` directly (the struct constructor is private), so
        // drive the formatters through `catch_unwind` with a captured
        // `Arc<Mutex<...>>` to record what a custom hook saw.
        use std::sync::{Arc, Mutex};
        let captured: Arc<Mutex<(String, String)>> =
            Arc::new(Mutex::new((String::new(), String::new())));
        let prev = std::panic::take_hook();
        let captured_in_hook = Arc::clone(&captured);
        std::panic::set_hook(Box::new(move |info| {
            let location = format_panic_location(info);
            let payload = format_panic_payload(info);
            *captured_in_hook.lock().unwrap() = (location, payload);
        }));
        let result = std::panic::catch_unwind(|| {
            panic!("test panic with str payload");
        });
        std::panic::set_hook(prev);
        assert!(result.is_err());
        let g = captured.lock().unwrap();
        assert!(
            g.0.contains("lib.rs"),
            "panic location should name source file; got: {:?}",
            g.0
        );
        assert!(
            g.0.contains(':'),
            "panic location should be `file:line:col`; got: {:?}",
            g.0
        );
        assert_eq!(
            g.1, "test panic with str payload",
            "panic payload should round-trip the panic message"
        );
    }

    #[test]
    fn panic_hook_formatters_handle_string_payload() {
        // TAURI-SHELL-C-008: `panic!("{}", String::from("..."))` produces a
        // `String` payload (not `&'static str`); the formatter must handle
        // both branches.
        use std::sync::{Arc, Mutex};
        let captured: Arc<Mutex<String>> = Arc::new(Mutex::new(String::new()));
        let prev = std::panic::take_hook();
        let captured_in_hook = Arc::clone(&captured);
        std::panic::set_hook(Box::new(move |info| {
            *captured_in_hook.lock().unwrap() = format_panic_payload(info);
        }));
        let result = std::panic::catch_unwind(|| {
            let s = String::from("string panic payload");
            panic!("{s}");
        });
        std::panic::set_hook(prev);
        assert!(result.is_err());
        let g = captured.lock().unwrap();
        assert_eq!(*g, "string panic payload");
    }

    #[test]
    fn shell_state_no_mutex_poison_paths() {
        // Round-trip through the same primitive the production close-handler
        // and command surface use; any future regression that re-introduces a
        // `lock()` call site will fail to compile against `AtomicBool`.
        let s = ShellState {
            started_by_shell: AtomicBool::new(false),
        };
        for _ in 0..32 {
            s.started_by_shell.store(true, Ordering::SeqCst);
            assert!(s.started_by_shell.load(Ordering::SeqCst));
            s.started_by_shell.store(false, Ordering::SeqCst);
            assert!(!s.started_by_shell.load(Ordering::SeqCst));
        }
    }
}

/// Stage 8-C carryover (Wave 9, Mike's reinforcement): the panic-event channel
/// completion ships with regression tests that pin the cross-domain payload
/// shape. The TS mirror at `app/src/types/daemon.ts` consumes the same three
/// stable field names — drift here is drift in the user-facing crash modal.
#[cfg(test)]
mod panic_emit_tests {
    use super::*;

    #[test]
    fn panic_payload_serializes_with_stable_field_names() {
        // Cross-domain contract: `message`, `location`, `timestamp_iso` are
        // the three field names the frontend `PanicModal` reads off the
        // `shell-panic` event payload. A field rename here is a TS-mirror
        // break — pin it mechanically.
        let payload = PanicPayload {
            message: "boom".to_string(),
            location: "src/lib.rs:42:7".to_string(),
            timestamp_iso: "2026-05-02T12:00:00Z".to_string(),
        };
        let json = serde_json::to_string(&payload).expect("PanicPayload serializes");
        assert!(
            json.contains("\"message\":\"boom\""),
            "payload missing `message` field: {json}"
        );
        assert!(
            json.contains("\"location\":\"src/lib.rs:42:7\""),
            "payload missing `location` field: {json}"
        );
        assert!(
            json.contains("\"timestamp_iso\":\"2026-05-02T12:00:00Z\""),
            "payload missing `timestamp_iso` field: {json}"
        );
        // No surprise extra fields — the TS mirror's `PanicEvent` shape is
        // exhaustive on these three. If a fourth field gets added here, the
        // TS mirror must update in lockstep.
        let v: serde_json::Value = serde_json::from_str(&json).unwrap();
        let obj = v.as_object().expect("payload is a JSON object");
        assert_eq!(
            obj.len(),
            3,
            "PanicPayload must have exactly 3 fields (message/location/timestamp_iso); got {}: {json}",
            obj.len()
        );
    }

    #[test]
    fn format_iso_utc_produces_rfc3339_z_suffix() {
        // Stable shape `YYYY-MM-DDTHH:MM:SSZ`. The frontend doesn't parse
        // this — it's display + support-bundle text — but the format is part
        // of the contract so a future change to e.g. fractional seconds
        // doesn't surprise the modal layout.
        let t = SystemTime::UNIX_EPOCH + std::time::Duration::from_secs(1_777_740_634);
        // 1_777_740_634 = 2026-05-02T16:50:34Z (matches the brand-fetch
        // header `date` line from this same Wave 13 amend session).
        let s = format_iso_utc(t);
        assert_eq!(s, "2026-05-02T16:50:34Z");
    }

    #[test]
    fn format_iso_utc_handles_unix_epoch() {
        let s = format_iso_utc(SystemTime::UNIX_EPOCH);
        assert_eq!(s, "1970-01-01T00:00:00Z");
    }

    // Note on Tauri-harness coverage: simulating a `tauri::AppHandle` in a
    // `cargo test` unit context requires `tauri::test::mock_app()` (or
    // equivalent), which in turn pulls the bundled-context macros and an
    // OS-level event loop. That's a much bigger surface than this Stage 8-C
    // carryover wants to take on — the payload-shape pin above is the
    // load-bearing test (it's the cross-domain TS-mirror contract). The
    // emit-on-panic call itself is exercised end-to-end by `npm run tauri
    // dev` + a deliberate panic during smoke; if that integration moves to
    // automated CI later (Wave 11 distribution work), the harness lands then.
}

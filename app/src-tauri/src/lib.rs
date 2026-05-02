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

use tauri::{Manager, RunEvent, WindowEvent};

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

    // TAURI-SHELL-C-008: install a panic hook so the shell emits a structured
    // event instead of hitting the user with a raw Rust traceback. The hook
    // logs a `shell.panic` event with the same `event` / structured-fields
    // shape used by the close-handler (TAURI-SHELL-B-006), so `sov doctor`
    // and operators see panics in the same trail as other lifecycle events.
    install_panic_hook();

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

/// Install a panic hook that emits a structured `shell.panic` log event.
///
/// TAURI-SHELL-C-008: a raw Rust traceback is a developer-grade error surface;
/// the user-facing path is the structured event captured by the same tracing
/// subscriber the rest of the shell uses. The hook calls back into the
/// previous panic hook so test harnesses (which install their own hooks for
/// `should_panic` machinery) keep working.
///
/// The hook does NOT crash the process — Rust's default behavior of aborting
/// on an unhandled panic still applies after the hook returns. The structured
/// log line gives `sov doctor` and the close-handler trail a breadcrumb to
/// surface in support bundles.
fn install_panic_hook() {
    let prev = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        let location = format_panic_location(info);
        let payload = format_panic_payload(info);
        tracing::error!(
            event = "shell.panic",
            location = %location,
            payload = %payload,
            "shell panicked; see structured log for context"
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

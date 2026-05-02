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

/// Handle window events. Specifically: on close, if the shell started the
/// daemon, fire a best-effort `daemon stop` so the user doesn't have to clean
/// up stray processes.
fn handle_window_event(window: &tauri::Window, event: &WindowEvent) {
    if let WindowEvent::CloseRequested { .. } = event {
        let state = window.state::<ShellState>();
        let started = state.started_by_shell.load(Ordering::SeqCst);
        if started {
            // Best-effort: errors are swallowed deliberately — the user is
            // closing the window; do not block on a stubborn daemon.
            let _ = daemon::stop_blocking();
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

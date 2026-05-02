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

use std::sync::Mutex;

use tauri::{Manager, RunEvent, WindowEvent};

/// Process-lifetime state for the shell. `started_by_shell` is `true` iff the
/// daemon was started by the shell itself via `daemon_start`. On window close
/// the shell only stops daemons it started; externally-started daemons stay
/// alive (the user controls them via CLI).
pub struct ShellState {
    pub started_by_shell: Mutex<bool>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(ShellState {
            started_by_shell: Mutex::new(false),
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
        let started = state.started_by_shell.lock().map(|g| *g).unwrap_or(false);
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
    fn shell_state_default_started_by_shell_is_false() {
        let s = ShellState {
            started_by_shell: Mutex::new(false),
        };
        assert!(!*s.started_by_shell.lock().unwrap());
    }

    #[test]
    fn shell_state_flag_can_be_toggled() {
        let s = ShellState {
            started_by_shell: Mutex::new(false),
        };
        {
            let mut g = s.started_by_shell.lock().unwrap();
            *g = true;
        }
        assert!(*s.started_by_shell.lock().unwrap());
    }
}

//! Tauri command surface — the four (and only four) commands the webview can
//! invoke on the Rust shell. Per `docs/v2.1-tauri-shell.md` §3.
//!
//! - `daemon_status()`        — runs `sov daemon status --json`
//! - `daemon_start(...)`      — runs `sov daemon start [...]`, sets `started_by_shell`
//! - `daemon_stop()`          — runs `sov daemon stop`
//! - `get_daemon_config()`    — reads `.sov/daemon.json` directly (no subprocess)

use std::sync::atomic::Ordering;

use serde::{Deserialize, Serialize};

use crate::config;
use crate::daemon;
use crate::ShellState;

// ──────────────────────────────────────────────────────────────────────
// Shapes (mirror docs/v2.1-tauri-shell.md §3 + docs/v2.1-daemon-ipc.md §6)
// ──────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DaemonConfig {
    pub pid: u32,
    pub port: u16,
    pub token: String,
    pub network: String,
    pub readonly: bool,
    pub ipc_version: u32,
    pub started_iso: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum DaemonState {
    Running,
    Stale,
    None,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DaemonStatus {
    pub state: DaemonState,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<DaemonConfig>,
    /// `true` iff the daemon was started by THIS shell instance (via
    /// `daemon_start`). The frontend uses this to scope auto-stop behavior on
    /// window close — no `?? true` fallback. Externally-started daemons
    /// (via the CLI in another terminal) read as `false` here even when the
    /// daemon is healthy and responsive.
    pub started_by_shell: bool,
}

/// Errors surfaced from the shell to the webview. Serialized as a tagged
/// union with stable `code` field per spec §3, so the frontend can dispatch
/// on `error.code === "DaemonNotRunning"` without parsing free-text.
///
/// Implementation note: serde's `tag` attribute requires a name distinct from
/// any variant field name. We use `code` for the discriminator and
/// `exit_code` for the numeric exit-code field on `SubprocessFailed` to keep
/// the serialized shape `{"code": "...", ...}` while sidestepping the
/// `tag-conflicts-with-field` derive error.
#[derive(Debug, thiserror::Error, Serialize)]
#[serde(tag = "code")]
pub enum ShellError {
    #[error("daemon not running")]
    DaemonNotRunning,

    #[error("daemon start failed: {stderr}")]
    DaemonStartFailed { stderr: String },

    #[error("daemon not installed (sov daemon --help fails)")]
    DaemonNotInstalled,

    #[error("config file missing")]
    ConfigFileMissing,

    #[error("config file malformed: {detail}")]
    ConfigFileMalformed { detail: String },

    #[error("subprocess failed: exit_code={exit_code}")]
    SubprocessFailed { exit_code: i32, stderr: String },
}

// ──────────────────────────────────────────────────────────────────────
// Tauri commands — exactly four. Re-audit fails the wave if more exist.
// ──────────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn daemon_status(
    state: tauri::State<'_, ShellState>,
) -> Result<DaemonStatus, ShellError> {
    let mut status = daemon::daemon_status_subprocess()?;
    // Inject the in-process flag — the daemon CLI cannot know whether THIS
    // shell instance started it. The frontend reads this directly without
    // any `?? true` fallback (cross-domain B with web-ui).
    status.started_by_shell = state.started_by_shell.load(Ordering::SeqCst);
    Ok(status)
}

#[tauri::command]
pub async fn daemon_start(
    state: tauri::State<'_, ShellState>,
    readonly: bool,
    network: Option<String>,
) -> Result<DaemonConfig, ShellError> {
    let config = daemon::daemon_start_subprocess(readonly, network.as_deref())?;
    state.started_by_shell.store(true, Ordering::SeqCst);
    Ok(config)
}

#[tauri::command]
pub async fn daemon_stop(state: tauri::State<'_, ShellState>) -> Result<(), ShellError> {
    let result = daemon::daemon_stop_subprocess();
    // Clear the flag regardless of the outcome — stop is idempotent and we
    // don't want a stuck `started_by_shell=true` if the daemon is already dead.
    state.started_by_shell.store(false, Ordering::SeqCst);
    result
}

#[tauri::command]
pub async fn get_daemon_config() -> Result<DaemonConfig, ShellError> {
    config::read_daemon_config()
}

// ──────────────────────────────────────────────────────────────────────
// Tests (serde + error-shape pinning)
// ──────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn daemon_config_round_trips_through_serde() {
        let cfg = DaemonConfig {
            pid: 12345,
            port: 47823,
            token: "some.bearer.token".to_string(),
            network: "testnet".to_string(),
            readonly: false,
            ipc_version: 1,
            started_iso: "2026-05-01T18:23:11Z".to_string(),
        };
        let json = serde_json::to_string(&cfg).unwrap();
        let back: DaemonConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(cfg, back);
    }

    #[test]
    fn daemon_state_serializes_lowercase() {
        assert_eq!(
            serde_json::to_string(&DaemonState::Running).unwrap(),
            "\"running\""
        );
        assert_eq!(
            serde_json::to_string(&DaemonState::Stale).unwrap(),
            "\"stale\""
        );
        assert_eq!(
            serde_json::to_string(&DaemonState::None).unwrap(),
            "\"none\""
        );
    }

    #[test]
    fn daemon_status_omits_config_when_none() {
        let status = DaemonStatus {
            state: DaemonState::None,
            config: None,
            started_by_shell: false,
        };
        let json = serde_json::to_string(&status).unwrap();
        assert!(!json.contains("\"config\""), "got {json}");
    }

    #[test]
    fn daemon_status_includes_started_by_shell_field() {
        // Cross-domain B contract: the field MUST be present and named
        // exactly `started_by_shell` so the TS shape matches without a
        // `?? true` fallback.
        let status = DaemonStatus {
            state: DaemonState::Running,
            config: None,
            started_by_shell: true,
        };
        let v: serde_json::Value = serde_json::to_value(&status).unwrap();
        assert_eq!(
            v.get("started_by_shell").and_then(|b| b.as_bool()),
            Some(true),
            "got {v}"
        );
    }

    #[test]
    fn daemon_status_started_by_shell_round_trips_false() {
        let status = DaemonStatus {
            state: DaemonState::None,
            config: None,
            started_by_shell: false,
        };
        let json = serde_json::to_string(&status).unwrap();
        let back: DaemonStatus = serde_json::from_str(&json).unwrap();
        assert!(!back.started_by_shell);
    }

    #[test]
    fn daemon_status_started_by_shell_mirrors_atomic_bool() {
        use std::sync::atomic::{AtomicBool, Ordering};
        // Prove the round-trip pattern used by the `daemon_status` command:
        // load from AtomicBool → write into DaemonStatus → serialize → field
        // value matches the AtomicBool's last store.
        let flag = AtomicBool::new(false);
        flag.store(true, Ordering::SeqCst);
        let mut status = DaemonStatus {
            state: DaemonState::Running,
            config: None,
            started_by_shell: false,
        };
        status.started_by_shell = flag.load(Ordering::SeqCst);
        let v: serde_json::Value = serde_json::to_value(&status).unwrap();
        assert_eq!(
            v.get("started_by_shell").and_then(|b| b.as_bool()),
            Some(true)
        );

        flag.store(false, Ordering::SeqCst);
        status.started_by_shell = flag.load(Ordering::SeqCst);
        let v: serde_json::Value = serde_json::to_value(&status).unwrap();
        assert_eq!(
            v.get("started_by_shell").and_then(|b| b.as_bool()),
            Some(false)
        );
    }

    #[test]
    fn shell_error_serializes_with_code_tag() {
        let err = ShellError::DaemonNotRunning;
        let json = serde_json::to_string(&err).unwrap();
        assert!(json.contains("\"code\""), "got {json}");
        assert!(json.contains("\"DaemonNotRunning\""), "got {json}");
    }

    #[test]
    fn shell_error_carries_stderr_for_start_failed() {
        let err = ShellError::DaemonStartFailed {
            stderr: "boom".to_string(),
        };
        let json = serde_json::to_string(&err).unwrap();
        assert!(json.contains("\"DaemonStartFailed\""), "got {json}");
        assert!(json.contains("boom"), "got {json}");
    }

    #[test]
    fn shell_error_subprocess_failed_includes_exit_code() {
        let err = ShellError::SubprocessFailed {
            exit_code: 137,
            stderr: "oom".to_string(),
        };
        let json = serde_json::to_string(&err).unwrap();
        assert!(json.contains("\"SubprocessFailed\""));
        assert!(json.contains("137"));
        assert!(json.contains("oom"));
        // Discriminator field name is `code`; numeric exit is `exit_code`.
        assert!(json.contains("\"code\":\"SubprocessFailed\""), "got {json}");
        assert!(json.contains("\"exit_code\":137"), "got {json}");
    }

    #[test]
    fn daemon_state_all_three_variants_round_trip() {
        for variant in [DaemonState::Running, DaemonState::Stale, DaemonState::None] {
            let s = serde_json::to_string(&variant).unwrap();
            let back: DaemonState = serde_json::from_str(&s).unwrap();
            assert_eq!(variant, back);
        }
    }

    #[test]
    fn daemon_config_field_names_match_daemon_json_schema() {
        // Pin the on-disk schema field names. If the daemon (Wave 3) changes a
        // field name and the shell forgets to follow, this test breaks.
        let cfg = DaemonConfig {
            pid: 1,
            port: 2,
            token: "t".into(),
            network: "testnet".into(),
            readonly: true,
            ipc_version: 1,
            started_iso: "x".into(),
        };
        let v: serde_json::Value = serde_json::to_value(&cfg).unwrap();
        for key in [
            "pid",
            "port",
            "token",
            "network",
            "readonly",
            "ipc_version",
            "started_iso",
        ] {
            assert!(v.get(key).is_some(), "missing field {key}");
        }
    }
}

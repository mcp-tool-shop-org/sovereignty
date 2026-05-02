//! Subprocess wrappers around `sov daemon {start,stop,status}`.
//!
//! Lifecycle logic stays in Python where Wave 3 tested it. The Rust shell
//! shells out for {start, stop, status}. `get_daemon_config` uses
//! [`crate::config::read_daemon_config`] instead — the file is the source of
//! truth, no subprocess needed.

use std::process::{Command, Output};

use crate::commands::{DaemonConfig, DaemonState, DaemonStatus, ShellError};
use crate::config;

/// Name of the daemon CLI binary. Lifted to a constant so tests can pin it
/// and a future rename or path-override stays narrow.
pub const SOV_BIN: &str = "sov";

/// Run `sov daemon status --json` and parse the result into a [`DaemonStatus`].
pub fn daemon_status_subprocess() -> Result<DaemonStatus, ShellError> {
    match Command::new(SOV_BIN)
        .args(["daemon", "status", "--json"])
        .output()
    {
        Ok(output) => parse_status_output(&output),
        Err(err) => Err(map_spawn_error(err)),
    }
}

/// Run `sov daemon start [--readonly] [--network X]` and return the resulting
/// [`DaemonConfig`] read from `.sov/daemon.json`.
pub fn daemon_start_subprocess(
    readonly: bool,
    network: Option<&str>,
) -> Result<DaemonConfig, ShellError> {
    let mut cmd = Command::new(SOV_BIN);
    cmd.args(["daemon", "start"]);
    if readonly {
        cmd.arg("--readonly");
    }
    if let Some(net) = network {
        cmd.args(["--network", net]);
    }

    let output = cmd.output().map_err(map_spawn_error)?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        // Heuristic: a missing-extra error from Python surfaces as a recognizable
        // module/import error or a "[daemon] extra" hint. The CLI smoke for
        // DAEMON_NOT_INSTALLED is daemon-help-fails; wave-4 scope keeps this
        // narrow — start failures other than that are DaemonStartFailed.
        return Err(ShellError::DaemonStartFailed { stderr });
    }

    // The daemon writes `.sov/daemon.json` atomically before the start
    // subprocess returns. Read it from disk as the authoritative config.
    config::read_daemon_config()
}

/// Run `sov daemon stop`. Idempotent — succeeds even if already stopped.
pub fn daemon_stop_subprocess() -> Result<(), ShellError> {
    let output = Command::new(SOV_BIN)
        .args(["daemon", "stop"])
        .output()
        .map_err(map_spawn_error)?;

    if output.status.success() {
        return Ok(());
    }

    // `sov daemon stop` is allowed to be a no-op when nothing is running.
    // We accept any "not running" / "no daemon" hint in stderr as success.
    let stderr = String::from_utf8_lossy(&output.stderr);
    let stderr_lower = stderr.to_ascii_lowercase();
    if stderr_lower.contains("not running")
        || stderr_lower.contains("no daemon")
        || stderr_lower.contains("none")
    {
        return Ok(());
    }

    Err(ShellError::SubprocessFailed {
        exit_code: output.status.code().unwrap_or(-1),
        stderr: stderr.into_owned(),
    })
}

/// Best-effort blocking stop, used from the window-close handler. Errors are
/// swallowed deliberately — the user is closing the window; we do not block
/// shutdown on a daemon that refuses to die.
pub fn stop_blocking() -> Result<(), ShellError> {
    daemon_stop_subprocess()
}

/// Map a `std::io::Error` from spawning `sov` into a typed [`ShellError`].
fn map_spawn_error(err: std::io::Error) -> ShellError {
    if err.kind() == std::io::ErrorKind::NotFound {
        ShellError::DaemonNotInstalled
    } else {
        ShellError::SubprocessFailed {
            exit_code: -1,
            stderr: err.to_string(),
        }
    }
}

/// Parse the output of `sov daemon status --json` into a [`DaemonStatus`].
///
/// The contract surfaces three states (running / stale / none). Wave 3's CLI
/// `--json` envelope uses `status: ok|warn|fail|info` plus a `fields[]` list.
/// Wave 4 contract reframes this to the shell's view: we treat any
/// well-formed JSON containing a `daemon` field with a `state` value as the
/// canonical shape; for now we accept either of the two plausible Wave 3
/// shapes (top-level `state` OR a nested `daemon.state`).
pub fn parse_status_output(output: &Output) -> Result<DaemonStatus, ShellError> {
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    if !output.status.success() {
        // Non-zero exit but with parseable stdout: still try; fall through to
        // SubprocessFailed if not parseable.
        if stdout.trim().is_empty() {
            return Err(ShellError::SubprocessFailed {
                exit_code: output.status.code().unwrap_or(-1),
                stderr: stderr.into_owned(),
            });
        }
    }

    let value: serde_json::Value =
        serde_json::from_str(stdout.trim()).map_err(|e| ShellError::SubprocessFailed {
            exit_code: output.status.code().unwrap_or(-1),
            stderr: format!("non-JSON status output: {e}"),
        })?;

    let state = extract_state(&value)?;
    let config = match state {
        DaemonState::Running => Some(extract_config(&value)?),
        _ => extract_config(&value).ok(),
    };

    Ok(DaemonStatus { state, config })
}

fn extract_state(value: &serde_json::Value) -> Result<DaemonState, ShellError> {
    // Try top-level `state`, then `daemon.state`, then `fields[].name == "state"`.
    if let Some(s) = value.get("state").and_then(|v| v.as_str()) {
        return parse_state_str(s);
    }
    if let Some(s) = value
        .get("daemon")
        .and_then(|d| d.get("state"))
        .and_then(|v| v.as_str())
    {
        return parse_state_str(s);
    }
    if let Some(fields) = value.get("fields").and_then(|f| f.as_array()) {
        for f in fields {
            if f.get("name").and_then(|n| n.as_str()) == Some("state") {
                if let Some(s) = f.get("value").and_then(|v| v.as_str()) {
                    return parse_state_str(s);
                }
            }
        }
    }
    Err(ShellError::SubprocessFailed {
        exit_code: 0,
        stderr: "no `state` field in `sov daemon status --json` output".to_string(),
    })
}

fn parse_state_str(s: &str) -> Result<DaemonState, ShellError> {
    match s.to_ascii_lowercase().as_str() {
        "running" => Ok(DaemonState::Running),
        "stale" => Ok(DaemonState::Stale),
        "none" => Ok(DaemonState::None),
        other => Err(ShellError::SubprocessFailed {
            exit_code: 0,
            stderr: format!("unrecognized daemon state: {other}"),
        }),
    }
}

fn extract_config(value: &serde_json::Value) -> Result<DaemonConfig, ShellError> {
    if let Some(cfg) = value.get("config") {
        return serde_json::from_value::<DaemonConfig>(cfg.clone()).map_err(|e| {
            ShellError::ConfigFileMalformed {
                detail: e.to_string(),
            }
        });
    }
    if let Some(cfg) = value.get("daemon").and_then(|d| d.get("config")) {
        return serde_json::from_value::<DaemonConfig>(cfg.clone()).map_err(|e| {
            ShellError::ConfigFileMalformed {
                detail: e.to_string(),
            }
        });
    }
    Err(ShellError::ConfigFileMissing)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::process::ExitStatusExt;
    use std::process::ExitStatus;

    fn make_output(code: i32, stdout: &str, stderr: &str) -> Output {
        Output {
            status: ExitStatus::from_raw(code << 8),
            stdout: stdout.as_bytes().to_vec(),
            stderr: stderr.as_bytes().to_vec(),
        }
    }

    #[test]
    fn parse_status_running_with_config() {
        let body = r#"{
            "state": "running",
            "config": {
                "pid": 99,
                "port": 47000,
                "token": "tok",
                "network": "testnet",
                "readonly": true,
                "ipc_version": 1,
                "started_iso": "2026-05-01T00:00:00Z"
            }
        }"#;
        let out = make_output(0, body, "");
        let status = parse_status_output(&out).unwrap();
        assert!(matches!(status.state, DaemonState::Running));
        let cfg = status.config.unwrap();
        assert_eq!(cfg.pid, 99);
        assert_eq!(cfg.port, 47000);
        assert!(cfg.readonly);
    }

    #[test]
    fn parse_status_none_no_config() {
        let body = r#"{"state": "none"}"#;
        let out = make_output(0, body, "");
        let status = parse_status_output(&out).unwrap();
        assert!(matches!(status.state, DaemonState::None));
        assert!(status.config.is_none());
    }

    #[test]
    fn parse_status_stale() {
        let body = r#"{"state": "stale"}"#;
        let out = make_output(0, body, "");
        let status = parse_status_output(&out).unwrap();
        assert!(matches!(status.state, DaemonState::Stale));
    }

    #[test]
    fn parse_status_nested_daemon_shape() {
        let body = r#"{"daemon": {"state": "running", "config": {
            "pid": 1, "port": 2, "token": "t", "network": "testnet",
            "readonly": false, "ipc_version": 1, "started_iso": "2026-05-01T00:00:00Z"
        }}}"#;
        let out = make_output(0, body, "");
        let status = parse_status_output(&out).unwrap();
        assert!(matches!(status.state, DaemonState::Running));
        assert_eq!(status.config.unwrap().pid, 1);
    }

    #[test]
    fn parse_status_doctor_envelope_shape() {
        // Wave 3 doctor-style envelope: `fields[]` with name/status/value.
        let body = r#"{
            "timestamp": "2026-05-01T00:00:00Z",
            "command": "sov daemon status",
            "status": "ok",
            "fields": [
                {"name": "state", "status": "ok", "value": "none"}
            ]
        }"#;
        let out = make_output(0, body, "");
        let status = parse_status_output(&out).unwrap();
        assert!(matches!(status.state, DaemonState::None));
    }

    #[test]
    fn parse_status_garbage_stdout_errors() {
        let out = make_output(0, "not json", "");
        let err = parse_status_output(&out).unwrap_err();
        assert!(matches!(err, ShellError::SubprocessFailed { .. }));
    }

    #[test]
    fn parse_status_unknown_state_errors() {
        let body = r#"{"state": "exploding"}"#;
        let out = make_output(0, body, "");
        let err = parse_status_output(&out).unwrap_err();
        assert!(matches!(err, ShellError::SubprocessFailed { .. }));
    }

    #[test]
    fn map_spawn_error_not_found_is_daemon_not_installed() {
        let err = std::io::Error::from(std::io::ErrorKind::NotFound);
        let mapped = map_spawn_error(err);
        assert!(matches!(mapped, ShellError::DaemonNotInstalled));
    }

    #[test]
    fn map_spawn_error_other_is_subprocess_failed() {
        let err = std::io::Error::from(std::io::ErrorKind::PermissionDenied);
        let mapped = map_spawn_error(err);
        assert!(matches!(mapped, ShellError::SubprocessFailed { .. }));
    }
}

//! Subprocess wrappers around `sov daemon {start,stop,status}`.
//!
//! Lifecycle logic stays in Python where Wave 3 tested it. The Rust shell
//! shells out for {start, stop, status}. `get_daemon_config` uses
//! [`crate::config::read_daemon_config`] instead — the file is the source of
//! truth, no subprocess needed.
//!
//! All subprocess calls are bounded by a wall-clock timeout (TAURI-SHELL-B-007).
//! A misbehaving CLI that hangs on disk/network I/O or a stuck SIGTERM-resistant
//! daemon must NOT freeze the webview's polling spinner. On timeout the helper
//! returns `ShellError::SubprocessFailed { exit_code: -1, stderr: "timeout" }`.

use std::path::Path;
use std::process::{Output, Stdio};
use std::time::Duration;

use tokio::process::Command;
use tokio::time::timeout;

use crate::commands::{DaemonConfig, DaemonState, DaemonStatus, ShellError};
use crate::config;

/// Name of the daemon CLI binary. Lifted to a constant so tests can pin it
/// and a future rename or path-override stays narrow.
pub const SOV_BIN: &str = "sov";

/// Hard wall-clock cap for any single `sov daemon ...` subprocess invocation.
///
/// Must be **strictly greater** than Python's
/// `_START_HANDSHAKE_TIMEOUT_SECONDS` (10) and `_STOP_POLL_TIMEOUT_SECONDS`
/// (10). Matching those bounds (the v2.1 10s wall) raced SIGKILL against a
/// live `sov daemon start`: the CLI had already detached the real daemon
/// (`start_new_session=True` / `DETACHED_PROCESS`) and was still inside
/// `_wait_for_handshake`, so killing the CLI tree left the grandchild +
/// handshake behind (F-029f9c24). A longer cap lets a failed start return
/// and `_remove_handshake()` instead of racing the kill; the timeout path
/// still reaps via the handshake pid if the CLI never returns.
pub const SUBPROCESS_TIMEOUT: Duration = Duration::from_secs(20);

/// Apply the portable subprocess envelope: `kill_on_drop`, a new process
/// group (so timeout can reap grandchildren), piped stdio, and cwd pinned
/// to the discovered player root rather than the Tauri binary CWD.
fn configure_daemon_command(cmd: &mut Command) {
    cmd.kill_on_drop(true);
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());
    cmd.current_dir(config::subprocess_cwd());
    #[cfg(unix)]
    {
        cmd.process_group(0);
    }
    #[cfg(windows)]
    {
        // CREATE_NEW_PROCESS_GROUP so timeout can taskkill /T the tree.
        const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
        cmd.creation_flags(CREATE_NEW_PROCESS_GROUP);
    }
}

/// Kill a spawned `sov daemon` child and its process group. `start_kill`
/// covers the direct child; the group/tree kill covers grandchildren the
/// CLI may have spawned before we timed out.
///
/// This does **not** reap a daemon that already `setsid`/`DETACHED_PROCESS`'d
/// itself — that pid lives in a different group and is tracked only via
/// `.sov/daemon.json`. See [`reap_handshake_daemon_at`].
fn kill_process_tree(pid: u32) {
    #[cfg(unix)]
    {
        let _ = std::process::Command::new("kill")
            .args(["-KILL", &format!("-{pid}")])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
    #[cfg(windows)]
    {
        let _ = std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
}

/// Signal one pid (the process, not `-{pid}` the group).
///
/// Needed for the post-`os.fork()` daemon: handshake `pid` is the grandchild,
/// whose PGID is the (already-exited) intermediate parent, so
/// `kill -KILL -handshake_pid` is ESRCH. Windows `taskkill /T` still covers
/// that pid's remaining children.
fn kill_pid(pid: u32) {
    #[cfg(unix)]
    {
        let _ = std::process::Command::new("kill")
            .args(["-KILL", &pid.to_string()])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
    #[cfg(windows)]
    {
        kill_process_tree(pid);
    }
}

/// Best-effort pid from `{path}` — loose JSON so a schema-mismatch handshake
/// still names the process we have to reap.
fn handshake_pid_at(path: &Path) -> Option<u32> {
    let contents = std::fs::read_to_string(path).ok()?;
    let value: serde_json::Value = serde_json::from_str(&contents).ok()?;
    let pid = value.get("pid")?.as_u64()?;
    u32::try_from(pid).ok()
}

/// On `sov daemon start` timeout, reap the detached grandchild named by the
/// handshake rather than only the CLI process group (F-029f9c24).
///
/// Skips when `pid` is unchanged from `prior_pid` so a hang *before* spawn
/// cannot SIGKILL an already-running external daemon whose handshake we
/// merely observed.
fn reap_handshake_daemon_at(path: &Path, prior_pid: Option<u32>) {
    let Some(pid) = handshake_pid_at(path) else {
        return;
    };
    if prior_pid == Some(pid) {
        return;
    }
    kill_pid(pid);
    kill_process_tree(pid);
}

fn is_timeout_error(result: &Result<Output, ShellError>) -> bool {
    matches!(
        result,
        Err(ShellError::SubprocessFailed {
            exit_code: -1,
            stderr
        }) if stderr.contains("did not respond")
    )
}

/// Best-effort liveness probe used by the timeout-kill regression.
#[cfg(test)]
fn pid_is_alive(pid: u32) -> bool {
    #[cfg(windows)]
    {
        let output = std::process::Command::new("tasklist")
            .args(["/FI", &format!("PID eq {pid}"), "/NH"])
            .output();
        match output {
            Ok(o) => {
                let text = String::from_utf8_lossy(&o.stdout);
                text.contains(&pid.to_string())
            }
            Err(_) => false,
        }
    }
    #[cfg(unix)]
    {
        // `kill -0` is true for zombies. After SIGKILL the fixture Child
        // is unreaped until drop, so treat state Z as dead.
        let stat = std::fs::read_to_string(format!("/proc/{pid}/stat")).ok();
        match stat {
            Some(s) => match s.rsplit_once(')') {
                Some((_, rest)) => !rest.trim_start().starts_with('Z'),
                None => true,
            },
            None => false,
        }
    }
}

/// Wrap a `tokio::process::Command` spawn with a timeout. On elapsed
/// timeout, kills the child (and process group) then returns
/// `ShellError::SubprocessFailed { exit_code: -1, stderr: <recovery> }`.
/// `exit_code == -1` remains the machine-readable timeout discriminator
/// the frontend can dispatch on (TAURI-SHELL-C-006).
async fn run_with_timeout(cmd: &mut Command) -> Result<Output, ShellError> {
    run_with_timeout_inner(cmd, SUBPROCESS_TIMEOUT).await.0
}

/// Start-specific timeout wrapper: after the CLI tree is killed, reap the
/// detached daemon named by `{handshake_path}` unless that pid pre-existed
/// the spawn attempt.
async fn run_start_with_timeout(
    cmd: &mut Command,
    handshake_path: &Path,
    prior_pid: Option<u32>,
) -> Result<Output, ShellError> {
    run_start_with_timeout_inner(cmd, SUBPROCESS_TIMEOUT, handshake_path, prior_pid)
        .await
        .0
}

async fn run_start_with_timeout_inner(
    cmd: &mut Command,
    bound: Duration,
    handshake_path: &Path,
    prior_pid: Option<u32>,
) -> (Result<Output, ShellError>, Option<u32>) {
    let (result, pid) = run_with_timeout_inner(cmd, bound).await;
    if is_timeout_error(&result) {
        reap_handshake_daemon_at(handshake_path, prior_pid);
    }
    (result, pid)
}

/// Inner seam — accepts an explicit duration so tests can drive timeouts on a
/// budget shorter than `SUBPROCESS_TIMEOUT`. Production callers go through
/// [`run_with_timeout`].
///
/// Returns the child pid alongside the result so tests can assert the
/// process was actually reaped after a timeout, not just that the error
/// shape contains `exit_code == -1`.
///
/// On elapsed timeout the `stderr` field carries a full sentence naming the
/// elapsed bound and the recovery commands (`sov daemon stop` + `sov doctor`).
async fn run_with_timeout_inner(
    cmd: &mut Command,
    bound: Duration,
) -> (Result<Output, ShellError>, Option<u32>) {
    use tokio::io::AsyncReadExt;

    configure_daemon_command(cmd);
    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(err) => return (Err(map_spawn_error(err)), None),
    };
    let pid = child.id();
    match timeout(bound, child.wait()).await {
        Ok(result) => {
            let status = match result {
                Ok(s) => s,
                Err(err) => return (Err(map_spawn_error(err)), pid),
            };
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            if let Some(mut pipe) = child.stdout.take() {
                let _ = pipe.read_to_end(&mut stdout).await;
            }
            if let Some(mut pipe) = child.stderr.take() {
                let _ = pipe.read_to_end(&mut stderr).await;
            }
            (
                Ok(Output {
                    status,
                    stdout,
                    stderr,
                }),
                pid,
            )
        }
        Err(_elapsed) => {
            let _ = child.start_kill();
            if let Some(pid) = pid {
                kill_process_tree(pid);
            }
            let _ = timeout(Duration::from_secs(2), child.wait()).await;
            (
                Err(ShellError::SubprocessFailed {
                    exit_code: -1,
                    stderr: format!(
                        "the `sov daemon` command did not respond within {}s. Run `sov daemon stop` then retry, or run `sov doctor` for diagnostics.",
                        bound.as_secs()
                    ),
                }),
                pid,
            )
        }
    }
}

/// Run `sov daemon status --json` and parse the result into a [`DaemonStatus`].
pub async fn daemon_status_subprocess() -> Result<DaemonStatus, ShellError> {
    let mut cmd = Command::new(SOV_BIN);
    cmd.args(["daemon", "status", "--json"]);
    let output = run_with_timeout(&mut cmd).await?;
    parse_status_output(&output)
}

/// Run `sov daemon start [--readonly] [--network X]` and return the resulting
/// [`DaemonConfig`] read from `.sov/daemon.json`.
///
/// CWD is the discovered player root. If a handshake already exists there
/// (CLI daemon the operator started from the table) we still invoke `sov
/// daemon start`, which refuses with DAEMON_PORT_BUSY rather than spawning
/// a second daemon against the Tauri binary CWD.
pub async fn daemon_start_subprocess(
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

    // Snapshot the handshake pid *before* spawn so a timeout cannot reap an
    // external daemon whose file we merely observed (hang-before-spawn).
    let handshake_path = config::default_config_path();
    let prior_pid = handshake_pid_at(&handshake_path);
    let output = run_start_with_timeout(&mut cmd, &handshake_path, prior_pid).await?;

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
pub async fn daemon_stop_subprocess() -> Result<(), ShellError> {
    let mut cmd = Command::new(SOV_BIN);
    cmd.args(["daemon", "stop"]);
    let output = run_with_timeout(&mut cmd).await?;

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

/// Best-effort blocking stop, used from the synchronous window-close handler.
/// Errors are not propagated up — the caller emits a structured `tracing::warn!`
/// (TAURI-SHELL-B-006) — but they are still typed for the tracing event.
///
/// The window-event callback is sync, but the subprocess driver is async, so
/// we drive a fresh single-thread current-thread runtime here. This is the
/// narrowest seam that keeps the rest of the file uniformly async without
/// requiring Tauri to surface a `tokio::Handle` to the close handler.
pub fn stop_blocking() -> Result<(), ShellError> {
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|e| ShellError::SubprocessFailed {
            exit_code: -1,
            stderr: format!("failed to build tokio runtime for stop: {e}"),
        })?;
    runtime.block_on(daemon_stop_subprocess())
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

    // `started_by_shell` is not derivable from subprocess output (the daemon
    // CLI has no view into THIS shell's in-memory flag). The wrapping
    // `daemon_status` command overlays the live value from `ShellState` after
    // this function returns; default to `false` here so any caller that
    // bypasses the command surface still gets a defined boolean.
    Ok(DaemonStatus {
        state,
        config,
        started_by_shell: false,
    })
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
    use std::path::Path;
    use std::process::ExitStatus;

    fn make_output(code: i32, stdout: &str, stderr: &str) -> Output {
        Output {
            status: exit_status_from_code(code),
            stdout: stdout.as_bytes().to_vec(),
            stderr: stderr.as_bytes().to_vec(),
        }
    }

    fn exit_status_from_code(code: i32) -> ExitStatus {
        #[cfg(unix)]
        {
            use std::os::unix::process::ExitStatusExt;
            ExitStatus::from_raw(code << 8)
        }
        #[cfg(windows)]
        {
            use std::os::windows::process::ExitStatusExt;
            ExitStatus::from_raw(code as u32)
        }
    }

    fn hanging_command() -> Command {
        #[cfg(windows)]
        {
            let mut cmd = Command::new("cmd");
            cmd.args(["/C", "ping", "-n", "30", "127.0.0.1"]);
            cmd
        }
        #[cfg(unix)]
        {
            let mut cmd = Command::new("sleep");
            cmd.arg("30");
            cmd
        }
    }

    fn quick_ok_command() -> Command {
        #[cfg(windows)]
        {
            let mut cmd = Command::new("cmd");
            cmd.args(["/C", "exit", "0"]);
            cmd
        }
        #[cfg(unix)]
        {
            Command::new("true")
        }
    }

    /// Detached grandchild matching `sov daemon start`: new session / process
    /// group so a CLI-tree `kill -KILL -pid` / `taskkill /T` cannot reap it.
    fn spawn_detached_grandchild() -> (u32, std::process::Child) {
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const DETACHED_PROCESS: u32 = 0x0000_0008;
            const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            let child = std::process::Command::new("cmd")
                .args(["/C", "ping", "-n", "30", "127.0.0.1"])
                .creation_flags(DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW)
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("spawn detached grandchild");
            wait_until_alive(child.id());
            (child.id(), child)
        }
        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            let child = std::process::Command::new("sleep")
                .arg("30")
                .process_group(0)
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("spawn detached grandchild");
            wait_until_alive(child.id());
            (child.id(), child)
        }
    }

    fn wait_until_alive(pid: u32) {
        let deadline = std::time::Instant::now() + Duration::from_secs(2);
        while std::time::Instant::now() < deadline && !pid_is_alive(pid) {
            std::thread::sleep(Duration::from_millis(20));
        }
    }

    fn write_handshake(path: &Path, pid: u32) {
        let body = format!(
            r#"{{
            "schema_version": 1,
            "pid": {pid},
            "port": 9,
            "token": "t",
            "network": "testnet",
            "readonly": true,
            "ipc_version": 1,
            "started_iso": "2026-05-01T00:00:00Z"
        }}"#
        );
        std::fs::write(path, body).unwrap();
    }

    /// Best-effort cleanup so a failed assertion does not leak a 30s ping/sleep.
    struct PidGuard(u32);
    impl Drop for PidGuard {
        fn drop(&mut self) {
            kill_pid(self.0);
            kill_process_tree(self.0);
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

    #[test]
    fn subprocess_timeout_fires_before_child_exits() {
        // TAURI-SHELL-B-007 + TAURI-SHELL-C-006: spawn a long-running child
        // with a 250ms wall-clock cap and assert the timeout returns
        // `SubprocessFailed { exit_code: -1, stderr: <recovery sentence> }`
        // well before the child would naturally finish. Cross-platform
        // (F-e8184f29): sleep/true are Unix-only; Windows uses ping/cmd.
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let start = std::time::Instant::now();
        let bound = Duration::from_millis(250);
        let (result, _pid) = runtime.block_on(async {
            let mut cmd = hanging_command();
            run_with_timeout_inner(&mut cmd, bound).await
        });
        let elapsed = start.elapsed();
        match result {
            Err(ShellError::SubprocessFailed { exit_code, stderr }) => {
                assert_eq!(exit_code, -1, "exit code -1 is the timeout discriminator");
                assert!(
                    stderr.contains("did not respond"),
                    "stderr should carry recovery sentence; got: {stderr:?}"
                );
                assert!(
                    stderr.contains("`sov doctor`"),
                    "stderr should name `sov doctor` recovery; got: {stderr:?}"
                );
                assert!(
                    stderr.contains("`sov daemon stop`"),
                    "stderr should name `sov daemon stop` recovery; got: {stderr:?}"
                );
                let expected_secs = bound.as_secs();
                assert!(
                    stderr.contains(&format!("{expected_secs}s")),
                    "stderr should name the bound seconds; got: {stderr:?}"
                );
            }
            other => panic!("expected SubprocessFailed timeout, got {other:?}"),
        }
        assert!(
            elapsed < Duration::from_secs(7),
            "timeout took too long: {elapsed:?}"
        );
    }

    #[test]
    fn subprocess_timeout_exceeds_cli_handshake_wait() {
        // F-029f9c24: Python `_START_HANDSHAKE_TIMEOUT_SECONDS = 10`. The
        // shell bound must be strictly larger so a failed `sov daemon start`
        // can return and `_remove_handshake()` instead of racing SIGKILL.
        assert!(
            SUBPROCESS_TIMEOUT > Duration::from_secs(10),
            "SUBPROCESS_TIMEOUT ({SUBPROCESS_TIMEOUT:?}) must exceed CLI handshake wait (10s)"
        );
    }

    #[test]
    fn subprocess_timeout_kills_detached_handshake_grandchild() {
        // F-029f9c24: replaces the F-a0203bc4 ping/sleep in-group pin. The
        // production start tree detaches the real daemon before waiting on
        // handshake; killing the CLI group leaves that grandchild alive.
        // Drive the start-timeout seam against a detached grandchild named
        // by a temp handshake — both CLI pid and handshake pid must die.
        let tmp = tempfile::TempDir::new().unwrap();
        let handshake = tmp.path().join("daemon.json");

        let (grandchild_pid, _grandchild) = spawn_detached_grandchild();
        let _reap_grandchild = PidGuard(grandchild_pid);
        write_handshake(&handshake, grandchild_pid);
        assert!(
            pid_is_alive(grandchild_pid),
            "fixture grandchild must be alive before the seam"
        );

        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let (result, cli_pid) = runtime.block_on(async {
            let mut cmd = hanging_command();
            run_start_with_timeout_inner(&mut cmd, Duration::from_millis(200), &handshake, None)
                .await
        });
        match result {
            Err(ShellError::SubprocessFailed { exit_code, .. }) => {
                assert_eq!(exit_code, -1);
            }
            other => panic!("expected timeout SubprocessFailed, got {other:?}"),
        }
        let cli_pid = cli_pid.expect("timeout path must report the child pid");

        let deadline = std::time::Instant::now() + Duration::from_secs(3);
        while std::time::Instant::now() < deadline
            && (pid_is_alive(cli_pid) || pid_is_alive(grandchild_pid))
        {
            std::thread::sleep(Duration::from_millis(50));
        }
        assert!(
            !pid_is_alive(cli_pid),
            "CLI child pid {cli_pid} must be dead after timeout kill"
        );
        assert!(
            !pid_is_alive(grandchild_pid),
            "detached handshake pid {grandchild_pid} must be dead after start-timeout reap"
        );
    }

    #[test]
    fn cli_tree_timeout_does_not_reap_detached_grandchild() {
        // Fixture-validity pin for F-029f9c24: a handshake pid outside the
        // CLI process group must survive `run_with_timeout_inner` (tree kill
        // only). If this assertion fails, the grandchild is still in-group
        // and `subprocess_timeout_kills_detached_handshake_grandchild`
        // would go green without exercising handshake reap.
        let tmp = tempfile::TempDir::new().unwrap();
        let handshake = tmp.path().join("daemon.json");

        let (grandchild_pid, _grandchild) = spawn_detached_grandchild();
        let _reap_grandchild = PidGuard(grandchild_pid);
        write_handshake(&handshake, grandchild_pid);

        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let (result, cli_pid) = runtime.block_on(async {
            let mut cmd = hanging_command();
            run_with_timeout_inner(&mut cmd, Duration::from_millis(200)).await
        });
        match result {
            Err(ShellError::SubprocessFailed { exit_code, .. }) => {
                assert_eq!(exit_code, -1);
            }
            other => panic!("expected timeout SubprocessFailed, got {other:?}"),
        }
        let cli_pid = cli_pid.expect("timeout path must report the child pid");

        let deadline = std::time::Instant::now() + Duration::from_secs(3);
        while std::time::Instant::now() < deadline && pid_is_alive(cli_pid) {
            std::thread::sleep(Duration::from_millis(50));
        }
        assert!(
            !pid_is_alive(cli_pid),
            "CLI child pid {cli_pid} must be dead after tree kill"
        );
        assert!(
            pid_is_alive(grandchild_pid),
            "detached handshake pid {grandchild_pid} must still be alive after CLI-tree-only kill"
        );
    }

    #[test]
    fn handshake_reap_skips_preexisting_pid() {
        // Hang-before-spawn must not SIGKILL an external daemon whose
        // handshake we merely observed.
        let tmp = tempfile::TempDir::new().unwrap();
        let handshake = tmp.path().join("daemon.json");
        let (grandchild_pid, _grandchild) = spawn_detached_grandchild();
        let _reap_grandchild = PidGuard(grandchild_pid);
        write_handshake(&handshake, grandchild_pid);

        reap_handshake_daemon_at(&handshake, Some(grandchild_pid));
        assert!(
            pid_is_alive(grandchild_pid),
            "pre-existing handshake pid {grandchild_pid} must not be killed"
        );
    }

    #[test]
    fn subprocess_timeout_message_format_pins_recovery_sentence() {
        // TAURI-SHELL-C-006: pin the recovery-sentence shape independently of
        // the integration test so a future regression that drops the sentence
        // back to a bare token fails here even if the hang binary is missing.
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let bound = Duration::from_secs(10);
        let (result, _pid) = runtime.block_on(async {
            let mut cmd = hanging_command();
            run_with_timeout_inner(&mut cmd, Duration::from_millis(50)).await
        });
        match result {
            Err(ShellError::SubprocessFailed { stderr, .. }) => {
                let _ = bound;
                assert!(
                    stderr.contains("retry"),
                    "stderr should suggest retry; got: {stderr:?}"
                );
            }
            other => panic!("expected SubprocessFailed timeout, got {other:?}"),
        }
    }

    #[test]
    fn subprocess_returns_output_when_under_budget() {
        // Sanity check: a fast command (exits 0 immediately) returns its
        // `Output` cleanly through the wrapper. Pins that the timeout seam
        // doesn't accidentally truncate fast happy-path completions.
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let (result, _pid) = runtime.block_on(async {
            let mut cmd = quick_ok_command();
            run_with_timeout_inner(&mut cmd, Duration::from_secs(5)).await
        });
        let output = result.expect("quick command should succeed under 5s budget");
        assert!(output.status.success());
    }

    #[test]
    fn subprocess_cwd_is_discovered_project_root() {
        // F-0a0c970a: daemon subprocesses inherit the discovered player
        // root, not the Tauri binary CWD.
        let cwd = config::subprocess_cwd();
        let handshake = config::default_config_path();
        assert_eq!(handshake, cwd.join(".sov").join("daemon.json"));
    }
}

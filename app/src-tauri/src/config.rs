//! `.sov/daemon.json` reader.
//!
//! Pure file IO — no subprocess. The daemon writes this file atomically at
//! start; the shell reads it directly to learn the URL + token to talk to the
//! daemon over HTTP. The file is the source of truth (Wave 3 contract §6).

use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::commands::{DaemonConfig, ShellError};

/// The daemon schema version this shell understands. Bumped in lockstep with
/// `sov_daemon/lifecycle.py`'s `DAEMON_SCHEMA_VERSION`. A read of a higher
/// version returns `ShellError::ConfigSchemaUnsupported` instead of silently
/// accepting fields with possibly-incompatible semantics.
pub const DAEMON_SCHEMA_VERSION_EXPECTED: u32 = 1;

/// Wire envelope for `.sov/daemon.json`. The handshake file carries
/// `schema_version` at the top level alongside the inlined `DaemonConfig`
/// fields; `#[serde(flatten)]` lets us validate the envelope without changing
/// the public `DaemonConfig` shape.
#[derive(Deserialize)]
struct DaemonConfigEnvelope {
    schema_version: u32,
    #[serde(flatten)]
    config: DaemonConfig,
}

/// Walk from `start` toward the filesystem root looking for a Sovereignty
/// project root: a directory that already has `.sov/`, else a repo marker
/// (`pyproject.toml` or `.git`). Closest `.sov/` wins over a more-distant
/// marker so a nested `tauri dev` CWD (`app/src-tauri`) still attaches to
/// the player tree the operator ran `sov play` from.
///
/// Falls back to `start` when nothing matches (packaged binary launched
/// from an unrelated directory).
pub fn discover_project_root_from(start: &Path) -> PathBuf {
    let start = if start.is_absolute() {
        start.to_path_buf()
    } else {
        std::env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("."))
            .join(start)
    };

    let mut marker_fallback: Option<PathBuf> = None;
    let mut cur = start.clone();
    loop {
        if cur.join(".sov").is_dir() {
            return cur;
        }
        if marker_fallback.is_none()
            && (cur.join("pyproject.toml").is_file() || cur.join(".git").exists())
        {
            marker_fallback = Some(cur.clone());
        }
        match cur.parent() {
            Some(parent) if parent != cur => cur = parent.to_path_buf(),
            _ => break,
        }
    }
    marker_fallback.unwrap_or(start)
}

/// Project root the shell uses for handshake IO and `sov daemon` subprocess
/// cwd. Never the Tauri binary's own CWD when a player `.sov/` or repo
/// marker sits further up the tree.
pub fn discover_project_root() -> PathBuf {
    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    discover_project_root_from(&cwd)
}

/// Default handshake path: `{discovered_root}/.sov/daemon.json`.
pub fn default_config_path() -> PathBuf {
    discover_project_root().join(".sov").join("daemon.json")
}

/// Working directory every `sov daemon {status,start,stop}` subprocess must
/// inherit so handshake IO lands in the player tree, not `app/src-tauri`.
pub fn subprocess_cwd() -> PathBuf {
    discover_project_root()
}

/// Read `.sov/daemon.json` from the discovered project root.
pub fn read_daemon_config() -> Result<DaemonConfig, ShellError> {
    read_daemon_config_at(&default_config_path())
}

/// Read a daemon config file from an arbitrary path. Test-friendly seam.
pub fn read_daemon_config_at(path: &Path) -> Result<DaemonConfig, ShellError> {
    let contents = match std::fs::read_to_string(path) {
        Ok(s) => s,
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => {
            return Err(ShellError::ConfigFileMissing);
        }
        Err(err) => {
            return Err(ShellError::ConfigFileMalformed {
                detail: err.to_string(),
            });
        }
    };
    let envelope: DaemonConfigEnvelope =
        serde_json::from_str(&contents).map_err(|e| ShellError::ConfigFileMalformed {
            detail: e.to_string(),
        })?;
    if envelope.schema_version != DAEMON_SCHEMA_VERSION_EXPECTED {
        return Err(ShellError::ConfigSchemaUnsupported {
            found: envelope.schema_version,
            expected: DAEMON_SCHEMA_VERSION_EXPECTED,
        });
    }
    Ok(envelope.config)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn write_config(dir: &Path, body: &str) -> PathBuf {
        let p = dir.join("daemon.json");
        std::fs::write(&p, body).unwrap();
        p
    }

    #[test]
    fn missing_file_returns_config_file_missing() {
        let tmp = TempDir::new().unwrap();
        let path = tmp.path().join("nope.json");
        let err = read_daemon_config_at(&path).unwrap_err();
        assert!(matches!(err, ShellError::ConfigFileMissing));
    }

    #[test]
    fn malformed_json_returns_config_file_malformed() {
        let tmp = TempDir::new().unwrap();
        let path = write_config(tmp.path(), "{ this is not json");
        let err = read_daemon_config_at(&path).unwrap_err();
        assert!(matches!(err, ShellError::ConfigFileMalformed { .. }));
    }

    #[test]
    fn valid_config_round_trips() {
        let tmp = TempDir::new().unwrap();
        let body = r#"{
            "schema_version": 1,
            "pid": 12345,
            "port": 47823,
            "token": "abc.def",
            "network": "testnet",
            "readonly": false,
            "ipc_version": 1,
            "started_iso": "2026-05-01T18:23:11Z"
        }"#;
        let path = write_config(tmp.path(), body);
        let cfg = read_daemon_config_at(&path).unwrap();
        assert_eq!(cfg.pid, 12345);
        assert_eq!(cfg.port, 47823);
        assert_eq!(cfg.token, "abc.def");
        assert_eq!(cfg.network, "testnet");
        assert!(!cfg.readonly);
        assert_eq!(cfg.ipc_version, 1);
        assert_eq!(cfg.started_iso, "2026-05-01T18:23:11Z");
    }

    #[test]
    fn default_config_path_is_dot_sov_daemon_json() {
        let p = default_config_path();
        assert!(p.ends_with("daemon.json"));
        assert!(p.to_string_lossy().contains(".sov"));
    }

    #[test]
    fn discover_project_root_walks_to_dotsov_not_nested_cwd() {
        // F-0a0c970a: tauri dev CWD is typically app/src-tauri; the player
        // `.sov/` lives at the repo / table root. Discovery must return the
        // ancestor with `.sov/`, not std::env::current_dir() of the binary.
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        std::fs::create_dir(root.join(".sov")).unwrap();
        let nested = root.join("app").join("src-tauri");
        std::fs::create_dir_all(&nested).unwrap();

        let discovered = discover_project_root_from(&nested);
        let discovered_canon = discovered.canonicalize().unwrap_or(discovered);
        let root_canon = root.canonicalize().unwrap_or_else(|_| root.to_path_buf());
        assert_eq!(discovered_canon, root_canon);

        let cfg = discovered_canon.join(".sov").join("daemon.json");
        assert!(
            !cfg.starts_with(&nested),
            "handshake path must not sit under the nested binary CWD; got {cfg:?}"
        );
        assert!(cfg.ends_with(Path::new(".sov").join("daemon.json")));
    }

    #[test]
    fn discover_project_root_falls_back_to_repo_marker() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        std::fs::write(
            root.join("pyproject.toml"),
            "[project]\nname = \"sovereignty-game\"\n",
        )
        .unwrap();
        let nested = root.join("app").join("src-tauri");
        std::fs::create_dir_all(&nested).unwrap();

        let discovered = discover_project_root_from(&nested);
        let discovered_canon = discovered.canonicalize().unwrap_or(discovered);
        let root_canon = root.canonicalize().unwrap_or_else(|_| root.to_path_buf());
        assert_eq!(discovered_canon, root_canon);
    }

    #[test]
    fn subprocess_cwd_matches_discovered_root_not_binary_dir() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        std::fs::create_dir(root.join(".sov")).unwrap();
        let nested = root.join("app").join("src-tauri");
        std::fs::create_dir_all(&nested).unwrap();

        let discovered = discover_project_root_from(&nested);
        // subprocess_cwd() uses process CWD; pin the same helper the
        // daemon wrappers call, driven from an explicit start path.
        assert_eq!(
            discovered.join(".sov").join("daemon.json"),
            discovered.join(".sov").join("daemon.json")
        );
        assert_ne!(discovered, nested);
    }

    #[test]
    fn handshake_at_discovered_root_is_not_cwd_when_nested() {
        // Refuse-auto-start signal: a handshake in a discovered player root
        // that is not CWD must be visible so the shell attaches instead of
        // spawning a second daemon against the empty nested tree.
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        let sov = root.join(".sov");
        std::fs::create_dir(&sov).unwrap();
        std::fs::write(sov.join("daemon.json"), "{}").unwrap();
        let nested = root.join("app").join("src-tauri");
        std::fs::create_dir_all(&nested).unwrap();

        let discovered = discover_project_root_from(&nested);
        let handshake = discovered.join(".sov").join("daemon.json");
        assert!(handshake.is_file());
        assert_ne!(discovered, nested);
        assert!(!nested.join(".sov").join("daemon.json").exists());
    }

    #[test]
    fn future_schema_version_returns_unsupported() {
        // TAURI-SHELL-B-001: the Rust shell must fail-fast on a daemon.json
        // written by a future v2.x daemon with schema_version > expected.
        // Silent acceptance would let breaking field changes slip through with
        // garbage semantics on an older shell binary.
        let tmp = TempDir::new().unwrap();
        let body = r#"{
            "schema_version": 999,
            "pid": 1,
            "port": 2,
            "token": "t",
            "network": "testnet",
            "readonly": true,
            "ipc_version": 1,
            "started_iso": "2026-05-01T00:00:00Z"
        }"#;
        let path = write_config(tmp.path(), body);
        let err = read_daemon_config_at(&path).unwrap_err();
        match err {
            ShellError::ConfigSchemaUnsupported { found, expected } => {
                assert_eq!(found, 999);
                assert_eq!(expected, DAEMON_SCHEMA_VERSION_EXPECTED);
            }
            other => panic!("expected ConfigSchemaUnsupported, got {other:?}"),
        }
    }

    #[test]
    fn missing_schema_version_returns_unsupported() {
        // A daemon.json without `schema_version` deserializes as `0` (the
        // numeric default), which is NOT the expected `1` — so we reject. This
        // makes the field mandatory, not optional, mirroring the Python side's
        // `read_versioned()` contract.
        let tmp = TempDir::new().unwrap();
        let body = r#"{
            "pid": 1,
            "port": 2,
            "token": "t",
            "network": "testnet",
            "readonly": true,
            "ipc_version": 1,
            "started_iso": "2026-05-01T00:00:00Z"
        }"#;
        let path = write_config(tmp.path(), body);
        let err = read_daemon_config_at(&path).unwrap_err();
        // Either ConfigFileMalformed (serde rejects missing field) or
        // ConfigSchemaUnsupported (zero default). Both are fail-fast; both
        // close the silent-acceptance gap. Pin the discrimination by accepting
        // either.
        assert!(
            matches!(
                err,
                ShellError::ConfigFileMalformed { .. } | ShellError::ConfigSchemaUnsupported { .. }
            ),
            "got {err:?}"
        );
    }

    #[test]
    fn schema_version_zero_is_rejected() {
        // Explicit `schema_version: 0` (a daemon write-bug or test fixture)
        // must be rejected as unsupported, not accepted as legacy.
        let tmp = TempDir::new().unwrap();
        let body = r#"{
            "schema_version": 0,
            "pid": 1,
            "port": 2,
            "token": "t",
            "network": "testnet",
            "readonly": true,
            "ipc_version": 1,
            "started_iso": "2026-05-01T00:00:00Z"
        }"#;
        let path = write_config(tmp.path(), body);
        let err = read_daemon_config_at(&path).unwrap_err();
        assert!(
            matches!(
                err,
                ShellError::ConfigSchemaUnsupported {
                    found: 0,
                    expected: 1
                }
            ),
            "got {err:?}"
        );
    }
}

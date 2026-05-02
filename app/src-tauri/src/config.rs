//! `.sov/daemon.json` reader.
//!
//! Pure file IO — no subprocess. The daemon writes this file atomically at
//! start; the shell reads it directly to learn the URL + token to talk to the
//! daemon over HTTP. The file is the source of truth (Wave 3 contract §6).

use std::path::{Path, PathBuf};

use crate::commands::{DaemonConfig, ShellError};

/// Default location relative to the current working directory.
pub fn default_config_path() -> PathBuf {
    PathBuf::from(".sov").join("daemon.json")
}

/// Read `.sov/daemon.json` from the default location (CWD-relative).
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
    serde_json::from_str::<DaemonConfig>(&contents).map_err(|e| ShellError::ConfigFileMalformed {
        detail: e.to_string(),
    })
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
}

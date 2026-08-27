"""JOB-029: Tauri updater wiring uses repo secrets by name; no private keys in git.

Never print, log, or assert by dumping private-key or password values.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLISH = ROOT / ".github" / "workflows" / "publish.yml"
TAURI_CONF = ROOT / "app" / "src-tauri" / "tauri.conf.json"
SECURITY = ROOT / "SECURITY.md"
CARGO_TOML = ROOT / "app" / "src-tauri" / "Cargo.toml"
PACKAGE_JSON = ROOT / "app" / "package.json"

# Public minisign key (safe to commit). Private key/password stay in GH secrets.
_PUBKEY = (
    "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDNBQzQ1Q0FEN0I5OUIwRDUK"
    "UldUVnNKbDdyVnpFT2poenlLZEZtOG00cnpmb2dEU2VUMXFyYnhGYjE1RDExMTBiV05hRFE2ZGoK"
)

_SECRET_NAMES = (
    "TAURI_SIGNING_PRIVATE_KEY",
    "TAURI_SIGNING_PRIVATE_KEY_PASSWORD",
)

_SKIP_DIRS = {
    ".git",
    "node_modules",
    "target",
    "__pycache__",
    ".venv",
    "dist",
    "gen",
}


def test_tauri_conf_has_updater_pubkey() -> None:
    conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    updater = conf["plugins"]["updater"]
    assert updater["pubkey"] == _PUBKEY
    assert conf["bundle"]["createUpdaterArtifacts"] is True
    endpoints = updater["endpoints"]
    assert any("releases/latest/download/latest.json" in e for e in endpoints)


def test_publish_yml_injects_secret_names_not_values() -> None:
    text = PUBLISH.read_text(encoding="utf-8")
    assert "secrets.TAURI_SIGNING_PRIVATE_KEY" in text
    assert "secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD" in text
    for name in _SECRET_NAMES:
        needle = "${{ secrets." + name + " }}"
        assert needle in text, "publish.yml must reference secret by name"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("TAURI_SIGNING_PRIVATE_KEY:"):
            assert "secrets.TAURI_SIGNING_PRIVATE_KEY" in stripped
        if stripped.startswith("TAURI_SIGNING_PRIVATE_KEY_PASSWORD:"):
            assert "secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD" in stripped


def test_security_md_documents_secret_names_only() -> None:
    text = SECURITY.read_text(encoding="utf-8")
    for name in _SECRET_NAMES:
        assert name in text
    assert "plugins.updater.pubkey" in text or "tauri.conf.json" in text


def test_updater_plugin_is_the_only_new_native_updater_dep() -> None:
    cargo = CARGO_TOML.read_text(encoding="utf-8")
    pkg = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    assert 'tauri-plugin-updater = "2"' in cargo
    assert "@tauri-apps/plugin-updater" in pkg["dependencies"]
    assert "tauri-plugin-process" not in cargo
    assert "@tauri-apps/plugin-process" not in pkg.get("dependencies", {})
    assert "@tauri-apps/plugin-process" not in pkg.get("devDependencies", {})


def test_repo_has_no_minisign_secret_file_header() -> None:
    marker = b"untrusted comment: " + b"minisign" + b" secret key"
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if marker in data.lower():
            hits.append(str(path.relative_to(ROOT)))
    assert hits == [], "committed tree must not include a minisign secret file"

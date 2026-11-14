"""The desktop app's Tauri crates and npm packages stay on one major.minor.

`tauri build` refuses to build when they differ ("Found version mismatched
Tauri packages"). CI's Tauri job runs cargo check, clippy and cargo test, never
`tauri build`, so that refusal was first seen in the v2.4.0 release run: the
`tauri` crate was 2.11.0 and `@tauri-apps/api` was 2.12.3, and no desktop
bundles were built. This test makes the same comparison from the two lock files
on every pull request.

Pairs: the `tauri` crate with `@tauri-apps/api`, and each `tauri-plugin-<name>`
crate with `@tauri-apps/plugin-<name>` when both are present.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CARGO_LOCK = ROOT / "app" / "src-tauri" / "Cargo.lock"
NPM_LOCK = ROOT / "app" / "package-lock.json"

_PACKAGE = re.compile(r'^\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"', re.M)


def _crates(text: str) -> dict[str, str]:
    return {name: version for name, version in _PACKAGE.findall(text.replace("\r\n", "\n"))}


def _npm_tauri(text: str) -> dict[str, str]:
    packages = json.loads(text)["packages"]
    prefix = "node_modules/@tauri-apps/"
    return {
        key[len(prefix) :]: str(value["version"])
        for key, value in packages.items()
        if key.startswith(prefix) and "/" not in key[len(prefix) :] and "version" in value
    }


def pairs(cargo_lock: str, npm_lock: str) -> list[tuple[str, str, str, str]]:
    """(crate, crate version, npm package, npm version) for every pair present."""
    crates = _crates(cargo_lock)
    npm = _npm_tauri(npm_lock)
    found = []
    if "tauri" in crates and "api" in npm:
        found.append(("tauri", crates["tauri"], "@tauri-apps/api", npm["api"]))
    for crate, version in sorted(crates.items()):
        if crate.startswith("tauri-plugin-"):
            plugin = "plugin-" + crate[len("tauri-plugin-") :]
            if plugin in npm:
                found.append((crate, version, f"@tauri-apps/{plugin}", npm[plugin]))
    return found


def _major_minor(version: str) -> tuple[str, str]:
    major, minor = version.split(".")[:2]
    return major, minor


def mismatches(cargo_lock: str, npm_lock: str) -> list[str]:
    return [
        f"{crate} ({cv}) : {pkg} ({pv})"
        for crate, cv, pkg, pv in pairs(cargo_lock, npm_lock)
        if _major_minor(cv) != _major_minor(pv)
    ]


def test_tauri_crates_and_npm_packages_share_major_minor() -> None:
    found = mismatches(CARGO_LOCK.read_text(encoding="utf-8"), NPM_LOCK.read_text(encoding="utf-8"))
    assert not found, "`tauri build` will refuse these (same major/minor needed): " + "; ".join(
        found
    )


def test_the_core_pair_is_checked() -> None:
    """The check is not vacuous: the core pair is found in today's lock files."""
    found = pairs(CARGO_LOCK.read_text(encoding="utf-8"), NPM_LOCK.read_text(encoding="utf-8"))
    assert ("tauri", "@tauri-apps/api") in {(c, p) for c, _, p, _ in found}


_CARGO = """# lock
[[package]]
name = "tauri"
version = "{tauri}"
source = "registry+https://github.com/rust-lang/crates.io-index"

[[package]]
name = "tauri-plugin-updater"
version = "2.10.1"

[[package]]
name = "tauri-plugin-shell"
version = "2.3.5"
"""


def _npm(api: str) -> str:
    return json.dumps(
        {
            "packages": {
                "": {"name": "app"},
                "node_modules/@tauri-apps/api": {"version": api},
                "node_modules/@tauri-apps/plugin-updater": {"version": "2.10.1"},
                "node_modules/@tauri-apps/cli": {"version": "2.11.4"},
                "node_modules/@tauri-apps/cli-win32-x64-msvc": {"version": "2.11.4"},
                "node_modules/@tauri-apps/api/node_modules/x": {"version": "9.9.9"},
            }
        }
    )


@pytest.mark.parametrize(
    ("tauri", "api", "expected"),
    [
        ("2.11.0", "2.12.3", ["tauri (2.11.0) : @tauri-apps/api (2.12.3)"]),  # the v2.4.0 failure
        ("2.12.5", "2.12.3", []),  # patch levels may differ
        ("2.12.5", "3.0.0", ["tauri (2.12.5) : @tauri-apps/api (3.0.0)"]),
    ],
)
def test_the_comparison(tauri: str, api: str, expected: list[str]) -> None:
    assert mismatches(_CARGO.format(tauri=tauri), _npm(api)) == expected


def test_plugins_are_paired_and_unpaired_crates_are_skipped() -> None:
    found = pairs(_CARGO.format(tauri="2.12.5"), _npm("2.12.3"))
    assert [(c, p) for c, _, p, _ in found] == [
        ("tauri", "@tauri-apps/api"),
        ("tauri-plugin-updater", "@tauri-apps/plugin-updater"),
    ]

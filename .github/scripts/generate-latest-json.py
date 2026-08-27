#!/usr/bin/env python3
"""Build Tauri updater latest.json from staged sovereignty-app-* artifacts."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _read_sig(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _pick_payload(artifacts: Path, names: tuple[str, ...]) -> tuple[Path, Path] | None:
    for name in names:
        payload = artifacts / name
        sig = artifacts / f"{name}.sig"
        if payload.is_file() and sig.is_file():
            return payload, sig
    return None


def generate_latest_json(
    artifacts: Path,
    *,
    version: str,
    tag: str,
    repo: str,
    pub_date: str | None = None,
) -> Path | None:
    version = version.removeprefix("v")
    tag = tag if tag.startswith("v") else f"v{tag}"
    base = f"https://github.com/{repo}/releases/download/{tag}"
    if pub_date is None:
        pub_date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    platforms: dict[str, dict[str, str]] = {}

    mac = _pick_payload(
        artifacts,
        (f"sovereignty-app-{version}-darwin-universal.app.tar.gz",),
    )
    if mac is not None:
        payload, sig = mac
        entry = {"signature": _read_sig(sig), "url": f"{base}/{payload.name}"}
        platforms["darwin-aarch64"] = entry
        platforms["darwin-x86_64"] = entry
        platforms["darwin-universal"] = entry

    linux = _pick_payload(
        artifacts,
        (
            f"sovereignty-app-{version}-linux-x64.AppImage.tar.gz",
            f"sovereignty-app-{version}-linux-x64.AppImage",
        ),
    )
    if linux is not None:
        payload, sig = linux
        platforms["linux-x86_64"] = {
            "signature": _read_sig(sig),
            "url": f"{base}/{payload.name}",
        }

    windows = _pick_payload(
        artifacts,
        (
            f"sovereignty-app-{version}-win-x64.nsis.zip",
            f"sovereignty-app-{version}-win-x64.msi.zip",
            f"sovereignty-app-{version}-win-x64.msi",
            f"sovereignty-app-{version}-win-x64.exe",
        ),
    )
    if windows is not None:
        payload, sig = windows
        platforms["windows-x86_64"] = {
            "signature": _read_sig(sig),
            "url": f"{base}/{payload.name}",
        }

    if not platforms:
        sigs = list(artifacts.glob("*.sig"))
        if sigs:
            print(
                "::error::.sig files present but no matching updater payload/sig pair",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print("::warning::no updater payloads; skipping latest.json", file=sys.stderr)
        return None

    doc = {
        "version": version,
        "notes": "See the GitHub release notes for this tag.",
        "pub_date": pub_date,
        "platforms": platforms,
    }
    out = artifacts / "latest.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} with platforms: {', '.join(sorted(platforms))}")
    return out


def main() -> int:
    artifacts = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    version = os.environ.get("VERSION", "")
    tag = os.environ.get("RELEASE_TAG", version)
    repo = os.environ.get("GITHUB_REPOSITORY", "mcp-tool-shop-org/sovereignty")
    if not version:
        print("::error::VERSION env is required", file=sys.stderr)
        return 1
    generate_latest_json(artifacts, version=version, tag=tag or version, repo=repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

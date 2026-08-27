#!/usr/bin/env python3
"""Static pins for .github/workflows/publish.yml Stage artifact + updater globs.

Renders each matrix.artifacts value into a for-loop and bash -n's it so a
YAML `|` newline cannot reach production again (F-04ad0b5c / F-464db793).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLISH = ROOT / ".github" / "workflows" / "publish.yml"
STAGE_SH = ROOT / ".github" / "scripts" / "stage-tauri-artifacts.sh"
LATEST_PY = ROOT / ".github" / "scripts" / "generate-latest-json.py"


def _bash() -> str:
    found = shutil.which("bash")
    if found:
        return found
    for candidate in (
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("bash not found; cannot bash -n Stage artifact scripts")


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def extract_artifacts_values(text: str) -> list[str]:
    if re.search(r"^\s+artifacts:\s*[|>]", text, re.M):
        _fail("matrix.artifacts must be a single-line scalar, not a YAML | or > block")
    values = [m.group(1).strip().strip("\"'") for m in re.finditer(r"^\s+artifacts:\s*(.+)$", text, re.M)]
    if not values:
        _fail("no matrix.artifacts values found")
    for value in values:
        if "\n" in value or "\r" in value:
            _fail(f"artifacts value contains a newline: {value!r}")
    return values


def main() -> int:
    text = PUBLISH.read_text(encoding="utf-8")
    bash = _bash()

    if "for glob in ${{ matrix.artifacts }}" in text:
        _fail("Stage artifact still interpolates ${{ matrix.artifacts }} unquoted into for-loop")
    if "ARTIFACT_GLOBS:" not in text or "stage-tauri-artifacts.sh" not in text:
        _fail("Stage artifact must bind globs to ARTIFACT_GLOBS and call stage-tauri-artifacts.sh")
    if "latest.json" not in text or "generate-latest-json.py" not in text:
        _fail("publish.yml must generate latest.json from staged updater artifacts")

    def bash_n(script: str, label: str) -> None:
        # Binary stdin so Windows text-mode pipes cannot inject CR into bash -n.
        proc = subprocess.run(
            [bash, "-n", "-"],
            input=script.encode("utf-8"),
            capture_output=True,
        )
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", "replace")
            _fail(f"bash -n {label} failed:\n{err}")

    bash_n(STAGE_SH.read_text(encoding="utf-8"), "stage-tauri-artifacts.sh")

    compile_proc = subprocess.run(
        [sys.executable, "-m", "py_compile", str(LATEST_PY)],
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        _fail(f"py_compile generate-latest-json.py failed:\n{compile_proc.stderr}")

    values = extract_artifacts_values(text)
    joined = "\n".join(values)

    def has(*needles: str) -> bool:
        return all(n in joined for n in needles)

    if not has("macos/Sovereignty.app.tar.gz", ".app.tar.gz.sig"):
        _fail(f"mac artifacts must include updater tar.gz + .sig; got {values!r}")
    if not has(".msi.sig"):
        _fail(f"win artifacts must include .msi.sig; got {values!r}")
    if not has("deb/*_amd64.deb", "appimage/*_amd64.AppImage"):
        _fail(f"linux artifacts must include .deb and .AppImage; got {values!r}")

    loop_template = """set -euo pipefail
for glob in %s; do
  echo "$glob"
done
"""
    for value in values:
        rendered = loop_template % value
        bash_n(rendered, f"rendered Stage loop artifacts={value!r}")

    # Pin job graph: PyPI/CLI must not wait on Tauri (F-bd71a354).
    publish_block = re.search(r"^  publish:\n((?:    .*\n)+)", text, re.M)
    if not publish_block or "needs: [build-binaries]" not in publish_block.group(0):
        _fail("publish job must needs: [build-binaries] only")
    if re.search(r"^  publish:.*?needs: \[build-binaries, build-tauri-binaries\]", text, re.S):
        _fail("publish still needs build-tauri-binaries")

    if "cancel-in-progress: true" in text.split("jobs:")[0]:
        _fail("publish.yml concurrency must not cancel-in-progress")

    if "libfuse2t64" not in text or "patchelf" not in text or "librsvg2-dev" not in text:
        _fail("Linux bundler package set (file/patchelf/libfuse2t64/librsvg2) missing")

    # workflow_dispatch must be able to run jobs on a v* tag (F-830579dd).
    if "workflow_dispatch" not in text:
        _fail("workflow_dispatch trigger missing")
    if text.count("github.event_name == 'release'") >= 4 and "workflow_dispatch" in text:
        # Every job used to be release-only; require the dispatch clause.
        if "startsWith(github.ref, 'refs/tags/v')" not in text:
            _fail("jobs must run on workflow_dispatch when github.ref is a v* tag")

    # Smoke generate-latest-json.py against compound extensions.
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        (tdir / "sovereignty-app-2.3.0-darwin-universal.app.tar.gz").write_bytes(b"mac")
        (tdir / "sovereignty-app-2.3.0-darwin-universal.app.tar.gz.sig").write_text(
            "macsig\n", encoding="utf-8"
        )
        (tdir / "sovereignty-app-2.3.0-win-x64.msi").write_bytes(b"msi")
        (tdir / "sovereignty-app-2.3.0-win-x64.msi.sig").write_text("winsig\n", encoding="utf-8")
        (tdir / "sovereignty-app-2.3.0-linux-x64.AppImage.tar.gz").write_bytes(b"app")
        (tdir / "sovereignty-app-2.3.0-linux-x64.AppImage.tar.gz.sig").write_text(
            "linuxsig\n", encoding="utf-8"
        )
        env = os.environ.copy()
        env["VERSION"] = "2.3.0"
        env["RELEASE_TAG"] = "v2.3.0"
        env["GITHUB_REPOSITORY"] = "mcp-tool-shop-org/sovereignty"
        proc = subprocess.run(
            [sys.executable, str(LATEST_PY), str(tdir)],
            env=env,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            _fail(f"generate-latest-json.py smoke failed:\n{proc.stderr}\n{proc.stdout}")
        doc = json.loads((tdir / "latest.json").read_text(encoding="utf-8"))
        for key in ("darwin-aarch64", "darwin-x86_64", "linux-x86_64", "windows-x86_64"):
            if key not in doc.get("platforms", {}):
                _fail(f"latest.json missing platform {key}")
        mac_url = doc["platforms"]["darwin-aarch64"]["url"]
        if not mac_url.endswith(".app.tar.gz"):
            _fail(f"mac updater url must keep compound suffix, got {mac_url}")

    print(f"OK: {len(values)} artifacts values, Stage script, latest.json generator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
inline-fonts.py — inline local @font-face files as base64 data URIs.

Produces a self-contained render copy of the print HTML with zero network
dependencies at print time (fonts + already-vendored React + precompiled
bundle). Google Fonts is no longer fetched; faces live in source/fonts/.

Usage:
    python3 inline-fonts.py "Sovereignty Print Pack - print.html"
    # writes "Sovereignty Print Pack - print.RENDER.html" alongside

The generated *.RENDER.html should NOT be committed — it is large because of
base64 fonts. Re-run any time fonts.css or the HTML font <link> changes.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

MIME = {
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


def _inline_url(raw: str, base: Path) -> str | None:
    if raw.startswith("data:"):
        return None
    cleaned = raw.strip().strip("\"'")
    path = Path(cleaned)
    if not path.is_absolute():
        path = (base / path).resolve()
    if not path.is_file():
        return None
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    return f"url(data:{mime};base64,{b64})"


def inline_local_urls(text: str, base: Path) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        replacement = _inline_url(match.group(1), base)
        if replacement is None:
            return match.group(0)
        count += 1
        return replacement

    patched = re.sub(r"url\(\s*([^)]+?)\s*\)", repl, text)
    return patched, count


def inline_local_images(html: str, base: Path) -> str:
    """Replace relative img src=logo.png with a data URI so the RENDER copy is self-contained."""

    def repl(match: re.Match[str]) -> str:
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        if src.startswith("data:") or src.startswith("http"):
            return match.group(0)
        path = (base / src).resolve()
        if not path.is_file():
            return match.group(0)
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
        }.get(path.suffix.lower(), "application/octet-stream")
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        print(f"inlined image {src} ({path.stat().st_size} bytes)", file=sys.stderr)
        return f"{prefix}data:{mime};base64,{b64}{suffix}"

    return re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)(")', repl, html)


def inline_linked_stylesheets(html: str, base: Path) -> str:
    """Replace <link rel=stylesheet href="fonts.css"> with inlined <style>."""

    def repl(match: re.Match[str]) -> str:
        href = match.group(1)
        sheet = (base / href).resolve()
        if not sheet.is_file():
            return match.group(0)
        css = sheet.read_text(encoding="utf-8")
        css, n = inline_local_urls(css, sheet.parent)
        print(f"inlined {n} font url(s) from {href}", file=sys.stderr)
        return f"<style>\n{css}\n</style>"

    return re.sub(
        r'<link\s+rel="stylesheet"\s+href="([^"]+\.css)"\s*/?>',
        repl,
        html,
        count=1,
    )


def main(html_path: str) -> None:
    src = Path(html_path)
    html = src.read_text(encoding="utf-8")
    patched = inline_linked_stylesheets(html, src.parent)
    patched = inline_local_images(patched, src.parent)
    patched, leftover = inline_local_urls(patched, src.parent)
    if leftover:
        print(f"inlined {leftover} additional local url(s)", file=sys.stderr)
    if "fonts.googleapis.com" in patched or "fonts.gstatic.com" in patched:
        print(
            "ERROR: Google Fonts URL still present — print HTML must use local fonts.css",
            file=sys.stderr,
        )
        sys.exit(1)
    if "unpkg.com" in patched:
        print(
            "ERROR: unpkg URL still present — print HTML must use vendor/ React",
            file=sys.stderr,
        )
        sys.exit(1)
    out = (
        src.with_name(src.stem + ".RENDER.html")
        if src.name.endswith(".html")
        else Path(str(src) + ".RENDER.html")
    )
    out.write_text(patched, encoding="utf-8")
    print(f"wrote {out} ({len(html):,} -> {len(patched):,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])

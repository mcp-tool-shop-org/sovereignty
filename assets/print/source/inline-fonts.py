#!/usr/bin/env python3
"""
inline-fonts.py — fetch Google Fonts CSS + inline woff2 as base64 data URIs.

Used to produce a self-contained render copy of "Sovereignty Print Pack - print.html"
that has zero network dependencies at print time. This eliminates the font-load
race condition where headless Chromium prints before Google Fonts arrive.

Usage:
    python3 inline-fonts.py "Sovereignty Print Pack - print.html"
    # writes "Sovereignty Print Pack - print.RENDER.html" alongside

The generated *.RENDER.html should NOT be committed — it's ~1.5MB of base64 fonts.
Re-run any time the source HTML's <link href="...fonts.googleapis.com..."> changes.
"""
import base64
import re
import sys
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)


def main(html_path: str) -> None:
    src = Path(html_path)
    html = src.read_text()

    url_match = re.search(r'(https://fonts\.googleapis\.com/css2\?[^"]+)', html)
    if not url_match:
        print(f"ERROR: no fonts.googleapis.com URL in {src}", file=sys.stderr)
        sys.exit(1)
    fonts_css_url = url_match.group(1)
    print(f"fetching {fonts_css_url}", file=sys.stderr)

    req = urllib.request.Request(fonts_css_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        css_text = r.read().decode("utf-8")

    woff2 = list(dict.fromkeys(re.findall(r"url\((https://[^)]+\.woff2)\)", css_text)))
    print(f"unique woff2 files: {len(woff2)}", file=sys.stderr)

    inlined = css_text
    for u in woff2:
        fr = urllib.request.Request(u, headers={"User-Agent": UA})
        with urllib.request.urlopen(fr, timeout=30) as r:
            data = r.read()
        b64 = base64.b64encode(data).decode("ascii")
        inlined = inlined.replace(u, f"data:font/woff2;base64,{b64}")

    # Replace the <link> + adjacent preconnects with an inline <style>.
    patched = re.sub(
        r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*'
        r'<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\s*'
        r'<link href="https://fonts\.googleapis\.com/css2[^"]*" rel="stylesheet">'
        r'|<link href="https://fonts\.googleapis\.com/css2[^"]*" rel="stylesheet">',
        f"<style>\n{inlined}\n</style>",
        html,
        count=1,
    )
    if patched == html:
        print("ERROR: failed to patch HTML — preconnect/stylesheet pattern not found", file=sys.stderr)
        sys.exit(2)

    out = src.with_suffix(".RENDER.html") if src.suffix == ".html" else Path(str(src) + ".RENDER.html")
    # If src has spaces / no nice .html replace, place RENDER before extension
    if src.name.endswith(".html"):
        out = src.with_name(src.stem + ".RENDER.html")
    out.write_text(patched)
    print(f"wrote {out} ({len(html):,} -> {len(patched):,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])

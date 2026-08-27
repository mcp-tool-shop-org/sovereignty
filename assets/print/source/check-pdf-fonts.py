#!/usr/bin/env python3
"""Fail if shipped print PDFs embed Type3 display fonts or system fallbacks.

Allowlist (subset prefix stripped): Cormorant Garamond, IM Fell English,
JetBrains Mono, ZapfDingbats. Type3 on any of the three display faces is a
hard fail — those must subset as Type0.

    python3 check-pdf-fonts.py [pdf ...]
    # default: ../pdf/*.pdf
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader

SOURCE = Path(__file__).resolve().parent
DEFAULT_PDFS = sorted((SOURCE.parent / "pdf").glob("*.pdf"))

ALLOW = (
    "cormorantgaramond",
    "imfellenglish",
    "jetbrainsmono",
    "zapfdingbats",
)
DISPLAY = ("cormorantgaramond", "imfellenglish", "jetbrainsmono")
FORBIDDEN = ("georgia", "times", "lucida", "menlo", "arial", "helvetica", "calibri")


def _norm(name: str) -> str:
    stripped = re.sub(r"^[A-Z]{6}\+", "", name)
    return re.sub(r"[^a-z0-9]", "", stripped.lower())


def inspect(path: Path) -> list[str]:
    errors: list[str] = []
    reader = PdfReader(str(path))
    seen: list[tuple[str, str, str]] = []
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        fonts = resources.get("/Font") or {}
        for _key, font in fonts.items():
            base = str(font.get("/BaseFont") or "")
            subtype = str(font.get("/Subtype") or "")
            seen.append((base, subtype, _norm(base)))

    if not seen:
        errors.append(f"{path.name}: no embedded fonts")
        return errors

    for base, subtype, norm in seen:
        if any(f in norm for f in FORBIDDEN):
            errors.append(f"{path.name}: system fallback {base} ({subtype})")
            continue
        if not any(a in norm for a in ALLOW):
            errors.append(f"{path.name}: unexpected font {base} ({subtype})")
            continue
        is_display = any(d in norm for d in DISPLAY)
        is_type3 = "Type3" in subtype
        if is_display and is_type3:
            errors.append(f"{path.name}: Type3 display font {base}")

    return errors


def main(argv: list[str]) -> int:
    pdfs = [Path(a) for a in argv] if argv else DEFAULT_PDFS
    if not pdfs:
        print("no PDFs to check", file=sys.stderr)
        return 1
    failed = False
    for pdf in pdfs:
        errs = inspect(pdf)
        if errs:
            failed = True
            for e in errs:
                print(f"FAIL {e}", file=sys.stderr)
        else:
            print(f"ok {pdf.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

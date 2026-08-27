#!/usr/bin/env python3
"""Pin print-pack card identity to sov_engine.content decks.

Reads EVENTS / DEALS / VOUCHERS name fields from artifact-cards.jsx and
asserts they equal build_event_deck() / build_deal_deck() name sets.
When PDFs exist, also asserts a third-row Default string survived the
9-up grid (Builder's Tab on vouchers.pdf).

Exit 0 on match; exit 1 with a diff otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
WORKTREE = SOURCE.parents[2]
JSX = SOURCE / "artifact-cards.jsx"
PDF_DIR = SOURCE.parent / "pdf"


def _const_block(src: str, name: str) -> str:
    m = re.search(rf"const {name} = \[(.*?)\n\];", src, re.S)
    if not m:
        raise SystemExit(f"could not find const {name} in {JSX.name}")
    return m.group(1)


def _names(block: str) -> list[str]:
    return re.findall(r'name:\s*"([^"]+)"', block)


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def main() -> int:
    sys.path.insert(0, str(WORKTREE))
    from sov_engine.content import build_deal_deck, build_event_deck
    from sov_engine.models import CardType

    src = JSX.read_text(encoding="utf-8")
    print_events = _names(_const_block(src, "EVENTS"))
    print_deals = _names(_const_block(src, "DEALS"))
    print_vouchers = _names(_const_block(src, "VOUCHERS"))

    engine_events = [c.name for c in build_event_deck()]
    engine_deals = [c.name for c in build_deal_deck() if c.card_type is CardType.DEAL]
    engine_vouchers = [c.name for c in build_deal_deck() if c.card_type is CardType.VOUCHER]

    failed = False
    for label, got, want in (
        ("EVENTS", print_events, engine_events),
        ("DEALS", print_deals, engine_deals),
        ("VOUCHERS", print_vouchers, engine_vouchers),
    ):
        if got != want:
            failed = True
            missing = [n for n in want if n not in got]
            extra = [n for n in got if n not in want]
            print(f"FAIL {label}: print={len(got)} engine={len(want)}", file=sys.stderr)
            if missing:
                print(f"  missing from print: {missing}", file=sys.stderr)
            if extra:
                print(f"  extra in print: {extra}", file=sys.stderr)
            if got != want and not missing and not extra:
                print(f"  order differs: print={got} engine={want}", file=sys.stderr)
        else:
            print(f"ok {label}: {len(got)}")

    scale_m = re.search(r"const CARD_SCALE = ([0-9.]+);", src)
    gap_m = re.search(r"const GRID_GAP = ([0-9.]+);", src)
    if not scale_m or not gap_m:
        print("FAIL could not read CARD_SCALE / GRID_GAP", file=sys.stderr)
        failed = True
    else:
        scale = float(scale_m.group(1))
        gap = float(gap_m.group(1))
        card_h = 700
        top = 240
        rows = 3
        bottom = top + rows * (card_h * scale) + (rows - 1) * gap
        print(f"ok grid bottom edge={bottom:.1f}px (must be < 2090)")
        if bottom >= 2090:
            print(f"FAIL 9-up grid still overflows: {bottom:.1f} >= 2090", file=sys.stderr)
            failed = True

    vouchers_pdf = PDF_DIR / "vouchers.pdf"
    if vouchers_pdf.is_file():
        text = _pdf_text(vouchers_pdf)
        for needle in ("Builder's Tab", "Festival Fund", "Emergency Loan", "Default"):
            if needle.lower() not in text.lower():
                print(f"FAIL vouchers.pdf missing {needle!r}", file=sys.stderr)
                failed = True
            else:
                print(f"ok vouchers.pdf contains {needle!r}")
    else:
        print("skip PDF-text check: vouchers.pdf not present")

    events_pdf = PDF_DIR / "events.pdf"
    if events_pdf.is_file():
        text = _pdf_text(events_pdf)
        for needle in ("Time to collect.", "been too long", "Good Rains"):
            if needle.lower() not in text.lower():
                print(f"FAIL events.pdf missing {needle!r}", file=sys.stderr)
                failed = True
            else:
                print(f"ok events.pdf contains {needle!r}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

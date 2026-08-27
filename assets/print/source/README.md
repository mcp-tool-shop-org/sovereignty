# Print pack — source

This directory holds the production sources for the print pack
(board, mat, quick-refs, cards, market board). The rendered PDFs live one
level up in `assets/print/pdf/`. The visual contract — palette, typography,
border treatment — is locked in [`docs/visual-language.md`](../../../docs/visual-language.md).

## What's here

```
source/
├─ Sovereignty Print Pack - print.html     production print entry (offline)
├─ Sovereignty Print Pack.html             viewer build (browse-and-iterate)
├─ Board A - Parchment Heritage.html       standalone board (single-artifact entry)
├─ board-a.jsx                             Direction A board (locked for v1)
├─ board-b.jsx                             Direction B (folk-craft, kept for future comparison)
├─ artifact-cards.jsx                      event / deal / voucher card components
├─ artifact-player-mat.jsx
├─ artifact-quick-ref.jsx
├─ artifact-treaty-ref.jsx
├─ artifact-market-board.jsx               Market Day / Town Hall shared market sheet
├─ tile-data.jsx                           authoritative tile content (mirrors docs/board/board_v1.md)
├─ tile-icons.jsx                          monoline tile icons
├─ primitives.jsx                          shared frame / pill / footer components
├─ tokens.js                               locked palette + typography tokens
├─ fonts.css                               local @font-face (OFL TTF under fonts/)
├─ fonts/                                  Cormorant Garamond, IM Fell English, JetBrains Mono
├─ vendor/                                 React 18 production UMD
├─ print-bundle.js                         precompiled JSX (node compile-jsx.mjs)
├─ print-entry.js                          production mount (no JSX, settle after paint)
├─ print-viewer.js                         viewer mount (no JSX)
├─ compile-jsx.mjs                         JSX → print-bundle.js
├─ inline-fonts.py                         inlines local TTF as data URIs
├─ render.mjs                              Puppeteer render script (macOS / Linux / Windows)
├─ check-deck-parity.py                    print names == engine decks + PDF-text pin
└─ check-pdf-fonts.py                      Type0 display-font allowlist gate
```

## Re-rendering the PDFs

You'll need:

- Google Chrome or Chromium on macOS, Linux, or Windows
- Node 20+
- Python 3
- `puppeteer-core` (dev-only, not a print-time network dependency)

Chrome is resolved in this order: `CHROME_PATH` (must exist), then well-known
install paths, then puppeteer-core's `channel: 'chrome'` locator. A missing
`CHROME_PATH` fails before launch.

### One-time setup

```bash
cd assets/print/source
npm install --no-save puppeteer-core esbuild
node compile-jsx.mjs
```

Re-run `node compile-jsx.mjs` whenever a `*.jsx` file changes. The print HTML
loads `print-bundle.js` — there is no Babel-in-Chrome and no unpkg fetch.

### Render

```bash
# 1. Inline local fonts so the render is deterministic (data-URI @font-face)
python3 inline-fonts.py "Sovereignty Print Pack - print.html"
# → writes "Sovereignty Print Pack - print.RENDER.html"

# 2. Combined PDF (all 13 sheets in one file)
node render.mjs \
  "$PWD/Sovereignty Print Pack - print.RENDER.html" \
  ../pdf/Sovereignty-Print-Pack.pdf

# 3. Per-artifact PDFs (uses the ?only= filter)
for ID in board mat quickref treaty events deals vouchers market; do
  node render.mjs \
    "$PWD/Sovereignty Print Pack - print.RENDER.html" \
    "../pdf/${ID}.pdf" \
    "$ID"
done
```

On Windows PowerShell the same commands work; `render.mjs` builds the file URL
with `pathToFileURL` so the space in `Sovereignty Print Pack - print.RENDER.html`
is encoded.

The generated `*.RENDER.html` file is gitignored — re-run `inline-fonts.py`
whenever `fonts.css` changes. `inline-fonts.py` refuses to write a RENDER copy
that still references fonts.googleapis.com or unpkg.com.

## Verifying a render

```bash
# Page count: 1+1+1+1+4+2+2+1 = 13 sheets (board mat quickref treaty events deals vouchers market)
python3 check-deck-parity.py
python3 check-pdf-fonts.py

# Embedded fonts should be ONLY:
#   Cormorant Garamond (roman + italic weights), IM Fell English (Roman + Italic),
#   JetBrains Mono, ZapfDingbats
# Zero Georgia / Lucida / Times / Menlo. Display faces must be Type0, not Type3.
```

`check-deck-parity.py` also asserts print card name sets equal
`sov_engine.content.build_event_deck()` / `build_deal_deck()` (28 events,
12 deals, 10 vouchers) and that `vouchers.pdf` still contains the third-row
Default lines (Builder's Tab / Festival Fund / Emergency Loan).

## What to print per tier

Town Hall and Market Day are **not** the Campfire sheets. Campfire uses
board + mat + quickref + events + deals + vouchers. Market Day and Town Hall
add `market.pdf` (shared supply / price tracker and player holdings). The
eight market-shift events and two resource deals print on the Event / Deal
sheets (events 21–28, deals 11–12) and are in the same shuffled decks the
console deals.

## Adding or changing content

| Change | Edit | Re-render |
|---|---|---|
| Board tile name / effect | `tile-data.jsx` (and `docs/board/board_v1.md` for parity) | board, combined |
| Card effect / flavor | the per-card data in `artifact-cards.jsx` | events / deals / vouchers + combined |
| Player mat field | `artifact-player-mat.jsx` | mat + combined |
| Quick-ref content | `artifact-quick-ref.jsx` (and `assets/print/quick-ref.md`) | quickref + combined |
| Treaty content | `artifact-treaty-ref.jsx` (and `assets/print/treaty-quick-ref.md`) | treaty + combined |
| Market board | `artifact-market-board.jsx` | market + combined |
| Visual language (color, type, border) | `tokens.js` + `docs/visual-language.md` | everything |
| Tile icons | `tile-icons.jsx` | board + combined |
| Card identity vs engine | keep `artifact-cards.jsx` names in lockstep; `python3 check-deck-parity.py` | — |

After any JSX edit: `node compile-jsx.mjs` then the render recipe above.

## Render-rig notes

- **Fonts:** Cormorant Garamond, IM Fell English, JetBrains Mono. Local TTF
  under `fonts/`, inlined as base64 data URIs at build time so headless Chrome
  doesn't race a network (or a `file://` fetch) during print.
- **JS:** React 18 production UMD in `vendor/` plus `print-bundle.js`. Print
  time has zero network dependencies — `inline-fonts.py` only inlines fonts.
- **Render scale:** `puppeteer.pdf({ scale: 0.48 })` maps the
  200dpi-equivalent design canvas (1700 × 2200 px) onto an 8.5 × 11 in page.
- **Settle signal:** `print-entry.js` sets `document.body.dataset.ready = "true"`
  after React paint **and** `document.fonts.ready` (explicit `fonts.load` of
  each face). Waiting for fonts before the first paint is what produced Type3
  display faces on earlier renders.
- **9-up grid:** `CARD_SCALE = 0.85` so three scaled rows plus header and
  footer fit inside 2200px. Do not raise it without re-checking
  `check-deck-parity.py`'s bottom-edge assertion.

## Direction B

`board-b.jsx` (Direction B — folk-craft warmth) is preserved but not mounted by
the print entry. Direction A is locked for v1. If you ever want to re-render
B for comparison, edit the print HTML's mount block to import `board-b.jsx` in
place of `board-a.jsx`.

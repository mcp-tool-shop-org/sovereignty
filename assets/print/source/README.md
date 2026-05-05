# Print pack — source

This directory holds the production sources for the Tier 1 print pack
(board, mat, quick-refs, cards). The rendered PDFs live one level up
in `assets/print/pdf/`. The visual contract — palette, typography,
border treatment — is locked in [`docs/visual-language.md`](../../../docs/visual-language.md).

## What's here

```
source/
├─ Sovereignty Print Pack - print.html     production print entry (no chrome)
├─ Sovereignty Print Pack.html             viewer build (Figma-ish browse-and-iterate)
├─ Board A - Parchment Heritage.html       standalone board (single-artifact entry)
├─ board-a.jsx                             Direction A board (locked for v1)
├─ board-b.jsx                             Direction B (folk-craft, kept for future comparison)
├─ artifact-cards.jsx                      event / deal / voucher card components
├─ artifact-player-mat.jsx
├─ artifact-quick-ref.jsx
├─ artifact-treaty-ref.jsx
├─ tile-data.jsx                           authoritative tile content (mirrors docs/board/board_v1.md)
├─ tile-icons.jsx                          monoline tile icons
├─ primitives.jsx                          shared frame / pill / footer components
├─ tokens.js                               locked palette + typography tokens
├─ inline-fonts.py                         build helper (fetches Google Fonts → data URIs)
└─ render.mjs                              Puppeteer render script
```

## Re-rendering the PDFs

You'll need:
- macOS or Linux with Google Chrome installed
- Node 20+
- Python 3
- Network access (to fetch Google Fonts on first build)

### One-time setup

```bash
cd assets/print/source
npm install --no-save puppeteer-core
```

### Render

```bash
# 1. Inline fonts so the render is deterministic (fonts arrive synchronously)
python3 inline-fonts.py "Sovereignty Print Pack - print.html"
# → writes "Sovereignty Print Pack - print.RENDER.html"

# 2. Combined PDF (all 11 sheets in one file)
node render.mjs \
  "$PWD/Sovereignty Print Pack - print.RENDER.html" \
  ../pdf/Sovereignty-Print-Pack.pdf

# 3. Per-artifact PDFs (uses the ?only= filter)
for ID in board mat quickref treaty events deals vouchers; do
  node render.mjs \
    "$PWD/Sovereignty Print Pack - print.RENDER.html" \
    "../pdf/${ID}.pdf" \
    "$ID"
done
```

The generated `*.RENDER.html` file (~1.5MB of base64 fonts) is gitignored —
re-run `inline-fonts.py` whenever you change the source HTML's font request.

## Verifying a render

```bash
# Page count should be 1+1+1+1+3+2+2 = 11 sheets per-artifact, 11 combined
for f in ../pdf/*.pdf; do
  echo "$f: $(pdfinfo "$f" | awk '/^Pages:/ {print $2}') pages"
done

# Embedded fonts should be ONLY:
#   Cormorant Garamond (×6 variants), IM Fell English (Roman + Italic),
#   JetBrains Mono, ZapfDingbats
# Zero Georgia / Lucida / Times / Menlo means clean.
pdffonts ../pdf/Sovereignty-Print-Pack.pdf | tail -n +3 \
  | awk '{print $1}' | sed 's/^[A-Z]\{6\}+//' | sort -u
```

## Adding or changing content

| Change | Edit | Re-render |
|---|---|---|
| Board tile name / effect | `tile-data.jsx` (and `docs/board/board_v1.md` for parity) | board, combined |
| Card effect / flavor | the per-card data in `artifact-cards.jsx` | events / deals / vouchers + combined |
| Player mat field | `artifact-player-mat.jsx` | mat + combined |
| Quick-ref content | `artifact-quick-ref.jsx` (and `assets/print/quick-ref.md`) | quickref + combined |
| Treaty content | `artifact-treaty-ref.jsx` (and `assets/print/treaty-quick-ref.md`) | treaty + combined |
| Visual language (color, type, border) | `tokens.js` + `docs/visual-language.md` | everything |
| Tile icons | `tile-icons.jsx` | board + combined |

## Render-rig notes

- **Fonts:** Cormorant Garamond, IM Fell English, JetBrains Mono. Inlined as
  base64 data URIs at build time so headless Chrome doesn't race the network
  during print.
- **Render scale:** `puppeteer.pdf({ scale: 0.48 })` maps the
  200dpi-equivalent design canvas (1700 × 2200 px) onto an 8.5 × 11 in page.
- **Settle signal:** the print HTML sets `document.body.dataset.ready = "true"`
  after `document.fonts.ready` resolves. Puppeteer waits on that exact attribute
  before printing, which is more reliable than `networkidle0` for in-browser
  Babel-compiled JSX.
- **Why headless+Puppeteer instead of `chrome --print-to-pdf` directly:** the
  CLI flag fires the print before Babel finishes compiling the JSX, so fonts
  land as Georgia fallbacks. Puppeteer's explicit ready-flag wait fixes that.

## Direction B

`board-b.jsx` (Direction B — folk-craft warmth) is preserved but not mounted by
the print entry. Direction A is locked for v1. If you ever want to re-render
B for comparison, edit the print HTML's mount block to import `board-b.jsx` in
place of `board-a.jsx`.

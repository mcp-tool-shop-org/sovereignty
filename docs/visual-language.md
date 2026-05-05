# Sovereignty — Visual Language (Tier 1 Print Pack)

**Locked from:** Direction A (Parchment Heritage), confirmed for v1.
**Applies to:** Campfire board, Player Mat, Quick-Ref (Campfire), Treaty Quick-Ref, Event cards, Deal cards, Voucher cards.

## Palette (print-safe)

| Token | Hex | Usage |
|---|---|---|
| `--ground` | `#f4ead4` | Page ground (warm parchment) |
| `--ground-soft` | `#f7eed7` | Tile / card body |
| `--ground-warm` | `#faf2dc` | Anchor tile / start emphasis |
| `--ink` | `#2a1d10` | Primary text, borders |
| `--ink-soft` | `#5a4a35` | Body / effect text |
| `--rule` | `#7a5d33` | Hairline rules, captions |
| `--gold` | `#c08a2e` | Accent rules, ornaments |
| `--gold-deep` | `#8a5e1a` | Shadowed gold, small caps stamps |
| `--navy` | `#15233a` | Logo ground / decorative anchors only |
| `--ember` | `#b54a18` | Tertiary accent (use sparingly) |

The screen palette (`--sov-accent: #e0af68` etc) is for digital surfaces. Print palette derives from it; do not port the dark-theme tokens directly.

## Typography

- **Display serif:** Cormorant Garamond — tile names, card names, page titles, all caps stamps.
- **Italic / flavor:** IM Fell English (italic) — tile/card effect text, flavor lines, taglines.
- **Body monospace:** JetBrains Mono — only for console-command blocks (treaty quick-ref).
- **Numerals (tile/card):** Cormorant Garamond, weight 600.

## Border treatment

- Hairline `1.5px var(--ink)` outer + inset `4px var(--ground)` + inset `1px var(--rule)` (a paper-margin effect).
- Small fleurons (`❦`, `✦`) at corners or section breaks — never multiple on the same element.
- Decorative motifs: compass-rose for board, star/sun for cards (subtle, in inactive corners).

## Numerals

- Tile / card numbers in **inset circular roundel**, hairline `1px var(--rule)` border.
- Anchor / start tile: navy fill, gold numeral.

## Card-type pills (light differentiation)

| Type | Pill | Ground hint | Border accent |
|---|---|---|---|
| Event | small caps "EVENT", `var(--gold)` text on transparent, no fill | `var(--ground-soft)` | `var(--ink)` hairline |
| Deal | small caps "DEAL", `var(--ember)` text, hairline border around pill | `var(--ground-soft)` | `var(--ember)` hairline at top |
| Voucher | small caps "VOUCHER", `var(--gold-deep)` text, dotted underline | `var(--ground-warm)` (paper-receipt warmth) | torn-edge top |

## Spacing & physical-token friendliness

- Tiles: 280×280 px on 1700-wide page. Lower half kept visually quiet — no body text, faint icon at most — for up to 4 stacked position markers.
- Mat fields: checkbox/coin slots at minimum **27×27 px** (≈3/8" at print) so a coin can rest in them.
- Card text never enters the lower 40% of card surface.

## Footer (every artifact)

`Sovereignty: Campfire v1.0 · mcp-tool-shop-org/sovereignty` — IM Fell English italic, `var(--rule)` color, 13px.

(Treaty quick-ref substitutes `Treaty Table v1.0`.)

## Render path

Source: HTML/CSS/SVG at 1:1 ratio (1700×2200 px = 8.5×11" × 200 dpi-equivalent). Production export via headless Chromium with embedded fonts, `@page { size: 8.5in 11in; margin: 0.25in }` safe margins, fonts subset and inlined. Browser Print → PDF acceptable for review only.

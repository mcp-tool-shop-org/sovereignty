/* global React, SovTiles, SovIcons */

// ============================================================================
// Direction A — Parchment Heritage
// ----------------------------------------------------------------------------
// Cream parchment ground, austere woodblock feel. Cormorant Garamond as the
// display serif (echoes the logo's banner wordmark), IM Fell English for
// rule text. Gold + warm-dark ink. Decorative rules are restrained — single
// hairline borders, small fleurons, a quiet center medallion.
// ============================================================================

const A_PALETTE = {
  ground:    "#f4ead4",    // warm parchment
  groundEdge:"#ead9b3",    // edge tint
  ink:       "#2a1d10",    // warm dark
  inkSoft:   "#5a4a35",    // muted body text
  rule:      "#7a5d33",    // hairline rule
  gold:      "#c08a2e",    // print-safe gold
  goldDeep:  "#8a5e1a",    // shadow gold
  navy:      "#15233a",    // logo ground
  ember:     "#b54a18",    // accent (use sparingly, for "0" coin pip)
};

const A_TILE_W = 280;
const A_TILE_H = 280;
const A_GAP = 6;

function ATileFrame({ tile, isStart, children }) {
  return (
    <div
      style={{
        width: A_TILE_W,
        height: A_TILE_H,
        background: isStart ? "#faf2dc" : "#f7eed7",
        border: `1.5px solid ${A_PALETTE.ink}`,
        boxShadow: `inset 0 0 0 4px ${A_PALETTE.ground}, inset 0 0 0 5px ${A_PALETTE.rule}`,
        position: "relative",
        boxSizing: "border-box",
        padding: "14px 16px 14px 16px",
        display: "flex",
        flexDirection: "column",
        fontFamily: "'IM Fell English', 'Cormorant Garamond', Georgia, serif",
      }}
    >
      {children}
    </div>
  );
}

function ATileNumber({ n, isStart }) {
  // Roman-numeral feel: place the arabic in a small medallion top-left.
  return (
    <div
      style={{
        position: "absolute",
        top: 10,
        left: 12,
        width: 30,
        height: 30,
        borderRadius: "50%",
        background: isStart ? A_PALETTE.navy : "transparent",
        border: `1px solid ${A_PALETTE.rule}`,
        color: isStart ? A_PALETTE.gold : A_PALETTE.ink,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Cormorant Garamond', Georgia, serif",
        fontWeight: 600,
        fontSize: 18,
        lineHeight: 1,
        letterSpacing: 0.5,
      }}
    >
      {n}
    </div>
  );
}

function ATile({ tile }) {
  const Icon = tile.icon ? SovIcons[tile.icon] : null;
  return (
    <ATileFrame tile={tile} isStart={tile.start}>
      <ATileNumber n={tile.n} isStart={tile.start} />

      {/* tiny ornament top-right */}
      <div
        style={{
          position: "absolute",
          top: 14,
          right: 16,
          color: A_PALETTE.gold,
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 16,
          letterSpacing: 2,
        }}
      >
        ❦
      </div>

      <div style={{ marginTop: 30 }}>
        <div
          style={{
            fontFamily: "'Cormorant Garamond', Georgia, serif",
            fontWeight: 600,
            fontSize: 28,
            color: A_PALETTE.ink,
            lineHeight: 1.05,
            letterSpacing: 0.2,
            textAlign: "left",
          }}
        >
          {tile.name}
        </div>
        <div
          style={{
            marginTop: 4,
            height: 1,
            width: 40,
            background: A_PALETTE.gold,
          }}
        />
        <div
          style={{
            marginTop: 8,
            fontFamily: "'IM Fell English', Georgia, serif",
            fontSize: 14,
            lineHeight: 1.35,
            color: A_PALETTE.inkSoft,
            fontStyle: "italic",
            paddingRight: 4,
          }}
        >
          {tile.effect}
        </div>
        {tile.start && (
          <div
            style={{
              marginTop: 6,
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 11,
              color: A_PALETTE.goldDeep,
              letterSpacing: 2,
              textTransform: "uppercase",
            }}
          >
            Start &middot; Home
          </div>
        )}
      </div>

      {/* icon bottom-right, recedes into negative space for marker placement */}
      {Icon && (
        <div
          style={{
            position: "absolute",
            bottom: 14,
            right: 16,
            width: 44,
            height: 44,
            color: A_PALETTE.goldDeep,
            opacity: 0.85,
          }}
        >
          {Icon}
        </div>
      )}
    </ATileFrame>
  );
}

function ACenter() {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 30,
        position: "relative",
        gap: 14,
      }}
    >
      {/* compass-rose-ish background ornament */}
      <svg
        viewBox="0 0 400 400"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.18 }}
      >
        <g stroke={A_PALETTE.gold} strokeWidth="0.8" fill="none">
          <circle cx="200" cy="200" r="180" />
          <circle cx="200" cy="200" r="160" />
          <circle cx="200" cy="200" r="120" strokeDasharray="2 4" />
          {Array.from({ length: 16 }).map((_, i) => {
            const a = (i * Math.PI * 2) / 16;
            const x1 = 200 + Math.cos(a) * 120;
            const y1 = 200 + Math.sin(a) * 120;
            const x2 = 200 + Math.cos(a) * 180;
            const y2 = 200 + Math.sin(a) * 180;
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
          })}
        </g>
      </svg>

      <img
        src="assets/logo.png"
        alt=""
        style={{ width: 260, height: 260, objectFit: "contain", marginBottom: -10, marginTop: -10 }}
      />

      <div
        style={{
          fontFamily: "'Cormorant Garamond', Georgia, serif",
          fontWeight: 600,
          fontSize: 14,
          color: A_PALETTE.goldDeep,
          letterSpacing: 6,
          textTransform: "uppercase",
        }}
      >
        Campfire &middot; v 1.0
      </div>

      <div
        style={{
          width: 200,
          height: 1,
          background: A_PALETTE.gold,
          opacity: 0.6,
        }}
      />

      <div
        style={{
          fontFamily: "'IM Fell English', Georgia, serif",
          fontSize: 16,
          color: A_PALETTE.inkSoft,
          fontStyle: "italic",
          textAlign: "center",
          lineHeight: 1.4,
          maxWidth: 280,
          textWrap: "pretty",
        }}
      >
        “Trust, trade, and<br />keeping your word.”
      </div>

      {/* tiny clockwise direction indicator */}
      <div
        style={{
          position: "absolute",
          bottom: 24,
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 11,
          color: A_PALETTE.rule,
          letterSpacing: 4,
          textTransform: "uppercase",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span>play clockwise</span>
        <svg width="14" height="14" viewBox="0 0 14 14" style={{ color: A_PALETTE.gold }}>
          <path
            d="M3 7a4 4 0 1 1 4 4"
            stroke="currentColor"
            strokeWidth="1.2"
            fill="none"
            strokeLinecap="round"
          />
          <path d="M11 11l-1.5-1 .2 2z" fill="currentColor" />
        </svg>
      </div>
    </div>
  );
}

function ABoardA() {
  const tiles = SovTiles;
  const top    = tiles.filter(t => t.pos.side === "top").sort((a,b) => a.pos.idx - b.pos.idx);
  const right  = tiles.filter(t => t.pos.side === "right").sort((a,b) => a.pos.idx - b.pos.idx);
  const bottom = tiles.filter(t => t.pos.side === "bottom").sort((a,b) => a.pos.idx - b.pos.idx);
  const left   = tiles.filter(t => t.pos.side === "left").sort((a,b) => a.pos.idx - b.pos.idx);

  // A US Letter at 200dpi-equivalent: 8.5*200 = 1700 wide, 11*200 = 2200 tall (portrait).
  // Loop occupies 5 cols × 5 rows of A_TILE_W cells. Total grid = 5*A_TILE_W = 1400 wide.
  // Center horizontally with 150px margin each side.
  const PAGE_W = 1700;
  const PAGE_H = 2200;
  const GRID_W = 5 * A_TILE_W + 4 * A_GAP;  // 1400 + 24 = 1424
  const SIDE_MARGIN = (PAGE_W - GRID_W) / 2;
  const TOP_MARGIN = 220;

  return (
    <div
      style={{
        width: PAGE_W,
        height: PAGE_H,
        background: A_PALETTE.ground,
        backgroundImage: `radial-gradient(ellipse at 30% 20%, rgba(255,250,235,0.6), transparent 60%),
                          radial-gradient(ellipse at 80% 90%, rgba(180,130,60,0.08), transparent 70%)`,
        position: "relative",
        boxSizing: "border-box",
        fontFamily: "'IM Fell English', Georgia, serif",
        color: A_PALETTE.ink,
      }}
    >
      {/* Page header */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: "'Cormorant Garamond', Georgia, serif",
        }}
      >
        <div
          style={{
            fontFamily: "'Cormorant Garamond', Georgia, serif",
            fontSize: 16,
            color: A_PALETTE.goldDeep,
            letterSpacing: 14,
            textTransform: "uppercase",
            fontWeight: 500,
          }}
        >
          The Campfire Board
        </div>
        <div
          style={{
            marginTop: 8,
            fontFamily: "'IM Fell English', Georgia, serif",
            fontSize: 14,
            color: A_PALETTE.inkSoft,
            fontStyle: "italic",
            letterSpacing: 1,
          }}
        >
          Sixteen spaces &middot; one round of the year &middot; played clockwise from the fire
        </div>
        {/* decorative double rule */}
        <div style={{ marginTop: 16, display: "flex", justifyContent: "center", alignItems: "center", gap: 16 }}>
          <div style={{ width: 240, height: 1, background: A_PALETTE.gold }} />
          <span style={{ color: A_PALETTE.gold, fontSize: 18 }}>✦</span>
          <div style={{ width: 240, height: 1, background: A_PALETTE.gold }} />
        </div>
      </div>

      {/* Loop */}
      <div
        style={{
          position: "absolute",
          top: TOP_MARGIN,
          left: SIDE_MARGIN,
          width: GRID_W,
          height: GRID_W, // square loop
          display: "grid",
          gridTemplateColumns: `repeat(5, ${A_TILE_W}px)`,
          gridTemplateRows: `repeat(5, ${A_TILE_W}px)`,
          gap: A_GAP,
        }}
      >
        {/* Row 1: top tiles 0..4 */}
        {top.map((t, i) => (
          <div key={`t-${t.n}`} style={{ gridColumn: i + 1, gridRow: 1 }}>
            <ATile tile={t} />
          </div>
        ))}

        {/* Right column rows 2,3,4 — tiles 5,6,7 */}
        {right.map((t, i) => (
          <div key={`r-${t.n}`} style={{ gridColumn: 5, gridRow: i + 2 }}>
            <ATile tile={t} />
          </div>
        ))}

        {/* Row 5: bottom tiles 8..12, but bottom[0]=tile8 must appear at gridCol 5 (bottom-right),
            because clockwise reading along the bottom is right-to-left. */}
        {bottom.map((t, i) => (
          <div key={`b-${t.n}`} style={{ gridColumn: 5 - i, gridRow: 5 }}>
            <ATile tile={t} />
          </div>
        ))}

        {/* Left column — tiles 13,14,15 going up */}
        {left.map((t, i) => (
          <div key={`l-${t.n}`} style={{ gridColumn: 1, gridRow: 4 - i }}>
            <ATile tile={t} />
          </div>
        ))}

        {/* Center 3x3 area — rows 2-4, cols 2-4 */}
        <div
          style={{
            gridColumn: "2 / 5",
            gridRow: "2 / 5",
            display: "flex",
            alignItems: "stretch",
          }}
        >
          <ACenter />
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          position: "absolute",
          bottom: 50,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: "'IM Fell English', Georgia, serif",
          fontSize: 13,
          color: A_PALETTE.rule,
          fontStyle: "italic",
          letterSpacing: 1,
        }}
      >
        Sovereignty: Campfire v1.0 &nbsp;·&nbsp; mcp-tool-shop-org/sovereignty
      </div>
    </div>
  );
}

window.SovBoardA = ABoardA;

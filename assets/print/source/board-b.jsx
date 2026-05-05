/* global React, SovTiles, SovIcons */

// ============================================================================
// Direction B — Folk-craft Warmth
// ----------------------------------------------------------------------------
// Warmer cream ground. Tile borders are wobbly hand-drawn rectangles with
// small flourishes at the corners. Type pairs Fraunces (display) with a
// slightly looser body in the same family. A textile-like central rosette
// echoes a quilt block. More ornament than A, less austerity, but still adult.
// ============================================================================

const B_PALETTE = {
  ground:    "#f8efd9",
  ground2:   "#f1e3c0",
  ink:       "#2d1c10",
  inkSoft:   "#65503a",
  rule:      "#8a6a3e",
  gold:      "#bf8a2c",
  goldDeep:  "#7d5316",
  rust:      "#a3471a",
  navy:      "#172439",
  teal:      "#3d6b6b",   // small folk-craft accent
};

const B_TILE_W = 280;
const B_TILE_H = 280;
const B_GAP = 6;

// Hand-drawn-feeling border using SVG with subtle path jitter.
function BTileBorder({ accent }) {
  const w = B_TILE_W;
  const h = B_TILE_H;
  const inset = 8;
  // Slight jitter on corners for hand-drawn feel
  const j = (n) => n + (Math.sin(n * 13) * 1.4);
  const x0 = inset, y0 = inset, x1 = w - inset, y1 = h - inset;
  const d = `
    M ${j(x0)} ${j(y0+0.5)}
    L ${j(x1-1)} ${j(y0+0.7)}
    L ${j(x1+0.4)} ${j(y1-0.6)}
    L ${j(x0+0.6)} ${j(y1+0.3)}
    Z
  `;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width={w}
      height={h}
      style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
    >
      {/* outer wobble */}
      <path d={d} stroke={B_PALETTE.ink} strokeWidth="1.4" fill="none" />
      {/* inner companion line */}
      <path
        d={`M ${x0+5} ${y0+5} L ${x1-5} ${y0+4} L ${x1-4} ${y1-5} L ${x0+5} ${y1-4} Z`}
        stroke={B_PALETTE.gold}
        strokeWidth="0.7"
        fill="none"
        opacity="0.7"
      />
      {/* corner flourishes */}
      {[
        [x0+5, y0+5, 1, 1],
        [x1-5, y0+5, -1, 1],
        [x1-5, y1-5, -1, -1],
        [x0+5, y1-5, 1, -1],
      ].map(([cx, cy, sx, sy], i) => (
        <g key={i} stroke={accent || B_PALETTE.gold} strokeWidth="0.9" fill="none">
          <path d={`M ${cx} ${cy + sy*10} Q ${cx + sx*4} ${cy + sy*4}, ${cx + sx*10} ${cy}`} />
          <circle cx={cx + sx*3} cy={cy + sy*3} r="0.8" fill={accent || B_PALETTE.gold} stroke="none" />
        </g>
      ))}
    </svg>
  );
}

function BTile({ tile }) {
  const Icon = tile.icon ? SovIcons[tile.icon] : null;
  const isStart = tile.start;
  return (
    <div
      style={{
        width: B_TILE_W,
        height: B_TILE_H,
        background: isStart
          ? `radial-gradient(circle at 50% 35%, #fbf3df, ${B_PALETTE.ground2})`
          : B_PALETTE.ground,
        position: "relative",
        boxSizing: "border-box",
        fontFamily: "'Fraunces', Georgia, serif",
        overflow: "hidden",
      }}
    >
      <BTileBorder accent={isStart ? B_PALETTE.rust : B_PALETTE.gold} />

      {/* Number — diamond shape echoing the logo */}
      <div
        style={{
          position: "absolute",
          top: 14,
          left: 14,
          width: 34,
          height: 34,
          transform: "rotate(45deg)",
          background: isStart ? B_PALETTE.navy : "transparent",
          border: `1.2px solid ${isStart ? B_PALETTE.gold : B_PALETTE.rule}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          style={{
            transform: "rotate(-45deg)",
            fontFamily: "'Fraunces', Georgia, serif",
            fontWeight: 600,
            fontSize: 16,
            color: isStart ? B_PALETTE.gold : B_PALETTE.ink,
            lineHeight: 1,
          }}
        >
          {tile.n}
        </span>
      </div>

      <div
        style={{
          position: "absolute",
          top: 22,
          right: 18,
          left: 60,
          textAlign: "right",
        }}
      >
        <div
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontVariationSettings: "'opsz' 144, 'SOFT' 100",
            fontWeight: 600,
            fontSize: 26,
            color: B_PALETTE.ink,
            lineHeight: 1.05,
            letterSpacing: 0.1,
          }}
        >
          {tile.name}
        </div>
      </div>

      {/* effect text — placed below the title, leaving lower half clear for markers */}
      <div
        style={{
          position: "absolute",
          top: 70,
          left: 22,
          right: 22,
          fontFamily: "'Fraunces', Georgia, serif",
          fontVariationSettings: "'opsz' 14, 'SOFT' 100",
          fontWeight: 400,
          fontSize: 14.5,
          lineHeight: 1.35,
          color: B_PALETTE.inkSoft,
          textWrap: "pretty",
        }}
      >
        {tile.effect}
      </div>

      {isStart && (
        <div
          style={{
            position: "absolute",
            top: 116,
            left: 22,
            right: 22,
            fontFamily: "'Fraunces', Georgia, serif",
            fontStyle: "italic",
            fontSize: 11,
            color: B_PALETTE.rust,
            letterSpacing: 3,
            textTransform: "uppercase",
            fontWeight: 500,
          }}
        >
          ◆ Start &middot; Home ◆
        </div>
      )}

      {/* icon — bottom-center, small, watermark-ish so markers can sit on top */}
      {Icon && (
        <div
          style={{
            position: "absolute",
            bottom: 18,
            left: "50%",
            transform: "translateX(-50%)",
            width: 64,
            height: 64,
            color: B_PALETTE.goldDeep,
            opacity: 0.55,
          }}
        >
          {Icon}
        </div>
      )}

      {/* tiny stitched mark bottom-right, like a quilt corner mark */}
      <div
        style={{
          position: "absolute",
          bottom: 12,
          right: 14,
          fontFamily: "'Fraunces', Georgia, serif",
          fontSize: 9,
          color: B_PALETTE.rule,
          letterSpacing: 2,
          fontVariant: "small-caps",
        }}
      >
        sov
      </div>
    </div>
  );
}

function BCenter() {
  // Quilt-block style rosette + logo
  return (
    <div
      style={{
        flex: 1,
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 30,
        gap: 12,
      }}
    >
      <svg
        viewBox="0 0 400 400"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.22 }}
      >
        <g fill="none" stroke={B_PALETTE.gold} strokeWidth="0.9">
          {/* Outer star/rosette — 8-petal */}
          {Array.from({ length: 8 }).map((_, i) => {
            const a = (i * Math.PI * 2) / 8;
            const x = 200 + Math.cos(a) * 170;
            const y = 200 + Math.sin(a) * 170;
            return <line key={`p${i}`} x1="200" y1="200" x2={x} y2={y} />;
          })}
          {/* concentric diamonds */}
          {[140, 110, 80].map((r, i) => (
            <polygon
              key={`d${i}`}
              points={`200,${200-r} ${200+r},200 200,${200+r} ${200-r},200`}
              opacity={0.7 - i * 0.15}
            />
          ))}
          {/* small dot ring */}
          {Array.from({ length: 16 }).map((_, i) => {
            const a = (i * Math.PI * 2) / 16;
            const x = 200 + Math.cos(a) * 185;
            const y = 200 + Math.sin(a) * 185;
            return <circle key={`c${i}`} cx={x} cy={y} r="2" fill={B_PALETTE.gold} stroke="none" />;
          })}
        </g>
      </svg>

      <img
        src="assets/logo.png"
        alt=""
        style={{ width: 270, height: 270, objectFit: "contain", marginTop: -8, marginBottom: -10 }}
      />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          fontFamily: "'Fraunces', Georgia, serif",
          fontWeight: 500,
          fontSize: 13,
          color: B_PALETTE.goldDeep,
          letterSpacing: 8,
          textTransform: "uppercase",
        }}
      >
        <span>◆</span>
        <span>Campfire &nbsp; v 1.0</span>
        <span>◆</span>
      </div>

      <div
        style={{
          fontFamily: "'Fraunces', Georgia, serif",
          fontStyle: "italic",
          fontSize: 17,
          color: B_PALETTE.inkSoft,
          textAlign: "center",
          lineHeight: 1.4,
          maxWidth: 300,
          marginTop: 4,
        }}
      >
        “Trust, trade,<br />and keeping your word.”
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 22,
          fontFamily: "'Fraunces', Georgia, serif",
          fontSize: 11,
          color: B_PALETTE.rule,
          letterSpacing: 4,
          textTransform: "uppercase",
          display: "flex",
          alignItems: "center",
          gap: 10,
          fontWeight: 500,
        }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" style={{ color: B_PALETTE.gold, transform: "scaleX(-1)" }}>
          <path d="M3 7a4 4 0 1 1 4 4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" />
          <path d="M11 11l-1.5-1 .2 2z" fill="currentColor" />
        </svg>
        <span>Play clockwise</span>
        <svg width="14" height="14" viewBox="0 0 14 14" style={{ color: B_PALETTE.gold }}>
          <path d="M3 7a4 4 0 1 1 4 4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" />
          <path d="M11 11l-1.5-1 .2 2z" fill="currentColor" />
        </svg>
      </div>
    </div>
  );
}

function BBoardB() {
  const tiles = SovTiles;
  const top    = tiles.filter(t => t.pos.side === "top").sort((a,b) => a.pos.idx - b.pos.idx);
  const right  = tiles.filter(t => t.pos.side === "right").sort((a,b) => a.pos.idx - b.pos.idx);
  const bottom = tiles.filter(t => t.pos.side === "bottom").sort((a,b) => a.pos.idx - b.pos.idx);
  const left   = tiles.filter(t => t.pos.side === "left").sort((a,b) => a.pos.idx - b.pos.idx);

  const PAGE_W = 1700;
  const PAGE_H = 2200;
  const GRID_W = 5 * B_TILE_W + 4 * B_GAP;
  const SIDE_MARGIN = (PAGE_W - GRID_W) / 2;
  const TOP_MARGIN = 220;

  return (
    <div
      style={{
        width: PAGE_W,
        height: PAGE_H,
        background: B_PALETTE.ground,
        backgroundImage: `
          radial-gradient(ellipse at 25% 15%, rgba(255,250,232,0.7), transparent 55%),
          radial-gradient(ellipse at 85% 85%, rgba(165,90,30,0.07), transparent 65%),
          repeating-linear-gradient(45deg, transparent 0 18px, rgba(140,90,30,0.025) 18px 19px)
        `,
        position: "relative",
        boxSizing: "border-box",
        color: B_PALETTE.ink,
      }}
    >
      {/* Page header */}
      <div
        style={{
          position: "absolute",
          top: 56,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontWeight: 600,
            fontVariationSettings: "'opsz' 144, 'SOFT' 100",
            fontSize: 38,
            color: B_PALETTE.ink,
            letterSpacing: 1,
            lineHeight: 1,
          }}
        >
          The Campfire Board
        </div>
        <div
          style={{
            marginTop: 10,
            fontFamily: "'Fraunces', Georgia, serif",
            fontStyle: "italic",
            fontSize: 14,
            color: B_PALETTE.inkSoft,
            letterSpacing: 0.5,
          }}
        >
          Sixteen spaces &mdash; one round of the year &mdash; played clockwise from the fire
        </div>
        {/* folk-craft band */}
        <div
          style={{
            marginTop: 14,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 8,
            color: B_PALETTE.gold,
          }}
        >
          <svg width="280" height="10" viewBox="0 0 280 10">
            <path d="M0 5 L260 5" stroke="currentColor" strokeWidth="1" />
            {Array.from({ length: 13 }).map((_, i) => (
              <circle key={i} cx={20 * i + 10} cy="5" r="1.4" fill="currentColor" />
            ))}
          </svg>
          <span style={{ fontSize: 16 }}>✦</span>
          <svg width="280" height="10" viewBox="0 0 280 10">
            <path d="M0 5 L260 5" stroke="currentColor" strokeWidth="1" />
            {Array.from({ length: 13 }).map((_, i) => (
              <circle key={i} cx={20 * i + 10} cy="5" r="1.4" fill="currentColor" />
            ))}
          </svg>
        </div>
      </div>

      {/* Loop */}
      <div
        style={{
          position: "absolute",
          top: TOP_MARGIN,
          left: SIDE_MARGIN,
          width: GRID_W,
          height: GRID_W,
          display: "grid",
          gridTemplateColumns: `repeat(5, ${B_TILE_W}px)`,
          gridTemplateRows: `repeat(5, ${B_TILE_W}px)`,
          gap: B_GAP,
        }}
      >
        {top.map((t, i) => (
          <div key={`t-${t.n}`} style={{ gridColumn: i + 1, gridRow: 1 }}>
            <BTile tile={t} />
          </div>
        ))}
        {right.map((t, i) => (
          <div key={`r-${t.n}`} style={{ gridColumn: 5, gridRow: i + 2 }}>
            <BTile tile={t} />
          </div>
        ))}
        {bottom.map((t, i) => (
          <div key={`b-${t.n}`} style={{ gridColumn: 5 - i, gridRow: 5 }}>
            <BTile tile={t} />
          </div>
        ))}
        {left.map((t, i) => (
          <div key={`l-${t.n}`} style={{ gridColumn: 1, gridRow: 4 - i }}>
            <BTile tile={t} />
          </div>
        ))}
        <div
          style={{
            gridColumn: "2 / 5",
            gridRow: "2 / 5",
            display: "flex",
            alignItems: "stretch",
          }}
        >
          <BCenter />
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
          fontFamily: "'Fraunces', Georgia, serif",
          fontStyle: "italic",
          fontSize: 13,
          color: B_PALETTE.rule,
          letterSpacing: 1,
        }}
      >
        Sovereignty: Campfire v1.0 &nbsp;·&nbsp; mcp-tool-shop-org/sovereignty
      </div>
    </div>
  );
}

window.SovBoardB = BBoardB;

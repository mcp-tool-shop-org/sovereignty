/* global React, SovTokens */
// Shared print primitives — used across all 7 Tier 1 artifacts.
// Each Page is 1700x2200 (US Letter @ 200dpi-equiv). Safe margins 0.25in = 50px.

const T = window.SovTokens;

function PrintPage({ children, footer, footerNote }) {
  return (
    <div style={{
      width: T.page.w,
      height: T.page.h,
      background: T.pageBg,
      backgroundColor: T.ground,
      position: "relative",
      boxSizing: "border-box",
      fontFamily: T.fontItalic,
      color: T.ink,
      overflow: "hidden",
    }}>
      {children}
      <div style={{
        position: "absolute",
        bottom: 50,
        left: 0,
        right: 0,
        textAlign: "center",
        fontFamily: T.fontItalic,
        fontStyle: "italic",
        fontSize: 13,
        color: T.rule,
        letterSpacing: 1,
      }}>
        {footer || T.footer}
        {footerNote && <span style={{opacity: 0.7}}> &nbsp;·&nbsp; {footerNote}</span>}
      </div>
    </div>
  );
}

function PageHeader({ eyebrow, title, subtitle }) {
  return (
    <div style={{ position: "absolute", top: 60, left: 0, right: 0, textAlign: "center" }}>
      {eyebrow && <div style={{
        fontFamily: T.fontDisplay,
        fontSize: 14,
        color: T.goldDeep,
        letterSpacing: 12,
        textTransform: "uppercase",
        fontWeight: 500,
      }}>{eyebrow}</div>}
      <div style={{
        marginTop: eyebrow ? 10 : 0,
        fontFamily: T.fontDisplay,
        fontWeight: 600,
        fontSize: 44,
        color: T.ink,
        letterSpacing: 0.5,
        lineHeight: 1.1,
      }}>{title}</div>
      {subtitle && <div style={{
        marginTop: 8,
        fontFamily: T.fontItalic,
        fontStyle: "italic",
        fontSize: 15,
        color: T.inkSoft,
        letterSpacing: 0.5,
      }}>{subtitle}</div>}
      <div style={{
        marginTop: 16,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 16,
      }}>
        <div style={{ width: 220, height: 1, background: T.gold }} />
        <span style={{ color: T.gold, fontSize: 18 }}>✦</span>
        <div style={{ width: 220, height: 1, background: T.gold }} />
      </div>
    </div>
  );
}

function Roundel({ n, accent, size = 30 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%",
      background: accent ? T.navy : "transparent",
      border: `1px solid ${T.rule}`,
      color: accent ? T.gold : T.ink,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: T.fontDisplay, fontWeight: 600, fontSize: size * 0.55, lineHeight: 1,
    }}>{n}</div>
  );
}

// Small ornament
function Fleuron({ color, size = 16 }) {
  return <span style={{ color: color || T.gold, fontSize: size, fontFamily: T.fontDisplay }}>❦</span>;
}

// Hairline section divider with center ornament
function Divider({ width = 200, ornament = "✦" }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
      <div style={{ width, height: 1, background: T.gold, opacity: 0.7 }} />
      <span style={{ color: T.gold, fontSize: 14 }}>{ornament}</span>
      <div style={{ width, height: 1, background: T.gold, opacity: 0.7 }} />
    </div>
  );
}

// Checkbox-style square (sized for coin placement)
function CoinSlot({ size = 32, label, marked }) {
  return (
    <div style={{
      width: size, height: size,
      border: `1.2px solid ${T.rule}`,
      background: marked ? T.groundWarm : "transparent",
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      fontFamily: T.fontDisplay, fontSize: size * 0.45, color: T.inkSoft,
      borderRadius: 2,
    }}>{label || ""}</div>
  );
}

window.SovPrim = { PrintPage, PageHeader, Roundel, Fleuron, Divider, CoinSlot, T };

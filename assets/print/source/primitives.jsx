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
        <StarMark size={16} />
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

// Vector ornaments — latin TTF subsets do not include U+2726/U+2766, and
// Chrome on Windows would otherwise embed Segoe UI Symbol (or Type3 paths).
function StarMark({ size = 16, color }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true"
      style={{ display: "inline-block", verticalAlign: "middle", flex: "0 0 auto" }}>
      <path
        d="M8 1.2 L9.7 6.1 L15 6.2 L10.8 9.3 L12.5 14.4 L8 11.4 L3.5 14.4 L5.2 9.3 L1 6.2 L6.3 6.1 Z"
        fill={color || T.gold}
      />
    </svg>
  );
}

function Fleuron({ color, size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true"
      style={{ display: "inline-block", verticalAlign: "middle", flex: "0 0 auto" }}>
      <path
        d="M8 1.5 C6.2 4.8 3.5 6 3.5 9.1 C3.5 11.6 5.4 13.4 8 14.5 C10.6 13.4 12.5 11.6 12.5 9.1 C12.5 6 9.8 4.8 8 1.5 Z"
        fill={color || T.gold}
      />
    </svg>
  );
}

function Divider({ width = 200 }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
      <div style={{ width, height: 1, background: T.gold, opacity: 0.7 }} />
      <StarMark size={12} />
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

window.SovPrim = { PrintPage, PageHeader, Roundel, Fleuron, StarMark, Divider, CoinSlot, T };

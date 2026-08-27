/* global React, SovTokens, SovPrim */
const { PrintPage, PageHeader, CoinSlot, StarMark } = window.SovPrim;
const T = window.SovTokens;

// ============================================================================
// Market Board — one US Letter portrait page for Market Day + Town Hall.
// Shared supply / price tracks live in the middle of the table; Campfire
// does not use this sheet.
// ============================================================================

const RESOURCES = [
  { name: "Food", note: "Bumper Harvest / Feast Day" },
  { name: "Wood", note: "Logging Ban · Workshop cost" },
  { name: "Tools", note: "Tinker's Arrival / Tool Shortage · Builder cost" },
];

function FieldLabel({ children, hint }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 8 }}>
      <div style={{
        fontFamily: T.fontDisplay, fontWeight: 600, fontSize: 20, color: T.ink,
        letterSpacing: 3, textTransform: "uppercase",
      }}>{children}</div>
      {hint && <div style={{
        fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 13, color: T.rule,
      }}>{hint}</div>}
    </div>
  );
}

function TrackBoxes({ count, marked, labels }) {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "flex-end", flexWrap: "wrap" }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
          <div style={{
            width: 28, height: 28,
            border: `1.2px solid ${T.rule}`,
            background: marked && marked.has(i) ? T.navy : "transparent",
            color: marked && marked.has(i) ? T.gold : T.inkSoft,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: T.fontDisplay, fontSize: 11, fontWeight: 600,
            borderRadius: marked && marked.has(i) ? "50%" : 2,
          }}>{marked && marked.has(i) ? <StarMark size={12} color={T.gold} /> : ""}</div>
          <div style={{
            fontFamily: T.fontDisplay, fontSize: 11, color: T.inkSoft, fontWeight: 500,
          }}>{labels ? labels[i] : i}</div>
        </div>
      ))}
    </div>
  );
}

function ResourceColumn({ name, note }) {
  return (
    <div style={{
      flex: 1,
      border: `1px solid ${T.rule}`,
      padding: "18px 16px 20px",
      background: "rgba(255,250,235,0.35)",
      display: "flex",
      flexDirection: "column",
      gap: 14,
    }}>
      <div>
        <div style={{
          fontFamily: T.fontDisplay, fontWeight: 600, fontSize: 26, color: T.ink,
          letterSpacing: 2, textTransform: "uppercase",
        }}>{name}</div>
        <div style={{
          fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 12, color: T.rule, marginTop: 4,
        }}>{note}</div>
      </div>
      <div>
        <div style={{
          fontFamily: T.fontDisplay, fontSize: 12, letterSpacing: 3, textTransform: "uppercase",
          color: T.goldDeep, marginBottom: 8,
        }}>Supply 0-12</div>
        <TrackBoxes count={13} labels={Array.from({ length: 13 }, (_, i) => String(i))} />
        <div style={{
          fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 12, color: T.inkSoft, marginTop: 8,
        }}>Start: 8 (2p) · 10 (3p) · 12 (4p). Market Day: unlimited, skip this track.</div>
      </div>
      <div>
        <div style={{
          fontFamily: T.fontDisplay, fontSize: 12, letterSpacing: 3, textTransform: "uppercase",
          color: T.goldDeep, marginBottom: 8,
        }}>Price 1–4</div>
        <TrackBoxes count={4} marked={new Set([1])} labels={["1", "2", "3", "4"]} />
        <div style={{
          fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 12, color: T.inkSoft, marginTop: 8,
        }}>Start at 2 (star). Town Hall clamp 1-4. Market Day: leave the token on 2.</div>
      </div>
    </div>
  );
}

function RuleRow({ k, v }) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "160px 1fr",
      columnGap: 16,
      padding: "7px 0",
      borderBottom: `0.6px solid ${T.rule}`,
    }}>
      <div style={{
        fontFamily: T.fontDisplay, fontWeight: 600, fontSize: 14, color: T.gold, letterSpacing: 1,
      }}>{k}</div>
      <div style={{
        fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 14, color: T.inkSoft, lineHeight: 1.35,
      }}>{v}</div>
    </div>
  );
}

function HoldingsRow({ n }) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "1.4fr 1fr 1fr 1fr",
      gap: 12,
      alignItems: "center",
      padding: "8px 0",
      borderBottom: `0.6px solid ${T.rule}`,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          fontFamily: T.fontDisplay, fontSize: 13, color: T.inkSoft, letterSpacing: 2,
          textTransform: "uppercase", width: 18,
        }}>{n}</div>
        <div style={{ flex: 1, borderBottom: `1.2px solid ${T.rule}`, height: 22 }} />
      </div>
      {["Food", "Wood", "Tools"].map((r) => (
        <div key={r} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{
            fontFamily: T.fontDisplay, fontSize: 11, letterSpacing: 1,
            textTransform: "uppercase", color: T.rule, width: 44,
          }}>{r}</span>
          {[0, 1, 2, 3, 4].map((i) => <CoinSlot key={i} size={22} />)}
        </div>
      ))}
    </div>
  );
}

function MarketBoardPage() {
  return (
    <PrintPage footer={T.footerMarket} footerNote="one per table · Market Day + Town Hall">
      <PageHeader
        eyebrow="Sovereignty · Market Day / Town Hall"
        title="Market Board"
        subtitle="Shared supply and prices · Campfire does not use this sheet"
      />

      <div style={{
        position: "absolute",
        top: 230, left: 70, right: 70, bottom: 100,
        display: "flex", flexDirection: "column", gap: 16,
      }}>
        <div style={{ display: "flex", gap: 14 }}>
          {RESOURCES.map((r) => <ResourceColumn key={r.name} {...r} />)}
        </div>

        <div style={{ display: "flex", gap: 14, flex: 1, minHeight: 0 }}>
          <div style={{
            flex: 1.15,
            border: `1px solid ${T.rule}`,
            padding: "18px 22px",
            background: "rgba(255,250,235,0.35)",
          }}>
            <FieldLabel>How to use</FieldLabel>
            <RuleRow k="Buy / sell" v="Land on Market: buy or sell up to 2 resources. Buy = pay the posted price, take 1 from supply. Sell = return 1, receive buy price - 1 (min 1)." />
            <RuleRow k="Market Day" v="Prices stay at 2. Supply never runs out. Market-shift events print flavor only -- no mechanical effect." />
            <RuleRow k="Town Hall" v="Start supply 8 / 10 / 12 by player count. Base price 2. Supply <= 2 -> price +1. Supply 0 -> cannot buy. Event price shifts last the round, then reset. Clamp 1-4." />
            <RuleRow k="Upgrades" v="Workshop: 2 coins + 1 Wood. Builder: 3 coins + 1 Tools (still needs Rep >= 3)." />
            <div style={{ borderBottom: "none" }} />
          </div>

          <div style={{
            flex: 1,
            border: `1px solid ${T.rule}`,
            padding: "18px 22px",
            background: "rgba(255,250,235,0.35)",
            display: "flex",
            flexDirection: "column",
          }}>
            <FieldLabel hint="tokens or pencil">Holdings</FieldLabel>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1.4fr 1fr 1fr 1fr",
              gap: 12,
              fontFamily: T.fontDisplay, fontSize: 11, letterSpacing: 2,
              textTransform: "uppercase", color: T.goldDeep, marginBottom: 4,
            }}>
              <div>Player</div><div>Food</div><div>Wood</div><div>Tools</div>
            </div>
            {[1, 2, 3, 4].map((n) => <HoldingsRow key={n} n={n} />)}
            <div style={{
              marginTop: "auto",
              fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 12, color: T.rule,
            }}>
              Events 21–28 (Bumper Harvest through Good Rains) and deals 11–12
              (Soup Kitchen, Lend Me Your Hammer) ship on the Event and Deal sheets.
            </div>
          </div>
        </div>
      </div>
    </PrintPage>
  );
}

window.SovMarketBoard = MarketBoardPage;

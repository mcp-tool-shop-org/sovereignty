/* global React, SovTokens, SovPrim */
const { PrintPage, PageHeader, Divider, CoinSlot } = window.SovPrim;
const T = window.SovTokens;

// ============================================================================
// Player Mat — one US Letter portrait page.
// Token-friendly: 32px coin slots, 48px goal checkboxes, writable promise band.
// ============================================================================

function CoinTracker() {
  // 5x4 = 20 boxes. Start: 5 (first 5 are pre-marked with subtle dot).
  const rows = 4, cols = 5;
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 36px)`, gap: 6 }}>
        {Array.from({ length: rows * cols }).map((_, i) => (
          <CoinSlot key={i} size={36} label={i < 5 ? "•" : ""} />
        ))}
      </div>
    </div>
  );
}

function RepTrack() {
  // 0..10 with markers. Start: 3.
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "flex-end" }}>
      {Array.from({ length: 11 }).map((_, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
          <div style={{
            width: 36, height: 36,
            border: `1.2px solid ${T.rule}`,
            background: i === 3 ? T.navy : "transparent",
            color: i === 3 ? T.gold : T.inkSoft,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: T.fontDisplay, fontSize: 16, fontWeight: 600,
            borderRadius: i === 3 ? "50%" : 2,
          }}>{i === 3 ? "✦" : ""}</div>
          <div style={{
            fontFamily: T.fontDisplay, fontSize: 14, color: T.inkSoft, fontWeight: 500,
          }}>{i}</div>
        </div>
      ))}
    </div>
  );
}

function FieldLabel({ children, hint }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 8 }}>
      <div style={{
        fontFamily: T.fontDisplay,
        fontWeight: 600,
        fontSize: 22,
        color: T.ink,
        letterSpacing: 3,
        textTransform: "uppercase",
      }}>{children}</div>
      {hint && <div style={{
        fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 13, color: T.rule,
      }}>{hint}</div>}
    </div>
  );
}

function MatSection({ children, style }) {
  return (
    <div style={{
      border: `1px solid ${T.rule}`,
      padding: "26px 32px",
      background: "rgba(255,250,235,0.35)",
      ...style,
    }}>{children}</div>
  );
}

function PlayerMatPage() {
  return (
    <PrintPage>
      <PageHeader
        eyebrow="Sovereignty · Campfire"
        title="Player Mat"
        subtitle="One per player · track with coins, beads, or pencil"
      />

      {/* Body */}
      <div style={{
        position: "absolute",
        top: 240,
        left: 100, right: 100,
        bottom: 110,
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}>
        {/* Identity + tallies */}
        <MatSection>
          {/* Name */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 22 }}>
            <div style={{
              fontFamily: T.fontDisplay, fontWeight: 600, fontSize: 22, letterSpacing: 3,
              textTransform: "uppercase", color: T.ink,
            }}>Name</div>
            <div style={{ flex: 1, borderBottom: `1.2px solid ${T.rule}`, height: 30 }} />
          </div>

          {/* Coins + Rep stacked */}
          <div style={{ display: "flex", gap: 40, alignItems: "flex-start" }}>
            <div>
              <FieldLabel hint="start: 5  ·  goal: 20 = Prosperity">Coins</FieldLabel>
              <CoinTracker />
            </div>
            <div style={{ flex: 1 }}>
              <FieldLabel hint="start: 3  ·  goal: 10 = Beloved">Reputation</FieldLabel>
              <RepTrack />

              <div style={{ marginTop: 26 }}>
                <FieldLabel hint="goal: 4 = Builder">Upgrades</FieldLabel>
                <div style={{ display: "flex", gap: 10 }}>
                  {[0,1,2,3].map(i => <CoinSlot key={i} size={42} />)}
                </div>
              </div>
            </div>
          </div>
        </MatSection>

        {/* Goal */}
        <MatSection>
          <FieldLabel hint="check one — keep secret">My Goal</FieldLabel>
          <div style={{ display: "flex", gap: 36, marginTop: 4 }}>
            {[
              { name: "Prosperity", note: "20 coins" },
              { name: "Beloved",    note: "10 reputation" },
              { name: "Builder",    note: "4 upgrades" },
            ].map((g, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <CoinSlot size={32} />
                <div>
                  <div style={{
                    fontFamily: T.fontDisplay, fontWeight: 600, fontSize: 20, color: T.ink,
                  }}>{g.name}</div>
                  <div style={{
                    fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 13, color: T.rule,
                  }}>{g.note}</div>
                </div>
              </div>
            ))}
          </div>
        </MatSection>

        {/* Promises this round */}
        <MatSection>
          <FieldLabel hint="once per round  ·  the table decides">Promises this round</FieldLabel>
          <div style={{
            fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 18, color: T.inkSoft,
            display: "flex", alignItems: "baseline", gap: 10,
          }}>
            <span>“I promise</span>
            <div style={{ flex: 1, borderBottom: `1.2px solid ${T.rule}`, height: 36 }} />
            <span>”</span>
          </div>
          <div style={{ display: "flex", gap: 36, marginTop: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <CoinSlot size={28} />
              <span style={{ fontFamily: T.fontDisplay, fontSize: 18, color: T.ink }}>Kept it</span>
              <span style={{ fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 14, color: T.gold }}>+ 1 Rep</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <CoinSlot size={28} />
              <span style={{ fontFamily: T.fontDisplay, fontSize: 18, color: T.ink }}>Broke it</span>
              <span style={{ fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 14, color: T.ember }}>- 2 Rep</span>
            </div>
          </div>
        </MatSection>

        {/* Apology + Rep gates side-by-side */}
        <div style={{ display: "flex", gap: 18, flex: 1 }}>
          <MatSection style={{ flex: 1 }}>
            <FieldLabel hint="once per game">The Apology</FieldLabel>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 14, marginTop: 4 }}>
              <CoinSlot size={32} />
              <div style={{ fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 15, color: T.inkSoft, lineHeight: 1.4 }}>
                Pay 1 coin to the player you wronged. Regain <span style={{color: T.gold, fontStyle: "normal", fontFamily: T.fontDisplay}}>+ 1 Rep</span>.
              </div>
            </div>
          </MatSection>
          <MatSection style={{ flex: 1.4 }}>
            <FieldLabel>Rep gates</FieldLabel>
            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 16, rowGap: 7,
                          fontFamily: T.fontItalic, fontSize: 14, color: T.inkSoft }}>
              <div style={{ color: T.ember, fontStyle: "italic" }}>Rep &lt; 2</div><div>Can’t issue Vouchers</div>
              <div style={{ color: T.gold, fontStyle: "italic" }}>Rep &gt;= 3</div><div>Can use Builder space</div>
              <div style={{ color: T.gold, fontStyle: "italic" }}>Rep &gt;= 5</div><div>Vouchers worth +1 (trusted)</div>
              <div style={{ color: T.gold, fontStyle: "italic" }}>Rep &gt;= 8</div><div>Trade with 2 players per turn</div>
            </div>
          </MatSection>
        </div>
      </div>
    </PrintPage>
  );
}

window.SovPlayerMat = PlayerMatPage;

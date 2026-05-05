/* global React, SovTokens, SovPrim */
const { PrintPage, PageHeader, Divider } = window.SovPrim;
const T = window.SovTokens;

// ============================================================================
// Quick-Reference (Campfire) — single US Letter portrait page, density-friendly.
// ============================================================================

function QRTable({ rows, cols, colWidths }) {
  return (
    <div style={{ width: "100%" }}>
      {rows.map((row, ri) => (
        <div key={ri} style={{
          display: "grid",
          gridTemplateColumns: colWidths.map(w => typeof w === "number" ? `${w}px` : w).join(" "),
          alignItems: "baseline",
          padding: "6px 0",
          borderBottom: ri < rows.length - 1 ? `0.6px solid ${T.rule}` : "none",
          fontFamily: T.fontItalic,
          fontSize: 13.5,
          color: T.inkSoft,
          fontStyle: "italic",
          lineHeight: 1.35,
        }}>
          {row.map((cell, ci) => (
            <div key={ci} style={{
              fontWeight: ci === 0 ? 600 : 400,
              fontFamily: ci === 0 || ci === 1 ? T.fontDisplay : T.fontItalic,
              fontStyle: ci === 0 || ci === 1 ? "normal" : "italic",
              color: ci === 0 ? T.gold : (ci === 1 ? T.ink : T.inkSoft),
              fontSize: ci === 1 ? 15 : 13.5,
              paddingRight: 12,
            }}>{cell}</div>
          ))}
        </div>
      ))}
    </div>
  );
}

function SectionBlock({ title, children, style }) {
  return (
    <div style={{ ...style }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 12, marginBottom: 8,
      }}>
        <div style={{
          fontFamily: T.fontDisplay,
          fontWeight: 600, fontSize: 20, color: T.ink, letterSpacing: 3,
          textTransform: "uppercase",
        }}>{title}</div>
        <div style={{ flex: 1, height: 0.6, background: T.gold, opacity: 0.7 }} />
      </div>
      {children}
    </div>
  );
}

function CampfireQuickRefPage() {
  const boardRows = [
    ["0",  "Campfire",   "+1 coin (safe). Also +1 when passing through."],
    ["1",  "Workshop",   "Pay 2c -> +1 Upgrade"],
    ["2",  "Market",     "Buy or sell 1 resource at posted price"],
    ["3",  "Rumor Mill", "Draw an Event card"],
    ["4",  "Trade Dock", "Propose a trade with any player"],
    ["5",  "Festival",   "Donate 1c -> +1 Rep"],
    ["6",  "Trouble",    "Lose 1c OR lose 1 Rep"],
    ["7",  "Help Desk",  "Give 1c to another, both +1 Rep"],
    ["8",  "Mint",       "+2 coins"],
    ["9",  "Rumor Mill", "Draw an Event card"],
    ["10", "Builder",    "Pay 3c -> +1 Upgrade (need Rep >= 3)"],
    ["11", "Faucet",     "+1 coin"],
    ["12", "Trade Dock", "Propose a trade with any player"],
    ["13", "Taxman",     "Pay 1c. Can’t? Lose 1 Rep."],
    ["14", "Commons",    "Vote: majority yes -> everyone +1c"],
    ["15", "Crossroads", "Draw a Deal card. Accept or pass."],
  ];

  return (
    <PrintPage>
      <PageHeader
        eyebrow="Sovereignty · Campfire"
        title="Quick Reference"
        subtitle="Sixteen spaces · turn order · promises · winning"
      />

      <div style={{
        position: "absolute",
        top: 240, left: 100, right: 100, bottom: 110,
        display: "grid",
        gridTemplateColumns: "1.1fr 1fr",
        columnGap: 50, rowGap: 28,
      }}>
        {/* Board spaces — full width left column */}
        <SectionBlock title="Board spaces · 0–15 · clockwise" style={{ gridColumn: "1 / 2", gridRow: "1 / span 4" }}>
          <QRTable rows={boardRows} colWidths={[34, 130, "1fr"]} />
        </SectionBlock>

        {/* Right column: turn order */}
        <SectionBlock title="Turn order">
          <ol style={{
            margin: 0, paddingLeft: 24,
            fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 15, color: T.inkSoft,
            lineHeight: 1.55,
          }}>
            <li>Roll the d6, move clockwise.</li>
            <li>Do what the space says.</li>
            <li>Optional: propose one trade.</li>
            <li>End your turn.</li>
          </ol>
        </SectionBlock>

        <SectionBlock title="Promises">
          <div style={{
            fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 14, color: T.inkSoft,
            lineHeight: 1.5,
          }}>
            Once per round, say <span style={{ fontWeight: 500, color: T.ink }}>“I&nbsp;promise…”</span> out loud.
            <div style={{ display: "flex", gap: 18, marginTop: 8 }}>
              <span><span style={{ color: T.gold, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Keep it</span> +1 Rep</span>
              <span><span style={{ color: T.ember, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Break it</span> -2 Rep</span>
            </div>
            <div style={{ marginTop: 6 }}>The table decides.</div>
          </div>
        </SectionBlock>

        <SectionBlock title="The Apology">
          <div style={{
            fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 14, color: T.inkSoft, lineHeight: 1.5,
          }}>
            Once per game. Pay <span style={{ color: T.ink, fontFamily: T.fontDisplay, fontStyle: "normal" }}>1 coin</span> to the player you wronged. Regain <span style={{ color: T.gold, fontFamily: T.fontDisplay, fontStyle: "normal" }}>+1 Rep</span>.
          </div>
        </SectionBlock>

        <SectionBlock title="Winning">
          <QRTable
            rows={[
              ["", "Prosperity", "20+ coins"],
              ["", "Beloved",    "10 reputation"],
              ["", "Builder",    "4+ upgrades"],
            ]}
            colWidths={[0, 130, "1fr"]}
          />
          <div style={{
            marginTop: 12,
            padding: "10px 12px",
            background: T.groundWarm,
            border: `1px solid ${T.rule}`,
            fontFamily: T.fontDisplay,
            fontSize: 14,
            color: T.ink,
            fontStyle: "italic",
            textAlign: "center",
          }}>
            After 15 rounds: <span style={{ fontWeight: 600 }}>(Coins ÷ 2) + Rep + (Upgrades × 3)</span> — highest wins.
          </div>
        </SectionBlock>

        <SectionBlock title="Vouchers" style={{ gridColumn: "2 / 3" }}>
          <div style={{
            fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 14, color: T.inkSoft, lineHeight: 1.5,
          }}>
            <div>Need <span style={{ color: T.ink, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Rep &gt;= 2</span> to issue.</div>
            <div><span style={{ color: T.gold, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Rep &gt;= 5</span>: vouchers pay face value +1 (trusted).</div>
            <div><span style={{ color: T.gold, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Rep &gt;= 8</span>: trade with 2 players per turn.</div>
            <div>Miss the deadline -&gt; automatic default, lose Rep.</div>
          </div>
        </SectionBlock>
      </div>
    </PrintPage>
  );
}

window.SovQuickRef = CampfireQuickRefPage;

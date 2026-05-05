/* global React, SovTokens, SovPrim */
const { PrintPage, PageHeader } = window.SovPrim;
const T = window.SovTokens;

// ============================================================================
// Treaty Quick-Reference — single US Letter portrait page.
// Centerpiece: 4-state lifecycle diagram.
// ============================================================================

function LifecycleDiagram() {
  // 4 nodes: MAKE → ACTIVE, then 3 outcomes from ACTIVE: KEEP, BREAK, DEADLINE.
  return (
    <svg viewBox="0 0 900 280" style={{ width: "100%", height: 240 }}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill={T.rule} />
        </marker>
      </defs>

      {/* MAKE */}
      <g>
        <rect x="30" y="110" width="140" height="60" rx="4" fill={T.groundSoft} stroke={T.ink} strokeWidth="1.4" />
        <text x="100" y="135" textAnchor="middle" fontFamily={T.fontDisplay} fontSize="22" fontWeight="600" fill={T.ink} letterSpacing="3">MAKE</text>
        <text x="100" y="156" textAnchor="middle" fontFamily={T.fontItalic} fontStyle="italic" fontSize="11" fill={T.rule}>stake declared</text>
      </g>

      <line x1="170" y1="140" x2="270" y2="140" stroke={T.rule} strokeWidth="1.4" markerEnd="url(#arrow)" />

      {/* ACTIVE */}
      <g>
        <rect x="280" y="100" width="160" height="80" rx="4" fill={T.navy} stroke={T.gold} strokeWidth="1.6" />
        <text x="360" y="130" textAnchor="middle" fontFamily={T.fontDisplay} fontSize="24" fontWeight="600" fill={T.gold} letterSpacing="4">ACTIVE</text>
        <text x="360" y="152" textAnchor="middle" fontFamily={T.fontItalic} fontStyle="italic" fontSize="11" fill={T.groundSoft}>both stakes held</text>
        <text x="360" y="168" textAnchor="middle" fontFamily={T.fontItalic} fontStyle="italic" fontSize="11" fill={T.groundSoft}>deadline running</text>
      </g>

      {/* Three branches from ACTIVE */}
      {/* KEEP (top) */}
      <path d={`M 440 115 Q 530 70, 600 70`} stroke={T.gold} strokeWidth="1.4" fill="none" markerEnd="url(#arrow)" />
      <text x="510" y="55" textAnchor="middle" fontFamily={T.fontDisplay} fontSize="13" fill={T.goldDeep} fontStyle="italic" fontWeight="500">keep</text>
      <g>
        <rect x="600" y="40" width="270" height="60" rx="4" fill={T.groundWarm} stroke={T.gold} strokeWidth="1.2" />
        <text x="612" y="62" fontFamily={T.fontDisplay} fontSize="16" fontWeight="600" fill={T.ink} letterSpacing="3">STAKES RETURNED</text>
        <text x="612" y="82" fontFamily={T.fontItalic} fontStyle="italic" fontSize="13" fill={T.gold}>+1 Rep each</text>
      </g>

      {/* BREAK (middle) */}
      <path d={`M 440 140 L 600 140`} stroke={T.ember} strokeWidth="1.4" fill="none" markerEnd="url(#arrow)" />
      <text x="520" y="132" textAnchor="middle" fontFamily={T.fontDisplay} fontSize="13" fill={T.ember} fontStyle="italic" fontWeight="500">break</text>
      <g>
        <rect x="600" y="115" width="270" height="60" rx="4" fill={T.groundSoft} stroke={T.ember} strokeWidth="1.2" />
        <text x="612" y="137" fontFamily={T.fontDisplay} fontSize="16" fontWeight="600" fill={T.ink} letterSpacing="3">STAKE FORFEITED</text>
        <text x="612" y="157" fontFamily={T.fontItalic} fontStyle="italic" fontSize="13" fill={T.ember}>breaker - 3 Rep · harmed party gets it</text>
      </g>

      {/* DEADLINE (bottom) */}
      <path d={`M 440 165 Q 530 220, 600 220`} stroke={T.rule} strokeWidth="1.4" fill="none" markerEnd="url(#arrow)" />
      <text x="510" y="245" textAnchor="middle" fontFamily={T.fontDisplay} fontSize="13" fill={T.rule} fontStyle="italic" fontWeight="500">deadline passes</text>
      <g>
        <rect x="600" y="190" width="270" height="60" rx="4" fill={T.groundSoft} stroke={T.rule} strokeWidth="1" strokeDasharray="3 3" />
        <text x="612" y="212" fontFamily={T.fontDisplay} fontSize="16" fontWeight="600" fill={T.ink} letterSpacing="3">AUTO-KEPT</text>
        <text x="612" y="232" fontFamily={T.fontItalic} fontStyle="italic" fontSize="13" fill={T.rule}>generous interpretation · stakes return</text>
      </g>
    </svg>
  );
}

function TQRBlock({ title, children, style }) {
  return (
    <div style={{ ...style }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 12, marginBottom: 8,
      }}>
        <div style={{
          fontFamily: T.fontDisplay, fontWeight: 600, fontSize: 18, color: T.ink, letterSpacing: 3,
          textTransform: "uppercase",
        }}>{title}</div>
        <div style={{ flex: 1, height: 0.6, background: T.gold, opacity: 0.7 }} />
      </div>
      {children}
    </div>
  );
}

function TreatyQuickRefPage() {
  return (
    <PrintPage footer={T.footerTreaty}>
      <PageHeader
        eyebrow="Sovereignty · Tier 3"
        title="Treaty Table"
        subtitle="A promise with teeth — put something on the line"
      />

      <div style={{
        position: "absolute",
        top: 240, left: 100, right: 100, bottom: 110,
        display: "flex", flexDirection: "column", gap: 20,
      }}>
        {/* What's a treaty */}
        <div style={{
          fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 17, color: T.inkSoft,
          textAlign: "center", lineHeight: 1.5, padding: "0 60px",
        }}>
          A promise with teeth. You put up coins or resources as collateral. Break it,
          and you lose your stake to the other party.
        </div>

        {/* Lifecycle — centerpiece */}
        <TQRBlock title="Lifecycle">
          <LifecycleDiagram />
        </TQRBlock>

        {/* Three columns: stakes / limits / keep-vs-break */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1.3fr", gap: 28 }}>
          <TQRBlock title="Stake types">
            <div style={{ fontFamily: T.fontItalic, fontSize: 13.5, color: T.inkSoft, fontStyle: "italic", lineHeight: 1.6 }}>
              <div><span style={{ color: T.gold, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Coins</span> &nbsp; “2 coins”, “5 coins”</div>
              <div><span style={{ color: T.gold, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Resources</span> &nbsp; “1 food”, “1 wood, 1 tools”</div>
              <div><span style={{ color: T.gold, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Mixed</span> &nbsp; “2 coins, 1 food”</div>
            </div>
          </TQRBlock>

          <TQRBlock title="Limits">
            <div style={{ fontFamily: T.fontItalic, fontSize: 13.5, color: T.inkSoft, fontStyle: "italic", lineHeight: 1.6 }}>
              <div>Active per player <span style={{ color: T.ink, fontFamily: T.fontDisplay, fontStyle: "normal" }}>2</span></div>
              <div>Max coins / stake <span style={{ color: T.ink, fontFamily: T.fontDisplay, fontStyle: "normal" }}>5</span></div>
              <div>Max resource units <span style={{ color: T.ink, fontFamily: T.fontDisplay, fontStyle: "normal" }}>3</span></div>
              <div>Makes per turn <span style={{ color: T.ink, fontFamily: T.fontDisplay, fontStyle: "normal" }}>1</span></div>
            </div>
          </TQRBlock>

          <TQRBlock title="Console commands">
            <pre style={{
              margin: 0,
              padding: "10px 12px",
              background: "rgba(20,15,10,0.06)",
              border: `1px dashed ${T.rule}`,
              fontFamily: T.fontMono,
              fontSize: 10.5,
              color: T.ink,
              lineHeight: 1.55,
              whiteSpace: "pre-wrap",
            }}>{`sov treaty make "help each other" \\
  --with Bob --stake "2 coins"
sov treaty list
sov treaty keep t_0001
sov treaty break t_0001 \\
  --breaker Alice`}</pre>
          </TQRBlock>
        </div>

        {/* What treaty table is NOT */}
        <div style={{
          marginTop: "auto",
          border: `1px solid ${T.rule}`,
          padding: "20px 28px",
          background: "rgba(255,250,235,0.4)",
        }}>
          <div style={{
            fontFamily: T.fontDisplay, fontSize: 16, color: T.goldDeep,
            letterSpacing: 4, textTransform: "uppercase", fontStyle: "italic", fontWeight: 500,
            marginBottom: 10,
          }}>What Treaty Table is not</div>
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr", columnGap: 30, rowGap: 6,
            fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 14, color: T.inkSoft, lineHeight: 1.45,
          }}>
            <div><span style={{ color: T.ember, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Not a courtroom.</span> There’s no judge — the table decides.</div>
            <div><span style={{ color: T.ember, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Not governance.</span> No votes, no policies, no alliances.</div>
            <div><span style={{ color: T.ember, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Not permanent.</span> Treaties have deadlines. Everything expires.</div>
            <div><span style={{ color: T.ember, fontFamily: T.fontDisplay, fontStyle: "normal" }}>Not required.</span> You can play a full game without one.</div>
          </div>
          <div style={{
            marginTop: 12, fontFamily: T.fontItalic, fontStyle: "italic", fontSize: 13, color: T.rule,
            textAlign: "center",
          }}>It’s just stakes. Put something on the line, or stick with promises.</div>
        </div>
      </div>
    </PrintPage>
  );
}

window.SovTreatyQuickRef = TreatyQuickRefPage;

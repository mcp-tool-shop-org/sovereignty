/* global React, SovTokens, SovPrim */
const { PrintPage, PageHeader } = window.SovPrim;
const T = window.SovTokens;

// ============================================================================
// Cards — Event / Deal / Voucher.
// All cards: 500x700 (poker 2.5x3.5 @ 200dpi). 9-up grid per US Letter portrait.
// Light per-type differentiation via type-pill color/style + small accent.
// ============================================================================

const CARD_W = 500;
const CARD_H = 700;
const GRID_COLS = 3;
const GRID_ROWS = 3;
// Available area on page: 1700x2200 with 50px safe margin = 1600x2100. 3*500 = 1500 fits.
// Vertical: 3*700 = 2100 = exactly fills; tighten to fit with header.
// Strategy: scale cards down slightly to leave a header band.
const CARD_SCALE = 0.95;

function CardFrame({ children, accent, type, ground, topAccent }) {
  return (
    <div style={{
      width: CARD_W * CARD_SCALE,
      height: CARD_H * CARD_SCALE,
      background: ground || T.groundSoft,
      border: `1.4px solid ${T.ink}`,
      boxShadow: `inset 0 0 0 5px ${ground || T.groundSoft}, inset 0 0 0 6px ${T.rule}`,
      position: "relative",
      boxSizing: "border-box",
      padding: "28px 30px 26px 30px",
      display: "flex",
      flexDirection: "column",
      fontFamily: T.fontItalic,
      overflow: "hidden",
    }}>
      {topAccent && <div style={{
        position: "absolute", top: 6, left: 6, right: 6, height: 3,
        background: topAccent,
      }} />}
      {children}
    </div>
  );
}

function TypePill({ kind }) {
  const styles = {
    Event:   { color: T.gold,     border: "none", letter: 4, ornament: "✦" },
    Deal:    { color: T.ember,    border: `1px solid ${T.ember}`, letter: 3, ornament: null },
    Voucher: { color: T.goldDeep, border: "none", underline: true, letter: 3, ornament: "❦" },
  }[kind];
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      fontFamily: T.fontDisplay,
      fontSize: 11,
      letterSpacing: styles.letter,
      textTransform: "uppercase",
      color: styles.color,
      border: styles.border,
      borderBottom: styles.underline ? `1px dotted ${styles.color}` : styles.border ? styles.border.split(" ").join(" ") : undefined,
      padding: styles.border ? "3px 9px" : (styles.underline ? "0 0 2px 0" : 0),
      fontWeight: 500,
    }}>
      {styles.ornament ? <span style={{ fontSize: 10 }}>{styles.ornament}</span> : null}
      <span>{kind}</span>
    </div>
  );
}

function CardName({ children }) {
  return (
    <div style={{
      fontFamily: T.fontDisplay,
      fontWeight: 600,
      fontSize: 28,
      lineHeight: 1.05,
      color: T.ink,
      letterSpacing: 1,
      textWrap: "balance",
    }}>{children}</div>
  );
}

function CardEffect({ children }) {
  return (
    <div style={{
      fontFamily: T.fontItalic,
      fontStyle: "italic",
      fontSize: 16,
      lineHeight: 1.4,
      color: T.inkSoft,
      textWrap: "pretty",
    }}>{children}</div>
  );
}

function CardFlavor({ children }) {
  return (
    <div style={{
      marginTop: "auto",
      fontFamily: T.fontItalic,
      fontStyle: "italic",
      fontSize: 13,
      color: T.rule,
      textAlign: "right",
      lineHeight: 1.4,
    }}>{children}</div>
  );
}

function CardOutcome({ reward, penalty }) {
  return (
    <div style={{
      marginTop: 14,
      padding: "10px 12px",
      background: "rgba(20,15,10,0.04)",
      border: `0.6px solid ${T.rule}`,
      display: "flex",
      flexDirection: "column",
      gap: 4,
      fontFamily: T.fontDisplay,
      fontSize: 13,
    }}>
      {reward && <div><span style={{ color: T.gold, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", fontSize: 11 }}>Reward</span> &nbsp;<span style={{ color: T.ink }}>{reward}</span></div>}
      {penalty && <div><span style={{ color: T.ember, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", fontSize: 11 }}>Penalty</span> &nbsp;<span style={{ color: T.ink }}>{penalty}</span></div>}
    </div>
  );
}

function EventCard({ name, effect, flavor }) {
  return (
    <CardFrame ground={T.groundSoft}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
        <TypePill kind="Event" />
      </div>
      <CardName>{name}</CardName>
      <div style={{ height: 1, width: 50, background: T.gold, margin: "12px 0 14px" }} />
      <CardEffect>{effect}</CardEffect>
      {flavor && <CardFlavor>“{flavor}”</CardFlavor>}
    </CardFrame>
  );
}

function DealCard({ name, action, reward, penalty, flavor }) {
  return (
    <CardFrame ground={T.groundSoft} topAccent={T.ember}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
        <TypePill kind="Deal" />
      </div>
      <CardName>{name}</CardName>
      <div style={{ height: 1, width: 50, background: T.ember, margin: "12px 0 14px" }} />
      <CardEffect>{action}</CardEffect>
      <CardOutcome reward={reward} penalty={penalty} />
      {flavor && <CardFlavor>“{flavor}”</CardFlavor>}
    </CardFrame>
  );
}

function VoucherCard({ name, iou, due, defaultPenalty }) {
  return (
    <CardFrame ground={T.groundWarm}>
      {/* torn-edge top */}
      <svg viewBox="0 0 500 14" preserveAspectRatio="none" style={{ position: "absolute", top: 0, left: 0, right: 0, width: "100%", height: 14 }}>
        <path d="M0,14 L0,4 L20,8 L40,2 L60,7 L80,3 L100,9 L120,4 L140,8 L160,3 L180,9 L200,5 L220,8 L240,3 L260,9 L280,4 L300,8 L320,3 L340,9 L360,5 L380,8 L400,3 L420,9 L440,4 L460,8 L480,3 L500,7 L500,14 Z"
          fill={T.groundWarm} stroke={T.rule} strokeWidth="0.6" />
      </svg>

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10, marginTop: 4 }}>
        <TypePill kind="Voucher" />
      </div>
      <CardName>{name}</CardName>
      <div style={{ height: 1, width: 50, background: T.goldDeep, margin: "12px 0 16px" }} />

      <div style={{
        fontFamily: T.fontItalic,
        fontStyle: "italic",
        fontSize: 17,
        lineHeight: 1.45,
        color: T.ink,
        padding: "12px 14px",
        background: "rgba(255,250,235,0.6)",
        borderLeft: `2px solid ${T.gold}`,
      }}>
        {iou}
      </div>

      {due && (
        <div style={{
          marginTop: 12,
          fontFamily: T.fontDisplay,
          fontSize: 13,
          color: T.inkSoft,
          letterSpacing: 2,
          textTransform: "uppercase",
        }}>Due &nbsp;<span style={{ color: T.ink }}>{due}</span></div>
      )}

      <div style={{
        marginTop: "auto",
        paddingTop: 10,
        borderTop: `0.6px dashed ${T.rule}`,
        fontFamily: T.fontDisplay,
        fontSize: 12,
        letterSpacing: 2,
        textTransform: "uppercase",
        color: T.ember,
      }}>Default &nbsp;<span style={{ color: T.ink, letterSpacing: 0, textTransform: "none", fontStyle: "italic", fontFamily: T.fontItalic, fontSize: 14 }}>{defaultPenalty}</span></div>
    </CardFrame>
  );
}

// ── Card data ──────────────────────────────────────────────────────────────

const EVENTS = [
  { name: "Supply Delay", effect: "Upgrades cost +1 coin this round.", flavor: "The shipment’s late. Again." },
  { name: "Boom Town",    effect: "Every player gains 1 coin.",         flavor: "Trade is good. Everyone’s eating." },
  { name: "Storm",        effect: "Every player pays 1 coin or loses 1 Rep.", flavor: "Batten down the hatches." },
  { name: "Rumor",        effect: "You lose 1 Rep — unless someone vouches for you.", flavor: "People are talking…" },
  { name: "Big Order",    effect: "Market prices +1 this round.",       flavor: "A caravan just arrived with deep pockets." },
  { name: "Festival of Plenty", effect: "Next 2 Festival landings give +2 Rep instead of +1.", flavor: "The whole town is celebrating." },
  { name: "Swindle",      effect: "Force one voucher redemption now.",  flavor: "Time to collect." },
  { name: "Windfall",     effect: "You gain 3 coins.",                  flavor: "Lucky day." },
  { name: "Drought",      effect: "No Market purchases this round.",    flavor: "Nothing on the shelves." },
  { name: "Trust Crisis", effect: "Players with Rep < 3 lose 1 more Rep.", flavor: "When trust is low, it falls further." },
  { name: "Lost Wallet",  effect: "You can’t trade this turn — unless someone lends you 1 coin.", flavor: "Has anyone seen a small leather pouch?" },
  { name: "Good News Travels", effect: "If you helped someone last round, gain 2 coins now.", flavor: "Word got around about what you did." },
  { name: "Awkward Favor", effect: "Ask any player to cover 2 coins for you. You owe them 3 later.", flavor: "Hey… got a minute?" },
  { name: "Found a Shortcut", effect: "Gain 3 coins, but lose 1 Rep. People noticed.", flavor: "Nobody saw… right?" },
  { name: "Community Dinner", effect: "Everyone may donate 1 coin. Each donor gains +1 Rep.", flavor: "Bring something to share." },
  { name: "Old Friend",   effect: "Pick a player. You each gain +1 Rep.", flavor: "It’s been too long." },
  { name: "Broken Bridge", effect: "Skip your next move. Stay where you are.", flavor: "Road’s out. Might as well make camp." },
  { name: "Harvest Moon", effect: "The player with the fewest coins gains 2 coins.", flavor: "The land provides for those who need it most." },
  { name: "Tall Tale",    effect: "Gain 1 Rep. But if you’re already above 7, lose 1 instead.", flavor: "Some stories are too good to be true." },
  { name: "Lucky Find",   effect: "Draw another Event immediately.",     flavor: "What’s this?" },
];

const DEALS = [
  { name: "Supply Run",         action: "Deliver 3 coins to any player within 2 rounds.", reward: "+2 Rep", penalty: "-1 Rep" },
  { name: "Builder's Promise",  action: "Build 1 Upgrade within 3 rounds.", reward: "+1 Rep, +1 coin", penalty: "-1 Rep" },
  { name: "Generosity Pledge",  action: "Give 1 coin to each other player.", reward: "+3 Rep", penalty: "-2 Rep" },
  { name: "Market Watcher",     action: "Buy or sell at Market twice within 4 rounds.", reward: "+1 Rep, +2 coins", penalty: "-1 Rep" },
  { name: "Peacekeeper",        action: "Help someone at Help Desk within 3 rounds.", reward: "+2 Rep", penalty: "-1 Rep" },
  { name: "Spot Me",            action: "Give 2 coins to a player now. They owe you 3 next round.", reward: "+3 coins, +1 Rep", penalty: "-1 Rep", flavor: "I’m good for it, I swear." },
  { name: "Two-Person Discount", action: "Find a partner. You both pay 1 coin, you both gain 2.", reward: "+2 coins", penalty: "-1 Rep", flavor: "Bulk deal. Split it?" },
  { name: "Mutual Aid Pact",    action: "Pick a partner. Next Trouble, the other helps for free.", reward: "+2 Rep", penalty: "-2 Rep", flavor: "I’ve got your back if you’ve got mine." },
  { name: "Reputation for Hire", action: "Give 1 coin to a player. They give you +1 Rep at Help Desk.", reward: "+1 Rep", penalty: "-1 Rep", flavor: "Put in a good word for me?" },
  { name: "The Long Game",      action: "Don’t spend any coins for 2 full rounds.", reward: "+4 coins, +1 Rep", penalty: "-1 Rep", flavor: "Patience pays. Eventually." },
];

const VOUCHERS = [
  { name: "Small Loan",      iou: "I owe you 2 coins.",                                due: "3 rounds", defaultPenalty: "-2 Rep" },
  { name: "Big Loan",        iou: "I owe you 4 coins.",                                due: "4 rounds", defaultPenalty: "-3 Rep" },
  { name: "Favor Owed",      iou: "I owe you 1 coin and a free Help Desk.",            due: "3 rounds", defaultPenalty: "-2 Rep" },
  { name: "Trade Credit",    iou: "I owe you 3 coins, but only at Trade Dock.",        due: "4 rounds", defaultPenalty: "-2 Rep" },
  { name: "Blank Voucher",   iou: "We’ll figure out the terms. (1–5 coins, 1–5 rounds.)", defaultPenalty: "Half face value Rep" },
  { name: "Quick Cash",      iou: "I need 1 coin now. I’ll pay you 2 next round. Promise.", due: "1 round", defaultPenalty: "-2 Rep" },
  { name: "Builder's Tab",   iou: "Cover my upgrade cost (2 coins). I’ll pay 3 back.", due: "3 rounds", defaultPenalty: "-2 Rep" },
  { name: "Festival Fund",   iou: "Lend me 1 coin for Festival. I’ll repay with interest.", due: "2 rounds", defaultPenalty: "-1 Rep" },
  { name: "Emergency Loan",  iou: "I’m broke. Lend me 3 coins. No interest, just trust.", due: "3 rounds", defaultPenalty: "-3 Rep" },
  { name: "Handshake Deal",  iou: "We agree on terms right now. (Negotiable.)",         defaultPenalty: "Negotiated" },
];

// ── Card sheet pages ───────────────────────────────────────────────────────

function CardSheet({ title, eyebrow, subtitle, footerNote, cards, renderCard }) {
  // Render up to 9 cards in a 3x3 grid; pad with blank "Cut along lines" footer
  return (
    <PrintPage footerNote={footerNote}>
      <PageHeader eyebrow={eyebrow} title={title} subtitle={subtitle} />
      <div style={{
        position: "absolute",
        top: 240, left: (T.page.w - GRID_COLS * CARD_W * CARD_SCALE - (GRID_COLS - 1) * 20) / 2,
        display: "grid",
        gridTemplateColumns: `repeat(${GRID_COLS}, ${CARD_W * CARD_SCALE}px)`,
        gridTemplateRows: `repeat(${GRID_ROWS}, ${CARD_H * CARD_SCALE}px)`,
        gap: 20,
      }}>
        {cards.map((c, i) => <div key={i}>{renderCard(c)}</div>)}
      </div>
    </PrintPage>
  );
}

function chunk(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

function EventCardPages() {
  const pages = chunk(EVENTS, 9);  // 20 -> [9, 9, 2]
  return pages.map((batch, i) => (
    <CardSheet key={i}
      eyebrow="Sovereignty · Campfire"
      title="Event Cards"
      subtitle={`Sheet ${i+1} of ${pages.length}  ·  shuffle face-down · cut along the lines`}
      footerNote={`Events ${i*9+1}–${Math.min((i+1)*9, EVENTS.length)} of ${EVENTS.length}`}
      cards={batch}
      renderCard={(c) => <EventCard {...c} />}
    />
  ));
}

function DealCardPages() {
  const pages = chunk(DEALS, 9);
  return pages.map((batch, i) => (
    <CardSheet key={i}
      eyebrow="Sovereignty · Campfire"
      title="Deal Cards"
      subtitle={`Sheet ${i+1} of ${pages.length}  ·  drawn at Crossroads · accept or pass`}
      footerNote={`Deals ${i*9+1}–${Math.min((i+1)*9, DEALS.length)} of ${DEALS.length}`}
      cards={batch}
      renderCard={(c) => <DealCard {...c} />}
    />
  ));
}

function VoucherCardPages() {
  const pages = chunk(VOUCHERS, 9);
  return pages.map((batch, i) => (
    <CardSheet key={i}
      eyebrow="Sovereignty · Campfire"
      title="Voucher Cards"
      subtitle={`Sheet ${i+1} of ${pages.length}  ·  IOUs between players`}
      footerNote={`Vouchers ${i*9+1}–${Math.min((i+1)*9, VOUCHERS.length)} of ${VOUCHERS.length}`}
      cards={batch}
      renderCard={(c) => <VoucherCard {...c} />}
    />
  ));
}

window.SovEventPages = EventCardPages;
window.SovDealPages = DealCardPages;
window.SovVoucherPages = VoucherCardPages;

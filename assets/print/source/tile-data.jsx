// Authoritative tile data from docs/board/board_v1.md.
// `effect` is the short tile-face string. `icon` is one of the SovIcons keys (or null).
// `pos` describes board placement: { side: 'top'|'right'|'bottom'|'left', index: 0..n }
//   - top:    indices 0..4, left-to-right, clockwise reading
//   - right:  indices 0..2, top-to-bottom
//   - bottom: indices 0..4, right-to-left (reading clockwise)
//   - left:   indices 0..2, bottom-to-top

const TILES = [
  { n: 0,  name: "Campfire",   effect: "Safe. +1 coin if you pass through.",          icon: "flame",  start: true,  pos: { side: "top",    idx: 0 } },
  { n: 1,  name: "Workshop",   effect: "Pay 2c -> +1 Upgrade.",                         icon: "anvil",                pos: { side: "top",    idx: 1 } },
  { n: 2,  name: "Market",     effect: "Buy or sell 1 resource at posted price.",      icon: "scales",               pos: { side: "top",    idx: 2 } },
  { n: 3,  name: "Rumor Mill", effect: "Draw an Event card.",                          icon: null,                   pos: { side: "top",    idx: 3 } },
  { n: 4,  name: "Trade Dock", effect: "Propose a trade with any player.",             icon: null,                   pos: { side: "top",    idx: 4 } },
  { n: 5,  name: "Festival",   effect: "Donate 1c -> +1 Rep. Optional.",                icon: null,                   pos: { side: "right",  idx: 0 } },
  { n: 6,  name: "Trouble",    effect: "Lose 1c OR lose 1 Rep. Your choice.",          icon: null,                   pos: { side: "right",  idx: 1 } },
  { n: 7,  name: "Help Desk",  effect: "Give 1c to another. Both gain +1 Rep.",        icon: null,                   pos: { side: "right",  idx: 2 } },
  { n: 8,  name: "Mint",       effect: "+2 coins from the bank.",                      icon: "coin",                 pos: { side: "bottom", idx: 0 } },
  { n: 9,  name: "Rumor Mill", effect: "Draw an Event card.",                          icon: null,                   pos: { side: "bottom", idx: 1 } },
  { n: 10, name: "Builder",    effect: "Pay 3c -> +1 Upgrade. Need Rep >= 3.",           icon: "trowel",               pos: { side: "bottom", idx: 2 } },
  { n: 11, name: "Faucet",     effect: "+1 coin from the bank.",                       icon: "drop",                 pos: { side: "bottom", idx: 3 } },
  { n: 12, name: "Trade Dock", effect: "Propose a trade with any player.",             icon: null,                   pos: { side: "bottom", idx: 4 } },
  { n: 13, name: "Taxman",     effect: "Pay 1c. Can't? Lose 1 Rep.",                   icon: "pouch",                pos: { side: "left",   idx: 0 } },
  { n: 14, name: "Commons",    effect: "All vote. Majority yes -> everyone +1c.",       icon: "hands",                pos: { side: "left",   idx: 1 } },
  { n: 15, name: "Crossroads", effect: "Draw a Deal card. Accept or pass.",            icon: null,                   pos: { side: "left",   idx: 2 } },
];

window.SovTiles = TILES;

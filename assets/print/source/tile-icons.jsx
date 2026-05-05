// Monoline tile icons — designed to read at small sizes on print.
// Stroke-based so both directions can restyle them via currentColor and stroke-width.
// Each icon renders inside a 24x24 viewBox.

const Icons = {
  flame: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21c3.6 0 6.4-2.6 6.4-6 0-2.4-1.4-3.8-2.6-5.2-1-1.2-1.6-2.4-1.6-4.2 0-1.4.6-2.6.6-2.6s-3 1.4-4.6 4c-1.4 2.4-1 4.2-.4 5-1.2-.4-2.4-1.6-2.4-3.4 0 0-2 2-2 5.2 0 4 3.4 7.2 6.6 7.2z" />
      <path d="M12 17.5c1.4 0 2.4-1 2.4-2.2 0-1-.6-1.6-1.2-2.2-.4-.4-.6-.8-.6-1.4 0 0-2 1-2 3 0 1.6 1 2.8 1.4 2.8z" />
    </svg>
  ),
  anvil: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9h12c2.2 0 3.6 1.4 4 3" />
      <path d="M3 9v3h11v-3" />
      <path d="M7 12v4" />
      <path d="M11 12v4" />
      <path d="M5 16h8" />
      <path d="M4 19h10" />
    </svg>
  ),
  scales: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 4v16" />
      <path d="M6 20h12" />
      <path d="M5 7h14" />
      <path d="M5 7l-3 6h6z" />
      <path d="M19 7l-3 6h6z" />
      <circle cx="12" cy="5" r="0.6" fill="currentColor" />
    </svg>
  ),
  coin: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="5.5" />
      <path d="M12 9v6" />
      <path d="M10.5 10.5h2.2a1.2 1.2 0 010 2.4h-2.2" />
      <path d="M10.5 12.9h2.6" />
    </svg>
  ),
  trowel: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="14" width="6" height="3" />
      <rect x="3" y="17" width="6" height="3" />
      <rect x="9" y="14" width="6" height="3" />
      <rect x="9" y="17" width="6" height="3" />
      <rect x="15" y="14" width="4" height="3" />
      <rect x="15" y="17" width="4" height="3" />
      <path d="M11 14V9l4-3 5 3-4 5" />
    </svg>
  ),
  drop: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3s-6 7-6 11.5C6 18 8.7 21 12 21s6-3 6-6.5C18 10 12 3 12 3z" />
      <path d="M9 15c.4 1.4 1.4 2.4 2.6 2.6" />
    </svg>
  ),
  pouch: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 7c-2 1.5-4 4.5-4 8 0 3.5 3 6 8 6s8-2.5 8-6c0-3.5-2-6.5-4-8" />
      <path d="M8 7l1.5-3h5L16 7" />
      <path d="M8 7h8" />
      <path d="M11 13c0 .5.5.8 1 .8s1-.3 1-.8-2-.5-2-1c0-.5.5-.8 1-.8s1 .3 1 .8" />
      <path d="M12 11v3.5" />
    </svg>
  ),
  hands: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 13c0-1 .5-2 1.5-2.4l3-1.4c.6-.3 1.4 0 1.6.6l1.4 3.4" />
      <path d="M3 13l1.4 3c.4 1 1.4 1.6 2.4 1.4l3-.4c1-.2 1.6-1 1.6-2v-3" />
      <path d="M21 13c0-1-.5-2-1.5-2.4l-3-1.4c-.6-.3-1.4 0-1.6.6L13.5 13" />
      <path d="M21 13l-1.4 3c-.4 1-1.4 1.6-2.4 1.4l-3-.4c-1-.2-1.6-1-1.6-2v-3" />
      <path d="M9 11l1.5 1.5L12 11l1.5 1.5L15 11" />
    </svg>
  ),
};

window.SovIcons = Icons;

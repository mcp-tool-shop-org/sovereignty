import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'Sovereignty',
  description: 'A strategy game about governance, trust, and trade — offline tabletop with optional XRPL verification.',
  logoBadge: 'SV',
  brandName: 'Sovereignty',
  repoUrl: 'https://github.com/mcp-tool-shop-org/sovereignty',
  // HACK: site-theme's SiteConfig only exposes `npmUrl?` for the registry-link
  // slot, but sovereignty is a Python package on PyPI. We point npmUrl at the
  // PyPI listing so the link lands correctly; the visible label still reads
  // "npm". Tracked upstream:
  //   https://github.com/mcp-tool-shop-org/site-theme/issues/4
  // Once site-theme 0.3.0 ships `packageUrl`, rename this field and drop the
  // HACK note.
  npmUrl: 'https://pypi.org/project/sovereignty-game/',

  // SECURITY — set:html boundary
  // The fields below (footerText, hero.badge, hero.description) are rendered
  // by @mcptoolshop/site-theme's BaseLayout via set:html (raw HTML injection).
  // Today they are hard-coded literals; the trust boundary is the literal
  // itself. NEVER source these from external input (env var, fetched JSON,
  // content collection, user form). If you need dynamic content here,
  // switch to a sanitized template.
  footerText: 'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>',

  hero: {
    badge: 'v2.0.2 — multi-save · daemon · audit viewer (dev preview)',
    headline: 'Sovereignty',
    headlineAccent: 'a board game about keeping your word.',
    description: 'Roll, trade, promise, betray. 2-4 players, 30 minutes, no screens required. The console keeps score — you keep your word. Optionally anchor results on the XRPL Testnet.',
    // F-004 (Stage D): primaryCta hardened to absolute base-prefixed href for
    // parity with secondaryCta. Hero is only rendered on the homepage today, so
    // a bare '#usage' fragment works there — but absolute paths are robust to
    // future refactors that might surface the Hero on additional routes.
    primaryCta: { href: '/sovereignty/#usage', label: 'Install with pipx' },
    // CTA href hardened (Wave 1 LOW → Wave 6 Stage C). Was 'handbook/' (relative,
    // fragile on non-homepage routes); now absolute base-prefixed so it resolves
    // correctly under the configured Astro `base` ('/sovereignty').
    secondaryCta: { href: '/sovereignty/handbook/', label: 'Read the Handbook' },
    previews: [
      { label: 'Install', code: 'pipx install sovereignty-game' },
      { label: 'Tutorial', code: 'sov tutorial' },
      { label: 'Play', code: 'sov new -p Alice -p Bob -p Carol' },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'What makes it different',
      subtitle: 'Reputation that you say out loud, not jargon you have to learn. Three mechanics carry the whole game.',
      features: [
        { title: 'Promises you say out loud', desc: 'Say "I promise..." at the table. Keep it: +1 reputation. Break it: -2 reputation. No app reminders — the table holds you to it.' },
        { title: 'Treaties with real stakes', desc: 'Put your coins where your mouth is. Binding agreements with escrowed stakes — promises with teeth, judged by the room.' },
        { title: 'Proofs anyone can verify', desc: 'Every round produces a SHA-256 fingerprint. Optionally anchor it on the XRPL Testnet — a public wall nobody can erase.' },
      ],
    },
    {
      kind: 'data-table',
      id: 'tiers',
      title: 'Pick your depth',
      subtitle: 'Three tiers. Start at Campfire on game night one — add complexity only when the table is ready.',
      columns: ['Tier', 'Name', 'What it adds'],
      rows: [
        ['1', 'Campfire', 'Coins, reputation, promises, IOUs'],
        ['2', 'Town Hall', 'Shared market, resource scarcity, dynamic pricing'],
        ['3', 'Treaty Table', 'Binding treaties with escrow stakes'],
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Get playing in 60 seconds',
      cards: [
        { title: 'Install', code: 'pipx install sovereignty-game\n# or: uv tool install sovereignty-game' },
        { title: 'Quick start', code: 'sov tutorial           # learn in 60 seconds\nsov new -p Alice -p Bob # start a game\nsov turn               # roll, land, resolve\nsov end-round          # generate proof' },
        // DOCS-D-003 (Wave 13 Stage 9-D): desktop-app entry point alongside
        // the CLI cards. Audit Viewer + Game Shell run from source for v2.1
        // dev preview; signed binaries ship via Wave 11.
        { title: 'Desktop app (v2.1, dev preview)', code: 'npm --prefix app run tauri dev\n# Audit Viewer + Game Shell — runs from source.\n# Signed binaries ship via Wave 11.' },
      ],
    },
    {
      kind: 'features',
      id: 'diary',
      title: 'Diary Mode — optional, educational',
      subtitle: 'Skip this on game night one. When you\'re curious how cryptographic proof works, the console can anchor each round to a public ledger — for free, with play-money tokens.',
      features: [
        { title: 'Wallet', desc: 'Create a free XRPL Testnet wallet. Test XRP has no value — it\'s play money.' },
        { title: 'Anchor', desc: 'Post your round proof hash to the ledger. Think of it as writing the score on a wall nobody can erase.' },
        { title: 'Verify', desc: 'Anyone can check the proof against the on-chain record. Trust but verify.' },
      ],
    },
  ],
};

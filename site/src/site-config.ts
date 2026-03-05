import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'Sovereignty',
  description: 'A strategy game about governance, trust, and trade — offline tabletop with optional XRPL verification.',
  logoBadge: 'SV',
  brandName: 'Sovereignty',
  repoUrl: 'https://github.com/mcp-tool-shop-org/sovereignty',
  pypiUrl: 'https://pypi.org/project/sovereignty-game/',
  footerText: 'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>',

  hero: {
    badge: 'Open source',
    headline: 'Sovereignty',
    headlineAccent: 'a board game about keeping your word.',
    description: 'Roll, trade, promise, betray. 2-4 players, 30 minutes, no screens required. The console keeps score — you keep your word. Optionally anchor results on the XRPL Testnet.',
    primaryCta: { href: '#usage', label: 'Get started' },
    secondaryCta: { href: 'handbook/', label: 'Read the Handbook' },
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
      title: 'Features',
      subtitle: 'Teach through consequences, not terminology.',
      features: [
        { title: 'Promises', desc: 'Say "I promise..." out loud. Keep it: +1 reputation. Break it: -2 reputation. The table decides.' },
        { title: 'Treaties', desc: 'Put your coins where your mouth is. Binding agreements with escrow stakes — promises with teeth.' },
        { title: 'Proofs', desc: 'Every round produces a SHA-256 fingerprint. Optionally anchor it on the XRPL Testnet — a wall nobody can erase.' },
      ],
    },
    {
      kind: 'data-table',
      id: 'tiers',
      title: 'Three Tiers',
      subtitle: 'Start simple, add complexity when ready.',
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
      title: 'Usage',
      cards: [
        { title: 'Install', code: 'pipx install sovereignty-game\n# or: uv tool install sovereignty-game' },
        { title: 'Quick start', code: 'sov tutorial           # learn in 60 seconds\nsov new -p Alice -p Bob # start a game\nsov turn               # roll, land, resolve\nsov end-round          # generate proof' },
      ],
    },
    {
      kind: 'features',
      id: 'diary',
      title: 'Diary Mode',
      subtitle: 'Optional on-chain verification — because trust is good, proof is better.',
      features: [
        { title: 'Wallet', desc: 'Create a free XRPL Testnet wallet. Test XRP has no value — it\'s play money.' },
        { title: 'Anchor', desc: 'Post your round proof hash to the ledger. Think of it as writing the score on a wall nobody can erase.' },
        { title: 'Verify', desc: 'Anyone can check the proof against the on-chain record. Trust but verify.' },
      ],
    },
  ],
};

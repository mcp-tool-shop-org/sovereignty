// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://mcp-tool-shop-org.github.io',
  base: '/sovereignty',
  integrations: [
    starlight({
      title: 'Sovereignty',
      description: 'Sovereignty handbook',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/mcp-tool-shop-org/sovereignty' },
      ],
      sidebar: [
        {
          label: 'Handbook',
          autogenerate: { directory: 'handbook' },
        },
      ],
      customCss: ['./src/styles/starlight-custom.css'],
      disable404Route: true,
      // F-002: surface the apple-touch + 32/16 favicons site-wide.
      // Starlight already injects favicon.svg via its own pipeline; we add
      // the supplementary sizes here. Paths are base-prefixed (Astro serves
      // public/ at the configured `base` so '/sovereignty/...' is correct
      // for the deployed GitHub Pages project URL).
      head: [
        { tag: 'link', attrs: { rel: 'apple-touch-icon', sizes: '180x180', href: '/sovereignty/apple-touch-icon.png' } },
        { tag: 'link', attrs: { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/sovereignty/favicon-32x32.png' } },
        { tag: 'link', attrs: { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/sovereignty/favicon-16x16.png' } },
        // OG + Twitter card meta tags. Asset at site/public/og-image.png is
        // served at https://mcp-tool-shop-org.github.io/sovereignty/og-image.png.
        // ci-docs handed off the exact tag block; do_not_drift on og:image path.
        { tag: 'meta', attrs: { property: 'og:title', content: 'Sovereignty — A board game about trust, trade, and keeping your word' } },
        { tag: 'meta', attrs: { property: 'og:description', content: "Sit down with 2-4 friends. Make promises out loud — keep them and people trust you, break them and they don't. No screens at the table." } },
        { tag: 'meta', attrs: { property: 'og:image', content: 'https://mcp-tool-shop-org.github.io/sovereignty/og-image.png' } },
        { tag: 'meta', attrs: { property: 'og:image:width', content: '1200' } },
        { tag: 'meta', attrs: { property: 'og:image:height', content: '630' } },
        { tag: 'meta', attrs: { property: 'og:url', content: 'https://mcp-tool-shop-org.github.io/sovereignty/' } },
        { tag: 'meta', attrs: { property: 'og:type', content: 'website' } },
        { tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
        { tag: 'meta', attrs: { name: 'twitter:title', content: 'Sovereignty' } },
        { tag: 'meta', attrs: { name: 'twitter:description', content: 'A board game about trust, trade, and keeping your word.' } },
        { tag: 'meta', attrs: { name: 'twitter:image', content: 'https://mcp-tool-shop-org.github.io/sovereignty/og-image.png' } },
      ],
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});

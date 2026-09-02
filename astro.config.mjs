import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://tohybetrhy.cz',
  // sekce Zdroje se přejmenovala na Radar; staré URL přesměrujeme
  redirects: { '/zdroje/': '/radar/' },
  integrations: [
    mdx(),
    sitemap({
      // přesměrovací stránky affiliate odkazů do sitemap nepatří
      filter: (page) => !page.includes('/go/'),
    }),
  ],
});

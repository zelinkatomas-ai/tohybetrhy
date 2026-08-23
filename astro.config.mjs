import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://tohybetrhy.cz',
  integrations: [
    mdx(),
    sitemap({
      // přesměrovací stránky affiliate odkazů do sitemap nepatří
      filter: (page) => !page.includes('/go/'),
    }),
  ],
});

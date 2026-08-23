/**
 * Volitelný Cloudflare Worker: serverové počítání prokliků na /go/<slug>/
 * imunní vůči ad-blockerům (nepotřebuje žádný JS na klientovi).
 *
 * Nasazení: viz README.md v této složce. Web funguje i bez tohoto Workeru –
 * prokliky pak měří jen Umami jako pageview stránky /go/<slug>/.
 *
 * Počítá do KV namespace GO_CLICKS klíče ve tvaru "<slug>:<YYYY-MM-DD>".
 * Čtení statistik: endpoint /go-stats?token=<STATS_TOKEN> (token nastavte
 * jako secret) nebo `wrangler kv key list`.
 */

const BOT_UA = /bot|crawl|spider|slurp|preview|fetch|monitor|curl|wget|headless/i;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // čtení statistik (chráněné tokenem)
    if (url.pathname === '/go-stats') {
      if (!env.STATS_TOKEN || url.searchParams.get('token') !== env.STATS_TOKEN) {
        return new Response('Forbidden', { status: 403 });
      }
      const list = await env.GO_CLICKS.list();
      const out = {};
      for (const key of list.keys) {
        out[key.name] = Number(await env.GO_CLICKS.get(key.name)) || 0;
      }
      return Response.json(out);
    }

    // počítání prokliků /go/<slug>/
    const match = url.pathname.match(/^\/go\/([a-z0-9-]+)\/?$/);
    if (match) {
      const ua = request.headers.get('user-agent') || '';
      const isBot = BOT_UA.test(ua) || request.cf?.botManagement?.verifiedBot;
      if (!isBot) {
        const day = new Date().toISOString().slice(0, 10);
        const key = `${match[1]}:${day}`;
        ctx.waitUntil(
          env.GO_CLICKS.get(key).then((v) =>
            env.GO_CLICKS.put(key, String((Number(v) || 0) + 1))
          )
        );
      }
    }

    // vždy pustit dál na statický web (Cloudflare Pages)
    return fetch(request);
  },
};

/**
 * Proxy pro Umami analytiku přes vlastní doménu.
 *
 * Blokátory reklam plošně blokují cloud.umami.is (EasyPrivacy seznam),
 * takže se část návštěv nikdy nezapočítá. Když měřicí skript i sběrný
 * endpoint běží pod tohybetrhy.cz, nemají blokátory co chytit. Umami je
 * cookieless a bez osobních dat, proxování oficiálně dokumentuje.
 *
 * Zapnutí: v Cloudflare Pages nastavit PUBLIC_UMAMI_URL=/stats
 * (místo https://cloud.umami.is) a redeploynout. Website ID se nemění.
 *
 *   GET  /stats/script.js  -> cloud.umami.is/script.js (cache 12 h)
 *   POST /stats/api/send   -> cloud.umami.is/api/send
 */
const UPSTREAM = 'https://cloud.umami.is';

export async function onRequest({ request, params }) {
  const path = (params.path ?? []).join('/');

  if (request.method === 'GET' && path === 'script.js') {
    const res = await fetch(`${UPSTREAM}/script.js`, {
      cf: { cacheTtl: 43200, cacheEverything: true },
    });
    return new Response(res.body, {
      status: res.status,
      headers: {
        'content-type': 'application/javascript; charset=utf-8',
        'cache-control': 'public, max-age=43200',
      },
    });
  }

  if (request.method === 'POST' && path === 'api/send') {
    // User-Agent a IP posíláme dál, protože z nich Umami počítá anonymní
    // hash návštěvníka (unikátní návštěvy); bez nich by byl každý hit nový.
    const res = await fetch(`${UPSTREAM}/api/send`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'user-agent': request.headers.get('user-agent') ?? '',
        'x-forwarded-for': request.headers.get('cf-connecting-ip') ?? '',
      },
      body: await request.text(),
    });
    return new Response(res.body, {
      status: res.status,
      headers: { 'content-type': res.headers.get('content-type') ?? 'text/plain' },
    });
  }

  return new Response('Not found', { status: 404 });
}

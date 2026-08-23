# Počítání affiliate prokliků na serveru (volitelné)

Cloudflare Worker, který počítá prokliky na `/go/<slug>/` přímo na edge –
funguje i lidem s ad-blockerem a filtruje zjevné boty podle User-Agentu
(a ověřené boty Cloudflare, pokud máte Bot Management).

Web funguje i bez něj: prokliky pak vidíte v Umami jako pageview
stránek `/go/xtb/` apod. Worker je druhá, přesnější vrstva.

## Nasazení

```bash
cd extras/go-click-counter
npx wrangler kv namespace create GO_CLICKS   # vrácené id vložte do wrangler.toml
npx wrangler secret put STATS_TOKEN          # zvolte si tajný token
npx wrangler deploy
```

Pak v Cloudflare dashboardu: Workers Routes → přidat route
`tohybetrhy.cz/go/*` → worker `tohybetrhy-go-counter`.

## Čtení statistik

```
https://tohybetrhy.cz/go-stats?token=<VÁŠ_TOKEN>
```

vrací JSON `{ "xtb:2026-07-29": 12, "degiro:2026-07-29": 5, ... }`.
Alternativně `npx wrangler kv key list --binding GO_CLICKS`.

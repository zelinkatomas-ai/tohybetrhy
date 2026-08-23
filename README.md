# Momentum web – kostra projektu

Statický web (Astro) s automaticky aktualizovanými daty o momentu trhů
(třídy aktiv, americké sektory, momentum ETF vs benchmarky; výnosy v měně
fondu, grafy od 1. 1. 2024). Architektura odděluje **obsah** (Markdown/MDX),
**data** (JSON generované pipeline) a **prezentaci** (komponenty).

## Struktura

```
pipeline/fetch_data.py        Python pipeline: Yahoo Finance → JSON (skupiny v GROUPS)
src/data/*.json               Vygenerovaná data: assets, sectors, momentum_etfs (zdroj pravdy)
src/components/LineChart.astro    Čárový graf (ECharts) – dostane data, vykreslí se sám
src/components/MomentumTable.astro  Tabulka momenta – server-side render, dobré SEO
src/layouts/                  Base (celý web) a ArticleLayout (články)
src/pages/index.astro         Dashboard
src/pages/clanky/*.mdx        Články – Markdown, do kterého vložíš graf jedním řádkem
src/config/links.json         Centrální správa affiliate/externích odkazů (/go/<klíč>/)
src/styles/tokens.css         Barvy a tokeny celého webu (validovaná paleta, dark mode)
.github/workflows/update-data.yml  Týdenní automatická aktualizace dat
```

## Rychlý start

```bash
# 1. data (Python 3.11+)
pip install -r pipeline/requirements.txt
python3 pipeline/fetch_data.py

# 2. web (Node 20+)
npm install
npm run dev        # vývojový server na http://localhost:4321
npm run build      # produkční build do dist/
```

## Jak se s tím pracuje

- **Nový článek** = nový soubor `src/pages/clanky/*.mdx`. Graf nebo tabulku vložíš
  importem komponenty a jedním řádkem – viz `co-je-momentum.mdx`.
- **Nové ETF / třída aktiv** = jeden záznam v poli `ETFS` v `pipeline/fetch_data.py`.
  Po spuštění pipeline se samo objeví v tabulce i grafu.
- **Změna affiliate odkazu** = jeden řádek v `src/config/links.json`. Na webu se
  vždy odkazuje na `/go/<klíč>/`, takže obsah se nikdy neupravuje.
- **Změna vzhledu** = `src/styles/tokens.css` (barvy, ramky) nebo příslušná
  komponenta. Barvy sérií mají pevné pořadí a paleta je validovaná pro
  barvoslepost ve světlém i tmavém režimu – při změně znovu ověř.

## Nasazení (zdarma)

1. Repo pushni na GitHub.
2. Připoj ho na **Cloudflare Pages** (nebo Netlify): build command `npm run build`,
   output `dist`. Každý push = nový deploy.
3. Workflow `update-data.yml` každý pátek stáhne čerstvá data, commitne je
   a tím spustí nový deploy. Frekvenci změníš v cronu, ručně spustíš na GitHubu
   záložka Actions → Aktualizace dat → Run workflow.

## Analytika (Umami)

Měření je bez cookies (žádná cookie lišta) a načítá se jen v produkčním
buildu, když jsou nastavené env proměnné – viz `.env.example`:

1. Rozjeďte Umami: nejjednodušeji [Umami Cloud](https://umami.is) (free tier),
   plná kontrola = self-host (oficiální Docker image; DB Postgres, poběží na
   malém VPS nebo Vercel + Neon/Supabase free tier).
2. V Umami vytvořte web a zkopírujte Website ID.
3. Na Cloudflare Pages nastavte env proměnné `PUBLIC_UMAMI_URL`
   a `PUBLIC_UMAMI_WEBSITE_ID` (Settings → Environment variables) a redeploy.

Co tím dostanete: návštěvnost, zdroje, stránky – a díky architektuře
`/go/<klíč>/` i affiliate prokliky jako pageview, bez konfigurace eventů.
Boti se do Umami prakticky nepočítají (nespouštějí JS); celkový provoz
včetně botů vidíte v Cloudflare (zone analytics, zapněte i Bot Fight Mode).
Rozdíl obou čísel ≈ botí provoz.

- `public/robots.txt` – AI crawlery jsou vědomě povolené (viditelnost
  v AI odpovědích), připravený blok pro jejich zákaz stačí odkomentovat.
- Sitemap se generuje automaticky (`@astrojs/sitemap`).
- `extras/go-click-counter/` – volitelný Cloudflare Worker: serverové
  počítání affiliate prokliků imunní vůči ad-blokerům (návod uvnitř).

## Datové zdroje a limity

- Ceny ETF: veřejné chart API Yahoo Finance (bez klíče; pro osobní projekt OK,
  pro růst zvaž placený zdroj – EODHD, Twelve Data apod.).
- Výnosy se počítají v nativní měně fondu (měna se ukládá k řádku tabulky).
  Případný měnový přepočet lze doplnit jako samostatnou vrstvu (Frankfurter
  API / ČNB, bez klíče) – záměrně není součástí určení momenta.

## Právní poznámka

Web je informační/vzdělávací, nesmí poskytovat individuální investiční
poradenství. Disclaimer je v patičce (`Base.astro`) – nech ho tam a před
spuštěním placených funkcí si ověř regulatorní hranice (ČNB).

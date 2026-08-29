# To hýbe trhy — stav projektu a fronta úkolů

> Živý pracovní dokument. Aktualizováno 2026-08-29. Web: tohybetrhy.cz (doména zatím nekoupena).
> Motto: Přehled, kde je na trzích momentum, kam se přesouvá kapitál a jaký je aktuální sentiment.

## Co je hotové

- **Architektura**: Astro (statický web) + Python pipeline (`pipeline/fetch_data.py`)
  generující JSON do `src/data/`. Obsah (MDX), data (JSON) a prezentace
  (komponenty) důsledně oddělené. Deploy cíl: Cloudflare Pages (zdarma).
- **Homepage jako teaser**: generovaný slovní vzkaz (`summary.json` — skládá ho
  pipeline z dat), dlaždice regionů, top 3 sektory, top 3 momentum ETF,
  mini-přehled chytrých peněz, poslední zdroje. Grafy až na podstránkách.
- **Sekce**: Regiony (4 hlavní + Čína, Indie, Japonsko, J. Amerika, Afrika/JAR),
  Sektory (11× SPDR, řazeno dle 3M) + **Bitcoin** jako oddělený barometr
  rizikového apetitu, Momentum ETF vs benchmarky (SPMO, MTUM, XSMO, FMTM,
  IDMO, IEMO, PIE, EEMO vs SPY/URTH), Chytré peníze vs retail (CFTC CoT,
  NAAIM, podíl pákových ETF na objemu), Zdroje (kurátorované, zatím ukázkové).
- **Detail každého titulu**: `/etf/<slug>/` generované z dat + popisů
  v `src/config/etf-info.json` (30+ titulů vč. BTC-USD).
- **Metodika**: na každé detailové stránce; momentum = klouzavé výnosy
  4/13/26/52 týdnů v měně fondu, signál = cena vs 52týdenní průměr,
  grafy od 1. 1. 2024. Bez měnových přepočtů (záměrně).
- **Automatická aktualizace dat**: GitHub Actions, pátky (`update-data.yml`) —
  funguje, commituje do repa a tím spouští redeploy.
- **Analytika (kód připraven)**: Umami snippet za env proměnnými
  (`PUBLIC_UMAMI_URL`, `PUBLIC_UMAMI_WEBSITE_ID`, viz `.env.example`),
  robots.txt (AI crawlery vědomě povolené), sitemap, volitelný Cloudflare
  Worker na počítání /go/* prokliků (`extras/go-click-counter/`).
- **Affiliate**: všechny externí odkazy přes `/go/<klíč>/`,
  správa v `src/config/links.json` (zatím bez skutečných provizních URL).

## Provozní kroky (na straně vlastníka)

- [ ] Napojit repo na **Cloudflare Pages** (build `npm run build`, output `dist`)
      → web poběží na `*.pages.dev` ještě před doménou.
- [ ] Koupit doménu **tohybetrhy.cz** a přesměrovat na Pages.
- [ ] Založit **Umami** (Cloud free tier nebo self-host) a nastavit
      env proměnné v Cloudflare Pages. Zapnout Bot Fight Mode.
- [ ] Registrace do **affiliate programů** (XTB, Portu, DEGIRO…) a doplnění
      skutečných URL do `src/config/links.json`.
- [ ] Nahradit ukázkové položky v `src/config/sources.json` skutečnými
      (mají `demo: true`; první kandidát: Vanda retail flows graf z X).

## Fronta vývoje (v pořadí priorit)

- [x] **Automat na plnění Zdrojů**: `pipeline/fetch_sources.py` — RSS feedy
      (MarketWatch, FT, Yahoo Finance, Investing.com; CNBC blokuje některé IP,
      Reuters/Bloomberg veřejné RSS nemají) → filtr klíčových slov dle
      regionů/sektorů → návrhy do `pipeline/sources_proposals.json` →
      `--approve 1,3` přesune vybrané do `sources.json` (kurátor pak doladí
      summary + why). Cache viděných URL v `pipeline/sources_seen.json`
      (obojí v .gitignore). Spouští se ručně, ne v CI.
- [x] **Reddit sentiment**: ApeWisdom API napojeno v pipeline
      (`fetch_reddit`) → `smart_money.json` klíč `reddit`. Top 10 tickerů,
      zmínky/24 h, upvoty; změna t/t proti snapshotu z minulého běhu
      (top 50 se ukládá přímo do JSON, první běh změnu nemá). Dlaždice
      na homepage + tabulka a metodika na /chytre-penize/.
- [x] **Směrový retail flow — prozkoumáno (2026-08-29)**: stará veřejná
      stránka Fidelity (eresearch…fidelityTopOrders.jhtml) už neexistuje —
      302 na SPA (digital.fidelity.com/prgw/digital/research/src), data se
      dotahují JS/za loginem → **nereplikovatelné bez skládání s jejich
      interním API, neriskovat**. Lepší kandidát: **Nasdaq Retail Trading
      Activity Tracker (RTAT)** — free tier `NDAQ/RTAT10` na data.nasdaq.com:
      denně top 10 retailových tickerů s aktivitou a *směrovým* net
      sentimentem; stačí bezplatný API klíč (do GitHub Actions jako secret
      `NASDAQ_DATA_LINK_API_KEY`). Endpoint ověřen (bez klíče vrací
      QEPx04 = existuje, chce klíč). Až bude klíč, přidat `fetch_rtat()`
      vedle `fetch_reddit()`.
- [x] **BTC do generovaného vzkazu** na homepage — věta o signálu vs 52t
      průměr (`sentences.btc` v summary.json, skládá se z crypto.json).
- [ ] Zvážit: backtest sekce (GEM / dual momentum na našich datech),
      e-mailový digest při změně signálů (budoucí platený tier).

## Známé věci / hlídat

- **NAAIM**: přestal publikovat xlsx; fallback čte jejich embed graf, ale data
  jsou ~3 měsíce stará → indikátor se automaticky skrývá (guard >60 dní).
  Občas zkontrolovat, jestli NAAIM nezačal publikovat znovu.
- **FMTM** = MarketDesk Focused U.S. Momentum, fond od 2024 (krátká historie).
  Kdyby byl záměr Fidelity Momentum, ticker je FDMO (změna 1 řádku v GROUPS).
- **Yahoo chart API** je neoficiální (bez klíče). Funguje spolehlivě, ale při
  růstu webu zvážit placený zdroj (EODHD, Twelve Data).
- Právní: web je informační/vzdělávací, žádné individuální poradenství;
  disclaimer v patičce nechat, před placenými funkcemi ověřit hranice ČNB.

## Jak se s projektem pracuje (rychlá reference)

```bash
pip install -r pipeline/requirements.txt
python3 pipeline/fetch_data.py   # stáhne data, přegeneruje src/data/*.json
npm install
npm run dev                      # lokální náhled
npm run build                    # produkční build do dist/
```

Nový sledovaný titul = 1 záznam v `GROUPS` (`pipeline/fetch_data.py`)
+ volitelně popis v `src/config/etf-info.json`. Nový článek = MDX soubor
v `src/pages/clanky/`. Změna barev = `src/styles/tokens.css`.

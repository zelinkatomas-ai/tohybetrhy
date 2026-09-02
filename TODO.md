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
- [x] **Stránka Likvidita** (/likvidita/): hromadí se v systému volná
      hotovost? Pět teploměrů v `build_liquidity()` → `liquidity.json`:
      čistá likvidita Fedu (WALCL − TGA − ON RRP, FRED), peníze vs inflace
      USA (M2 vs CPI) i eurozóna (M3 vs HICP, ECB Data Portal), zaparkovaná
      hotovost (vklady H.8 + retail MMF, podíl MMF na M2), S&P 500 / M2
      a dolarový index. Vše FRED/ECB/Yahoo CSV bez API klíče. Dlaždice
      na homepage + `sentences.liquidity` ve vzkazu. Záměrně teploměry
      s metodikou, ne Risk-On/Off semafor (prahy bez backtestů neslibovat).
- [ ] Likvidita – kandidáti na rozšíření: AAII Asset Allocation Survey
      (podíl hotovosti v portfoliích; data za free registrací – ověřit
      replikovatelnost), týdenní MMF od ICI (xls, křehké, licence?).
- [x] **Sekce Sítě** (/socialni-site/): Reddit přesunut z Chytrých peněz
      (data nově v `social.json`, klíč `reddit`) + nový StockTwits trending
      (`fetch_stocktwits`, veřejné API bez klíče). Chytré peníze zpět u tří
      původních pohledů (CoT, NAAIM, retail proxy).
- [x] **VIX do Chytrých peněz**: `fetch_vix` (Yahoo ^VIX + ^VIX3M) —
      graf VIX vs 52t průměr + termínová struktura VIX3M/VIX (pod 1 =
      backwardace = akutní stres; věta do `sentences.smart` jen v tom
      případě). Dlaždice na homepage. Případná budoucí stránka „Nálada
      trhu" (VIX + put/call ratio z CBOE + AAII survey) — zatím netříštit.
- [x] **Sekce Rizika** (/rizika/): kvantifikovaná geopolitika —
      `build_risks()` → `risks.json`: index GPR (Caldara–Iacoviello,
      denní řada z webu autorů, týdenní průměr vs dlouhodobý průměr),
      EPU (FRED `USEPUINDXD`) a relativní síla obranných ETF (ITA, EUAD)
      vůči S&P 500. Věta `sentences.risks` jen při GPR > 1,5× průměr.
      Metodika poctivě říká, že čisté geopolitické šoky trhy vstřebávají
      rychle — je to kontext, ne signál.
- [x] **Polymarket** (`fetch_polymarket` → `polymarket.json`): veřejné
      gamma API, výběr mechanicky — nejobchodovanější otevřené otázky
      (objem 24 h) tříděné podle tagů do skupin `geopolitics` (tabulka
      na /rizika/) a `macro` (tabulka na /likvidita/). Seznam se sám
      obměňuje s děním, žádná ruční kurátorská volba. Další skupiny
      (volby, krypto…) = jen přidat tagy do POLYMARKET_GROUPS.
- [ ] **Sítě – kandidáti na rozšíření**: YouTube Data API (zdarma s klíčem,
      secret `YOUTUBE_API_KEY`; metrika: videa + zhlédnutí k top tickerům
      z Redditu = pozornost napříč platformami). Wikipedia pageviews API
      (bez klíče; návštěvnost článků firem = akademicky ověřená proxy
      retailové pozornosti; chce mapování ticker→článek). Twitter/X jen
      s placeným API (od ~100 USD/měs.) – bez něj nereplikovatelné.
      Google Trends: neoficiální API, z cloudových IP blokuje – neriskovat.
- [ ] **Denní aktualizace rychlých dat** (rozmyšleno 2026-08-30, odloženo):
      druhý lehký workflow, cron `30 21 * * 1-5` (po uzavření NYSE, funguje
      v EDT i EST), `fetch_data.py --daily` aktualizuje jen `reddit`
      v smart_money.json (popisky t/t → d/d). Momentum zůstává týdenní
      (denní přepočet částečných týdenních barů = šum, proti metodice).
      Až bude klíč NASDAQ_DATA_LINK_API_KEY, přidat do denního běhu RTAT.
- [ ] Zvážit: backtest sekce (GEM / dual momentum na našich datech),
      e-mailový digest při změně signálů (budoucí platený tier).

## Známé věci / hlídat

- **FRED blokuje IP GitHub Actions runnerů** (CSV endpoint visí do timeoutu,
  browser hlavičky nepomáhají). Vyřešeno bezplatným klíčem v secretu
  `FRED_API_KEY` (nastaven 2026-08-30) — s klíčem jde oficiální API první,
  CSV zůstává fallback. Kdyby klíč přestal platit: nový na
  https://fred.stlouisfed.org/docs/api/api_key.html, FRED grafy/dlaždice
  se do té doby samy skryjí.
- **HICP po rebasi na 2025=100**: staré řady (ECB ICP…4.ANR/INX i Eurostat
  prc_hicp_manr) zamrzly na 2025-12. Pipeline zkouší i kandidátní nový kod
  `prc_hicp25_manr`; pokud nezabere, dohledat skutečný nový kód datasetu na
  ec.europa.eu/eurostat a doplnit do `fetch_eurostat_hicp()`. Graf zatím
  poctivě ukazuje M3 čerstvé a čáru HICP končící u posledních dat.
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

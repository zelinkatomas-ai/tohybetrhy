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

- [ ] **Automat na plnění Zdrojů**: RSS feedy (Reuters, FT, Bloomberg…) →
      filtr klíčových slov dle regionů/sektorů → návrh shrnutí → ruční
      schválení (kurátorský krok zůstává lidský). Výstup = `sources.json`.
- [ ] **Reddit sentiment**: ApeWisdom má veřejné API (apewisdom.io/api),
      alternativa AltIndex. Metrika: top tickery, zmínky, změna t/t.
      Zobrazit jako dlaždici v Chytrých penězích + detail.
- [ ] **Směrový retail flow**: pákové ETF měří aktivitu, ne směr. Prozkoumat
      veřejnou stránku Fidelity s denními top obchody klientů (poměr
      buy/sell příkazů). Inspirace: VandaTrack (placené, nereplikovatelné).
- [ ] **BTC do generovaného vzkazu** na homepage (věta o signálu vs 52t průměr).
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

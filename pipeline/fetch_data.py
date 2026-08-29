#!/usr/bin/env python3
"""
Datová pipeline: stáhne ceny ETF (Yahoo Finance chart API), spočítá momentum
v NATIVNÍ měně fondu a vygeneruje JSON soubory pro web.

Momentum měříme v měně fondu – kurzové riziko je téma samo o sobě, ale pro
určení toho, "co jede", by přepočet měn jen přidával šum.

Výstupy (src/data/):
  - regions.json         ... regiony (tabulka + graf hlavních čtyř)
  - sectors.json         ... americké sektory, SPDR (tabulka, řazeno dle 3M)
  - crypto.json          ... Bitcoin (tabulka + graf)
  - momentum_etfs.json   ... momentum ETF vs benchmarky (tabulka + graf)
  - smart_money.json     ... chytré peníze vs retail (CoT, NAAIM, pákové ETF)
  - summary.json         ... generovaný slovní vzkaz pro hlavní stránku

Spouštění:  python3 pipeline/fetch_data.py
Závislosti: requests (pip install -r pipeline/requirements.txt)
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Konfigurace – JEDINÉ místo, kde se přidávají/mění sledované tituly.
#   chart=True      ... titul se kreslí v čárovém grafu skupiny
#   benchmark=True  ... v grafu čárkovaně, v tabulce oddělen jako srovnání
# ---------------------------------------------------------------------------
CHART_START = "2024-01-01"   # všechny grafy začínají tady
HISTORY_RANGE = "4y"          # stahovaná historie (kvůli 12M oknu a 52t průměru)
MOMENTUM_WEEKS = {"r1": 4, "r3": 13, "r6": 26, "r12": 52}
SMA_WEEKS = 52

GROUPS: dict[str, dict] = {
    "regions": {
        "file": "regions.json",
        "note": "Regiony přes ETF, výnosy v měně fondu. Hlavní čtyři regiony i v grafu.",
        "items": [
            {"ticker": "IWDA.AS", "name": "Svět (MSCI World)",   "chart": True, "core": True},
            {"ticker": "CSPX.AS", "name": "USA (S&P 500)",       "chart": True, "core": True},
            {"ticker": "MEUD.PA", "name": "Evropa (STOXX 600)",  "chart": True, "core": True},
            {"ticker": "EMIM.AS", "name": "Rozvíjející se trhy", "chart": True, "core": True},
            {"ticker": "MCHI",    "name": "Čína"},
            {"ticker": "QDV5.DE", "name": "Indie"},
            {"ticker": "CSJP.MI", "name": "Japonsko"},
            {"ticker": "ILF",     "name": "Jižní Amerika"},
            {"ticker": "EZA",     "name": "Afrika (JAR)"},
        ],
    },
    "sectors": {
        "file": "sectors.json",
        "note": "Americké sektory (Select Sector SPDR), výnosy v USD. Řazeno podle 3M momenta.",
        "sort_by": "r3",
        "items": [
            {"ticker": "XLK",  "name": "Technologie"},
            {"ticker": "XLC",  "name": "Komunikační služby"},
            {"ticker": "XLY",  "name": "Zbytná spotřeba"},
            {"ticker": "XLF",  "name": "Finance"},
            {"ticker": "XLV",  "name": "Zdravotnictví"},
            {"ticker": "XLI",  "name": "Průmysl"},
            {"ticker": "XLB",  "name": "Materiály"},
            {"ticker": "XLE",  "name": "Energie"},
            {"ticker": "XLP",  "name": "Základní spotřeba"},
            {"ticker": "XLU",  "name": "Utility"},
            {"ticker": "XLRE", "name": "Reality"},
        ],
    },
    "crypto": {
        "file": "crypto.json",
        "note": "Bitcoin, spotová cena v USD. Obchoduje se nonstop; vzorkujeme týdně jako ostatní data.",
        "items": [
            {"ticker": "BTC-USD", "name": "Bitcoin", "chart": True},
        ],
    },
    "momentum_etfs": {
        "file": "momentum_etfs.json",
        "note": "ETF stavěná na momentum faktoru vs široký trh (čárkovaně). Výnosy v měně fondu.",
        "items": [
            {"ticker": "SPMO",    "name": "SPMO – S&P 500 Momentum",            "chart": True},
            {"ticker": "MTUM",    "name": "MTUM – MSCI USA Momentum",           "chart": True},
            {"ticker": "XSMO",    "name": "XSMO – S&P SmallCap Momentum",       "chart": True},
            {"ticker": "FMTM",    "name": "FMTM – Focused U.S. Momentum",       "chart": True},
            {"ticker": "IDMO",    "name": "IDMO – Intl Developed Momentum",     "chart": True},
            {"ticker": "IEMO.MI", "name": "IEMO – Europe Momentum (UCITS)"},
            {"ticker": "PIE",     "name": "PIE – Emerging Markets Momentum"},
            {"ticker": "EEMO",    "name": "EEMO – S&P EM Momentum"},
            {"ticker": "SPY",     "name": "USA (S&P 500)",   "chart": True, "benchmark": True},
            {"ticker": "URTH",    "name": "Svět (MSCI World)", "chart": True, "benchmark": True},
        ],
    },
}

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "data"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; momentum-web-pipeline)"}


def fetch_yahoo_weekly(ticker: str) -> tuple[dict[str, float], str]:
    """Vrátí ({ISO datum: adjusted close}, měna)."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?range={HISTORY_RANGE}&interval=1wk&events=div%2Csplit"
    )
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    currency = result["meta"].get("currency", "?")
    ts = result["timestamp"]
    ind = result["indicators"]
    closes = (ind.get("adjclose", [{}])[0].get("adjclose")
              or ind["quote"][0]["close"])
    out: dict[str, float] = {}
    for t, c in zip(ts, closes):
        if c is not None:
            out[date.fromtimestamp(t).isoformat()] = round(float(c), 4)
    return out, currency


def pct(series: list[float], weeks_back: int) -> float | None:
    if len(series) <= weeks_back:
        return None
    old, new = series[-1 - weeks_back], series[-1]
    return round((new / old - 1) * 100, 2)


def build_group(key: str, cfg: dict) -> None:
    rows = []
    raw_series = []  # {name, benchmark, points: {date: indexovaná hodnota}}

    for item in cfg["items"]:
        print(f"[{key}] Stahuji {item['ticker']} ({item['name']}) ...")
        prices, currency = fetch_yahoo_weekly(item["ticker"])
        time.sleep(1)  # ohleduplnost k API

        dates = sorted(prices)
        vals = [prices[d] for d in dates]

        sma = (sum(vals[-SMA_WEEKS:]) / SMA_WEEKS) if len(vals) >= SMA_WEEKS else None
        rows.append({
            "ticker": item["ticker"],
            "name": item["name"],
            "currency": currency,
            "benchmark": bool(item.get("benchmark")),
            "core": bool(item.get("core")),
            **{k: pct(vals, w) for k, w in MOMENTUM_WEEKS.items()},
            "signal": ("above" if vals[-1] >= sma else "below") if sma else None,
        })

        if item.get("chart"):
            idx = [i for i, d in enumerate(dates) if d >= CHART_START]
            base = vals[idx[0]]
            raw_series.append({
                "name": item["name"],
                "benchmark": bool(item.get("benchmark")),
                "points": {dates[i]: round(vals[i] / base * 100, 2) for i in idx},
            })

    # řazení tabulky (benchmarky vždy dole)
    if cfg.get("sort_by"):
        k = cfg["sort_by"]
        rows.sort(key=lambda r: (r["benchmark"], -(r[k] if r[k] is not None else -999)))

    # graf: společná osa, série zarovnané přes null
    chart = None
    if raw_series:
        chart_dates = sorted({d for s in raw_series for d in s["points"]})
        chart = {
            "dates": chart_dates,
            "series": [
                {"name": s["name"], "benchmark": s["benchmark"],
                 "values": [s["points"].get(d) for d in chart_dates]}
                for s in raw_series
            ],
        }

    (OUT_DIR / cfg["file"]).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": cfg["note"],
        "rows": rows,
        "chart": chart,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{key}] -> {cfg['file']}")


# ---------------------------------------------------------------------------
# Chytré peníze vs retail
# ---------------------------------------------------------------------------

def fetch_cot() -> dict:
    """CFTC Traders in Financial Futures – E-mini S&P 500, čisté pozice
    jako % open interestu. Asset manažeři = instituce, leveraged funds =
    hedge fondy, nonreportable = malí obchodníci (proxy retailu)."""
    import urllib.parse
    where = urllib.parse.quote(
        f"contract_market_name = 'E-MINI S&P 500' AND "
        f"report_date_as_yyyy_mm_dd >= '{CHART_START}'"
    )
    url = ("https://publicreporting.cftc.gov/resource/gpe5-46if.json"
           f"?$where={where}&$order=report_date_as_yyyy_mm_dd&$limit=5000")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    dates, inst, hedge, small = [], [], [], []
    for row in r.json():
        oi = float(row["open_interest_all"])
        if oi <= 0:
            continue
        net = lambda l, s: round((float(row[l]) - float(row[s])) / oi * 100, 2)
        dates.append(row["report_date_as_yyyy_mm_dd"][:10])
        inst.append(net("asset_mgr_positions_long", "asset_mgr_positions_short"))
        hedge.append(net("lev_money_positions_long", "lev_money_positions_short"))
        small.append(net("nonrept_positions_long_all", "nonrept_positions_short_all"))
    return {
        "dates": dates,
        "series": [
            {"name": "Instituce (asset manažeři)", "values": inst},
            {"name": "Hedge fondy (leveraged funds)", "values": hedge},
            {"name": "Malí obchodníci (retail)", "values": small},
        ],
    }


def fetch_naaim() -> dict:
    """NAAIM Exposure Index – průměrná akciová expozice aktivních správců
    (0 = mimo trh, 100 = plně zainvestováno).

    Primárně hledáme xlsx s historií na stránce programu (NAAIM ho občas
    publikuje, občas ne); záložně čteme data z jejich vloženého grafu
    (index.naaim.org/embeddable/chart). Pokud je poslední hodnota starší
    než 60 dní, indikátor raději vynecháme, než abychom ukazovali
    zastaralá čísla."""
    import html as html_mod
    import io
    import re

    points: dict[str, float] = {}

    # 1) xlsx s kompletní historií (pokud je odkaz na stránce)
    try:
        page = requests.get("https://naaim.org/programs/naaim-exposure-index/",
                            headers=HEADERS, timeout=30)
        m = re.search(r'href="([^"]+\.xlsx)"', page.text)
        if m:
            from openpyxl import load_workbook
            xlsx = requests.get(m.group(1), headers=HEADERS, timeout=60)
            wb = load_workbook(io.BytesIO(xlsx.content), read_only=True)
            ws = wb.active
            rows = ws.iter_rows(values_only=True)
            header = next(rows)
            i_date = header.index("Date")
            i_mean = next(i for i, h in enumerate(header) if h and "Mean" in str(h))
            for row in rows:
                d, v = row[i_date], row[i_mean]
                if d is None or v is None:
                    continue
                iso = d.date().isoformat() if hasattr(d, "date") else str(d)[:10]
                if iso >= CHART_START:
                    points[iso] = round(float(v), 1)
    except Exception as e:
        print(f"[smart_money] NAAIM xlsx nedostupné ({e}), zkouším embed")

    # 2) záloha: data z vloženého grafu
    if not points:
        t = requests.get("https://index.naaim.org/embeddable/chart",
                         headers=HEADERS, timeout=30).text
        u = html_mod.unescape(t)
        lab = re.search(r'"labels":(\[[^\]]*\])', u)
        dat = re.search(r'"data":(\[[^\]]*\])', u)
        if not (lab and dat):
            raise RuntimeError("NAAIM: data nenalezena ani v embedu")
        labels = json.loads(lab.group(1))
        values = json.loads(dat.group(1))
        for d, v in zip(labels, values):
            if str(d)[:10] >= CHART_START:
                points[str(d)[:10]] = round(float(v), 1)

    dates = sorted(points)
    if not dates:
        raise RuntimeError("NAAIM: žádná data")
    # kontrola čerstvosti – zastaralý indikátor je horší než žádný
    age_days = (date.today() - date.fromisoformat(dates[-1])).days
    if age_days > 60:
        raise RuntimeError(f"NAAIM: poslední hodnota je {age_days} dní stará, vynechávám")
    return {
        "dates": dates,
        "series": [{"name": "NAAIM Exposure Index", "values": [points[d] for d in dates]}],
    }


def fetch_retail_proxy() -> dict:
    """Proxy retailového apetitu: podíl pákových ETF (TQQQ, SQQQ, SPXL, SPXS)
    na dolarovém objemu vůči SPY + QQQ. Pákové ETF obchoduje převážně retail."""
    def dollar_volume(ticker: str) -> dict[str, float]:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?range={HISTORY_RANGE}&interval=1wk")
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        out = {}
        for t, c, v in zip(res["timestamp"], q["close"], q["volume"]):
            if c and v:
                out[date.fromtimestamp(t).isoformat()] = c * v
        return out

    lev = ["TQQQ", "SQQQ", "SPXL", "SPXS"]
    base = ["SPY", "QQQ"]
    vols: dict[str, dict[str, float]] = {}
    for t in lev + base:
        print(f"[smart_money] Stahuji objemy {t} ...")
        vols[t] = dollar_volume(t)
        time.sleep(1)

    common = sorted(set.intersection(*(set(v) for v in vols.values())))
    common = [d for d in common if d >= CHART_START]
    values = [
        round(sum(vols[t][d] for t in lev) / sum(vols[t][d] for t in base) * 100, 1)
        for d in common
    ]
    return {
        "dates": common,
        "series": [{"name": "Objem pákových ETF vs SPY+QQQ (%)", "values": values}],
    }


def fetch_reddit() -> dict:
    """Reddit sentiment (ApeWisdom, veřejné API): top tickery podle počtu
    zmínek za posledních 24 h napříč investičními subreddity (WSB, r/stocks…).

    Změna t/t se počítá proti snapshotu z minulého běhu pipeline (typicky
    před týdnem) uloženému přímo v smart_money.json; při prvním běhu změna
    není k dispozici a dopočítá se od druhého týdne."""
    import html as html_mod

    r = requests.get("https://apewisdom.io/api/v1.0/filter/all-stocks/page/1",
                     headers=HEADERS, timeout=30)
    r.raise_for_status()
    results = r.json()["results"]

    # předchozí snapshot (kvůli změně t/t) – čteme starý soubor před přepisem
    prev_mentions: dict[str, int] = {}
    prev_date: str | None = None
    try:
        old = json.loads((OUT_DIR / "smart_money.json").read_text(encoding="utf-8"))
        snap = (old.get("reddit") or {}).get("snapshot") or {}
        prev_mentions = snap.get("mentions") or {}
        prev_date = snap.get("date")
    except Exception:
        pass

    top = []
    for row in results[:10]:
        ticker = row["ticker"]
        mentions = int(row["mentions"])
        prev = prev_mentions.get(ticker)
        top.append({
            "rank": int(row["rank"]),
            "ticker": ticker,
            "name": html_mod.unescape(row["name"]),
            "mentions": mentions,
            "upvotes": int(row["upvotes"]),
            "prev_mentions": prev,
            "change_pct": round((mentions / prev - 1) * 100, 1) if prev else None,
        })

    return {
        "top": top,
        "prev_date": prev_date,
        # snapshot top 50, aby měly změnu i tituly, které se do top 10 teprve dostanou
        "snapshot": {
            "date": date.today().isoformat(),
            "mentions": {r_["ticker"]: int(r_["mentions"]) for r_ in results[:50]},
        },
    }


def build_smart_money() -> None:
    charts = {}
    for key, fn in [("cot", fetch_cot), ("naaim", fetch_naaim),
                    ("retail", fetch_retail_proxy), ("reddit", fetch_reddit)]:
        try:
            print(f"[smart_money] {key} ...")
            charts[key] = fn()
        except Exception as e:  # jeden rozbitý zdroj nesmí shodit celý build
            print(f"[smart_money] {key} SELHALO: {e}")
            charts[key] = None

    (OUT_DIR / "smart_money.json").write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "CoT: čisté pozice v E-mini S&P 500 futures jako % open interestu (CFTC, týdně). "
                "NAAIM: průměrná akciová expozice aktivních správců. "
                "Retail proxy: podíl pákových ETF na dolarovém objemu. "
                "Reddit: zmínky za 24 h dle ApeWisdom, změna t/t proti minulému běhu.",
        **charts,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[smart_money] -> smart_money.json")


# ---------------------------------------------------------------------------
# Generovaný slovní vzkaz pro hlavní stránku
# ---------------------------------------------------------------------------

def _fmt(v: float) -> str:
    return f"{v:+.1f}".replace(".", ",").replace("+", "+") + " %"


def build_summary() -> None:
    regions = json.loads((OUT_DIR / "regions.json").read_text(encoding="utf-8"))
    sectors = json.loads((OUT_DIR / "sectors.json").read_text(encoding="utf-8"))
    etfs = json.loads((OUT_DIR / "momentum_etfs.json").read_text(encoding="utf-8"))
    smart = json.loads((OUT_DIR / "smart_money.json").read_text(encoding="utf-8"))
    crypto = json.loads((OUT_DIR / "crypto.json").read_text(encoding="utf-8"))

    by_ticker = {r["ticker"]: r for r in regions["rows"]}

    # 1) globální vzkaz podle světového indexu
    world = by_ticker["IWDA.AS"]
    r3, above = world["r3"] or 0, world["signal"] == "above"
    if above and r3 >= 2:
        s_global = (f"Globální momentum zůstává pozitivní – světový index se drží nad "
                    f"52týdenním průměrem a za poslední tři měsíce přidal {_fmt(r3)}.")
    elif above and r3 >= 0:
        s_global = ("Globální momentum je neutrální až mírně pozitivní – světový index "
                    "se drží nad 52týdenním průměrem, tempo růstu ale polevilo.")
    elif above:
        s_global = (f"Globální momentum slábne – trh se zatím drží nad dlouhodobým "
                    f"průměrem, poslední tři měsíce jsou ale ztrátové ({_fmt(r3)}).")
    elif r3 > 0:
        s_global = (f"Trh se odráží ode dna – světový index je stále pod 52týdenním "
                    f"průměrem, krátkodobé momentum ale sílí ({_fmt(r3)} za tři měsíce).")
    else:
        s_global = (f"Globální momentum je negativní – světový index je pod 52týdenním "
                    f"průměrem a za tři měsíce ztrácí {_fmt(r3)}.")

    # 2) rotace mezi hlavními regiony podle 4týdenního výnosu
    decl = {  # skloňování pro věty
        "CSPX.AS": ("USA", "USA"),
        "MEUD.PA": ("Evropy", "Evropě"),
        "EMIM.AS": ("rozvíjejících se trhů", "rozvíjejícím se trhům"),
    }
    ranked = sorted(decl, key=lambda t: by_ticker[t]["r1"] or 0, reverse=True)
    spread = (by_ticker[ranked[0]]["r1"] or 0) - (by_ticker[ranked[-1]]["r1"] or 0)
    if spread < 1.5:
        s_rotation = ("Rozdíly mezi hlavními regiony jsou v posledních čtyřech týdnech "
                      "malé – výrazná rotace kapitálu neprobíhá.")
    else:
        best, second, worst = ranked[0], ranked[1], ranked[-1]
        close = ((by_ticker[best]["r1"] or 0) - (by_ticker[second]["r1"] or 0)) < 1.0
        target = (f"{decl[best][1]} a {decl[second][1]}" if close else decl[best][1])
        s_rotation = (f"V posledních čtyřech týdnech se relativní síla přesouvá "
                      f"z {decl[worst][0]} směrem k {target}.")

    # 3) nejsilnější sektory (tabulka je už seřazená podle 3M)
    top3 = [r["name"].lower() for r in sectors["rows"][:3]]
    s_sectors = f"Nejlepší sektorové momentum mají {top3[0]}, {top3[1]} a {top3[2]}."

    # 4) nejúspěšnější momentum ETF podle 6M
    cands = [r for r in etfs["rows"] if not r["benchmark"] and r["r6"] is not None]
    best_etf = max(cands, key=lambda r: r["r6"])
    s_etfs = (f"Z momentum ETF se nejvíce daří {best_etf['name']} "
              f"({_fmt(best_etf['r6'])} za šest měsíců).")

    # 5) chytré peníze vs retail (poslední hodnota + posun za ~4 týdny)
    def last_and_delta(chart, idx=0):
        vals = chart["series"][idx]["values"]
        return vals[-1], vals[-1] - (vals[-5] if len(vals) >= 5 else vals[0])

    # věta se skládá z indikátorů, které jsou zrovna k dispozici
    trend = lambda d, up, down, flat, lim=1: (up if d > lim else down if d < -lim else flat)
    parts = []
    if smart.get("naaim"):
        naaim, d_naaim = last_and_delta(smart["naaim"])
        parts.append(
            f"aktivní správci drží akciovou expozici {naaim:.0f} % "
            f"({trend(d_naaim, 'a za poslední měsíc ji zvyšují', 'a za poslední měsíc ji snižují', 'beze změny za poslední měsíc', 3)})"
        )
    if smart.get("retail"):
        _, d_retail = last_and_delta(smart["retail"])
        parts.append(f"apetit retailu podle objemu pákových ETF {trend(d_retail, 'roste', 'klesá', 'stagnuje')}")
    if smart.get("cot"):
        _, d_inst = last_and_delta(smart["cot"], 0)
        parts.append(f"instituce ve futures na S&P 500 {trend(d_inst, 'pozice přidávají', 'pozice ubírají', 'pozice drží')}")
    s_smart = (parts[0][0].upper() + ", ".join(parts)[1:] + ".") if parts else None

    # 6) Bitcoin jako barometr rizikového apetitu (signál vs 52t průměr)
    s_btc = None
    btc = next((r for r in crypto["rows"] if r["ticker"] == "BTC-USD"), None)
    if btc and btc["signal"]:
        b3 = btc["r3"]
        if btc["signal"] == "above":
            s_btc = ("Bitcoin, barometr rizikového apetitu, se drží nad svým "
                     "52týdenním průměrem"
                     + (f" ({_fmt(b3)} za tři měsíce)." if b3 is not None else "."))
        elif b3 is not None and b3 > 0:
            s_btc = (f"Bitcoin, barometr rizikového apetitu, je stále pod svým "
                     f"52týdenním průměrem, krátkodobé momentum ale sílí "
                     f"({_fmt(b3)} za tři měsíce).")
        else:
            s_btc = ("Bitcoin, barometr rizikového apetitu, je pod svým "
                     "52týdenním průměrem"
                     + (f" a za tři měsíce ztrácí {_fmt(b3)}." if b3 is not None else "."))

    (OUT_DIR / "summary.json").write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sentences": {
            "global": s_global,
            "rotation": s_rotation,
            "sectors": s_sectors,
            "etfs": s_etfs,
            "smart": s_smart,
            "btc": s_btc,
        },
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[summary] -> summary.json")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, cfg in GROUPS.items():
        build_group(key, cfg)
    build_smart_money()
    build_summary()
    print(f"Hotovo. Vygenerováno do {OUT_DIR}")


if __name__ == "__main__":
    main()

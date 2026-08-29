#!/usr/bin/env python3
"""
Automat na plnění sekce Zdroje – NÁVRHY, ne publikace.

Stáhne RSS feedy zahraničních finančních médií, vyfiltruje zprávy podle
klíčových slov navázaných na regiony/sektory webu, ohodnotí relevanci
a uloží návrhy do pipeline/sources_proposals.json. Kurátorský krok zůstává
lidský: návrhy projdeš, u vybraných doplníš/upravíš shrnutí a „proč to hýbe
trhy", a schválíš je do src/config/sources.json.

Použití:
  python3 pipeline/fetch_sources.py              # stáhne feedy, vypíše návrhy
  python3 pipeline/fetch_sources.py --approve 2,5
      # přesune návrhy č. 2 a 5 do src/config/sources.json (na začátek);
      # texty pak doladíš přímo v sources.json

Bez závislostí navíc – jen requests + stdlib (xml.etree).
Poznámky ke zdrojům: Reuters a Bloomberg veřejné RSS nenabízejí; CNBC blokuje
některé IP rozsahy (z GitHub Actions může fungovat – proto je v seznamu,
selhání jednoho feedu nic nerozbije).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Konfigurace
# ---------------------------------------------------------------------------
FEEDS = [
    {"name": "MarketWatch",   "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss/home"},
    {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news_25.rss"},
    {"name": "CNBC",          "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html"},
]

# tag -> klíčová slova (malými písmeny; hledá se v titulku + popisu)
# Tagy odpovídají regionům a sektorům webu, aby návrhy zapadly do SourceCard.
KEYWORDS: dict[str, list[str]] = {
    "USA":           ["s&p 500", "sp500", "wall street", "nasdaq", "dow jones", "federal reserve", "the fed", "fomc", "treasury yield"],
    "Evropa":        ["europe", "european", "ecb", "stoxx", "dax", "eurozone", "euro zone", "ftse"],
    "Čína":          ["china", "chinese", "beijing", "hang seng", "shanghai", "yuan"],
    "Indie":         ["india", "indian", "nifty", "sensex", "rupee"],
    "Japonsko":      ["japan", "japanese", "nikkei", "boj", "yen"],
    "Rozvíjející se trhy": ["emerging market", "emerging-market", "brazil", "latin america", "south africa"],
    "Technologie":   ["nvidia", "semiconductor", "chip", " ai ", "artificial intelligence", "microsoft", "apple", "alphabet", "meta ", "amazon", "big tech", "tech stocks"],
    "Finance":       ["bank", "banks", "banking", "insurer", "financials"],
    "Zdravotnictví": ["pharma", "healthcare", "health care", "biotech", "drugmaker"],
    "Energie":       ["oil", "crude", "opec", "natural gas", "energy stocks"],
    "Materiály":     ["copper", "gold", "commodities", "mining", "lithium"],
    "Průmysl":       ["industrial", "defense", "aerospace", "manufacturing"],
    "Krypto":        ["bitcoin", "crypto", "ethereum", "btc"],
    "Sentiment":     ["momentum", "rally", "correction", "sell-off", "selloff", "bear market", "bull market", "volatility", "vix", "fund flows", "retail investors"],
}

MAX_AGE_DAYS = 7      # starší zprávy nenavrhujeme
MAX_PROPOSALS = 25    # strop, ať je ruční průchod zvládnutelný
MIN_SCORE = 1         # minimální počet zásahů klíčových slov

ROOT = Path(__file__).resolve().parent.parent
PROPOSALS_FILE = Path(__file__).resolve().parent / "sources_proposals.json"
SEEN_FILE = Path(__file__).resolve().parent / "sources_seen.json"
SOURCES_FILE = ROOT / "src" / "config" / "sources.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; momentum-web-pipeline)"}


# ---------------------------------------------------------------------------
# Stažení a parsování RSS (RSS 2.0 i Atom, bez externích závislostí)
# ---------------------------------------------------------------------------

def _text(el) -> str:
    return html.unescape("".join(el.itertext())).strip() if el is not None else ""


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).date()   # RFC 2822 (RSS)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()  # ISO (Atom)
    except Exception:
        return None


def fetch_feed(feed: dict) -> list[dict]:
    r = requests.get(feed["url"], headers=HEADERS, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []

    for item in root.iter("item"):               # RSS 2.0
        link = _text(item.find("link"))
        items.append({
            "title": _text(item.find("title")),
            "url": link,
            "summary": _strip_html(_text(item.find("description")))[:300],
            "date": _parse_date(_text(item.find("pubDate"))),
        })
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):  # Atom
        link_el = entry.find("atom:link", ns)
        items.append({
            "title": _text(entry.find("atom:title", ns)),
            "url": link_el.get("href") if link_el is not None else "",
            "summary": _strip_html(_text(entry.find("atom:summary", ns)))[:300],
            "date": _parse_date(_text(entry.find("atom:updated", ns))),
        })

    for it in items:
        it["source"] = feed["name"]
    return [it for it in items if it["title"] and it["url"]]


# ---------------------------------------------------------------------------
# Filtr a skórování
# ---------------------------------------------------------------------------

def score_item(item: dict) -> tuple[int, list[str]]:
    text = f" {item['title']} {item['summary']} ".lower()
    tags, score = [], 0
    for tag, words in KEYWORDS.items():
        hits = sum(1 for w in words if w in text)
        if hits:
            tags.append(tag)
            score += hits
    return score, tags


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def build_proposals() -> None:
    seen: list[str] = load_json(SEEN_FILE, [])
    published = {i.get("url") for i in load_json(SOURCES_FILE, {"items": []})["items"]}
    cutoff = date.today() - timedelta(days=MAX_AGE_DAYS)

    candidates: dict[str, dict] = {}
    for feed in FEEDS:
        try:
            items = fetch_feed(feed)
            print(f"[{feed['name']}] {len(items)} položek")
        except Exception as e:                    # jeden rozbitý feed nevadí
            print(f"[{feed['name']}] SELHALO: {e}")
            continue
        for it in items:
            if it["url"] in seen or it["url"] in published or it["url"] in candidates:
                continue
            if it["date"] and it["date"] < cutoff:
                continue
            score, tags = score_item(it)
            if score < MIN_SCORE:
                continue
            candidates[it["url"]] = {
                "title": it["title"],
                "source": it["source"],
                "url": it["url"],
                "date": (it["date"] or date.today()).isoformat(),
                "tags": tags[:3],
                "summary": it["summary"] or it["title"],
                "why": "",          # doplní kurátor
                "_score": score,
            }

    proposals = sorted(candidates.values(), key=lambda c: -c["_score"])[:MAX_PROPOSALS]
    for i, p in enumerate(proposals, 1):
        p["_id"] = i

    PROPOSALS_FILE.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "_comment": "Návrhy ke schválení. Schválení: python3 pipeline/fetch_sources.py --approve 1,3 "
                    "(čísla _id). Texty (summary, why) pak doladíš v src/config/sources.json.",
        "proposals": proposals,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # do "viděných" ukládáme jen to, co jsme navrhli – nenavržené zprávy
    # dostanou šanci v příštím běhu, dokud nezestárnou
    SEEN_FILE.write_text(json.dumps(seen + [p["url"] for p in proposals],
                                    ensure_ascii=False, indent=0), encoding="utf-8")

    print(f"\n{len(proposals)} návrhů -> {PROPOSALS_FILE.name}")
    for p in proposals:
        print(f"  [{p['_id']:2d}] ({p['_score']}) {p['source']}: {p['title'][:80]}  {{{', '.join(p['tags'])}}}")
    print("\nSchválení vybraných: python3 pipeline/fetch_sources.py --approve <čísla oddělená čárkou>")


def approve(ids: list[int]) -> None:
    data = load_json(PROPOSALS_FILE, None)
    if not data:
        raise SystemExit("Žádné návrhy – nejdřív spusť bez parametrů.")
    by_id = {p["_id"]: p for p in data["proposals"]}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise SystemExit(f"Návrhy {missing} neexistují. K dispozici: {sorted(by_id)}")

    sources = load_json(SOURCES_FILE, {"items": []})
    approved = []
    for i in ids:
        p = {k: v for k, v in by_id[i].items() if not k.startswith("_")}
        if not p["why"]:
            p["why"] = "DOPLŇ: proč je zpráva relevantní pro momentum."
        approved.append(p)

    sources["items"] = approved + sources["items"]
    SOURCES_FILE.write_text(json.dumps(sources, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    data["proposals"] = [p for p in data["proposals"] if p["_id"] not in ids]
    PROPOSALS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                              encoding="utf-8")

    demo = sum(1 for i in sources["items"] if i.get("demo"))
    print(f"Schváleno {len(approved)} položek -> {SOURCES_FILE.relative_to(ROOT)}")
    print("Teď v sources.json dolaď 'summary' a doplň 'why' (má tam placeholder).")
    if demo:
        print(f"Pozn.: v sources.json zbývá {demo} ukázkových položek (demo:true) – můžeš je smazat.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approve", help="čísla návrhů (_id) oddělená čárkou")
    args = ap.parse_args()
    if args.approve:
        approve([int(x) for x in args.approve.replace(" ", "").split(",") if x])
    else:
        build_proposals()

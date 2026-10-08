#!/usr/bin/env python3
"""Publish up to two DRLabs desk notes a day from free public data.

Slot 1 (core): curated majors first, then the broader CoinGecko top list by market cap.
Slot 2 (satellite): rotates DeFi -> GameFi -> Meme -> L2; curated names first, then the
CoinGecko sector list. Coins already written are never rewritten.

If nothing is writable (pools empty, every API refusing), exit 0 quietly so the
workflow commits nothing and sends no failure email.

Writing lives in desk_analyst.py: every note is composed from what the data shows for
that one coin. No paid API, no invented numbers.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from desk_analyst import compose_note, verdict  # noqa: E402
import desk_sources as ds  # noqa: E402

ROOT = Path(os.environ.get("DRLABS_ROOT", "/tmp/drlabs-live"))
UNIVERSE_PATH = Path(os.environ.get("DESK_UNIVERSE", HERE / "desk_universe.json"))
SITE = os.environ.get("DRLABS_SITE", "https://drlabs-code.github.io/drlabs").rstrip("/")
UA = "DRLabs-desk/2.0 (+https://github.com/DRLabs-code)"
PERTH = ZoneInfo("Australia/Perth")
LANES = ("DeFi", "GameFi", "Meme", "L2")
LANGS = ("zh", "en", "ja", "ko", "fr", "es", "ru")
CG = "https://api.coingecko.com/api/v3"
LLAMA = "https://api.llama.fi"

LANE_CATEGORY = {
    "DeFi": "decentralized-finance-defi",
    "GameFi": "gaming",
    "Meme": "meme-token",
    "L2": "layer-2",
    "L1": "layer-1",
    "AI": "artificial-intelligence",
    "RWA": "real-world-assets-rwa",
    "Exchange": "exchange-based-tokens",
}
# CoinGecko category label -> (lane tag, category id used for peers)
SECTOR_FROM_LABEL = (
    ("Meme", "Meme", "meme-token"),
    ("Gaming (GameFi)", "GameFi", "gaming"),
    ("Play To Earn", "GameFi", "gaming"),
    ("Layer 2 (L2)", "L2", "layer-2"),
    ("Privacy Coins", "L1", "privacy-coins"),
    ("Oracle", "Infra", "oracle"),
    ("Decentralized Exchange (DEX)", "DeFi", "decentralized-exchange"),
    ("Lending/Borrowing Protocols", "DeFi", "lending-borrowing"),
    ("Derivatives", "DeFi", "derivatives"),
    ("Liquid Staking", "DeFi", "liquid-staking"),
    ("Artificial Intelligence (AI)", "AI", "artificial-intelligence"),
    ("Real World Assets (RWA)", "RWA", "real-world-assets-rwa"),
    ("Smart Contract Platform", "L1", "smart-contract-platform"),
    ("Layer 1 (L1)", "L1", "layer-1"),
    ("Decentralized Finance (DeFi)", "DeFi", "decentralized-finance-defi"),
    ("Exchange-based Tokens", "Exchange", "exchange-based-tokens"),
)
EXCLUDE_CAT_WORDS = (
    "stablecoin", "wrapped", "liquid staking tokens", "liquid staked", "liquid restaking tokens",
    "bridged", "tokenized gold", "tokenized stock", "tokenized treasury", "tokenized commodit",
    "rehypothecated", "yield-bearing stablecoin", "synthetic dollar",
)
EXCLUDE_NAME = re.compile(
    r"(wrapped|bridged|staked|restaked|tokenized|xstock|\bgold\b|usd|binance-peg|\(wormhole\)|"
    r"\beur\b|euro coin|treasury)",
    re.I,
)
EXCLUDE_SYMBOL = re.compile(
    r"^((w|st|wst|cb|r|ez|we|m|s|j|b|lb|bn|os|k|t|f|e|u|p|x|ts|lst)(btc|eth|sol|bnb|avax|hype)|[a-z]{0,3}usd[a-z0-9]*|[a-z]{0,2}eur[a-z]?)$",
    re.I,
)

_CACHE: dict[str, object] = {}
_LAST_CG = [0.0]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def perth_today() -> str:
    return datetime.now(PERTH).strftime("%Y-%m-%d")


def warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


# ---------------------------------------------------------------- http

def get_json(url: str, retries: int = 4, timeout: int = 40):
    if url in _CACHE:
        return _CACHE[url]
    if url.startswith(CG):
        gap = time.time() - _LAST_CG[0]
        if gap < 2.6:  # free tier: stay well under the per-minute cap
            time.sleep(2.6 - gap)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if url.startswith(CG):
                _LAST_CG[0] = time.time()
            _CACHE[url] = data
            return data
        except urllib.error.HTTPError as exc:
            last = exc
            if url.startswith(CG):
                _LAST_CG[0] = time.time()
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(20 * (attempt + 1))
                continue
            if exc.code in (500, 502, 503, 504) and attempt < min(retries, 2) - 1:
                time.sleep(4)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"failed {url}: {last}")


def soft(fn, *args, default=None, label: str = ""):
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 — one missing source never kills the note
        warn(f"{label or fn.__name__} {args[:1]}: {exc}")
        return default


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml;q=0.9, text/html;q=0.8, */*;q=0.5"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def num(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


# ---------------------------------------------------------------- site state

def load_universe() -> dict:
    return json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))


def parse_head(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    if not text.startswith("---"):
        return data
    end = text.find("\n---\n", 4)
    if end == -1:
        return data
    for line in text[4:end].split("\n"):
        if ":" in line and not line.startswith(" "):
            key, raw = line.split(":", 1)
            data[key.strip()] = raw.strip().strip('"')
    return data


def list_notes() -> list[dict[str, str]]:
    research = ROOT / "research"
    notes: list[dict[str, str]] = []
    if not research.exists():
        return notes
    for folder in research.iterdir():
        report = folder / "report.md"
        if not folder.is_dir() or not report.exists():
            continue
        head = parse_head(report.read_text(encoding="utf-8"))
        notes.append(
            {
                "slug": folder.name,
                "ticker": (head.get("ticker") or folder.name).upper(),
                "cg": head.get("cgId") or "",
                "title": head.get("title") or folder.name.upper(),
                "date": (head.get("date") or "")[:10],
                "score": head.get("score") or "",
                "url": f"{SITE}/research/{folder.name}/",
            }
        )
    notes.sort(key=lambda n: (n["date"], n["score"]), reverse=True)
    return notes


def taken_sets() -> tuple[set[str], set[str], set[str]]:
    notes = list_notes()
    tickers = {n["ticker"] for n in notes}
    slugs = {n["slug"] for n in notes}
    cg_ids = {n["cg"] for n in notes if n["cg"]}
    return tickers, slugs, cg_ids


def print_status(day: str | None = None) -> None:
    notes = list_notes()
    focus = [n for n in notes if n["date"] == day] if day else notes[:2]
    print(f"首页 {SITE}/")
    print(f"目录 {SITE}/research/")
    if day:
        print(f"当日 {day}（珀斯）")
    if not focus:
        print("当日没有新研报。")
        return
    for note in focus:
        score = f"{note['score']} / 10" if note["score"] else ""
        print(f"- {note['ticker']} {score} {note['title']}")
        print(f"  {note['url']}")


# ---------------------------------------------------------------- shared market context

def cg_top(pages: int = 1) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, pages + 1):
        data = get_json(
            f"{CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page={page}"
            "&price_change_percentage=7d,30d,200d,1y"
        )
        rows.extend(r for r in (data or []) if isinstance(r, dict))
    return rows


def cg_category(cat_id: str, per_page: int = 100) -> list[dict]:
    data = get_json(
        f"{CG}/coins/markets?vs_currency=usd&category={cat_id}&order=market_cap_desc&per_page={per_page}&page=1"
        "&price_change_percentage=7d,30d,200d,1y"
    )
    return [r for r in (data or []) if isinstance(r, dict)]


def market_row(row: dict) -> dict:
    return {
        "cg": row.get("id"),
        "ticker": str(row.get("symbol") or "").upper(),
        "name": row.get("name"),
        "price": num(row.get("current_price")),
        "mcap": num(row.get("market_cap")),
        "fdv": num(row.get("fully_diluted_valuation")),
        "volume": num(row.get("total_volume")),
        "rank": row.get("market_cap_rank"),
        "chg_7d": num(row.get("price_change_percentage_7d_in_currency")),
        "chg_30d": num(row.get("price_change_percentage_30d_in_currency")),
        "chg_200d": num(row.get("price_change_percentage_200d_in_currency")),
        "chg_1y": num(row.get("price_change_percentage_1y_in_currency")),
        "ath_chg": num(row.get("ath_change_percentage")),
    }


def looks_excluded(row: dict) -> bool:
    name = str(row.get("name") or "")
    sym = str(row.get("symbol") or row.get("ticker") or "")
    if EXCLUDE_NAME.search(name) or EXCLUDE_SYMBOL.match(sym):
        return True
    price = num(row.get("current_price") if "current_price" in row else row.get("price"))
    chg = num(row.get("price_change_percentage_30d_in_currency") if "current_price" in row else row.get("chg_30d"))
    if price is not None and 0.97 <= price <= 1.03 and (chg is None or abs(chg) < 2):
        return True  # dollar-pegged
    return False


def context() -> dict:
    if "ctx" in _CACHE:
        return _CACHE["ctx"]  # type: ignore[return-value]
    ctx: dict = {"top": [], "btc": None, "eth": None, "trending": [], "fng": None, "meme_ids": set()}
    top = soft(cg_top, default=[], label="cg top") or []
    ctx["top"] = top
    for row in top:
        if row.get("id") == "bitcoin":
            ctx["btc"] = market_row(row)
        if row.get("id") == "ethereum":
            ctx["eth"] = market_row(row)
    trend = soft(get_json, f"{CG}/search/trending", default={}, label="trending") or {}
    ctx["trending"] = [
        {"cg": c["item"].get("id"), "ticker": str(c["item"].get("symbol") or "").upper(), "pos": i + 1}
        for i, c in enumerate(trend.get("coins") or [])
        if isinstance(c, dict) and isinstance(c.get("item"), dict)
    ]
    memes = soft(cg_category, "meme-token", 250, default=[], label="meme list") or []
    ctx["meme_ids"] = {r.get("id") for r in memes if r.get("id")}
    fng = soft(get_json, "https://api.alternative.me/fng/?limit=30", default={}, label="fng") or {}
    vals = [num(x.get("value")) for x in (fng.get("data") or []) if isinstance(x, dict)]
    vals = [v for v in vals if v is not None]
    if vals:
        ctx["fng"] = {
            "now": vals[0],
            "label": (fng["data"][0].get("value_classification") or ""),
            "avg30": sum(vals) / len(vals),
        }
    _CACHE["ctx"] = ctx
    return ctx


# ---------------------------------------------------------------- DefiLlama maps

def llama_maps() -> dict:
    if "llama" in _CACHE:
        return _CACHE["llama"]  # type: ignore[return-value]
    out: dict = {"gecko": {}, "children": {}, "tvl": {}, "tvl_prev": {}, "meta": {}, "chains": {}, "chain_gecko": {}}
    protocols = soft(get_json, f"{LLAMA}/protocols", default=[], label="llama protocols") or []
    lite = soft(get_json, f"{LLAMA}/lite/protocols2?b=2", default={}, label="llama lite") or {}
    for row in lite.get("protocols") or []:
        pid = str(row.get("defillamaId") or "")
        out["tvl"][pid] = num(row.get("tvl"))
        out["tvl_prev"][pid] = num(row.get("tvlPrevMonth"))
    for row in protocols:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("id") or "")
        parent = row.get("parentProtocol")
        out["meta"][pid] = {"name": row.get("name"), "slug": row.get("slug"), "category": row.get("category"),
                            "chains": row.get("chains") or [], "parent": parent}
        if out["tvl"].get(pid) is None:
            out["tvl"][pid] = num(row.get("tvl"))
        if parent:
            out["children"].setdefault(parent, []).append(pid)
        if row.get("gecko_id") and not parent:
            out["gecko"].setdefault(row["gecko_id"], pid)
    for row in lite.get("parentProtocols") or []:
        if row.get("gecko_id"):
            out["gecko"][row["gecko_id"]] = row["id"]
            out["meta"][row["id"]] = {"name": row.get("name"), "slug": str(row["id"]).split("#", 1)[-1],
                                      "category": None, "chains": row.get("chains") or [], "parent": None}
    # children whose parent has no gecko id, last resort
    for row in protocols:
        if isinstance(row, dict) and row.get("gecko_id") and row.get("parentProtocol"):
            out["gecko"].setdefault(row["gecko_id"], str(row.get("id")))
    chains = soft(get_json, f"{LLAMA}/v2/chains", default=[], label="llama chains") or []
    ranked = sorted([c for c in chains if isinstance(c, dict) and num(c.get("tvl"))], key=lambda c: -num(c["tvl"]))
    for i, c in enumerate(ranked, 1):
        out["chains"][c["name"]] = {"name": c["name"], "tvl": num(c.get("tvl")), "rank": i, "n": len(ranked)}
        if c.get("gecko_id"):
            out["chain_gecko"][c["gecko_id"]] = c["name"]
    _CACHE["llama"] = out
    return out


def fee_table(data_type: str) -> list[dict]:
    data = soft(
        get_json,
        f"{LLAMA}/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType={data_type}",
        default={},
        label=f"fees {data_type}",
    ) or {}
    return [r for r in (data.get("protocols") or []) if isinstance(r, dict)]


def sum_rows(rows: list[dict], pid: str, field: str) -> float | None:
    vals = [num(r.get(field)) for r in rows if str(r.get("defillamaId")) == pid or r.get("parentProtocol") == pid]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def protocol_entity(pid: str) -> dict:
    maps = llama_maps()
    ids = maps["children"].get(pid) or [pid]
    tvl_vals = [maps["tvl"].get(i) for i in ids if maps["tvl"].get(i) is not None]
    prev_vals = [maps["tvl_prev"].get(i) for i in ids if maps["tvl_prev"].get(i) is not None]
    meta = maps["meta"].get(pid) or {}
    cats = [maps["meta"].get(i, {}).get("category") for i in ids]
    cats = [c for c in cats if c]
    out = {
        "id": pid,
        "name": meta.get("name"),
        "slug": meta.get("slug"),
        "category": meta.get("category") or (max(set(cats), key=cats.count) if cats else None),
        "chains_n": len(meta.get("chains") or []),
        "tvl": sum(tvl_vals) if tvl_vals else None,
        "tvl_prev_month": sum(prev_vals) if prev_vals and len(prev_vals) == len(tvl_vals) else None,
    }
    for key, dtype in (("fees", "dailyFees"), ("rev", "dailyRevenue"), ("hrev", "dailyHoldersRevenue")):
        rows = fee_table(dtype)
        out[f"{key}30"] = sum_rows(rows, pid, "total30d")
        out[f"{key}_prev30"] = sum_rows(rows, pid, "total60dto30d")
        out[f"{key}7"] = sum_rows(rows, pid, "total7d")
        out[f"{key}1y"] = sum_rows(rows, pid, "total1y")
    return out


def tvl_history_change(slug: str) -> dict:
    data = get_json(f"{LLAMA}/protocol/{slug}", timeout=60)
    series = data.get("tvl") if isinstance(data, dict) else None
    out: dict = {}
    if isinstance(series, list) and len(series) > 40:
        pts = [(int(p.get("date") or 0), num(p.get("totalLiquidityUSD"))) for p in series if isinstance(p, dict)]
        pts = [p for p in pts if p[1] is not None]
        out = series_changes(pts)
    return out


def series_changes(pts: list[tuple[int, float]]) -> dict:
    if not pts:
        return {}
    pts.sort()
    last_t, last_v = pts[-1]
    out = {"last": last_v}
    for days in (30, 90, 365):
        target = last_t - days * 86400
        prior = [v for t, v in pts if t <= target]
        if prior and prior[-1]:
            out[f"chg_{days}d"] = 100 * (last_v / prior[-1] - 1)
    return out


def chain_entity(chain: str) -> dict:
    maps = llama_maps()
    base = dict(maps["chains"].get(chain) or {"name": chain})
    hist = soft(get_json, f"{LLAMA}/v2/historicalChainTvl/{urllib.request.quote(chain)}", default=[], label="chain hist") or []
    pts = [(int(p.get("date") or 0), num(p.get("tvl"))) for p in hist if isinstance(p, dict)]
    pts = [p for p in pts if p[1] is not None]
    base.update({f"tvl_{k}": v for k, v in series_changes(pts).items() if k.startswith("chg")})
    for key, dtype in (("fees", "dailyFees"), ("rev", "dailyRevenue")):
        rows = [r for r in fee_table(dtype) if r.get("protocolType") == "chain" and str(r.get("name") or "").lower() == chain.lower()]
        if rows:
            base[f"{key}30"] = num(rows[0].get("total30d"))
            base[f"{key}_prev30"] = num(rows[0].get("total60dto30d"))
            base[f"{key}7"] = num(rows[0].get("total7d"))
    dex = soft(
        get_json,
        f"{LLAMA}/overview/dexs/{urllib.request.quote(chain)}?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
        default={},
        label="chain dex",
    ) or {}
    if isinstance(dex, dict):
        base["dex30"] = num(dex.get("total30d"))
        base["dex_prev30"] = num(dex.get("total60dto30d"))
        base["dex7"] = num(dex.get("total7d"))
    stables = soft(get_json, "https://stablecoins.llama.fi/stablecoinchains", default=[], label="stables") or []
    for row in stables:
        if str(row.get("name") or "").lower() == chain.lower():
            usd = row.get("totalCirculatingUSD")
            base["stables"] = num(usd.get("peggedUSD")) if isinstance(usd, dict) else num(usd)
    return base


# ---------------------------------------------------------------- per-coin pack

class Skip(Exception):
    pass


def chart_stats(cg_id: str) -> dict:
    data = get_json(f"{CG}/coins/{cg_id}/market_chart?vs_currency=usd&days=365&interval=daily")
    prices = [num(p[1]) for p in (data.get("prices") or []) if isinstance(p, list)]
    caps = [num(p[1]) for p in (data.get("market_caps") or []) if isinstance(p, list)]
    vols = [num(p[1]) for p in (data.get("total_volumes") or []) if isinstance(p, list)]
    prices = [p for p in prices if p]
    out: dict = {"days": len(prices)}
    if len(prices) < 35:
        return out

    def rets(seq):
        return [math.log(b / a) for a, b in zip(seq, seq[1:]) if a and b]

    r30 = rets(prices[-31:])
    r90 = rets(prices[-91:])
    if len(r30) > 20:
        out["vol30"] = statistics.pstdev(r30) * math.sqrt(365) * 100
    if len(r90) > 60:
        out["vol90"] = statistics.pstdev(r90) * math.sqrt(365) * 100
    last = prices[-1]
    if len(prices) >= 50:
        out["ma50"] = sum(prices[-50:]) / 50
    if len(prices) >= 200:
        out["ma200"] = sum(prices[-200:]) / 200
    window = prices[-90:]
    out["hi90"], out["lo90"] = max(window), min(window)
    peak, mdd = window[0], 0.0
    for p in window:
        peak = max(peak, p)
        mdd = min(mdd, p / peak - 1)
    out["mdd90"] = 100 * mdd
    if len(prices) > 91:
        out["ret90"] = 100 * (last / prices[-91] - 1)
    if len(prices) > 181:
        out["ret180"] = 100 * (last / prices[-181] - 1)
    vols = [v for v in vols if v]
    if len(vols) >= 37:
        out["vol7_avg"] = sum(vols[-7:]) / 7
        out["vol30_avg"] = sum(vols[-37:-7]) / 30
    pairs = [(c, p) for c, p in zip(caps, [num(x[1]) for x in data.get("prices") or []]) if c and p]
    circ = [c / p for c, p in pairs]
    if len(circ) > 95:
        out["circ_chg_90d"] = 100 * (circ[-1] / circ[-91] - 1)
    if len(circ) > 360:
        out["circ_chg_365d"] = 100 * (circ[-1] / circ[0] - 1)
    return out


def pick_sector(categories: list[str], lane: str) -> tuple[list[str], str | None]:
    tags: list[str] = []
    cat_id = None
    for label, tag, cid in SECTOR_FROM_LABEL:
        if label in categories:
            if tag not in tags:
                tags.append(tag)
            cat_id = cat_id or cid
    if lane in LANES and lane not in tags:
        tags.insert(0, lane)
    specific = {"decentralized-exchange", "lending-borrowing", "derivatives", "liquid-staking"}
    if lane in LANE_CATEGORY and lane != "major" and not (lane == "DeFi" and cat_id in specific):
        cat_id = LANE_CATEGORY[lane]  # a DeFi coin keeps its narrower sub-sector (DEX, lending...) for peers
    if "L2" in tags and "L1" in tags:
        tags.remove("L1")
    return tags[:3] or ["Other"], cat_id


CAT_NAME = {cid: label for label, _tag, cid in SECTOR_FROM_LABEL}
CAT_NAME.update({"gaming": "Gaming (GameFi)", "meme-token": "Meme", "layer-2": "Layer 2 (L2)",
                 "decentralized-finance-defi": "Decentralized Finance (DeFi)"})


def build_peers(cg_id: str, cat_id: str | None, mcap: float, lane: str | None = None, target_is_meme: bool = False) -> tuple[list[dict], dict]:
    """Peers by sector fit: CoinGecko category list minus memecoins / off-sector tokens
    (desk_sectors.json + name heuristics), curated sector core preferred, leader = largest fitted peer."""
    sector: dict = {}
    rows: list[dict] = []
    if cat_id:
        rows = soft(cg_category, cat_id, default=[], label="cg category") or []
    if not rows:
        rows = context()["top"]
        cat_id = None
    rows = [market_row(r) for r in rows if not looks_excluded(r) and num(r.get("market_cap"))]
    meme_ids = context().get("meme_ids") or set()
    kept, dropped = ds.sector_fit(rows, cat_id, cg_id, meme_ids, target_is_meme)
    kept.sort(key=lambda r: -(r["mcap"] or 0))
    chg = [r["chg_30d"] for r in kept if r["chg_30d"] is not None]
    if chg:
        sector["median_30d"] = statistics.median(chg)
    chg1y = [r["chg_1y"] for r in kept if r["chg_1y"] is not None]
    if chg1y:
        sector["median_1y"] = statistics.median(chg1y)
    ex = [r for r in kept if r["cg"] != cg_id and r["chg_30d"] is not None and r["mcap"]]
    if ex:
        sector["wavg_ex_30d"] = sum(r["mcap"] * r["chg_30d"] for r in ex) / sum(r["mcap"] for r in ex)
    sector["n"] = len(kept)
    sector["cat_id"] = cat_id
    sector["cat_name"] = CAT_NAME.get(cat_id or "", cat_id) if cat_id else "Top 250 by market cap"
    sector["dropped"] = len(dropped)
    sector["dropped_ids"] = dropped[:25]
    ids = [r["cg"] for r in kept]
    if cg_id in ids:
        sector["pos"] = ids.index(cg_id) + 1
    core = ds.sector_core(cat_id, soft(load_universe, default={}, label="universe") or {}, lane)
    chosen, _leader = ds.choose_peers(kept, cg_id, mcap, core)
    maps = llama_maps()
    for p in chosen:
        p["meme"] = p["cg"] in meme_ids
        pid = maps["gecko"].get(p["cg"])
        if pid:
            ent = protocol_entity(pid)
            p.update({k: ent.get(k) for k in ("tvl", "fees30", "rev30")})
        chain = maps["chain_gecko"].get(p["cg"])
        if chain:
            c = maps["chains"].get(chain) or {}
            p["chain_tvl"] = c.get("tvl")
            rows_f = [r for r in fee_table("dailyFees") if r.get("protocolType") == "chain" and str(r.get("name") or "").lower() == chain.lower()]
            if rows_f and p.get("fees30") is None:
                p["fees30"] = num(rows_f[0].get("total30d"))
    return chosen, sector


def fetch_lunarcrush(ticker: str, cg_id: str) -> dict | None:
    for url in (f"https://lunarcrush.com/coins/{ticker.lower()}/{cg_id}", f"https://lunarcrush.com/coins/{ticker.lower()}"):
        try:
            html = get_text(url)
        except Exception:  # noqa: BLE001
            continue
        dom = re.search(r"Social Dominance[^%]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*%", html, re.I | re.S)
        if not dom:
            continue
        sent = re.search(r"Sentiment[^%]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*%", html, re.I | re.S)
        return {"dominance": float(dom.group(1)), "sentiment": float(sent.group(1)) if sent else None, "url": url}
    return None


def build_pack(item: dict, lane: str, as_of: str, day: str) -> dict:
    cg_id = item["cg"]
    coin = get_json(f"{CG}/coins/{cg_id}?localization=false&tickers=false&community_data=false&developer_data=false")
    if not isinstance(coin, dict) or not coin.get("market_data"):
        raise Skip("no market data")
    cats = [c for c in (coin.get("categories") or []) if c]
    # "Stablecoin Issuer" / "Stablecoin Protocol" are governance tokens (ENA, SKY...), not stablecoins
    low = " | ".join(c for c in cats if not re.search(r"stablecoin (issuer|protocol)", c, re.I)).lower()
    if any(w in low for w in EXCLUDE_CAT_WORDS):
        raise Skip("stable / wrapped / tokenized asset")
    md = coin["market_data"]

    def usd(key):
        val = md.get(key)
        return num(val.get("usd")) if isinstance(val, dict) else num(val)

    ticker = str(item.get("ticker") or coin.get("symbol") or "").upper()
    pack: dict = {
        "ticker": ticker,
        "name": coin.get("name") or ticker,
        "cg_id": cg_id,
        "lane": lane,
        "as_of": as_of,
        "day": day,
        "cg": {
            "price": usd("current_price"),
            "mcap": usd("market_cap"),
            "fdv": usd("fully_diluted_valuation"),
            "volume": usd("total_volume"),
            "rank": coin.get("market_cap_rank"),
            "circ": num(md.get("circulating_supply")),
            "total": num(md.get("total_supply")),
            "max_supply": num(md.get("max_supply")),
            "max_infinite": bool(md.get("max_supply_infinite")),
            "ath": usd("ath"),
            "ath_date": str((md.get("ath_date") or {}).get("usd") or "")[:10] or None,
            "ath_chg": usd("ath_change_percentage"),
            "atl": usd("atl"),
            "atl_date": str((md.get("atl_date") or {}).get("usd") or "")[:10] or None,
            "chg_7d": num(md.get("price_change_percentage_7d")),
            "chg_30d": num(md.get("price_change_percentage_30d")),
            "chg_60d": num(md.get("price_change_percentage_60d")),
            "chg_200d": num(md.get("price_change_percentage_200d")),
            "chg_1y": num(md.get("price_change_percentage_1y")),
            "categories": cats,
            "votes_up": num(coin.get("sentiment_votes_up_percentage")),
            "watchlist": num(coin.get("watchlist_portfolio_users")),
            "genesis": coin.get("genesis_date"),
            "platform": coin.get("asset_platform_id"),
            "hashing": coin.get("hashing_algorithm"),
        },
        "sources": ["CoinGecko coin + 365d chart"],
    }
    c = pack["cg"]
    if not c["price"] or not c["mcap"]:
        raise Skip("CoinGecko has no price or market cap")
    if looks_excluded({"name": pack["name"], "symbol": ticker, "price": c["price"], "chg_30d": c["chg_30d"]}):
        raise Skip("looks like a pegged / wrapped asset")
    if (c["volume"] or 0) < 300_000:
        raise Skip("24h volume too thin to write responsibly")
    pack["tags"], cat_id = pick_sector(cats, lane)
    if item.get("tags"):
        pack["tags"] = list(dict.fromkeys(list(item["tags"]) + pack["tags"]))[:3]
        if "Other" in pack["tags"] and len(pack["tags"]) > 1:
            pack["tags"].remove("Other")
    pack["hist"] = soft(chart_stats, cg_id, default={}, label="chart") or {}
    ctx = context()
    pack["btc"], pack["eth"] = ctx.get("btc"), ctx.get("eth")
    is_meme = "Meme" in cats or cg_id in (ctx.get("meme_ids") or set())
    pack["peers"], pack["sector"] = build_peers(cg_id, cat_id, c["mcap"], lane, is_meme)
    if pack["peers"]:
        pack["sources"].append("CoinGecko sector list (peers)")
    maps = llama_maps()
    pid = maps["gecko"].get(cg_id) or (f"parent#{item['llama']}" if item.get("llama") and f"parent#{item['llama']}" in maps["meta"] else None)
    if not pid and item.get("llama"):
        pid = next((k for k, m in maps["meta"].items() if m.get("slug") == item["llama"]), None)
    pack["protocol"] = None
    chain_hint = maps["chain_gecko"].get(cg_id)
    if pid and chain_hint and (maps["meta"].get(pid) or {}).get("category") in ("Canonical Bridge", "Bridge", "CEX", "Chain", None):
        pid = None  # a chain's own token: read the chain, not its foundation / bridge wallet
    if pid:
        ent = protocol_entity(pid)
        if ent.get("slug"):
            hist = soft(tvl_history_change, ent["slug"], default={}, label="tvl history") or {}
            ent.update({f"tvl_{k}": v for k, v in hist.items() if k.startswith("chg")})
        if any(ent.get(k) for k in ("tvl", "fees30", "rev30")):
            pack["protocol"] = ent
            pack["sources"].append("DefiLlama protocol TVL / fees / revenue")
    chain_name = maps["chain_gecko"].get(cg_id) or item.get("chain")
    pack["chain"] = None
    if chain_name and chain_name in maps["chains"]:
        pack["chain"] = chain_entity(chain_name)
        pack["sources"].append("DefiLlama chain TVL / fees / DEX / stablecoins")
    trending = {t["cg"]: t["pos"] for t in ctx.get("trending") or []}
    pack["social"] = {
        "fng": ctx.get("fng"),
        "trending_pos": trending.get(cg_id),
        "trending_n": len(trending),
        "lunar": soft(fetch_lunarcrush, ticker, cg_id, default=None, label="lunarcrush"),
    }
    if ctx.get("fng"):
        pack["sources"].append("alternative.me Fear & Greed")
    if trending:
        pack["sources"].append("CoinGecko trending search")
    if pack["social"]["lunar"]:
        pack["sources"].append("LunarCrush")
    add_extras(pack, coin, pid, maps)
    return pack


def add_extras(pack: dict, coin: dict, pid: str | None, maps: dict) -> None:
    """Zero-cost extras: headlines, unlock schedule, hack history, project self-description.
    Each one fails soft; a missing source just drops that part of the note."""
    c = pack["cg"]
    now = utc_now()
    pack["profile"] = soft(ds.project_profile, coin, default={}, label="profile") or {}
    c["categories"] = ds.drop_categories(pack["cg_id"], c["categories"], (pack.get("chain") or {}).get("tvl"))
    answered = [0]

    def fetch_text(url: str) -> str:
        text = get_text(url)
        answered[0] += 1
        return text

    news = soft(ds.collect_news, fetch_text, pack["name"], pack["ticker"], now, default=None, label="news")
    pack["news"] = news or []
    pack["news_checked"] = answered[0] > 0
    if answered[0]:
        pack["sources"].append("Headlines: CoinDesk / Cointelegraph / The Block / Decrypt / CryptoSlate RSS + Google News search")

    def quiet_json(url: str, timeout: int = 40):
        return soft(lambda: get_json(url, 2, timeout), default=None, label="unlocks")

    llama_slug = ((maps.get("meta") or {}).get(pid) or {}).get("slug") if pid else None
    pack["unlocks"] = soft(ds.fetch_unlocks, quiet_json, pack["cg_id"], pack["name"], pack["ticker"], llama_slug, now,
                           c.get("price"), c.get("circ"), default=None, label="unlocks")
    if pack["unlocks"]:
        pack["sources"].append("DefiLlama unlock schedule (emissions dataset)")
    hacks_rows = soft(get_json, f"{LLAMA}/hacks", default=[], label="hacks") or []
    names = [pack["name"], (pack.get("protocol") or {}).get("name")]
    ids = [str(pid).split("#")[-1]] + list((maps.get("children") or {}).get(pid, [])) if pid else []
    pack["hacks"] = ds.find_hacks(hacks_rows, [n for n in names if n], ids) if hacks_rows else []
    if hacks_rows:
        pack["sources"].append("DefiLlama hacks database")


# ---------------------------------------------------------------- selection

def core_candidates(universe: dict) -> list[dict]:
    out = [dict(x) for x in universe.get("majors") or []]
    for row in context()["top"]:
        rank = row.get("market_cap_rank") or 999
        if rank > 200 or looks_excluded(row) or (num(row.get("market_cap")) or 0) < 1e8:
            continue
        out.append({"ticker": str(row.get("symbol") or "").upper(), "cg": row["id"]})
    return out


def lane_candidates(universe: dict, lane: str) -> list[dict]:
    out = [dict(x) for x in (universe.get("lanes") or {}).get(lane, [])]
    cat = LANE_CATEGORY.get(lane)
    if cat:
        for row in soft(cg_category, cat, default=[], label=f"lane {lane}") or []:
            if looks_excluded(row):
                continue
            if (num(row.get("market_cap")) or 0) < 2.5e7 or (num(row.get("total_volume")) or 0) < 5e5:
                continue
            out.append({"ticker": str(row.get("symbol") or "").upper(), "cg": row["id"]})
    return out


def pick(cands: list[dict], taken: tuple[set, set, set], lane: str, as_of: str, day: str, budget: int = 6) -> dict | None:
    tickers, slugs, cg_ids = taken
    seen: set[str] = set()
    for item in cands:
        ticker = str(item.get("ticker") or "").upper()
        if not ticker or item["cg"] in seen:
            continue
        seen.add(item["cg"])
        slug = re.sub(r"[^a-z0-9]+", "-", ticker.lower()).strip("-")
        if ticker in tickers or slug in slugs or item["cg"] in cg_ids:
            continue
        if budget <= 0:
            warn(f"{lane}: fetch budget spent, stopping")
            return None
        budget -= 1
        try:
            pack = build_pack(item, lane, as_of, day)
        except Skip as exc:
            print(f"[skip] {ticker}: {exc}", file=sys.stderr)
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {ticker}: {exc}", file=sys.stderr)
            continue
        pack["slug"] = slug
        return pack
    return None


def select(as_of: str, day: str, want: int) -> list[dict]:
    universe = load_universe()
    taken = taken_sets()
    picked: list[dict] = []
    core = pick(core_candidates(universe), taken, "major", as_of, day)
    if core:
        picked.append(core)
        taken[0].add(core["ticker"]); taken[1].add(core["slug"]); taken[2].add(core["cg_id"])
    else:
        warn("no writable core coin today")
    if len(picked) >= want:
        return picked
    yday = datetime.now(PERTH).timetuple().tm_yday
    first = LANES[yday % len(LANES)]
    order = [first] + [x for x in LANES if x != first]
    for lane in order:
        sat = pick(lane_candidates(universe, lane), taken, lane, as_of, day, budget=4)
        if sat:
            if lane != first:
                print(f"[info] {first} empty or failing, used {lane}", file=sys.stderr)
            picked.append(sat)
            break
    return picked[:want]


# ---------------------------------------------------------------- write

def write_note(pack: dict, drafted: dict) -> Path:
    folder = ROOT / "research" / pack["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        name = "report.md" if lang == "zh" else f"report.{lang}.md"
        (folder / name).write_text(drafted["bodies"][lang], encoding="utf-8")
    return folder


def slugify(ticker: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ticker.lower()).strip("-")


def same_day_bodies(day: str, exclude: set[str] | None = None) -> list[dict]:
    """zh/en bodies of notes already published for `day`: the phrase picker avoids their sentence patterns."""
    out = []
    for n in list_notes():
        if n["date"] != day or n["slug"] in (exclude or set()):
            continue
        folder = ROOT / "research" / n["slug"]
        en = folder / "report.en.md"
        out.append({"zh": (folder / "report.md").read_text(encoding="utf-8"),
                    "en": en.read_text(encoding="utf-8") if en.exists() else ""})
    return out


def dump_note(pack: dict, drafted: dict | None, dump: str) -> None:
    out = Path(dump)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{pack['slug']}.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if drafted:
        for lang in ("zh", "en"):
            (out / f"{pack['slug']}.{lang}.md").write_text(drafted["bodies"][lang], encoding="utf-8")


def run(dry_run: bool, force: bool, dump: str | None) -> int:
    day = perth_today()
    existing = [n for n in list_notes() if n["date"] == day]
    if len(existing) >= 2 and not force:
        print(f"already have {len(existing)} notes on {day}: {', '.join(n['slug'] for n in existing)}")
        return 0
    as_of = utc_now().strftime("%Y-%m-%d %H:%M UTC")
    want = 2 if force else 2 - len(existing)
    packs = select(as_of, day, want)
    if not packs:
        print("::warning::Daily desk: nothing writable today (pools empty or APIs refusing). Skipped quietly.")
        print("nothing writable today; skipped quietly, no files written")
        return 0
    avoid = same_day_bodies(day, {p["slug"] for p in packs})
    for pack in packs:
        try:
            drafted = compose_note(pack, avoid=avoid)
        except Exception as exc:  # noqa: BLE001 — an audit failure skips the note, never publishes it
            print(f"::warning::Daily desk: {pack['ticker']} not published ({exc})")
            if dump:
                dump_note(pack, None, dump)
            continue
        avoid.append(drafted["bodies"])
        print(f"{pack['ticker']} [{pack['lane']}] {drafted['score']:.1f} {verdict(drafted['score'])[1]} as-of {as_of} -> {pack['slug']}")
        if dump:
            dump_note(pack, drafted, dump)
        if dry_run:
            continue
        write_note(pack, drafted)
    if dry_run:
        print("dry-run: no site files written")
        return 0
    print_status(day)
    return 0


def run_one(cg_id: str | None, lane: str, ticker: str | None, slug: str | None, from_pack: str | None,
            dry_run: bool, dump: str | None) -> int:
    """Write (or rewrite) one coin's note, bypassing the daily cap; same slug is overwritten."""
    if from_pack:
        pack = json.loads(Path(from_pack).read_text(encoding="utf-8"))
        if slug:
            pack["slug"] = slug
    else:
        as_of = utc_now().strftime("%Y-%m-%d %H:%M UTC")
        item = {"cg": cg_id}
        if ticker:
            item["ticker"] = ticker
        pack = build_pack(item, lane, as_of, perth_today())
        pack["slug"] = slug or slugify(pack["ticker"])
    drafted = compose_note(pack, avoid=same_day_bodies(pack["day"], {pack["slug"]}))
    print(f"{pack['ticker']} [{pack['lane']}] {drafted['score']:.1f} {verdict(drafted['score'])[1]} as-of {pack['as_of']} -> {pack['slug']}")
    if dump:
        dump_note(pack, drafted, dump)
    if dry_run:
        print("dry-run: no site files written")
        return 0
    write_note(pack, drafted)
    print(f"wrote {ROOT / 'research' / pack['slug']}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish DRLabs desk notes from free public data.")
    parser.add_argument("--dry-run", action="store_true", help="pick coins, fetch data, compose, do not write")
    parser.add_argument("--force", action="store_true", help="ignore the two-notes-per-day stop")
    parser.add_argument("--status", action="store_true", help="print public URLs for today's notes")
    parser.add_argument("--dump", help="also write <slug>.json (full data pack) + <slug>.zh.md / .en.md to this folder")
    parser.add_argument("--coin", help="CoinGecko id: write just this coin (bypasses the daily cap, overwrites its slug)")
    parser.add_argument("--lane", default="major", help="lane for --coin (major, DeFi, GameFi, Meme, L2, ...)")
    parser.add_argument("--ticker", help="ticker override for --coin")
    parser.add_argument("--slug", help="slug override for --coin / --from-pack")
    parser.add_argument("--from-pack", help="recompose from a dumped <slug>.json without fetching anything")
    args = parser.parse_args()
    if args.status:
        print_status(perth_today())
        return
    if args.coin or args.from_pack:
        raise SystemExit(run_one(args.coin, args.lane, args.ticker, args.slug, args.from_pack, args.dry_run, args.dump))
    raise SystemExit(run(dry_run=args.dry_run, force=args.force, dump=args.dump))


if __name__ == "__main__":
    main()

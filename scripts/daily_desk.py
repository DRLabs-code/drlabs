#!/usr/bin/env python3
"""Publish one major note and one rotating DeFi/GameFi/Meme note from public data.

Writing is per-asset (see desk_write.py). Do not reuse one paragraph for every ticker.
Internet heat is a required dimension when a sourced print exists.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from desk_write import draft_note, score_note, verdict, yaml_escape

ROOT = Path(os.environ.get("DRLABS_ROOT", "/tmp/drlabs-live"))
ASTRO_CONTENT = Path(os.environ.get("ASTRO_CONTENT", "/workspace/src/content/research"))
UNIVERSE_PATH = Path(os.environ.get("DESK_UNIVERSE", HERE / "desk_universe.json"))
SITE = os.environ.get("DRLABS_SITE", "https://drlabs-code.github.io/drlabs").rstrip("/")
UA = "DRLabs-desk/1.0 (+https://github.com/DRLabs-code)"
LANES = ("DeFi", "GameFi", "Meme")
LANGS = ("zh", "en", "ja", "ko", "fr", "es", "ru")


@dataclass
class Snap:
    ticker: str
    name: str
    cg_id: str
    tags: list[str]
    lane: str
    as_of: str
    price: float | None = None
    mcap: float | None = None
    fdv: float | None = None
    volume: float | None = None
    rank: int | None = None
    circ: float | None = None
    total: float | None = None
    max_supply: float | None = None
    ath: float | None = None
    ath_date: str | None = None
    chg_7d: float | None = None
    chg_30d: float | None = None
    tvl: float | None = None
    tvl_label: str = ""
    fees_30d: float | None = None
    rev_30d: float | None = None
    sources: list[str] = field(default_factory=list)
    peers: list[dict] = field(default_factory=list)
    chains: list[dict] = field(default_factory=list)
    dexs: list[dict] = field(default_factory=list)
    stables: float | None = None
    x_mentions: dict | None = None
    lunar: dict | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def today_utc() -> str:
    return utc_now().strftime("%Y-%m-%d")


def load_universe() -> dict:
    return json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))


def published_tickers() -> set[str]:
    research = ROOT / "research"
    out: set[str] = set()
    if not research.exists():
        return out
    for folder in research.iterdir():
        report = folder / "report.md"
        if not folder.is_dir() or not report.exists():
            continue
        text = report.read_text(encoding="utf-8")
        ticker = folder.name.upper()
        if text.startswith("---"):
            end = text.find("\n---\n", 4)
            head = text[4:end] if end != -1 else ""
            for line in head.split("\n"):
                if line.startswith("ticker:"):
                    ticker = line.split(":", 1)[1].strip().strip('"').upper()
                    break
        out.add(ticker)
    return out


def notes_on(day: str) -> list[str]:
    return [item["slug"] for item in list_notes() if item["date"] == day]


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
                "ticker": head.get("ticker") or folder.name.upper(),
                "title": head.get("title") or folder.name.upper(),
                "date": (head.get("date") or "")[:10],
                "score": head.get("score") or "",
                "url": f"{SITE}/research/{folder.name}/",
            }
        )
    notes.sort(key=lambda n: (n["date"], n["score"]), reverse=True)
    return notes


def print_status(day: str | None = None) -> None:
    notes = list_notes()
    focus = [n for n in notes if n["date"] == day] if day else notes[:2]
    print(f"首页 {SITE}/")
    print(f"目录 {SITE}/research/")
    if day:
        print(f"当日 {day}")
    if not focus:
        print("当日还没有新研报。")
        return
    for note in focus:
        score = f"{note['score']} / 10" if note["score"] else ""
        print(f"- {note['ticker']} {score} {note['title']}")
        print(f"  {note['url']}")


def get_json(url: str, retries: int = 3) -> dict | list:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in (429, 502, 503, 504) and attempt < retries - 1:
                time.sleep(8 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"failed {url}: {last}")


def num(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_usd(value: float | None) -> str:
    if value is None:
        return "未披露 / not disclosed"
    n = abs(value)
    sign = "-" if value < 0 else ""
    if n >= 1e12:
        return f"{sign}≈ ${n / 1e12:.2f}T"
    if n >= 1e9:
        return f"{sign}≈ ${n / 1e9:.2f}B"
    if n >= 1e6:
        return f"{sign}≈ ${n / 1e6:.2f}M"
    if n >= 1:
        return f"{sign}≈ ${n:,.2f}"
    if n >= 0.01:
        return f"{sign}≈ ${n:.4f}"
    return f"{sign}≈ ${n:.6f}"


def fmt_qty(value: float | None) -> str:
    if value is None:
        return "未披露 / not disclosed"
    n = abs(value)
    if n >= 1e12:
        return f"≈ {n / 1e12:.2f}T"
    if n >= 1e9:
        return f"≈ {n / 1e9:.2f}B"
    if n >= 1e6:
        return f"≈ {n / 1e6:.2f}M"
    if n >= 1e3:
        return f"≈ {n / 1e3:.2f}K"
    return f"≈ {n:,.2f}"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "未披露 / not disclosed"
    return f"{value:+.1f}%"


def fetch_coingecko(cg_id: str) -> dict:
    url = (
        f"https://api.coingecko.com/api/v3/coins/{cg_id}"
        "?localization=false&tickers=false&community_data=false&developer_data=false"
    )
    data = get_json(url)
    if not isinstance(data, dict):
        raise RuntimeError(f"unexpected CoinGecko payload for {cg_id}")
    return data


def fetch_llama_protocol(slug: str) -> tuple[float | None, str]:
    data = get_json(f"https://api.llama.fi/protocol/{slug}")
    if not isinstance(data, dict):
        return None, ""
    tvl = num(data.get("tvl"))
    if tvl is None:
        series = data.get("tvl")
        if isinstance(series, list) and series:
            tvl = num(series[-1].get("totalLiquidityUSD"))
    name = str(data.get("name") or slug)
    return tvl, name


def fetch_llama_fees(slug: str, data_type: str) -> float | None:
    url = f"https://api.llama.fi/summary/fees/{slug}?dataType={data_type}"
    try:
        data = get_json(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if not isinstance(data, dict):
        return None
    return num(data.get("total30d"))


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_altindex(ticker: str) -> dict | None:
    url = f"https://altindex.com/ticker/{ticker.lower()}/x-mentions"
    try:
        html = get_text(url)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] altindex {ticker}: {exc}", file=sys.stderr)
        return None
    if "No company found" in html or "404" in html[:80]:
        return None
    mentions = None
    m = re.search(r">\s*([0-9]{2,5})\s*<.*?Est\.\s*daily mentions", html, re.I | re.S)
    if m:
        mentions = int(m.group(1))
    updated = None
    u = re.search(r"Updated ([A-Za-z]{3} \d{1,2}, \d{4})", html)
    if u:
        updated = u.group(1)
    sent = None
    s = re.search(r"sentiment for \w+:\s*(\d+)\s*/\s*100", html, re.I)
    if s:
        sent = int(s.group(1))
    if mentions is None:
        return None
    return {"ticker": ticker.upper(), "mentions": mentions, "updated": updated, "sentiment": sent, "url": url}


def altindex_stale(updated: str | None, as_of: str) -> bool:
    if not updated:
        return False
    try:
        stamped = datetime.strptime(updated, "%b %d, %Y").replace(tzinfo=timezone.utc)
        as_of_day = datetime.strptime(as_of[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return (as_of_day - stamped).days > 21


def fetch_lunarcrush(ticker: str, cg_id: str) -> dict | None:
    paths = (
        f"https://lunarcrush.com/coins/{ticker.lower()}/{cg_id}",
        f"https://lunarcrush.com/coins/{ticker.lower()}",
        f"https://lunarcrush.com/coins/{cg_id}",
    )
    html = ""
    for url in paths:
        try:
            html = get_text(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] lunarcrush {url}: {exc}", file=sys.stderr)
            continue
        if "No company found" in html or len(html) < 200:
            continue
        dom = re.search(r"Social Dominance[^%]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*%", html, re.I | re.S)
        sent = re.search(r"Sentiment[^%]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*%", html, re.I | re.S)
        posts = re.search(r">\s*([0-9]+(?:\.[0-9]+)?[KM]?)\s*<[^>]*>\s*posts", html, re.I | re.S)
        if not dom:
            continue
        out = {
            "dominance": float(dom.group(1)),
            "sentiment": float(sent.group(1)) if sent else None,
            "posts": posts.group(1) if posts else None,
            "url": url,
        }
        return out
    return None


_FEE_ROWS: list[dict] | None = None
_REV_ROWS: list[dict] | None = None


def _fee_table(data_type: str) -> list[dict]:
    global _FEE_ROWS, _REV_ROWS
    cache = _FEE_ROWS if data_type == "dailyFees" else _REV_ROWS
    if cache is not None:
        return cache
    url = (
        "https://api.llama.fi/overview/fees?excludeTotalDataChart=true"
        f"&excludeTotalDataChartBreakdown=true&dataType={data_type}"
    )
    data = get_json(url)
    rows = data.get("protocols") if isinstance(data, dict) else []
    rows = [r for r in rows if isinstance(r, dict)]
    if data_type == "dailyFees":
        _FEE_ROWS = rows
    else:
        _REV_ROWS = rows
    return rows


def fetch_named_fees(name: str) -> tuple[float | None, float | None]:
    fees = rev = None
    try:
        for row in _fee_table("dailyFees"):
            if str(row.get("name") or "") == name:
                fees = num(row.get("total30d"))
                break
        for row in _fee_table("dailyRevenue"):
            if str(row.get("name") or "") == name:
                rev = num(row.get("total30d"))
                break
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] fees table {name}: {exc}", file=sys.stderr)
    return fees, rev


def fetch_peers(exclude: str, lane: str) -> list[dict]:
    ids = {
        "major": "bitcoin,ethereum,solana,binancecoin",
        "DeFi": "uniswap,aave,lido-dao,curve-dao-token",
        "GameFi": "immutable-x,axie-infinity,the-sandbox,gala",
        "Meme": "dogecoin,shiba-inu,pepe,bonk",
    }.get(lane, "bitcoin,ethereum,solana")
    url = (
        "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
        f"&ids={ids}&price_change_percentage=7d,30d"
    )
    try:
        data = get_json(url)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] peers: {exc}", file=sys.stderr)
        return []
    out = []
    if not isinstance(data, list):
        return out
    for row in data:
        ticker = str(row.get("symbol") or "").upper()
        if ticker == exclude:
            continue
        out.append(
            {
                "ticker": ticker,
                "mcap": num(row.get("market_cap")),
                "volume": num(row.get("total_volume")),
                "rank": row.get("market_cap_rank"),
                "chg_30d": num(row.get("price_change_percentage_30d_in_currency")),
            }
        )
    return out


def fetch_top_chains(limit: int = 6) -> list[dict]:
    try:
        data = get_json("https://api.llama.fi/v2/chains")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] chains: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    rows = [c for c in data if isinstance(c, dict) and c.get("tvl")]
    rows.sort(key=lambda c: float(c.get("tvl") or 0), reverse=True)
    return [{"name": c.get("name"), "tvl": num(c.get("tvl"))} for c in rows[:limit]]


def fetch_dex_chains() -> list[dict]:
    out = []
    for chain in ("Ethereum", "Solana", "BSC", "Base"):
        try:
            data = get_json(
                f"https://api.llama.fi/overview/dexs/{chain}?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] dex {chain}: {exc}", file=sys.stderr)
            continue
        if isinstance(data, dict):
            out.append({"name": chain, "vol_24h": num(data.get("total24h")), "vol_30d": num(data.get("total30d"))})
        time.sleep(0.3)
    return out


def fetch_chain_stables(chain: str | None) -> float | None:
    if not chain:
        return None
    try:
        data = get_json("https://stablecoins.llama.fi/stablecoinchains")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] stables: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, list):
        return None
    target = chain.lower()
    for row in data:
        if str(row.get("name") or "").lower() != target:
            continue
        usd = row.get("totalCirculatingUSD")
        if isinstance(usd, dict):
            return num(usd.get("peggedUSD"))
        return num(usd)
    return None


def fetch_chain_tvl(chain: str) -> float | None:
    data = get_json("https://api.llama.fi/v2/chains")
    if not isinstance(data, list):
        return None
    target = chain.lower()
    for row in data:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("gecko_id") or "").lower()
        if name == target:
            return num(row.get("tvl"))
    return None


def fetch_snap(item: dict, lane: str, as_of: str) -> Snap:
    cg = fetch_coingecko(item["cg"])
    md = cg.get("market_data") or {}
    snap = Snap(
        ticker=item["ticker"].upper(),
        name=str(cg.get("name") or item["ticker"]),
        cg_id=item["cg"],
        tags=list(item.get("tags") or []),
        lane=lane,
        as_of=as_of,
        price=num((md.get("current_price") or {}).get("usd")),
        mcap=num((md.get("market_cap") or {}).get("usd")),
        fdv=num((md.get("fully_diluted_valuation") or {}).get("usd")),
        volume=num((md.get("total_volume") or {}).get("usd")),
        rank=int(cg["market_cap_rank"]) if cg.get("market_cap_rank") is not None else None,
        circ=num(md.get("circulating_supply")),
        total=num(md.get("total_supply")),
        max_supply=num(md.get("max_supply")),
        ath=num((md.get("ath") or {}).get("usd")),
        ath_date=str(((md.get("ath_date") or {}).get("usd") or ""))[:10] or None,
        chg_7d=num(md.get("price_change_percentage_7d")),
        chg_30d=num(md.get("price_change_percentage_30d")),
        sources=["CoinGecko"],
    )
    llama = item.get("llama")
    if llama:
        try:
            tvl, label = fetch_llama_protocol(llama)
            if tvl is not None:
                snap.tvl = tvl
                snap.tvl_label = f"{label} TVL"
                snap.sources.append("DefiLlama protocol")
            fees = fetch_llama_fees(llama, "dailyFees")
            rev = fetch_llama_fees(llama, "dailyRevenue")
            if fees is not None:
                snap.fees_30d = fees
                snap.sources.append("DefiLlama fees")
            if rev is not None:
                snap.rev_30d = rev
                snap.sources.append("DefiLlama revenue")
        except Exception as exc:  # noqa: BLE001 — keep the note if only Llama fails
            print(f"[warn] llama {llama}: {exc}", file=sys.stderr)
    elif item.get("chain"):
        try:
            tvl = fetch_chain_tvl(item["chain"])
            if tvl is not None:
                snap.tvl = tvl
                snap.tvl_label = f"{item['chain']} DeFi TVL"
                snap.sources.append("DefiLlama chains")
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] chain {item['chain']}: {exc}", file=sys.stderr)
    snap.sources = list(dict.fromkeys(snap.sources))
    if snap.price is None or snap.mcap is None:
        raise RuntimeError(f"{snap.ticker}: CoinGecko missing price or market cap")
    time.sleep(0.4)
    snap.peers = fetch_peers(snap.ticker, lane)
    if snap.peers:
        snap.sources.append("CoinGecko peers")
    if lane == "major" or "L1" in snap.tags:
        snap.chains = fetch_top_chains()
        snap.dexs = fetch_dex_chains()
        snap.stables = fetch_chain_stables(item.get("chain"))
        if snap.chains:
            snap.sources.append("DefiLlama chains")
        if snap.dexs:
            snap.sources.append("DefiLlama dexs")
        if snap.stables is not None:
            snap.sources.append("DefiLlama stablecoins")
    if snap.fees_30d is None and item.get("chain"):
        fees, rev = fetch_named_fees(item["chain"] if item["chain"] != "BSC" else "BSC")
        # DefiLlama chain rows use Ethereum / Solana / Bitcoin / BSC
        if fees is None:
            fees, rev = fetch_named_fees(str(item.get("chain")))
        if fees is not None:
            snap.fees_30d = fees
            snap.sources.append("DefiLlama chain fees")
        if rev is not None:
            snap.rev_30d = rev
            snap.sources.append("DefiLlama chain revenue")
    x = fetch_altindex(snap.ticker)
    btc_x = fetch_altindex("BTC") if snap.ticker != "BTC" else x
    stale = altindex_stale((x or {}).get("updated"), as_of) if x else False
    if x:
        snap.x_mentions = {"self": x, "btc": None if stale else btc_x, "stale": stale}
        snap.sources.append("AltIndex X mentions")
        if stale:
            print(f"[warn] altindex {snap.ticker} print is stale: {x.get('updated')}", file=sys.stderr)
    lunar = fetch_lunarcrush(snap.ticker, snap.cg_id)
    if lunar:
        snap.lunar = lunar
        snap.sources.append("LunarCrush")
    snap.sources = list(dict.fromkeys(snap.sources))
    return snap


def pick_item(candidates: list[dict], taken: set[str], lane: str, as_of: str) -> tuple[dict, Snap] | None:
    for item in candidates:
        ticker = item["ticker"].upper()
        if ticker in taken:
            continue
        try:
            snap = fetch_snap(item, lane, as_of)
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {ticker}: {exc}", file=sys.stderr)
            time.sleep(1.2)
            continue
        return item, snap
    return None


def write_langs(folder: Path, bodies: dict[str, str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.md").write_text(bodies["zh"], encoding="utf-8")
    for lang in LANGS:
        if lang == "zh":
            continue
        (folder / f"report.{lang}.md").write_text(bodies[lang], encoding="utf-8")


def astro_content_dir() -> Path | None:
    raw = os.environ.get("ASTRO_CONTENT", str(ASTRO_CONTENT))
    if not raw:
        return None
    path = Path(raw)
    return path if path.parent.exists() else None


def write_astro(snap: Snap, score: float, titles: dict[str, str], desc: dict[str, str], conclusions: dict[str, str], day: str, zh_body: str) -> None:
    dest_dir = astro_content_dir()
    if dest_dir is None:
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    tags = "\n".join(f"  - {tag}" for tag in snap.tags)
    body = zh_body.split("\n---\n", 1)[-1].lstrip()
    text = (
        "---\n"
        f"title: \"{yaml_escape(titles['zh'])}\"\n"
        f"titleEn: \"{yaml_escape(titles['en'])}\"\n"
        f"description: \"{yaml_escape(desc['zh'])}\"\n"
        f"descriptionEn: \"{yaml_escape(desc['en'])}\"\n"
        f"date: {day}\n"
        f"asOf: \"{snap.as_of}\"\n"
        f"ticker: {snap.ticker}\n"
        f"score: {score:.1f}\n"
        f"tags:\n{tags}\n"
        f"conclusion: \"{yaml_escape(conclusions['zh'])}\"\n"
        f"conclusionEn: \"{yaml_escape(conclusions['en'])}\"\n"
        "---\n\n"
        f"{body}"
    )
    (dest_dir / f"{snap.ticker.lower()}-{day}.md").write_text(text, encoding="utf-8")


def select_pair(as_of: str) -> list[tuple[str, Snap]]:
    universe = load_universe()
    taken = published_tickers()
    yday = utc_now().timetuple().tm_yday
    lane = LANES[yday % 3]
    picked: list[tuple[str, Snap]] = []

    major = pick_item(universe["majors"], taken, "major", as_of)
    if not major:
        raise SystemExit("no unused major left that CoinGecko will serve")
    picked.append(("major", major[1]))
    taken.add(major[1].ticker)
    time.sleep(1.2)

    order = [lane] + [x for x in LANES if x != lane]
    sat = None
    for name in order:
        sat = pick_item(universe["lanes"][name], taken, name, as_of)
        if sat:
            if name != lane:
                print(f"[info] {lane} empty or failing, using {name}", file=sys.stderr)
            picked.append((name, sat[1]))
            break
        time.sleep(1.0)
    if not sat:
        raise SystemExit("no unused satellite left that CoinGecko will serve")
    return picked


def run(dry_run: bool, force: bool) -> int:
    day = today_utc()
    existing = notes_on(day)
    if len(existing) >= 2 and not force:
        print(f"already have {len(existing)} notes on {day}: {', '.join(existing)}")
        print_status(day)
        return 0
    as_of = utc_now().strftime("%Y-%m-%d %H:%M UTC")
    pair = select_pair(as_of)
    for lane, snap in pair:
        score, dims = score_note(snap)
        drafted = draft_note(snap, score, dims, day)
        print(f"{snap.ticker} [{lane}] {score:.1f} {verdict(score)[1]} as-of {snap.as_of}")
        if dry_run:
            continue
        folder = ROOT / "research" / snap.ticker.lower()
        if folder.exists() and (folder / "report.md").exists() and not force:
            raise SystemExit(f"{folder} already exists")
        write_langs(folder, drafted["bodies"])
        write_astro(snap, score, drafted["titles"], drafted["desc"], drafted["conclusions"], day, drafted["bodies"]["zh"])
    if dry_run:
        print("dry-run: no files written")
        return 0
    print_status(day)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish two DRLabs desk notes from public data.")
    parser.add_argument("--dry-run", action="store_true", help="pick names and fetch prints, do not write")
    parser.add_argument("--force", action="store_true", help="ignore the two-notes-per-day stop")
    parser.add_argument("--status", action="store_true", help="print public URLs for today's notes")
    args = parser.parse_args()
    if args.status:
        print_status(today_utc())
        return
    raise SystemExit(run(dry_run=args.dry_run, force=args.force))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Zero-cost extra sources for desk notes: headlines (RSS), unlock schedules (DefiLlama
datasets), hack history (DefiLlama), project self-description (CoinGecko), and the
sector-fit rules used to pick peers. Every function fails soft: if a source does not
answer, the caller gets None / [] and the note simply leaves that part out.

Nothing here invents text. Headlines are passed through verbatim with outlet, date and link.
"""
from __future__ import annotations

import email.utils
import html
import json
import math
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTORS = json.loads((HERE / "desk_sectors.json").read_text(encoding="utf-8"))

FEEDS = (
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("The Block", "https://www.theblock.co/rss.xml"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("CryptoSlate", "https://cryptoslate.com/feed/"),
)
# outlets accepted from the Google News search feed (by publisher domain)
OUTLETS = {
    "coindesk.com": "CoinDesk", "cointelegraph.com": "Cointelegraph", "theblock.co": "The Block",
    "decrypt.co": "Decrypt", "blockworks.co": "Blockworks", "cryptoslate.com": "CryptoSlate",
    "bitcoinmagazine.com": "Bitcoin Magazine", "dlnews.com": "DL News", "thedefiant.io": "The Defiant",
    "unchainedcrypto.com": "Unchained", "reuters.com": "Reuters", "bloomberg.com": "Bloomberg",
    "cnbc.com": "CNBC", "forbes.com": "Forbes", "fortune.com": "Fortune", "finance.yahoo.com": "Yahoo Finance",
    "barrons.com": "Barron's", "ft.com": "Financial Times", "wsj.com": "WSJ", "axios.com": "Axios",
    "techcrunch.com": "TechCrunch", "beincrypto.com": "BeInCrypto", "crypto.news": "crypto.news",
    "cryptonews.com": "Cryptonews", "cryptopotato.com": "CryptoPotato", "theguardian.com": "The Guardian",
    "coinbase.com": "Coinbase", "messari.io": "Messari", "galaxy.com": "Galaxy", "kaiko.com": "Kaiko",
}
# second tier: sector / regional outlets, used only when the first tier finds fewer than two headlines
OUTLETS_2 = {
    "egamers.io": "eGamers.io", "blockchaingamer.biz": "BlockchainGamer.biz", "playtoearn.com": "PlayToEarn",
    "cryptoticker.io": "CryptoTicker", "kalkine.com.au": "Kalkine Media", "theblockcrypto.com": "The Block",
    "coingape.com": "CoinGape", "u.today": "U.Today", "ambcrypto.com": "AMBCrypto", "bitcoinist.com": "Bitcoinist",
    "newsbtc.com": "NewsBTC", "coincu.com": "Coincu", "cryptobriefing.com": "Crypto Briefing", "protos.com": "Protos",
    "theminermag.com": "TheMinerMag", "pymnts.com": "PYMNTS", "investing.com": "Investing.com", "benzinga.com": "Benzinga",
}
JUNK_TITLE = re.compile(
    r"(price prediction|we asked|chatgpt|\bgrok\b|ai predicts|can .{1,40} reach|will .{1,40} hit|\bto \$[\d,.]+\?|sponsored|press release|top \d+ (coins|altcoins|cryptos))",
    re.I,
)
COMMON_TICKERS = {
    "ONE", "GAS", "SUPER", "PRIME", "BEAM", "SAND", "GODS", "NEAR", "SUN", "MOVE", "GALA", "ICE", "PEOPLE", "ACE",
    "HIGH", "LOOKS", "RARE", "REAL", "SAFE", "MASK", "BOND", "FLOW", "KEY", "LIT", "MAGIC", "TRUMP", "GAME",
    "HOT", "POWER", "HUNT", "PORTAL", "NOT", "BIG", "OPEN", "VERSE", "ALL", "CAT", "DOG", "AI", "ID", "OM", "WAX",
    "ARB", "OP", "SEI", "SUI", "TON", "ENA", "JUP", "IMX",
}
NEWS_TAGS = (
    ("security", r"\b(hack(ed|er|s)?|exploit(ed)?|drain(ed)?|breach|stolen|attack(er)?|vulnerab\w+)\b"),
    ("regulation", r"\b(sec|cftc|doj|lawsuit|sues?|sued|court|regulat\w+|ban(s|ned)?|fine[ds]?|settle\w*|probe|investigat\w+|mica|sanction\w*|subpoena)\b"),
    ("listing", r"\b(list(s|ed|ing)?|delist\w*)\b"),
    ("institutional", r"\b(etf|etp|treasury|institution\w*|blackrock|grayscale|fidelity|vaneck|fund)\b"),
    ("funding", r"\b(raise[sd]?|funding|acquir\w+|acquisition|series [abc]|backs|invest(s|ment))\b"),
    ("token", r"\b(unlock\w*|airdrop\w*|burn\w*|buyback\w*|tokenomics|emission\w*|inflation|halving|staking)\b"),
    ("product", r"\b(launch\w*|goes live|is live|demo|beta|mainnet|upgrade\w*|testnet|v[2-9]\b|release\w*|integrat\w+|partner\w*|rollout|roadmap)\b"),
    ("opinion", r"\b(analyst\w*|trader\w*|says|said|argues?|predicts?|warns?|case for|opinion|long & short|why|bull(ish)? case|bear(ish)? case|outlook|thesis)\b"),
    ("price", r"\b(surg\w+|soar\w*|jump\w*|rall\w+|plung\w+|slump\w*|tumbl\w+|drop\w*|ris(es|ing)|fall(s|ing)?|climb\w*|record high|all-time high|crash\w*|rebound\w*)\b"),
)


def _ts(dt: datetime) -> float:
    return dt.timestamp()


def parse_rss(xml_text: str, default_outlet: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out: list[dict] = []
    for item in root.iter("item"):
        title = html.unescape((item.findtext("title") or "").strip())
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or ""
        try:
            dt = email.utils.parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                continue
        outlet = default_outlet
        src = item.find("source")
        if src is not None:
            dom = urllib.parse.urlparse(src.attrib.get("url", "")).netloc.lower().removeprefix("www.")
            outlet = OUTLETS.get(dom) or (("2:" + OUTLETS_2[dom]) if dom in OUTLETS_2 else "")
            name = (src.text or "").strip()
            if name and title.endswith(f" - {name}"):
                title = title[: -len(name) - 3].strip()
        if not title or not link or not outlet:
            continue
        out.append({"title": title, "url": link, "outlet": outlet, "ts": _ts(dt), "date": dt.astimezone(timezone.utc).strftime("%Y-%m-%d")})
    return out


def mentions(title: str, name: str, ticker: str) -> bool:
    if name and len(name) >= 4 and re.search(rf"(?<![\w$]){re.escape(name)}(?!\w)", title, re.I):
        if name.upper() not in COMMON_TICKERS or re.search(r"\b(token|coin|crypto|blockchain|network|protocol)\b", title, re.I):
            return True
    t = ticker.upper()
    if len(t) >= 3 and t not in COMMON_TICKERS and re.search(rf"(?<![\w]){re.escape(t)}(?![\w])", title):
        return True
    if len(t) >= 2 and re.search(rf"\${re.escape(t)}\b", title):
        return True
    return False


def tag_headline(title: str) -> list[str]:
    return [tag for tag, rx in NEWS_TAGS if re.search(rx, title, re.I)]


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    return title.replace("[", "(").replace("]", ")").replace("*", "").replace("|", "/")


def clean_url(url: str) -> str:
    return url.replace("(", "%28").replace(")", "%29").replace(" ", "%20")


def collect_news(fetch_text, name: str, ticker: str, now: datetime, days: int = 30, limit: int = 6) -> list[dict]:
    """fetch_text(url) -> str. Returns newest-first headlines that name the coin."""
    pool: list[dict] = []
    for outlet, url in FEEDS:
        try:
            pool.extend(parse_rss(fetch_text(url), outlet))
        except Exception:  # noqa: BLE001
            continue
    q = f'"{name}" (crypto OR token OR blockchain) when:{days}d'
    gurl = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    try:
        pool.extend(parse_rss(fetch_text(gurl), ""))
    except Exception:  # noqa: BLE001
        pass
    cutoff = _ts(now - timedelta(days=days))
    seen: set[str] = set()
    hits: list[dict] = []
    for it in sorted(pool, key=lambda r: -r["ts"]):
        if it["ts"] < cutoff or it["ts"] > _ts(now) + 3600:
            continue
        if JUNK_TITLE.search(it["title"]) or not mentions(it["title"], name, ticker):
            continue
        key = re.sub(r"[^a-z0-9]+", "", it["title"].lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        hits.append({"title": clean_title(it["title"]), "url": clean_url(it["url"]), "outlet": it["outlet"],
                     "date": it["date"], "tags": tag_headline(it["title"])})
    # keep outlet variety: at most 2 per outlet; second-tier outlets only fill a near-empty list
    first = [h for h in hits if not h["outlet"].startswith("2:")]
    if len(first) < 2:
        per2: dict[str, int] = {}
        for h in hits:
            if h["outlet"].startswith("2:") and per2.get(h["outlet"], 0) < 1 and sum(per2.values()) < 3:
                per2[h["outlet"]] = per2.get(h["outlet"], 0) + 1
                first.append(dict(h, outlet=h["outlet"][2:]))
    out, per = [], {}
    for h in first:
        if per.get(h["outlet"], 0) >= 2:
            continue
        per[h["outlet"]] = per.get(h["outlet"], 0) + 1
        out.append(h)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- unlocks (DefiLlama datasets, free)

UNLOCK_BASE = "https://defillama-datasets.llama.fi"


def unlock_candidates(cg_id: str, name: str, ticker: str, llama_slug: str | None) -> list[str]:
    raw = [llama_slug, cg_id, cg_id.replace("-", ""), re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
           re.sub(r"[^a-z0-9]+", "", name.lower()), ticker.lower()]
    return list(dict.fromkeys(x for x in raw if x))


def _value_at(points: list[tuple[float, float]], t: float) -> float:
    prior = [v for ts, v in points if ts <= t]
    return prior[-1] if prior else 0.0


def summarise_unlocks(data: dict, now: datetime, price: float | None, circ: float | None, slug: str) -> dict | None:
    series = ((data.get("documentedData") or {}).get("data")) or ((data.get("realTimeData") or {}).get("data")) or []
    if not series:
        return None
    t0 = _ts(now)
    tot_now = tot30 = tot90 = 0.0
    by_label90: dict[str, float] = {}
    last_ts = 0.0
    for sec in series:
        pts = sorted((float(p.get("timestamp") or 0), float(p.get("unlocked") or 0)) for p in sec.get("data") or [] if isinstance(p, dict))
        if not pts:
            continue
        last_ts = max(last_ts, pts[-1][0])
        a, b, c = _value_at(pts, t0), _value_at(pts, t0 + 30 * 86400), _value_at(pts, t0 + 90 * 86400)
        tot_now += a
        tot30 += max(0.0, b - a)
        tot90 += max(0.0, c - a)
        if c - a > 0:
            by_label90[str(sec.get("label") or "other")] = c - a
    if tot_now <= 0 and tot90 <= 0:
        return None
    events = ((data.get("metadata") or {}).get("events")) or []
    cliffs = []
    for ev in events:
        ts = float(ev.get("timestamp") or 0)
        if ts <= t0 or ts > t0 + 365 * 86400 or ev.get("unlockType") != "cliff":
            continue
        toks = sum(float(x or 0) for x in (ev.get("noOfTokens") or []))
        if toks <= 0:
            continue
        m = re.search(r"from (.+?) on \{timestamp\}", ev.get("description") or "")
        cliffs.append({"date": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d"), "tokens": toks,
                       "label": (m.group(1) if m else ev.get("category") or "").strip(), "category": ev.get("category")})
    cliffs.sort(key=lambda e: e["date"])
    out = {
        "slug": slug,
        "url": f"https://defillama.com/unlocks/{slug}",
        "unlocked_now": tot_now,
        "next30": tot30,
        "next90": tot90,
        "schedule_ends": datetime.fromtimestamp(last_ts, timezone.utc).strftime("%Y-%m-%d") if last_ts else None,
        "top_label90": max(by_label90, key=by_label90.get) if by_label90 else None,
        "next_cliff": cliffs[0] if cliffs else None,
    }
    if circ:
        out["next30_pct_circ"] = 100 * tot30 / circ
        out["next90_pct_circ"] = 100 * tot90 / circ
        out["schedule_vs_circ"] = tot_now / circ if circ else None
        if cliffs:
            out["next_cliff"]["pct_circ"] = 100 * cliffs[0]["tokens"] / circ
    if price:
        out["next30_usd"] = tot30 * price
        out["next90_usd"] = tot90 * price
        if cliffs:
            out["next_cliff"]["usd"] = cliffs[0]["tokens"] * price
    return out


def fetch_unlocks(get_json, cg_id: str, name: str, ticker: str, llama_slug: str | None, now: datetime,
                  price: float | None, circ: float | None) -> dict | None:
    listed = get_json(f"{UNLOCK_BASE}/emissionsProtocolsList")
    listed = set(listed) if isinstance(listed, list) else set()
    cands = unlock_candidates(cg_id, name, ticker, llama_slug)
    # the index is incomplete (e.g. "arbitrum" has a file but is not listed): listed slugs first, then the rest
    cands = [c for c in cands if c in listed] + [c for c in cands if c not in listed]
    for slug in cands:
        data = get_json(f"{UNLOCK_BASE}/emissions/{slug}", timeout=60)
        if not isinstance(data, dict):
            continue
        gid = data.get("gecko_id")
        if gid and gid != cg_id:
            continue
        out = summarise_unlocks(data, now, price, circ, slug)
        if out:
            # sanity: a schedule that disagrees wildly with CoinGecko's circulating supply is not this token
            ratio = out.get("schedule_vs_circ")
            if ratio is not None and not (0.2 <= ratio <= 5):
                return None
            return out
    return None


# ---------------------------------------------------------------- hacks (DefiLlama, free)

def find_hacks(rows: list, names: list[str], llama_ids: list[str]) -> list[dict]:
    norm = {re.sub(r"[^a-z0-9]+", "", n.lower()) for n in names if n}
    ids = {str(i) for i in llama_ids if i}
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        nm = re.sub(r"[^a-z0-9]+", "", str(r.get("name") or "").lower())
        if (str(r.get("defillamaId") or "") in ids) or (nm and nm in norm):
            ts = r.get("date") or 0
            out.append({"date": datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d") if ts else None,
                        "name": r.get("name"), "amount": r.get("amount"), "technique": r.get("technique"),
                        "classification": r.get("classification"), "returned": r.get("returnedFunds")})
    out.sort(key=lambda h: h["date"] or "", reverse=True)
    return out[:3]


# ---------------------------------------------------------------- project profile (CoinGecko, already fetched)

def first_sentence(text: str, limit: int = 220) -> str | None:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    if not text:
        return None
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    sent = (m.group(1) if m else text).strip()
    if len(sent) > limit:
        cut = sent[:limit].rsplit(" ", 1)[0]
        sent = cut.rstrip(",;:") + "…"
    return sent.replace("[", "(").replace("]", ")").replace("*", "").replace("|", "/")


def project_profile(coin: dict) -> dict:
    links = coin.get("links") or {}
    home = next((u for u in (links.get("homepage") or []) if u), None)
    wp = links.get("whitepaper") or None
    gh = [u for u in ((links.get("repos_url") or {}).get("github") or []) if u]
    tw = links.get("twitter_screen_name") or None
    return {
        "about": first_sentence(((coin.get("description") or {}).get("en")) or ""),
        "homepage": clean_url(home) if home else None,
        "whitepaper": clean_url(wp) if isinstance(wp, str) and wp.startswith("http") else None,
        "x": tw,
        "github": clean_url(gh[0]) if gh else None,
        "genesis": coin.get("genesis_date"),
    }


# ---------------------------------------------------------------- sector fit

_MEME_RX = re.compile(SECTORS.get("meme_name") or r"$^", re.I)
_OFF_RX = re.compile(SECTORS.get("offsector_name") or r"$^", re.I)


def sector_core(cat_id: str | None, universe: dict, lane: str | None) -> set[str]:
    core = set((SECTORS.get("core") or {}).get(cat_id or "", []))
    lane_map = {"gaming": "GameFi", "decentralized-finance-defi": "DeFi", "layer-2": "L2", "meme-token": "Meme"}
    ln = lane_map.get(cat_id or "") or (lane if lane in (universe.get("lanes") or {}) else None)
    for item in (universe.get("lanes") or {}).get(ln or "", []):
        core.add(item["cg"])
    return core


def sector_fit(rows: list[dict], cat_id: str | None, target_cg: str, meme_ids: set[str], target_is_meme: bool) -> tuple[list[dict], list[str]]:
    """Drop memecoins and off-sector tokens from a CoinGecko category list. Returns (kept, dropped ids)."""
    excl = set((SECTORS.get("exclude") or {}).get("_all", [])) | set((SECTORS.get("exclude") or {}).get(cat_id or "", []))
    kept, dropped = [], []
    for r in rows:
        cid = r.get("cg") or r.get("id")
        if cid == target_cg:
            kept.append(r)
            continue
        label = f"{r.get('name') or ''} {r.get('ticker') or r.get('symbol') or ''}"
        meme = cid in meme_ids or bool(_MEME_RX.search(label))
        if (not target_is_meme and (meme or cid in excl)) or (target_is_meme and cid in excl and not meme):
            dropped.append(cid)
            continue
        if not target_is_meme and _OFF_RX.search(label) and cat_id != "artificial-intelligence":
            dropped.append(cid)
            continue
        kept.append(r)
    return kept, dropped


def choose_peers(rows: list[dict], target_cg: str, mcap: float, core: set[str], n: int = 4) -> tuple[list[dict], dict | None]:
    others = [r for r in rows if r["cg"] != target_cg and r.get("mcap")]
    if not others:
        return [], None
    core_rows = [r for r in others if r["cg"] in core]
    pool_for_leader = core_rows or others
    top = max(pool_for_leader, key=lambda r: r["mcap"])
    leader = top if top["mcap"] > mcap else None

    def dist(r):
        return abs(math.log((r["mcap"] or 1) / (mcap or 1)))

    near_core = sorted([r for r in core_rows if dist(r) <= math.log(6)], key=dist)
    near_rest = sorted([r for r in others if r["cg"] not in core], key=dist)
    chosen: list[dict] = []
    for r in ([leader] if leader else []) + near_core + near_rest:
        if r and r["cg"] not in {c["cg"] for c in chosen}:
            chosen.append(r)
        if len(chosen) >= n:
            break
    for r in chosen:
        r["core"] = r["cg"] in core
    if leader:
        leader["leader"] = True
    return chosen, leader


def drop_categories(cg_id: str, cats: list[str], chain_tvl: float | None) -> list[str]:
    rule = (SECTORS.get("category_drop") or {}).get("always", {})
    drop = set(rule.get(cg_id, []))
    if "Smart Contract Platform" in cats and (chain_tvl or 0) < 2e7:
        drop.add("Smart Contract Platform")
    return [c for c in cats if c not in drop]

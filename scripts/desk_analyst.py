#!/usr/bin/env python3
"""Compose one DRLabs note from one coin's data pack.

The writer works like a desk analyst, not a form:
  1. derive signals from whatever was actually fetched (market structure, supply and unlock
     schedule, on-chain usage, valuation vs sector-fit peers, news flow, crowd sentiment);
  2. classify every signal against explicit numeric thresholds (TH) so a label can never
     contradict its number; audit() re-checks every label independently before publishing;
  3. turn each signal into a finding with a weight and a tone, and build the note around the
     strongest findings: the title, the section order, the headings, the score and the KOL take.
Wording comes from desk_phrases.P: several variants per slot, picked per coin/day, skipping any
variant whose sentence skeleton already appears in another note published the same day.
A dimension with no fetched data is left out, never filled with invented numbers.
"""
from __future__ import annotations

import hashlib
import math
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime

from desk_phrases import P

LANGS = ("zh", "en", "ja", "ko", "fr", "es", "ru")

BANNED = (
    "定价厚，链上锁仓只解释一部分",
    "能核的规模",
    "只对上面能核的数字负责",
    "按赛道给底，不编功能进度",
    "迷因资产额外下调",
    "对照同行之后，结论写在下面",
    "而不是社交媒体热度",
    "市值排序、成交排序和锁仓排序可能是三件事",
    "分数跟的是这一个标的的位置",
)

# Every qualitative label is tied to one of these numbers. audit() re-checks them.
TH = {
    "mom_hot": 25.0,       # 30d % for "frenzy"
    "mom_warm": 10.0,      # 30d % for "warm"
    "mom_cold": -10.0,     # 30d % for "cold"
    "mom_capit": -25.0,    # 30d % for "capitulation"
    "jolt7": 12.0,         # |7d %| that breaks a "quiet" read
    "pull7": -10.0,        # 7d % for a pullback after a big run
    "pull7_finding": -12.0,
    "spike7": 15.0,
    "boom1y": 200.0,       # 1y % for "big run"
    "vol_surge": 35.0,     # 7d avg volume vs prior 30d, %
    "vol_dry": -35.0,
    "turn_hot": 35.0,      # 24h turnover %
    "turn_thin": 2.0,
    "vola_high": 90.0,     # 30d annualised %
    "vola_low": 40.0,
    "ath_deep": -80.0,
    "ath_near": -15.0,
    "ext200": 60.0,        # % above 200d that counts as overextended
    "rs30": 6.0,
    "rs1y": 30.0,
    "rs_sector": 8.0,
    "val_cheap": 0.75,
    "val_rich": 1.4,
    "unlock_heavy30": 2.0,  # % of float unlocking in 30d
    "unlock_light90": 1.0,  # % of float unlocking in 90d
}

FIXED_H = {
    "snap": {"zh": "数据快照", "en": "Snapshot", "ja": "データスナップショット", "ko": "데이터 스냅샷", "fr": "Instantané", "es": "Instantánea", "ru": "Снимок"},
    "score": {"zh": "买入评分", "en": "Buy score", "ja": "買いスコア", "ko": "매수 점수", "fr": "Score d’achat", "es": "Puntuación de compra", "ru": "Оценка покупки"},
    "risk": {"zh": "催化与风险", "en": "Catalysts and risks", "ja": "カタリストとリスク", "ko": "촉매와 위험", "fr": "Catalyseurs et risques", "es": "Catalizadores y riesgos", "ru": "Катализаторы и риски"},
    "src": {"zh": "数据来源", "en": "Sources", "ja": "出典", "ko": "출처", "fr": "Sources", "es": "Fuentes", "ru": "Источники"},
    "disc": {"zh": "免责声明", "en": "Disclaimer", "ja": "免責", "ko": "면책", "fr": "Avertissement", "es": "Aviso", "ru": "Отказ от ответственности"},
}
TAKE_H = (("研究结论", "Research take"), ("核心判断", "The call"), ("结论先行", "Bottom line first"))

DIM_LABEL = {
    "market": ("市场结构", "Market structure"),
    "token": ("代币与供给", "Token and supply"),
    "usage": ("链上使用", "On-chain usage"),
    "valuation": ("估值与同行", "Valuation vs peers"),
    "narrative": ("叙事与定位", "Narrative and seat"),
    "news": ("消息面", "News flow"),
    "kol": ("KOL 视角", "KOL angle"),
}
NEWS_TAG_ZH = {"security": "安全事件", "regulation": "监管/诉讼", "listing": "上架/下架", "institutional": "ETF/机构",
               "funding": "融资/并购", "token": "代币经济", "product": "产品/合作", "opinion": "观点/分析", "price": "价格异动"}
NEWS_TAG_EN = {"security": "security", "regulation": "regulation/legal", "listing": "listings", "institutional": "ETF/institutional",
               "funding": "funding/M&A", "token": "tokenomics", "product": "product/partnerships", "opinion": "opinion/analysis", "price": "price moves"}

CAT_ZH = {
    "Layer 1 (L1)": "Layer 1 公链", "Layer 2 (L2)": "Layer 2", "Smart Contract Platform": "智能合约平台",
    "Decentralized Finance (DeFi)": "DeFi", "Decentralized Exchange (DEX)": "去中心化交易所",
    "Meme": "迷因", "Gaming (GameFi)": "链游", "Play To Earn": "边玩边赚", "Artificial Intelligence (AI)": "AI",
    "Real World Assets (RWA)": "真实世界资产（RWA）", "Derivatives": "衍生品", "Lending/Borrowing Protocols": "借贷",
    "Liquid Staking": "流动性质押", "Exchange-based Tokens": "交易所代币", "Rollup": "Rollup", "Zero Knowledge (ZK)": "零知识证明",
    "Oracle": "预言机", "Infrastructure": "基础设施", "Governance": "治理代币", "Yield Farming": "收益耕作",
    "Perpetuals": "永续合约", "Stablecoin Protocol": "稳定币协议", "Restaking": "再质押", "DePIN": "DePIN",
    "AI Agents": "AI 智能体", "Privacy Coins": "隐私币", "Interoperability": "跨链互操作", "Storage": "存储",
    "NFT": "NFT", "Metaverse": "元宇宙", "Payment Solutions": "支付", "Proof of Work (PoW)": "工作量证明",
    "Proof of Stake (PoS)": "权益证明", "Solana Ecosystem": "Solana 生态", "Ethereum Ecosystem": "以太坊生态",
    "BNB Chain Ecosystem": "BNB Chain 生态", "Base Ecosystem": "Base 生态", "Arbitrum Ecosystem": "Arbitrum 生态",
    "Modular Blockchain": "模块化区块链", "Data Availability": "数据可用性", "Launchpad": "发射台",
    "Prediction Markets": "预测市场", "Bitcoin Ecosystem": "比特币生态", "Social": "社交",
    "Energi Ecosystem": "Energi 生态", "Polygon Ecosystem": "Polygon 生态", "Avalanche Ecosystem": "Avalanche 生态",
    "Optimism Ecosystem": "Optimism 生态", "Immutable Ecosystem": "Immutable 生态", "Ronin Ecosystem": "Ronin 生态",
    "Hyperliquid Ecosystem": "Hyperliquid 生态", "Sui Ecosystem": "Sui 生态", "Cosmos Ecosystem": "Cosmos 生态",
    "Liquid Staking Governance Tokens": "流动性质押治理代币", "Lending/Borrowing": "借贷", "Automated Market Maker (AMM)": "自动做市商（AMM）",
    "Real World Assets (RWA) Protocol": "RWA 协议", "Synthetic Issuer": "合成资产", "Bridge Governance Tokens": "跨链桥治理代币",
}
CAT_ZH.update({"Stablecoin Issuer": "稳定币发行方", "Cross-chain Communication": "跨链通信", "RWA Protocol": "RWA 协议",
               "Quantum-Resistant": "抗量子", "Privacy": "隐私", "Privacy Infrastructure": "隐私基础设施",
               "Decentralized Science (DeSci)": "去中心化科学", "Chain Abstraction": "链抽象", "Yield Tokenization": "收益代币化",
               "Liquid Staking Tokens": "流动性质押代币", "Seigniorage": "铸币税", "Restaking": "再质押"})
CAT_EN_SHORT = {"Gaming (GameFi)": "GameFi", "Decentralized Finance (DeFi)": "DeFi", "Layer 1 (L1)": "Layer 1", "Layer 2 (L2)": "Layer 2"}


# ------------------------------------------------------------------ formatting

def zh_usd(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "-" if v < 0 else ""
    n = abs(v)
    if n >= 1e12:
        return f"{sign}{n / 1e12:.2f} 万亿美元"
    if n >= 1e10:
        return f"{sign}{n / 1e8:.0f} 亿美元"
    if n >= 1e8:
        return f"{sign}{n / 1e8:.2f} 亿美元".replace(".00 ", " ")
    if n >= 1e6:
        return f"{sign}{n / 1e4:.0f} 万美元"
    if n >= 1e4:
        return f"{sign}{n / 1e4:.1f} 万美元"
    return f"{sign}{n:,.0f} 美元"


def en_usd(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "-" if v < 0 else ""
    n = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            return f"{sign}${n / div:.2f}{suf}"
    return f"{sign}${n:,.0f}"


def price_str(p: float | None) -> str:
    if p is None:
        return "—"
    if p >= 1000:
        return f"${p:,.0f}"
    if p >= 1:
        return f"${p:,.2f}" if p >= 10 else f"${p:.3f}"
    digits = 3
    q = p
    while q < 0.1 and digits < 12:
        q *= 10
        digits += 1
    return f"${p:.{digits}f}"


def pct(v: float | None, digits: int = 1) -> str:
    if v is None:
        return "—"
    if round(v, digits) == 0:
        v = 0.0
    return f"{v:+.{digits}f}%"


def apct(v: float | None, digits: int = 1) -> str:
    return "—" if v is None else f"{abs(v):.{digits}f}%"


def mult(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}×" if v < 100 else f"{v:,.0f}×"


def qty(v: float | None) -> str:
    if v is None:
        return "—"
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= div:
            return f"{v / div:.2f}{suf}"
    return f"{v:,.0f}"


def fnum(v: float, digits: int = 0) -> str:
    return f"{v:.{digits}f}"


def zh_date(day: str) -> str:
    dt = datetime.strptime(day[:10], "%Y-%m-%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def en_date(day: str) -> str:
    dt = datetime.strptime(day[:10], "%Y-%m-%d")
    return f"{dt.day} {dt.strftime('%b %Y')}"


def ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def chg(a: float | None, b: float | None) -> float | None:
    r = ratio(a, b)
    return None if r is None else 100 * (r - 1)


def median(vals) -> float | None:
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def deg(x: float, small: float, big: float) -> tuple[str, str]:
    a = abs(x)
    return ("大幅", "far") if a >= big else ("明显", "clearly") if a >= small else ("小幅", "slightly")


def tidy_zh(text: str) -> str:
    """Drop stray spaces between two CJK characters (e.g. "3171 万美元 的" -> "3171 万美元的")."""
    text = re.sub(r"(?<=[\u4e00-\u9fff）」』”》])[ ]+(?=[\u4e00-\u9fff（「『“《])", "", text)
    return re.sub(r"(?<=[：，。；！？])[ ]+(?=\S)", "", text)


# ------------------------------------------------------------------ skeletons / voice

def skeleton(text: str, lang: str = "zh") -> str:
    s = re.sub(r"\*\*", "", text)
    s = re.sub(r"\[[^\]]*\]\([^)]*\)", "L", s)
    s = re.sub(r"[$]?[-+]?\d[\d,]*(\.\d+)?", "N", s)
    if lang == "zh":
        s = re.sub(r"[A-Za-z][A-Za-z0-9.'&\-]*", "X", s)
    else:
        s = re.sub(r"\b[A-Z][A-Za-z0-9.'&\-]*", "X", s)
    s = re.sub(r"\s+", "", s)
    return s


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？])|\n|(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p and p.strip()]


class Voice:
    """Deterministic phrase choice. `avoid` holds the bodies of notes already published the same
    day; a variant whose skeleton appears in them is skipped, so two same-day notes never share a
    sentence pattern."""

    def __init__(self, seed: str, avoid: list[str] | None = None):
        self.seed = seed
        self.blob = {"zh": "", "en": ""}
        for body in avoid or []:
            for lang in ("zh", "en"):
                text = body.get(lang, "") if isinstance(body, dict) else (body if lang == "zh" else "")
                self.blob[lang] += "\n" + "\n".join(skeleton(s, lang) for s in split_sentences(text))

    def _order(self, key: str, n: int) -> list[int]:
        return sorted(range(n), key=lambda i: hashlib.sha256(f"{self.seed}:{key}:{i}".encode()).hexdigest())

    def pick(self, key: str, *options):
        return options[self._order(key, len(options))[0]]

    def _clash(self, zh: str, en: str) -> bool:
        for lang, txt in (("zh", zh), ("en", en)):
            if not self.blob[lang]:
                continue
            for sent in split_sentences(txt):
                sk = skeleton(sent, lang)
                if len(sk) >= 8 and sk in self.blob[lang]:
                    return True
        return False

    def say(self, slot: str, en: dict | None = None, **kw) -> tuple[str, str]:
        """Format one variant. `en` overrides fields for the English text (e.g. $ amounts)."""
        opts = P[slot]
        kw_en = {**kw, **(en or {})}
        first = None
        for i in self._order(slot, len(opts)):
            zh, en_txt = opts[i][0].format(**kw), opts[i][1].format(**kw_en)
            first = first or (zh, en_txt)
            if not self._clash(zh, en_txt):
                return zh, en_txt
        return first  # every variant clashes: fall back (tests flag this)


@dataclass
class Finding:
    dim: str
    key: str
    sal: float
    tone: int
    head: tuple[str, str]
    text: tuple[str, str]
    proof: tuple[str, str] = ("", "")
    span: str = ""  # "short" / "long" for market findings


@dataclass
class Ctx:
    pack: dict
    s: dict = field(default_factory=dict)
    f: list[Finding] = field(default_factory=list)
    labels: dict = field(default_factory=dict)

    def add(self, *args, **kw):
        self.f.append(Finding(*args, **kw))


# ------------------------------------------------------------------ signals

def launch_ath(c: dict) -> bool:
    g, a = c.get("genesis"), c.get("ath_date")
    if not g or not a:
        return False
    try:
        return abs((datetime.strptime(a[:10], "%Y-%m-%d") - datetime.strptime(g[:10], "%Y-%m-%d")).days) <= 45
    except ValueError:
        return False


def signals(pack: dict) -> dict:
    c = pack["cg"]
    h = pack.get("hist") or {}
    p = pack.get("protocol") or {}
    ch = pack.get("chain") or {}
    btc = pack.get("btc") or {}
    sector = pack.get("sector") or {}
    peers = pack.get("peers") or []
    s: dict = {}
    tv = ratio(c.get("volume"), c.get("mcap"))
    s["turnover"] = 100 * tv if tv is not None else None
    fdv = c.get("fdv")
    if fdv and c.get("mcap") and fdv >= c["mcap"] * 0.999:
        s["float"] = min(1.0, c["mcap"] / fdv)
        s["overhang"] = max(0.0, fdv - c["mcap"])
    if c.get("max_supply") and c.get("circ"):
        s["circ_max"] = min(1.0, c["circ"] / c["max_supply"])
        if s.get("float") is None or s["circ_max"] < s["float"] - 0.02:
            s["float"] = s["circ_max"]
            s["overhang"] = max(0.0, (c["max_supply"] - c["circ"]) * c["price"])
    s["pow"] = bool(c.get("hashing"))
    for k in ("chg_30d", "chg_1y", "chg_200d", "chg_7d"):
        if c.get(k) is not None and btc.get(k) is not None and pack["cg_id"] != "bitcoin":
            s[f"rs_btc_{k[4:]}"] = c[k] - btc[k]
    if c.get("chg_30d") is not None and sector.get("median_30d") is not None:
        s["rs_sector_30"] = c["chg_30d"] - sector["median_30d"]
    for k in ("ma50", "ma200"):
        if h.get(k):
            s[f"{k}_gap"] = 100 * (c["price"] / h[k] - 1)
    if h.get("hi90"):
        s["from_hi90"] = 100 * (c["price"] / h["hi90"] - 1)
    if h.get("lo90"):
        s["from_lo90"] = 100 * (c["price"] / h["lo90"] - 1)
    if h.get("vol7_avg") and h.get("vol30_avg"):
        s["vol_trend"] = 100 * (h["vol7_avg"] / h["vol30_avg"] - 1)
    circ = h.get("circ_chg_365d")
    if circ is not None and -10 < circ < 80:
        s["infl_1y"] = circ
    circ90 = h.get("circ_chg_90d")
    if circ90 is not None and -5 < circ90 < 40:
        s["infl_90d"] = circ90
    s["launch_ath"] = launch_ath(c)
    s["fees_material"] = bool(p and (p.get("fees30") or 0) >= 50_000)
    if p:
        s["fees_ann"] = p["fees30"] * 365 / 30 if p.get("fees30") else None
        s["rev_ann"] = p["rev30"] * 365 / 30 if p.get("rev30") else None
        s["fees_mom"] = chg(p.get("fees30"), p.get("fees_prev30"))
        s["rev_mom"] = chg(p.get("rev30"), p.get("rev_prev30"))
        if p.get("fees7") and p.get("fees30"):
            s["fees_accel"] = 100 * ((p["fees7"] * 30 / 7) / p["fees30"] - 1)
        if p.get("fees30") and p.get("rev30") is not None and p["fees30"] > 0:
            s["capture"] = 100 * p["rev30"] / p["fees30"]
        if p.get("rev30") and p.get("hrev30") is not None and p["rev30"] > 0:
            s["holder_share"] = 100 * p["hrev30"] / p["rev30"]
        s["tvl_mom"] = p.get("tvl_chg_30d") if p.get("tvl_chg_30d") is not None else chg(p.get("tvl"), p.get("tvl_prev_month"))
        s["tvl_90d"] = p.get("tvl_chg_90d")
        s["pf"] = ratio(c["mcap"], s["fees_ann"]) if s.get("fees_ann") else None
        s["ps"] = ratio(c["mcap"], s["rev_ann"]) if s.get("rev_ann") and s["rev_ann"] > 0 else None
        s["fdv_ps"] = ratio(fdv, s["rev_ann"]) if s.get("rev_ann") and fdv else None
        s["mtvl"] = ratio(c["mcap"], p.get("tvl")) if p.get("tvl") and p["tvl"] > 1e6 else None
        if s.get("fees_ann") and p.get("tvl") and p["tvl"] > 1e6:
            s["fee_yield"] = 100 * s["fees_ann"] / p["tvl"]
    if ch:
        s["chain_fees_ann"] = ch["fees30"] * 365 / 30 if ch.get("fees30") else None
        s["chain_fees_mom"] = chg(ch.get("fees30"), ch.get("fees_prev30"))
        s["dex_mom"] = chg(ch.get("dex30"), ch.get("dex_prev30"))
        s["chain_mtvl"] = ratio(c["mcap"], ch.get("tvl")) if ch.get("tvl") and ch["tvl"] > 1e6 else None
        s["chain_pf"] = ratio(c["mcap"], s["chain_fees_ann"]) if s.get("chain_fees_ann") else None
        s["dex_turn"] = ratio(ch.get("dex30"), ch.get("tvl")) if ch.get("dex30") and ch.get("tvl") else None
    pf_peers, ps_peers, mtvl_peers, turn_peers = [], [], [], []
    for q in peers:
        fees_ann = q["fees30"] * 365 / 30 if q.get("fees30") else None
        rev_ann = q["rev30"] * 365 / 30 if q.get("rev30") else None
        q["pf"] = ratio(q.get("mcap"), fees_ann) if fees_ann else None
        q["ps"] = ratio(q.get("mcap"), rev_ann) if rev_ann and rev_ann > 0 else None
        tvl = q.get("tvl") or q.get("chain_tvl")
        q["mtvl"] = ratio(q.get("mcap"), tvl) if tvl and tvl > 1e6 else None
        qt = ratio(q.get("volume"), q.get("mcap"))
        q["turnover"] = 100 * qt if qt is not None else None
        pf_peers.append(q["pf"]); ps_peers.append(q["ps"]); mtvl_peers.append(q["mtvl"]); turn_peers.append(q["turnover"])
    s["peer_pf"] = median(pf_peers) if sum(v is not None for v in pf_peers) >= 2 else None
    s["peer_ps"] = median(ps_peers) if sum(v is not None for v in ps_peers) >= 2 else None
    s["peer_mtvl"] = median(mtvl_peers) if sum(v is not None for v in mtvl_peers) >= 2 else None
    s["peer_turn"] = median(turn_peers)
    leader = next((q for q in peers if q.get("leader")), None)
    if leader and leader.get("mcap"):
        s["leader"] = leader
        s["leader_x"] = leader["mcap"] / c["mcap"]
    s["is_meme"] = "Meme" in (pack.get("tags") or []) or "Meme" in (c.get("categories") or [])
    if p and (s["fees_material"] or (p.get("tvl") or 0) >= 1e7):
        s["profile"] = "protocol"
    elif ch and ch.get("tvl") and (s.get("chain_mtvl") or 0) <= 300:
        s["profile"] = "chain"
    elif s["is_meme"]:
        s["profile"] = "meme"
    else:
        s["profile"] = "market"
    # sector temperature vs BTC: the median and the cap-weighted ex-self change must agree before
    # the sector is called hot or cold (one giant or one outlier cannot set the label alone)
    med, wav, b30 = sector.get("median_30d"), sector.get("wavg_ex_30d"), btc.get("chg_30d")
    if med is not None and b30 is not None:
        both = [med] + ([wav] if wav is not None and sector.get("n", 0) >= 5 else [])
        s["sector_basis"] = "both" if len(both) == 2 else "median"
        s["sector_temp"] = med
        s["sector_wavg"] = wav if len(both) == 2 else None
        calls = {"hot" if x - b30 > 5 else "cold" if b30 - x > 5 else "sync" for x in both}
        s["sector_call"] = calls.pop() if len(calls) == 1 else "split"
    u = pack.get("unlocks") or {}
    if u.get("next30_pct_circ") is not None:
        s["unlock30"] = u["next30_pct_circ"]
        s["unlock90"] = u.get("next90_pct_circ")
    s["crowd"] = crowd_state(pack, s)
    return s


def crowd_state(pack: dict, s: dict) -> str:
    c = pack["cg"]
    c30, c7, c1y = c.get("chg_30d"), c.get("chg_7d"), c.get("chg_1y")
    trend = (pack.get("social") or {}).get("trending_pos")
    attention = bool(trend) or (s.get("turnover") or 0) >= TH["turn_hot"]
    hot = (c30 is not None and c30 >= TH["mom_hot"]) or (attention and (c30 or 0) > 0)
    if hot and (c7 is None or c7 > TH["pull7"]):  # no FOMO call while the week is falling hard
        return "frenzy"
    if c1y is not None and c1y >= TH["boom1y"]:
        return "pullback" if (c7 is not None and c7 <= TH["pull7"]) else "runup"
    if c30 is None:
        return "quiet"
    if c30 <= TH["mom_capit"]:
        return "capit"
    if c30 >= TH["mom_warm"]:
        return "warm"
    if c30 <= TH["mom_cold"]:
        return "cold"
    if c7 is not None and abs(c7) >= TH["jolt7"]:
        return "jolt"
    return "quiet"


# ------------------------------------------------------------------ findings: market

def market_findings(x: Ctx, v: Voice) -> None:
    pk, s, c = x.pack, x.s, x.pack["cg"]
    h = pk.get("hist") or {}
    t = pk["ticker"]
    btc = pk.get("btc") or {}
    p = price_str(c["price"])
    g200, g50 = s.get("ma200_gap"), s.get("ma50_gap")
    if g200 is not None:
        if g200 > 0 and (g50 is None or g50 > 0):
            g50z = f"、比 50 日均线高 {g50:.0f}%" if g50 is not None else ""
            g50e = f" and {g50:.0f}% above the 50-day" if g50 is not None else ""
            if g200 > TH["ext200"]:
                half = 100 * (g200 / 200) / (1 + g200 / 100)
                txt = v.say("trend_up_ext", t=t, p=p, g200=fnum(g200), g50z=g50z, g50e=g50e, half=fnum(half))
                x.add("market", "trend_up", min(0.75, 0.45 + g200 / 160), +1, ("价格远高于 200 日均线", "stretched far above its 200-day average"),
                      txt, (f"高于 200 日均线 {g200:.0f}%", f"{g200:.0f}% above the 200-day"), "long")
            else:
                txt = v.say("trend_up", t=t, p=p, g200=fnum(g200), g50z=g50z, g50e=g50e)
                x.add("market", "trend_up", min(0.75, 0.45 + g200 / 80), +1, ("价格站在 200 日均线之上", "trading above its 200-day average"),
                      txt, (f"高于 200 日均线 {g200:.0f}%", f"{g200:.0f}% above the 200-day"), "long")
        elif g200 < 0 and (g50 is None or g50 < 0):
            g50z = f"，也低于 50 日均线 {abs(g50):.0f}%" if g50 is not None else ""
            g50e = f" and {abs(g50):.0f}% under the 50-day" if g50 is not None else ""
            txt = v.say("trend_down", t=t, p=p, g200=fnum(abs(g200)), g50z=g50z, g50e=g50e)
            x.add("market", "trend_down", min(0.8, 0.45 + abs(g200) / 80), -1, ("价格仍压在 200 日均线之下", "still pinned under its 200-day average"),
                  txt, (f"低于 200 日均线 {abs(g200):.0f}%", f"{abs(g200):.0f}% under the 200-day"), "long")
        else:
            txt = v.say("trend_mixed", t=t, p=p, g200s=pct(g200, 0), g50s=pct(g50, 0))
            x.add("market", "trend_mixed", 0.35, 0, ("价格卡在 50 日和 200 日均线之间", "caught between its 50- and 200-day averages"),
                  txt, (f"200 日均线 {pct(g200, 0)}", f"{pct(g200, 0)} vs 200-day"), "long")
    rs = s.get("rs_btc_30d")
    if rs is not None and abs(rs) >= TH["rs30"]:
        up = rs > 0
        dz, de = deg(rs, TH["rs30"], 20)
        txt = v.say("rs30_up" if up else "rs30_dn", t=t, c30=pct(c["chg_30d"]), b30=pct(btc.get("chg_30d")), rs=pct(rs), rsabs=apct(rs), deg=dz, deg_en=de)
        x.add("market", "rs_btc", min(1, 0.35 + abs(rs) / 50), +1 if up else -1,
              ("30 日跑赢比特币" if up else "30 日跑输比特币", "outrunning Bitcoin over 30 days" if up else "lagging Bitcoin over 30 days"),
              txt, (f"30 日相对比特币 {pct(rs)}", f"{pct(rs)} vs BTC over 30d"), "short")
    rs1y = s.get("rs_btc_1y")
    if rs1y is not None and abs(rs1y) >= TH["rs1y"]:
        up = rs1y > 0
        dz, de = deg(rs1y, TH["rs1y"], 150)
        txt = v.say("rs1y_up" if up else "rs1y_dn", t=t, c1y=pct(c.get("chg_1y")), b1y=pct(btc.get("chg_1y")), rs=pct(rs1y, 0), rsabs=apct(rs1y, 0), deg=dz, deg_en=de)
        x.add("market", "rs_btc_1y", min(0.9, 0.3 + abs(rs1y) / 200), +1 if up else -1,
              (f"一年维度{dz}跑赢比特币" if up else f"一年维度{dz}跑输比特币", "a one-year winner against Bitcoin" if up else "a one-year laggard against Bitcoin"),
              txt, (f"一年相对比特币 {pct(rs1y, 0)}", f"{pct(rs1y, 0)} vs BTC over 1y"), "long")
    rss = s.get("rs_sector_30")
    sec = pk.get("sector") or {}
    if rss is not None and abs(rss) >= TH["rs_sector"] and sec.get("n", 0) >= 8:
        up = rss > 0
        txt = v.say("rss_up" if up else "rss_dn", t=t, n=sec["n"], med=pct(sec["median_30d"]), c30=pct(c["chg_30d"]), rs=pct(rss), rsabs=apct(rss),
                    basis="中位数", basis_en="median")
        x.add("market", "rs_sector", min(0.8, 0.3 + abs(rss) / 60), +1 if up else -1,
              ("在板块里领涨" if up else "在板块里掉队", "leading its sector" if up else "trailing its sector"),
              txt, (f"板块内相对 {pct(rss)}", f"{pct(rss)} vs sector"), "short")
    ath = c.get("ath_chg")
    if ath is not None:
        athp = f"{abs(ath):.1f}" if abs(ath) >= 99 else f"{abs(ath):.0f}"
        if s.get("launch_ath") and h.get("hi90"):
            txt = v.say("ath_launch", t=t, ath=price_str(c.get("ath")), athd=c.get("ath_date"), genesis=c.get("genesis"),
                        hi90=price_str(h["hi90"]), from_hi=pct(s.get("from_hi90"), 0))
            x.add("market", "ath_launch", 0.3, 0, ("历史高点是上线初期的报价", "carrying an ATH that is only a launch-week print"),
                  txt, (f"距 90 日高点 {pct(s.get('from_hi90'), 0)}", f"{pct(s.get('from_hi90'), 0)} from the 90-day high"), "long")
        elif not s.get("launch_ath") and ath <= TH["ath_deep"]:
            txt = v.say("ath_deep", t=t, ath=price_str(c.get("ath")), athd=c.get("ath_date"), athp=athp, year=(c.get("ath_date") or "")[:4])
            x.add("market", "ath_deep", min(0.6, 0.3 + abs(ath) / 400), -1, ("距历史高点仍很远", "still far below its all-time high"),
                  txt, (f"距 ATH -{athp}%", f"-{athp}% from ATH"), "long")
        elif not s.get("launch_ath") and ath >= TH["ath_near"]:
            txt = v.say("ath_near", t=t, ath=price_str(c.get("ath")), athp=athp)
            x.add("market", "ath_near", 0.7, +1, ("逼近历史高点", "pressing against its all-time high"),
                  txt, (f"距 ATH {pct(ath, 0)}", f"{pct(ath, 0)} from ATH"), "long")
    c7, c30, c1y = c.get("chg_7d"), c.get("chg_30d"), c.get("chg_1y")
    if c7 is not None and c7 <= TH["pull7_finding"] and ((c30 or 0) > 0 or (c1y or 0) >= 100 or (g200 or 0) > 20):
        if (c1y or 0) >= 100:
            ctxz, ctxe = f"一年 {pct(c1y, 0)} 的大涨", f"a {pct(c1y, 0)} year"
        elif (c30 or 0) > 0:
            ctxz, ctxe = f"30 日 {pct(c30, 0)} 的上涨", f"a {pct(c30, 0)} month"
        else:
            ctxz, ctxe = f"站上 200 日均线 {g200:.0f}% 的趋势", f"a trend {g200:.0f}% above the 200-day"
        txt = v.say("pullback7", t=t, c7=pct(c7), c7abs=apct(c7), ctx=ctxz, ctx_en=ctxe)
        x.add("market", "pullback7", min(0.6, 0.3 + abs(c7) / 60), -1, ("短线明显回落", "pulling back sharply short term"),
              txt, (f"7 日 {pct(c7)}", f"{pct(c7)} over 7d"), "short")
    elif c7 is not None and c7 >= TH["spike7"]:
        txt = v.say("spike7", t=t, c7=pct(c7), c30=pct(c30))
        x.add("market", "spike7", min(0.55, 0.3 + c7 / 80), 0, ("短线急拉", "spiking short term"),
              txt, (f"7 日 {pct(c7)}", f"{pct(c7)} over 7d"), "short")
    tv = s.get("turnover")
    if tv is not None:
        pt = s.get("peer_turn")
        vt = s.get("vol_trend")
        trendz = f"，7 日均量较前 30 日 {pct(vt, 0)}" if vt is not None and abs(vt) >= 15 else ""
        trende = f"; 7-day average volume is {pct(vt, 0)} vs the prior 30 days" if vt is not None and abs(vt) >= 15 else ""
        peerz = f"（同行中位数约 {pt:.1f}%）" if pt is not None else ""
        peere = f" (peer median about {pt:.1f}%)" if pt is not None else ""
        kw = dict(t=t, vol=zh_usd(c["volume"]), tv=f"{tv:.0f}" if tv >= 10 else f"{tv:.1f}", peerz=peerz, peere=peere, trendz=trendz, trende=trende)
        if tv >= TH["turn_hot"]:
            z, e = v.say("turn_hot", **kw)
            e = e.replace(zh_usd(c["volume"]), en_usd(c["volume"]))
            x.add("market", "turn_hot", min(0.9, 0.4 + tv / 150), -1, ("换手过热，筹码在快速易手", "turning over at a frothy pace"),
                  (z, e), (f"换手 {tv:.0f}%", f"{tv:.0f}% turnover"), "short")
        elif tv < TH["turn_thin"]:
            z, e = v.say("turn_thin", **kw)
            e = e.replace(zh_usd(c["volume"]), en_usd(c["volume"]))
            x.add("market", "turn_thin", 0.55, -1, ("成交偏冷，流动性是硬约束", "thinly traded, with liquidity a hard constraint"),
                  (z, e), (f"换手 {tv:.1f}%", f"{tv:.1f}% turnover"), "short")
        elif pt and pt > 0 and (tv / pt >= 2.5 or tv / pt <= 0.4):
            hot_rel = tv / pt >= 2.5
            txt = v.say("turn_rel_hot" if hot_rel else "turn_rel_cold", t=t, tv=f"{tv:.1f}", pt=f"{pt:.1f}", x=f"{tv / pt:.1f}", trendz=trendz, trende=trende)
            x.add("market", "turn_rel", 0.5, +1 if hot_rel else -1,
                  ("交易活跃度远高于同行" if hot_rel else "交易活跃度明显落后同行", "far more actively traded than peers" if hot_rel else "traded far less than peers"),
                  txt, (f"换手 {tv:.1f}% vs 同行 {pt:.1f}%", f"turnover {tv:.1f}% vs peers {pt:.1f}%"), "short")
        elif vt is not None and (vt >= TH["vol_surge"] or vt <= TH["vol_dry"]):
            up = vt > 0
            txt = v.say("vol_up" if up else "vol_dn", t=t, vt=pct(vt, 0), tv=f"{tv:.1f}", peerz=peerz, peere=peere)
            x.add("market", "vol_shift", min(0.75, 0.3 + abs(vt) / 200), +1 if up else -1,
                  ("成交在放量" if up else "成交在缩量", "seeing volume expand" if up else "seeing volume dry up"),
                  txt, (f"7 日量能 {pct(vt, 0)}", f"7d volume {pct(vt, 0)}"), "short")
    v30, mdd = h.get("vol30"), h.get("mdd90")
    if v30 is not None and (v30 >= TH["vola_high"] or v30 <= TH["vola_low"]):
        hi = v30 >= TH["vola_high"]
        mddz = f"，近 90 日最大回撤 {pct(mdd, 0)}" if mdd is not None else ""
        mdde = f", 90-day max drawdown {pct(mdd, 0)}" if mdd is not None else ""
        txt = v.say("vola_hi" if hi else "vola_lo", t=t, v30=fnum(v30), d=f"{v30 / math.sqrt(365):.1f}", mddz=mddz, mdde=mdde)
        x.add("market", "volatility", min(0.6, 0.25 + v30 / 400) if hi else 0.35, 0,
              ("波动率很高，仓位要按风险算" if hi else "波动率处在低位", "running high volatility" if hi else "in a low-volatility squeeze"),
              txt, (f"年化波动 {v30:.0f}%", f"{v30:.0f}% annualised vol"), "short")


# ------------------------------------------------------------------ findings: token

def token_findings(x: Ctx, v: Voice) -> None:
    pk, s, c = x.pack, x.s, x.pack["cg"]
    t = pk["ticker"]
    fl = s.get("float")
    if fl is not None:
        flp = f"{100 * fl:.0f}"
        if fl < 0.6 and s.get("pow"):
            txt = v.say("issuance", t=t, circ=qty(c.get("circ")), maxs=qty(c.get("max_supply")), fl=flp, rest=f"{100 - 100 * fl:.0f}", ovh=zh_usd(s["overhang"]))
            txt = (txt[0], txt[1].replace(zh_usd(s["overhang"]), en_usd(s["overhang"])))
            x.add("token", "issuance", min(0.9, 0.45 + (0.6 - fl)), -1, ("区块奖励还远没挖完", "still far from fully mined"),
                  txt, (f"已发行 {flp}%", f"{flp}% issued"))
        elif fl < 0.6:
            kw = dict(t=t, mc=zh_usd(c["mcap"]), fdv=zh_usd(c.get("fdv")), fl=flp, ovh=zh_usd(s["overhang"]), ovx=mult(s["overhang"] / c["mcap"]))
            z, e = v.say("overhang", **kw)
            for a, b in ((kw["mc"], en_usd(c["mcap"])), (kw["fdv"], en_usd(c.get("fdv"))), (kw["ovh"], en_usd(s["overhang"]))):
                e = e.replace(a, b)
            x.add("token", "overhang", min(1, 0.5 + (0.6 - fl)), -1,
                  ("大部分供给还没进流通" if fl < 0.4 else "仍有大块供给未进流通", "mostly not yet circulating" if fl < 0.4 else "carrying a large block of locked supply"),
                  (z, e), (f"流通仅 {flp}%", f"only {flp}% float"))
        elif fl >= 0.93 or (s.get("pow") and fl >= 0.75):
            if s.get("pow") and c.get("max_supply"):
                txt = v.say("pow_float", t=t, circ=qty(c.get("circ")), maxs=qty(c.get("max_supply")), fl=flp)
                x.add("token", "pow_float", 0.4, +1, ("没有解锁悬顶", "free of any unlock overhang"), txt, (f"已发行 {flp}%", f"{flp}% issued"))
            else:
                kw = dict(t=t, mc=zh_usd(c["mcap"]), fdv=zh_usd(c.get("fdv") or c["mcap"]), fl=flp)
                z, e = v.say("full_float", **kw)
                e = e.replace(kw["mc"], en_usd(c["mcap"])).replace(kw["fdv"], en_usd(c.get("fdv") or c["mcap"]))
                x.add("token", "full_float", 0.25 if s.get("is_meme") else 0.45, +1, ("流通基本到位，解锁压力不大", "essentially fully circulating"),
                      (z, e), (f"流通约 {flp}%", f"~{flp}% float"))
        else:
            kw = dict(t=t, mc=zh_usd(c["mcap"]), fdv=zh_usd(c.get("fdv")), fl=flp, ovh=zh_usd(s["overhang"]))
            z, e = v.say("mid_float", **kw)
            for a, b in ((kw["mc"], en_usd(c["mcap"])), (kw["fdv"], en_usd(c.get("fdv"))), (kw["ovh"], en_usd(s["overhang"]))):
                e = e.replace(a, b)
            x.add("token", "mid_float", 0.4, 0, ("仍有一段解锁尾巴", "left with an unlock tail"), (z, e), (f"流通约 {flp}%", f"~{flp}% float"))
    infl = s.get("infl_1y")
    if infl is not None and (infl >= 8 or infl <= 1):
        hi = infl >= 8
        i90 = s.get("infl_90d")
        i90z = f"，最近 90 日 {pct(i90)}" if i90 is not None else ""
        i90e = f", {pct(i90)} in the last 90 days" if i90 is not None else ""
        txt = v.say("infl_hi" if hi else "infl_lo", t=t, infl=pct(infl, 0), i90z=i90z, i90e=i90e)
        x.add("token", "inflation", min(0.95, 0.35 + abs(infl) / 40) if hi else 0.4, -1 if hi else +1,
              ("流通量一年明显膨胀" if hi else "流通量一年几乎没变", "inflating its circulating supply fast" if hi else "holding circulating supply nearly flat for a year"),
              txt, (f"一年流通 {pct(infl, 0)}", f"supply {pct(infl, 0)}/yr"))
    if c.get("max_infinite"):
        txt = v.say("no_cap", t=t)
        x.add("token", "no_cap", 0.3, -1, ("没有供给上限", "uncapped in supply"), txt, ("无上限", "uncapped"))
    elif s.get("circ_max") is not None and s["circ_max"] >= 0.9 and fl is None:
        txt = v.say("cap_near", t=t, circ=qty(c["circ"]), maxs=qty(c["max_supply"]), cm=f"{100 * s['circ_max']:.0f}")
        x.add("token", "cap_near", 0.35, +1, ("接近供应上限", "close to its supply cap"), txt, (f"已发行 {100 * s['circ_max']:.0f}%", f"{100 * s['circ_max']:.0f}% issued"))
    u = pk.get("unlocks") or {}
    if u.get("next30_pct_circ") is not None:
        cl = u.get("next_cliff") or {}
        cliffz = cliffe = ""
        if cl.get("date") and cl.get("pct_circ") is not None and cl["pct_circ"] >= 0.3:
            lab = cl.get("label") or ""
            cliffz = f"；最近一笔集中解锁在 {cl['date']}，约 {qty(cl['tokens'])} 枚（流通量的 {cl['pct_circ']:.1f}%" + (f"，{lab}" if lab else "") + "）"
            cliffe = f"; the next cliff is on {cl['date']}, about {qty(cl['tokens'])} tokens ({cl['pct_circ']:.1f}% of float" + (f", {lab}" if lab else "") + ")"
        p30, p90 = u["next30_pct_circ"], u.get("next90_pct_circ") or 0
        end = u.get("schedule_ends")
        endz = f"，DefiLlama 记录的释放计划到 {end} 结束" if end else ""
        ende = f"; DefiLlama's schedule runs to {end}" if end else ""
        if p30 >= TH["unlock_heavy30"]:
            txt = v.say("unlock_heavy", t=t, n30=qty(u["next30"]), pct30=f"{p30:.1f}", usd30=zh_usd(u.get("next30_usd")), cliffz=cliffz, cliffe=cliffe, en=dict(usd30=en_usd(u.get("next30_usd"))))
            x.add("token", "unlock_sched", min(0.95, 0.5 + p30 / 20), -1, ("未来 30 天有大额解锁", "facing a heavy unlock in the next 30 days"),
                  txt, (f"30 天解锁 {p30:.1f}% 流通量", f"{p30:.1f}% of float unlocking in 30d"))
        elif p90 <= TH["unlock_light90"]:
            txt = v.say("unlock_light", t=t, n90=qty(u.get("next90")), pct90=f"{p90:.2f}" if p90 < 0.1 else f"{p90:.1f}", endz=endz, ende=ende)
            x.add("token", "unlock_sched", 0.4, +1, ("近 90 天几乎没有解锁", "facing almost no unlocks for 90 days"),
                  txt, (f"90 天解锁 {p90:.1f}% 流通量", f"{p90:.1f}% of float unlocking in 90d"))
        else:
            txt = v.say("unlock_mid", t=t, n90=qty(u.get("next90")), pct90=f"{p90:.1f}", usd90=zh_usd(u.get("next90_usd")), cliffz=cliffz, cliffe=cliffe, en=dict(usd90=en_usd(u.get("next90_usd"))))
            x.add("token", "unlock_sched", 0.45, 0, ("解锁在温和释放", "releasing unlocks at a moderate pace"),
                  txt, (f"90 天解锁 {p90:.1f}% 流通量", f"{p90:.1f}% of float unlocking in 90d"))


# ------------------------------------------------------------------ findings: usage

def _tone(val, up, dn):
    if val is None:
        return 0
    return +1 if val > up else -1 if val < dn else 0


def usage_findings(x: Ctx, v: Voice) -> None:
    pk, s = x.pack, x.s
    t = pk["ticker"]
    mc = pk["cg"]["mcap"]
    p = pk.get("protocol") or {}
    ch = pk.get("chain") or {}
    if p:
        name = p.get("name") or pk["name"]
        if p.get("fees30") is not None and not s.get("fees_material"):
            txt = v.say("fees_tiny", t=t, name=name, f30=zh_usd(p["fees30"]), mc=zh_usd(mc),
                        fannz=f"，年化约 {zh_usd(s['fees_ann'])}" if s.get("fees_ann") else "",
                        pfz=f"，市值 / 年化费用高达 {mult(s.get('pf'))}" if s.get("pf") else "",
                        en=dict(f30=en_usd(p["fees30"]), mc=en_usd(mc), fanne=f", about {en_usd(s['fees_ann'])} annualised" if s.get("fees_ann") else "",
                                pfe=f" (mcap / annualised fees {mult(s.get('pf'))})" if s.get("pf") else ""))
            x.add("usage", "fees_tiny", 0.55, -1, ("协议费用小到可以忽略", "earning protocol fees too small to matter"),
                  txt, (f"30 日费用仅 {zh_usd(p['fees30'])}", f"30d fees only {en_usd(p['fees30'])}"))
        if p.get("fees30") and s.get("fees_material"):
            mom, acc = s.get("fees_mom"), s.get("fees_accel")
            tone = _tone(mom, 8, -12)
            slot = "fees_up" if tone > 0 else "fees_dn" if tone < 0 else "fees_flat"
            txt = v.say(slot, t=t, name=name, f30=zh_usd(p["fees30"]), fann=zh_usd(s["fees_ann"]),
                        momz=f"，环比上一个 30 日 {pct(mom, 0)}" if mom is not None else "",
                        accz=f"；按最近 7 日的速度折算，月度节奏 {pct(acc, 0)}" if acc is not None and abs(acc) >= 10 else "",
                        en=dict(f30=en_usd(p["fees30"]), fann=en_usd(s["fees_ann"]), mome=f", {pct(mom, 0)} vs the prior 30" if mom is not None else "",
                                acce=f"; at the last 7 days' pace the monthly run-rate is {pct(acc, 0)}" if acc is not None and abs(acc) >= 10 else ""))
            hz = "费用在增长" if tone > 0 else "费用在萎缩" if tone < 0 else "费用基本持平"
            he = "growing its fees" if tone > 0 else "seeing its fees shrink" if tone < 0 else "holding fees flat"
            x.add("usage", "fees", 0.55 + min(0.35, abs(mom or 0) / 100) + (0.1 if p["fees30"] > 1e7 else 0), tone,
                  (f"{name} {hz}", he), txt,
                  (f"30 日费用 {zh_usd(p['fees30'])}" + (f"，环比 {pct(mom, 0)}" if mom is not None else ""),
                   f"30d fees {en_usd(p['fees30'])}" + (f", {pct(mom, 0)} MoM" if mom is not None else "")))
        cap = s.get("capture") if s.get("fees_material") else None
        if cap is not None:
            hs = s.get("holder_share")
            thin, keep = cap < 15, cap > 40
            hsz = f"；其中分给代币持有人的约 {zh_usd(p.get('hrev30'))}（收入的 {hs:.0f}%）" if hs is not None and p.get("hrev30") else ""
            hse = f"; holders received about {en_usd(p.get('hrev30'))} ({hs:.0f}% of revenue)" if hs is not None and p.get("hrev30") else ""
            txt = v.say("cap_thin" if thin else "cap_keep" if keep else "cap_mid", t=t, name=name, rev=zh_usd(p.get("rev30")), cap=f"{cap:.0f}", hsz=hsz, hse=hse,
                        en=dict(rev=en_usd(p.get("rev30"))))
            x.add("usage", "capture", (0.7 if (hs or 0) > 50 else 0.6) if thin or keep else 0.4, -1 if thin else +1 if keep else 0,
                  ("协议只留下很薄的一层收入" if thin else "协议留得住收入" if keep else "收入留存中等",
                   "keeping only a thin slice of fees" if thin else "keeping most of its fees as revenue" if keep else "retaining a middling share of fees"),
                  txt, (f"捕获率 {cap:.0f}%", f"{cap:.0f}% capture"))
        if p.get("tvl") and p["tvl"] > 1e6:
            tm, t90, fy = s.get("tvl_mom"), s.get("tvl_90d"), s.get("fee_yield")
            tone = _tone(tm, 8, -10)
            txt = v.say("tvl_in" if tone > 0 else "tvl_out" if tone < 0 else "tvl_flat", t=t, name=name, tvl=zh_usd(p["tvl"]),
                        tmz=f"，30 日 {pct(tm, 0)}" if tm is not None else "", t90z=f"、90 日 {pct(t90, 0)}" if t90 is not None else "",
                        fyz=f"；年化费用相当于锁仓的 {fy:.1f}%" if fy is not None else "",
                        en=dict(tvl=en_usd(p["tvl"]), tme=f", {pct(tm, 0)} over 30 days" if tm is not None else "",
                                t90e=f", {pct(t90, 0)} over 90" if t90 is not None else "", fye=f"; annualised fees equal {fy:.1f}% of TVL" if fy is not None else ""))
            x.add("usage", "tvl", 0.4 + min(0.4, abs(tm or 0) / 60), tone,
                  ("锁仓在流入" if tone > 0 else "锁仓在流出" if tone < 0 else "锁仓稳定", "drawing TVL in" if tone > 0 else "leaking TVL" if tone < 0 else "holding TVL steady"),
                  txt, (f"TVL {zh_usd(p['tvl'])}" + (f"，30 日 {pct(tm, 0)}" if tm is not None else ""),
                        f"TVL {en_usd(p['tvl'])}" + (f", {pct(tm, 0)} 30d" if tm is not None else "")))
    if ch:
        cname = ch.get("name") or pk["name"]
        if ch.get("tvl"):
            tm = ch.get("tvl_chg_30d")
            tone = _tone(tm, 8, -10)
            minor = (s.get("chain_mtvl") or 0) > 300
            sal = (0.45 + min(0.35, abs(tm or 0) / 60)) * (0.5 if minor else 1) * (0.7 if s.get("fees_material") else 1)
            slot = "ctvl_minor" if minor else "ctvl_in" if tone > 0 else "ctvl_out" if tone < 0 else "ctvl_flat"
            t90 = ch.get("tvl_chg_90d")
            txt = v.say(slot, t=t, cname=cname, tvl=zh_usd(ch["tvl"]), mc=zh_usd(mc),
                        rankz=f"，在 DefiLlama 统计的 {ch.get('n')} 条链里排第 {ch.get('rank')}" if ch.get("rank") else "",
                        tmz=f"，30 日 {pct(tm, 0)}" if tm is not None else "", t90z=f"、90 日 {pct(t90, 0)}" if t90 is not None else "",
                        stz=f"；稳定币存量 {zh_usd(ch.get('stables'))}" if ch.get("stables") else "",
                        en=dict(tvl=en_usd(ch["tvl"]), mc=en_usd(mc), ranke=f", #{ch.get('rank')} of {ch.get('n')} chains on DefiLlama" if ch.get("rank") else "",
                                tme=f", {pct(tm, 0)} over 30 days" if tm is not None else "", t90e=f" and {pct(t90, 0)} over 90" if t90 is not None else "",
                                ste=f"; stablecoins on chain {en_usd(ch.get('stables'))}" if ch.get("stables") else ""))
            if minor:
                head = (f"{cname} 链上 DeFi 体量很小", f"running only a small DeFi economy on {cname}")
            elif tone > 0:
                head = (f"{cname} 链上资金在流入", f"drawing capital onto {cname}")
            elif tone < 0:
                head = (f"{cname} 链上资金在流失", f"losing capital from {cname}")
            else:
                head = (f"{cname} 链上锁仓排第 {ch.get('rank')}" if ch.get("rank") else f"{cname} 链上锁仓持平",
                        f"ranked #{ch.get('rank')} by DeFi TVL" if ch.get("rank") else f"holding {cname} TVL flat")
            x.add("usage", "chain_tvl", sal, 0 if minor else tone, head, txt,
                  (f"链上 TVL {zh_usd(ch['tvl'])}" + (f"，30 日 {pct(tm, 0)}" if tm is not None else ""),
                   f"chain TVL {en_usd(ch['tvl'])}" + (f", {pct(tm, 0)} 30d" if tm is not None else "")))
        if ch.get("dex30"):
            dm = s.get("dex_mom")
            tone = _tone(dm, 10, -15)
            txt = v.say("dex_up" if tone > 0 else "dex_dn" if tone < 0 else "dex_flat", t=t, cname=cname, dex=zh_usd(ch["dex30"]),
                        dmz=f"，环比 {pct(dm, 0)}" if dm is not None else "", dtz=f"，约为链上锁仓的 {mult(s.get('dex_turn'))}" if s.get("dex_turn") else "",
                        en=dict(dex=en_usd(ch["dex30"]), dme=f", {pct(dm, 0)} month on month" if dm is not None else "",
                                dte=f", about {mult(s.get('dex_turn'))} its TVL" if s.get("dex_turn") else ""))
            x.add("usage", "chain_dex", (0.35 + min(0.4, abs(dm or 0) / 80)) * (0.7 if s.get("fees_material") else 1), tone,
                  ("链上交易在升温" if tone > 0 else "链上交易在降温" if tone < 0 else "链上交易平稳",
                   "seeing on-chain trading heat up" if tone > 0 else "seeing on-chain trading cool" if tone < 0 else "seeing steady on-chain trading"),
                  txt, (f"DEX 30 日 {zh_usd(ch['dex30'])}" + (f"，环比 {pct(dm, 0)}" if dm is not None else ""),
                        f"30d DEX {en_usd(ch['dex30'])}" + (f", {pct(dm, 0)} MoM" if dm is not None else "")))
        if ch.get("fees30"):
            fm = s.get("chain_fees_mom")
            tiny = (s.get("chain_fees_ann") or 0) < 0.001 * mc
            tone = 0 if tiny else _tone(fm, 10, -15)
            slot = "cfee_tiny" if tiny else "cfee_up" if tone > 0 else "cfee_dn" if tone < 0 else "cfee_flat"
            txt = v.say(slot, t=t, cname=cname, f30=zh_usd(ch["fees30"]), mc=zh_usd(mc),
                        fmz=f"，环比 {pct(fm, 0)}" if fm is not None else "", revz=f"，收入 {zh_usd(ch.get('rev30'))}" if ch.get("rev30") else "",
                        en=dict(f30=en_usd(ch["fees30"]), mc=en_usd(mc), fme=f", {pct(fm, 0)} month on month" if fm is not None else "",
                                reve=f", revenue {en_usd(ch.get('rev30'))}" if ch.get("rev30") else ""))
            x.add("usage", "chain_fees", 0.3 if tiny else (0.4 + min(0.3, abs(fm or 0) / 100)) * (0.7 if s.get("fees_material") else 1), tone,
                  ("链上费用相对市值微不足道" if tiny else "链上费用在增长" if tone > 0 else "链上费用在下滑" if tone < 0 else "链上费用持平",
                   "earning chain fees that are tiny next to its cap" if tiny else "growing chain fees" if tone > 0 else "seeing chain fees fall" if tone < 0 else "holding chain fees flat"),
                  txt, (f"链费 30 日 {zh_usd(ch['fees30'])}", f"30d chain fees {en_usd(ch['fees30'])}"))


# ------------------------------------------------------------------ findings: valuation

def valuation_findings(x: Ctx, v: Voice) -> None:
    pk, s, c = x.pack, x.s, x.pack["cg"]
    t = pk["ticker"]
    done = False
    mismatch = None
    material = s.get("fees_material")
    for key, own, peer, zh_lbl, en_lbl, zh_s, en_s in (
        ("ps", s.get("ps") if material else None, s.get("peer_ps"), "市值 / 年化收入（P/S）", "mcap / annualised revenue (P/S)", "P/S", "P/S"),
        ("pf", s.get("pf") if material else None, s.get("peer_pf"), "市值 / 年化费用（P/F）", "mcap / annualised fees (P/F)", "P/F", "P/F"),
        ("mtvl", s.get("mtvl") or s.get("chain_mtvl"), s.get("peer_mtvl"), "市值 / TVL", "mcap / TVL", "市值/TVL", "mcap/TVL"),
        ("cpf", s.get("chain_pf"), None, "市值 / 年化链费", "mcap / annualised chain fees", "市值/链费", "mcap/chain fees"),
    ):
        if own is None:
            continue
        if peer is not None:
            r = own / peer
            if r > 5 or r < 0.2:
                mismatch = mismatch or (zh_lbl, en_lbl, own, peer)
                continue
            cheap, rich = r < TH["val_cheap"], r > TH["val_rich"]
            txt = v.say("val_cheap" if cheap else "val_rich" if rich else "val_inline", t=t, lbl=zh_lbl, lbl_en=en_lbl, own=mult(own), peer=mult(peer), r=f"{r:.2f}")
            x.add("valuation", key, min(1, 0.45 + abs(r - 1) / 2), +1 if cheap else -1 if rich else 0,
                  ("估值比同行便宜" if cheap else "估值比同行贵" if rich else "估值与同行相当",
                   "cheaper than its peers" if cheap else "richer than its peers" if rich else "valued in line with peers"),
                  txt, (f"{zh_s} {mult(own)}，同行 {mult(peer)}", f"{en_s} {mult(own)} vs peers {mult(peer)}"))
            x.labels["val_ratio"] = r
        elif key == "cpf" and not mismatch and own > 1000:
            txt = v.say("val_anchor_cpf", t=t, lbl=zh_lbl, lbl_en=en_lbl, own=mult(own))
            x.add("valuation", "anchor", 0.35, 0, ("链上费用不是它的估值锚", "not anchored by chain fees at all"), txt, (f"{zh_s} {mult(own)}", f"{en_s} {mult(own)}"))
        elif key in ("ps", "pf") or (key == "cpf" and not mismatch):
            txt = v.say("val_abs", t=t, lbl=zh_lbl, lbl_en=en_lbl, own=mult(own))
            x.add("valuation", key, 0.4, 0, (f"{zh_s} 约 {mult(own)}", f"priced at about {mult(own)} {en_s}"), txt, (f"{zh_s} {mult(own)}", f"{en_s} {mult(own)}"))
        else:
            continue
        done = True
        break
    if not done and mismatch:
        zl, el, own, peer = mismatch
        txt = v.say("val_mismatch", t=t, lbl=zl, lbl_en=el, own=mult(own), peer=mult(peer))
        x.add("valuation", "anchor", 0.45, 0, ("链上数据不是它的估值锚", "not priced on on-chain data"), txt,
              (f"{zl.split('（')[0]} {mult(own)}", f"{el.split(' (')[0]} {mult(own)}"))
    if s.get("fdv_ps") and s.get("float") is not None and s["float"] < 0.7:
        txt = v.say("fdv_ps", t=t, fps=mult(s["fdv_ps"]))
        x.add("valuation", "fdv_ps", 0.45, -1, ("按完全稀释算，倍数更高", "pricier on a fully diluted basis"), txt,
              (f"FDV/收入 {mult(s['fdv_ps'])}", f"FDV/revenue {mult(s['fdv_ps'])}"))
    leader = s.get("leader")
    if leader and s.get("leader_x") and s["leader_x"] > 1:
        lx = s["leader_x"]
        pos = (pk.get("sector") or {}).get("pos")
        nsec = (pk.get("sector") or {}).get("n")
        if pos and nsec:
            posz = f"；在筛选后的 {nsec} 个同板块代币里，{t} 的市值排第 {pos}"
            pose = f"; {t} ranks #{pos} by cap among {nsec} filtered sector tokens"
        else:
            posz = f"；按筛选后的同行名单，{t} 的市值排第 {pos}" if pos else ""
            pose = f"; {t} ranks #{pos} by cap in the filtered peer list" if pos else ""
        txt = v.say("vs_leader", t=t, ldr=leader["ticker"], lmc=zh_usd(leader["mcap"]), lx=mult(lx), lpct=f"{100 / lx:.0f}" if lx < 50 else f"{100 / lx:.1f}",
                    posz=posz, pose=pose, en=dict(lmc=en_usd(leader["mcap"])))
        x.add("valuation", "vs_leader", 0.3, 0,
              (f"市值约为板块龙头 {leader['ticker']} 的 {100 / lx:.0f}%" if lx < 50 else f"市值不到板块龙头 {leader['ticker']} 的 2%",
               f"worth about {100 / lx:.0f}% of sector leader {leader['ticker']}" if lx < 50 else f"worth under 2% of sector leader {leader['ticker']}"),
              txt, (f"龙头是其 {mult(lx)}", f"leader is {mult(lx)} its size"))


# ------------------------------------------------------------------ findings: narrative

def narrative_findings(x: Ctx, v: Voice) -> list[tuple[str, str]]:
    """Returns the narrative paragraph sentences; also adds one finding for scoring/ordering."""
    pk, s, c = x.pack, x.s, x.pack["cg"]
    t = pk["ticker"]
    cats = c.get("categories") or []
    noise = re.compile(r"Portfolio|Index|Ecosystem|Made in|Launchpool|Launchpad|Airdrop|Alpha|Native|Holdings|Coinbase|GMCI|x402", re.I)
    sectors = [q for q in cats if not noise.search(q)][:4]
    eco = [q for q in cats if q.endswith("Ecosystem")][:3]
    backers = [q.replace(" Portfolio", "") for q in cats if q.endswith("Portfolio")][:5]
    backers = [re.sub(r"\s*\(Prev\.?\s*([^)]*)\)", r" (formerly \1)", q) for q in backers]
    prof = pk.get("profile") or {}
    out: list[tuple[str, str]] = []
    if sectors:
        out.append(v.say("narr_cats", t=t, secs="、".join(CAT_ZH.get(q, q) for q in sectors), secs_en=", ".join(CAT_EN_SHORT.get(q, q) for q in sectors),
                         ecoz=f"，生态标签为{'、'.join(CAT_ZH.get(q, q) for q in eco)}" if eco else "", ecoe=f", ecosystems {', '.join(eco)}" if eco else ""))
    if prof.get("about"):
        out.append(v.say("narr_about", t=t, about=prof["about"]))
    if backers:
        out.append(v.say("narr_backers", t=t, backers="、".join(backers), en=dict(backers=", ".join(backers))))
    temp, btc30 = s.get("sector_temp"), (pk.get("btc") or {}).get("chg_30d")
    hot = cold = False
    if s.get("sector_call") and btc30 is not None:
        hot, cold = s["sector_call"] == "hot", s["sector_call"] == "cold"
        both = s.get("sector_basis") == "both"
    if s.get("sector_call") == "split" and btc30 is not None:
        out.append(v.say("narr_split", t=t, m=pct(temp), w=pct(s["sector_wavg"]), b30=pct(btc30)))
    elif s.get("sector_call") and btc30 is not None:
        med = f"{pct(temp)} / {pct(s['sector_wavg'])}" if both else pct(temp)
        out.append(v.say("narr_hot" if hot else "narr_cold" if cold else "narr_sync", t=t, med=med, b30=pct(btc30),
                         basis="涨跌中位数 / 市值加权（不含本币）" if both else "涨跌中位数",
                         basis_en="median / cap-weighted ex-self change" if both else "median change"))
        x.labels["sector_temp"] = temp
    if c.get("genesis") and not s.get("launch_ath"):
        out.append(v.say("narr_genesis", t=t, genesis=c["genesis"]))
    if not out:
        return out
    first_zh = CAT_ZH.get(sectors[0], sectors[0]) if sectors else "未分类"
    first_en = CAT_EN_SHORT.get(sectors[0], sectors[0]) if sectors else "n/a"
    x.add("narrative", "sector", 0.5 if (hot or cold) else 0.3, +1 if hot else -1 if cold else 0,
          ("所在叙事正热" if hot else "所在叙事偏冷" if cold else f"定位在{first_zh}",
           "riding a hot narrative" if hot else "stuck in a cold narrative" if cold else f"seated in {first_en}"),
          (out[0][0], out[0][1]),
          ("板块跑赢比特币" if hot else "板块跑输比特币" if cold else first_zh, "sector beating BTC" if hot else "sector lagging BTC" if cold else first_en))
    return out


# ------------------------------------------------------------------ news flow

def headline_md(n: dict) -> tuple[str, str]:
    line = f"{n['date']} · {n['outlet']} · [{n['title']}]({n['url']})"
    return line, line


def news_block(x: Ctx, v: Voice) -> dict | None:
    pk = x.pack
    t = pk["ticker"]
    news = pk.get("news")
    hacks = pk.get("hacks") or []
    checked = bool(pk.get("news_checked")) or bool(news)
    if not checked and not hacks:
        return None
    news = news or []
    days = 30
    counts: dict[str, int] = {}
    for n in news:
        for tg in n.get("tags") or []:
            counts[tg] = counts.get(tg, 0) + 1
    top = sorted((k for k in counts if k != "price"), key=lambda k: -counts[k])[:3]
    tagz = ("，其中" + "、".join(f"涉及{NEWS_TAG_ZH[k]} {counts[k]} 条" for k in top)) if top else ""
    tage = (", including " + ", ".join(f"{counts[k]} on {NEWS_TAG_EN[k]}" for k in top)) if top else ""
    paras: list[tuple[str, str]] = []
    bullets: list[tuple[str, str]] = []
    if len(news) >= 2:
        paras.append(v.say("news_lead", t=t, n=len(news), days=days, tagz=tagz, tage=tage))
    elif len(news) == 1:
        paras.append(v.say("news_one", t=t, days=days, tagz=tagz, tage=tage))
    elif checked:
        paras.append(v.say("news_quiet", t=t, days=days))
    bullets = [headline_md(n) for n in news]
    if hacks:
        hk = hacks[0]
        paras.append(v.say("hack_hist", t=t, hname=hk.get("name") or pk["name"], hdate=hk.get("date") or "—", hamt=zh_usd(hk.get("amount")),
                           htech=hk.get("technique") or hk.get("classification") or "未注明",
                           en=dict(hamt=en_usd(hk.get("amount")), htech=hk.get("technique") or hk.get("classification") or "unspecified")))
    neg = counts.get("security", 0) + counts.get("regulation", 0)
    posn = counts.get("product", 0) + counts.get("listing", 0) + counts.get("institutional", 0) + counts.get("funding", 0)
    recent_hack = bool(hacks and (hacks[0].get("date") or "") >= f"{int(pk['day'][:4]) - 2}{pk['day'][4:]}")
    tone = -1 if (neg or recent_hack) else (+1 if posn >= 2 else 0)
    x.labels["news_neg"], x.labels["news_pos"] = neg, posn
    if news:
        hz = f"近 {days} 天 {len(news)} 条公开报道" + (f"，{counts[top[0]]} 条涉及{NEWS_TAG_ZH[top[0]]}" if top else "")
        he = f"{len(news)} public headlines in {days} days" + (f", {counts[top[0]]} on {NEWS_TAG_EN[top[0]]}" if top else "")
    elif hacks and not checked:
        hz, he = "安全记录值得一看", "a security record worth a look"
    else:
        hz, he = f"近 {days} 天没有点名报道", f"no headlines naming it in {days} days"
    x.add("news", "news", 0.45 if (neg or recent_hack) else 0.3, tone,
          (f"消息面：{hz}" if False else hz, he), paras[0] if paras else ("", ""), (hz, he))
    return {"head": (hz, he), "paras": paras, "bullets": bullets, "tone": tone, "counts": counts}


# ------------------------------------------------------------------ KOL angle

def kol_block(x: Ctx, v: Voice):
    pk, s, c = x.pack, x.s, x.pack["cg"]
    soc = pk.get("social") or {}
    t = pk["ticker"]
    fng, votes, trend = soc.get("fng"), c.get("votes_up"), soc.get("trending_pos")
    lunar = soc.get("lunar") or {}
    c30, c7, c1y = c.get("chg_30d"), c.get("chg_7d"), c.get("chg_1y")
    state = s["crowd"]
    x.labels["crowd"] = state
    items: list[tuple[str, str]] = []
    mood: list[tuple[str, str]] = []
    if fng:
        mood.append(v.say("mood_fng", t=t, fng=f"{fng['now']:.0f}", fngl=fng["label"], fnga=f"{fng['avg30']:.0f}"))
    if trend:
        mood.append(v.say("mood_trend_in", t=t, pos=trend))
    elif soc.get("trending_n"):
        mood.append(v.say("mood_trend_out", t=t, n=soc["trending_n"]))
    if votes is not None:
        mood.append(v.say("mood_votes", t=t, votes=f"{votes:.0f}"))
    if c.get("watchlist"):
        mood.append(v.say("mood_watch", t=t, wl=f"{c['watchlist'] / 1e4:.1f}", wle=f"{c['watchlist'] / 1e3:.0f}"))
    if lunar.get("dominance") is not None:
        mood.append(v.say("mood_lunar", t=t, dom=f"{lunar['dominance']:.2f}"))
    if mood:
        items.append(v.say("mood_wrap", items="；".join(a for a, _ in mood), items_en="; ".join(b for _, b in mood)))
    trendz = f"、CoinGecko 热搜第 {trend}" if trend else ""
    trende = f", #{trend} on CoinGecko trending" if trend else ""
    kw = dict(t=t, c30=pct(c30, 0), c7=pct(c7, 0), c1y=pct(c1y, 0), c7abs=apct(c7, 0), c30abs=apct(c30, 0), trendz=trendz, trende=trende)
    items.append(v.say(f"crowd_{state}", **kw))
    dw = {"usage": 1.2, "valuation": 1.15, "token": 1.0, "market": 0.8, "narrative": 0.7, "news": 0.6}
    pos = sorted([f for f in x.f if f.tone > 0], key=lambda f: -f.sal * dw.get(f.dim, 1))
    neg = sorted([f for f in x.f if f.tone < 0], key=lambda f: -f.sal * dw.get(f.dim, 1))
    hotish = state in ("frenzy", "runup", "pullback", "warm")
    coldish = state in ("cold", "capit")
    if hotish:  # the crowd already sees the tape; a contrarian point should come from elsewhere first
        neg = [f for f in neg if f.dim != "market"] + [f for f in neg if f.dim == "market" and f.key not in ("pullback7", "rs_btc")]
    g200 = s.get("ma200_gap")
    if state in ("pullback", "runup") and not neg and g200 is not None and g200 > TH["ext200"]:
        items.append(v.say("contra_stretched", t=t, h="远高于 200 日均线", hp=f"高于 200 日均线 {g200:.0f}%",
                           h_en="stretched far above its 200-day average", hp_en=f"{g200:.0f}% above the 200-day"))
        stance = -1
    elif hotish and neg:
        f = neg[0]
        items.append(v.say("contra_hot_neg", t=t, h=f.head[0], hp=f.proof[0], h_en=f.head[1], hp_en=f.proof[1]))
        stance = -1
    elif coldish and pos:
        f = pos[0]
        items.append(v.say("contra_cold_pos", t=t, h=f.head[0], hp=f.proof[0], h_en=f.head[1], hp_en=f.proof[1]))
        stance = +1
    elif pos and neg:
        a, b = (pos[0], neg[0]) if pos[0].sal >= neg[0].sal else (neg[0], pos[0])
        items.append(v.say("contra_mixed", t=t, a=a.head[0], a_en=a.head[1], h=b.head[0], hp=b.proof[0], h_en=b.head[1], hp_en=b.proof[1]))
        stance = b.tone
    else:
        items.append(v.say("contra_none", t=t))
        stance = 0
    greed = bool(fng and fng["now"] >= 70)
    fear = bool(fng and fng["now"] <= 30)
    if greed and state == "frenzy":
        items.append(v.say("thermo_greed", t=t, fng=f"{fng['now']:.0f}"))
    elif fear and state != "frenzy":
        items.append(v.say("thermo_fear", t=t, fng=f"{fng['now']:.0f}"))
    h = pk.get("hist") or {}
    lz, le = [], []
    if h.get("ma200"):
        lz.append(f"200 日均线 {price_str(h['ma200'])}")
        le.append(f"200-day average {price_str(h['ma200'])}")
    if h.get("ma50"):
        lz.append(f"50 日均线 {price_str(h['ma50'])}")
        le.append(f"50-day {price_str(h['ma50'])}")
    if h.get("hi90") and h.get("lo90"):
        lz.append(f"90 日区间 {price_str(h['lo90'])}–{price_str(h['hi90'])}")
        le.append(f"90-day range {price_str(h['lo90'])}–{price_str(h['hi90'])}")
    if h.get("ma200"):
        above = (s.get("ma200_gap") or 0) > 0
        items.append(v.say("levels_above" if above else "levels_below", t=t, lv="、".join(lz), lv_en=", ".join(le)))
    views = [n for n in (pk.get("news") or []) if "opinion" in (n.get("tags") or [])][:2]
    if views:
        iz = "、".join(f"[{n['title']}]({n['url']})（{n['outlet']}，{n['date']}）" for n in views)
        ie = ", ".join(f"[{n['title']}]({n['url']}) ({n['outlet']}, {n['date']})" for n in views)
        items.append(v.say("views", t=t, items=iz, items_en=ie))
    heads = {
        "frenzy": ("热度很高，反着想", "a hot tape, think the other way") if greed else ("涨幅吸引眼球，先看筹码", "the move draws eyes, check the holders first"),
        "pullback": ("大涨之后的分歧", "disagreement after a big run"),
        "runup": ("高位整理，多空都有话说", "consolidating high, both sides have a case"),
        "warm": ("关注度在回升", "attention coming back"),
        "cold": ("冷门时段，数据没坏", "out of favour, data intact") if pos else ("关注度在流失", "attention draining away"),
        "capit": ("情绪接近投降", "sentiment near capitulation"),
        "jolt": ("短线波动把它推回台前", "a sharp week puts it back on screens"),
        "quiet": v.pick("kh", ("共识与反共识", "consensus vs contrarian"), ("情绪站在哪一边", "which side the mood is on")),
    }
    head = ("上了热搜，分清资金和噪音", "trending, separate money from noise") if trend else heads[state]
    return head, items, stance


# ------------------------------------------------------------------ takes / score / verdict

SHORT_KEYS = {"rs_btc", "pullback7", "spike7", "rs_sector", "vol_shift", "turn_hot", "turn_thin", "turn_rel", "volatility"}
LONG_KEYS = {"trend_up", "trend_down", "trend_mixed", "rs_btc_1y", "ath_launch", "ath_deep", "ath_near"}


def dim_take(dim: str, fs: list[Finding], x: Ctx, v: Voice) -> tuple[str, str, str]:
    """Returns (zh, en, kind) with kind in up/down/flat/mixed; audited against the heading."""
    t = x.pack["ticker"]
    if dim == "usage" and x.s.get("profile") == "market":
        z, e = v.say("take_usage_market", t=t)
        return z, e, "flat"
    tone = sum(f.tone * f.sal for f in fs)
    pos = sorted([f for f in fs if f.tone > 0], key=lambda f: -f.sal)
    neg = sorted([f for f in fs if f.tone < 0], key=lambda f: -f.sal)
    head = fs[0]
    kind = "up" if tone > 0.25 else "down" if tone < -0.25 else "flat"
    split_span = dim == "market" and pos and neg and neg[0].sal >= 0.45 and pos[0].sal >= 0.45 and \
        ((pos[0].key in SHORT_KEYS) != (neg[0].key in SHORT_KEYS))
    if pos and neg and (split_span or abs(tone) <= 0.35 or (head.tone and (head.tone > 0) != (tone > 0))):
        kind = "mixed"
    elif head.tone and kind != "flat" and (head.tone > 0) != (kind == "up"):
        kind = "flat"
    if kind == "mixed":
        hp, hn = pos[0], neg[0]
        slot = f"take_{dim}_mixed"
        if dim == "market" and hp.key in LONG_KEYS and hn.key in SHORT_KEYS:
            slot = "take_market_mixed_rev"
        elif dim == "market" and not (hp.key in SHORT_KEYS and hn.key in LONG_KEYS):
            slot = "take_market_mixed_same"
        if slot in P:
            z, e = v.say(slot, t=t, hp=hp.head[0], hn=hn.head[0], hp_en=hp.head[1], hn_en=hn.head[1])
            return z, e, "mixed"
        kind = "flat"
    z, e = v.say(f"take_{dim}_{kind}", t=t)
    return z, e, kind


def clamp(v: float) -> float:
    return max(1.0, min(10.0, v))


def score(x: Ctx, kol_stance: int):
    pk, s, c = x.pack, x.s, x.pack["cg"]
    h = pk.get("hist") or {}
    rows = []
    m, nz, ne = 5.0, [], []
    if s.get("ma200_gap") is not None:
        g = s["ma200_gap"]
        m += (0.4 if g > TH["ext200"] else 1.0) if g > 0 else (-1.0 if g < -20 else -0.4)
        nz.append(f"200 日均线 {pct(g, 0)}"); ne.append(f"{pct(g, 0)} vs 200d")
    if s.get("rs_btc_30d") is not None:
        m += 0.8 if s["rs_btc_30d"] > 10 else (-0.8 if s["rs_btc_30d"] < -15 else 0)
        rsd = 1 if abs(s['rs_btc_30d']) < 10 else 0
        nz.append(f"30 日相对比特币 {pct(s['rs_btc_30d'], rsd)}"); ne.append(f"{pct(s['rs_btc_30d'], rsd)} vs BTC 30d")
    if (c.get("chg_7d") or 0) <= TH["pull7_finding"]:
        m -= 0.4
        nz.append(f"7 日 {pct(c['chg_7d'], 0)}"); ne.append(f"7d {pct(c['chg_7d'], 0)}")
    tv = s.get("turnover")
    if tv is not None:
        m += 0.5 if 3 <= tv <= 25 else (-1.0 if tv < 1 else -0.5 if tv > 60 else 0)
        nz.append(f"换手 {tv:.1f}%"); ne.append(f"turnover {tv:.1f}%")
    if (c.get("volume") or 0) >= 2e8:
        m += 0.4
    rows.append(("market", clamp(m), "；".join(nz), "; ".join(ne)))
    tk, nz, ne = 5.5, [], []
    if s.get("float") is not None:
        fl = s["float"]
        tk += 1.5 if fl >= 0.9 else 0.5 if fl >= 0.7 else -0.5 if fl >= 0.5 else -1.5
        nz.append(f"流通 {100 * fl:.0f}%"); ne.append(f"float {100 * fl:.0f}%")
    if s.get("infl_1y") is not None:
        i = s["infl_1y"]
        tk += -2 if i > 30 else -1 if i > 12 else -0.4 if i > 6 else 0.5 if i < 3 else 0
        nz.append(f"一年流通 {pct(i, 0)}"); ne.append(f"supply {pct(i, 0)}/yr")
    if c.get("max_infinite"):
        tk -= 0.4
        nz.append("无上限"); ne.append("uncapped")
    if s.get("unlock30") is not None:
        u30, u90 = s["unlock30"], s.get("unlock90") or 0
        tk += -1.2 if u30 >= TH["unlock_heavy30"] else 0.5 if u90 <= TH["unlock_light90"] else -0.3
        nz.append(f"30 天解锁 {u30:.1f}%"); ne.append(f"30d unlock {u30:.1f}%")
    rows.append(("token", clamp(tk), "；".join(nz) or "供给数据有限", "; ".join(ne) or "limited supply data"))
    if s["profile"] in ("protocol", "chain"):
        u, nz, ne = 5.0, [], []
        ch = pk.get("chain") or {}
        for key, lz, le, up, dn in (("fees_mom", "费用环比", "fees MoM", 8, -12), ("tvl_mom", "TVL 30 日", "TVL 30d", 8, -10),
                                    ("chain_fees_mom", "链费环比", "chain fees MoM", 10, -15), ("dex_mom", "DEX 环比", "DEX MoM", 10, -15)):
            val = s.get(key)
            if key == "tvl_mom" and val is None and ch.get("tvl_chg_30d") is not None:
                val, lz, le = ch["tvl_chg_30d"], "链上 TVL 30 日", "chain TVL 30d"
            if val is None:
                continue
            u += 0.9 if val > up else -0.9 if val < dn else 0
            nz.append(f"{lz} {pct(val, 0)}"); ne.append(f"{le} {pct(val, 0)}")
        if s.get("capture") is not None and s.get("fees_material"):
            u += 0.8 if s["capture"] > 40 else -0.6 if s["capture"] < 10 else 0
            nz.append(f"捕获率 {s['capture']:.0f}%"); ne.append(f"capture {s['capture']:.0f}%")
        if (s.get("fees_accel") or 0) > 15:
            u += 0.4
        if ((pk.get("protocol") or {}).get("fees30") or 0) > 1e7 or (ch.get("fees30") or 0) > 1e7:
            u += 0.5
        rows.append(("usage", clamp(u), "；".join(nz) or "有锁仓/费用数据，变化不大", "; ".join(ne) or "TVL/fee data, little change"))
    val, nz, ne, used = 5.0, [], [], False
    material = s.get("fees_material")
    for own, peer, lz, le in ((s.get("ps") if material else None, s.get("peer_ps"), "P/S", "P/S"), (s.get("pf") if material else None, s.get("peer_pf"), "P/F", "P/F"),
                              (s.get("mtvl") or s.get("chain_mtvl"), s.get("peer_mtvl"), "市值/TVL", "mcap/TVL")):
        if own is not None and peer is not None and not used and 0.2 <= own / peer <= 5:
            r = own / peer
            val += 1.6 if r < 0.6 else 0.7 if r < TH["val_cheap"] else -1.8 if r > 2.5 else -1.0 if r > TH["val_rich"] else 0
            nz.append(f"{lz} {mult(own)}，同行 {mult(peer)}"); ne.append(f"{le} {mult(own)} vs peers {mult(peer)}")
            used = True
    if not used and s.get("pf") and not material:
        val -= 1.0
        nz.append(f"费用微小，P/F {mult(s['pf'])}"); ne.append(f"tiny fees, P/F {mult(s['pf'])}")
    elif not used:
        ath = c.get("ath_chg")
        if s.get("launch_ath") and s.get("from_hi90") is not None:
            val += -0.4 if s["from_hi90"] > -10 else 0
            nz.append(f"距 90 日高点 {pct(s['from_hi90'], 0)}，无同口径同行倍数"); ne.append(f"{pct(s['from_hi90'], 0)} from 90d high, no like-for-like peer multiple")
        elif ath is not None:
            val += 0.4 if ath < -85 else -0.6 if ath > -10 else 0
            nz.append(f"距 ATH {pct(ath, 0)}，无同口径同行倍数"); ne.append(f"{pct(ath, 0)} from ATH, no like-for-like peer multiple")
    if s.get("float") is not None and s["float"] < 0.5:
        val -= 0.6
        nz.append("低流通抬高真实估值"); ne.append("low float inflates the real valuation")
    rows.append(("valuation", clamp(val), "；".join(nz), "; ".join(ne)))
    se, nz, ne = 5.0 + 0.6 * kol_stance, [], []
    soc = pk.get("social") or {}
    fng = soc.get("fng")
    if fng:
        se += 0.5 if fng["now"] <= 25 else -0.5 if fng["now"] >= 75 else 0
        nz.append(f"恐贪指数 {fng['now']:.0f}"); ne.append(f"F&G {fng['now']:.0f}")
    if soc.get("trending_pos"):
        se += 0.4
        nz.append(f"热搜第 {soc['trending_pos']}"); ne.append(f"trending #{soc['trending_pos']}")
    if c.get("votes_up") is not None:
        se += 0.3 if c["votes_up"] >= 80 else -0.3 if c["votes_up"] < 55 else 0
        nz.append(f"投票看涨 {c['votes_up']:.0f}%"); ne.append(f"votes {c['votes_up']:.0f}% bullish")
    nn, npos = x.labels.get("news_neg", 0), x.labels.get("news_pos", 0)
    if nn or npos:
        se += -0.4 if nn else 0.3
        nz.append(f"负面报道 {nn} 条" if nn else f"正面事件 {npos} 条"); ne.append(f"{nn} negative headlines" if nn else f"{npos} constructive headlines")
    nz.append("数据与情绪背离" if kol_stance else "情绪与数据同向"); ne.append("data diverges from mood" if kol_stance else "mood and data agree")
    rows.append(("kol", clamp(se), "；".join(nz), "; ".join(ne)))
    r, nz, ne = 6.0, [], []
    v30 = h.get("vol30")
    if v30 is not None:
        r += -1.5 if v30 > 120 else -0.8 if v30 > TH["vola_high"] - 10 else 0.5 if v30 < 50 else 0
        nz.append(f"年化波动 {v30:.0f}%"); ne.append(f"vol {v30:.0f}%")
    if h.get("mdd90") is not None and h["mdd90"] < -50:
        r -= 1.0
        nz.append(f"90 日回撤 {pct(h['mdd90'], 0)}"); ne.append(f"90d drawdown {pct(h['mdd90'], 0)}")
    if (c.get("volume") or 0) < 5e6:
        r -= 1.0
        nz.append(f"日成交仅 {en_usd(c.get('volume'))}"); ne.append(f"only {en_usd(c.get('volume'))} daily volume")
    if s["is_meme"]:
        r -= 0.5
        nz.append("无协议现金流"); ne.append("no protocol cash flow")
    hk = (pk.get("hacks") or [None])[0]
    if hk and (hk.get("date") or "") >= f"{int(pk['day'][:4]) - 2}{pk['day'][4:]}":
        r -= 1.0
        nz.append(f"{hk['date'][:4]} 年遭攻击"); ne.append(f"exploited in {hk['date'][:4]}")
    rows.append(("risk", clamp(r), "；".join(nz) or "波动与流动性中性", "; ".join(ne) or "neutral vol/liquidity"))
    weights = {
        "protocol": {"usage": .25, "valuation": .20, "token": .15, "market": .15, "kol": .10, "risk": .15},
        "chain": {"usage": .25, "valuation": .15, "token": .15, "market": .20, "kol": .10, "risk": .15},
        "meme": {"valuation": .10, "token": .15, "market": .30, "kol": .25, "risk": .20},
        "market": {"valuation": .15, "token": .20, "market": .30, "kol": .15, "risk": .20},
    }[s["profile"]]
    label = {"market": ("市场结构与趋势", "Market structure & trend"), "token": ("代币经济与供给", "Tokenomics & supply"),
             "usage": ("链上使用与现金流", "On-chain usage & cash flow"), "valuation": ("相对估值", "Relative valuation"),
             "kol": ("情绪、消息与 KOL 面", "Sentiment, news & KOL"), "risk": ("风险（越高越稳）", "Risk (higher = safer)")}
    total_w = sum(weights.get(k, 0) for k, *_ in rows)
    raw, out = 0.0, []
    for key, val_, nzh, nen in rows:
        w = weights.get(key, 0) / total_w if total_w else 0
        if w <= 0:
            continue
        raw += w * val_
        out.append((label[key][0], label[key][1], w, val_, nzh, nen))
    return round(max(3.0, min(8.2, raw)) + 1e-9, 1), out


def verdict(score_: float) -> tuple[str, str]:
    if score_ >= 6.5:
        return "谨慎跟踪", "cautious watch"
    if score_ >= 5.0:
        return "观望", "hold / wait"
    return "回避", "avoid"


# ------------------------------------------------------------------ catalysts / risks

def _recent_hack(pk: dict) -> dict | None:
    hk = (pk.get("hacks") or [None])[0]
    if hk and (hk.get("date") or "") >= f"{int(pk['day'][:4]) - 3}{pk['day'][4:]}":
        return hk
    return None


def catalysts_risks(x: Ctx, v: Voice):
    pk, s, c = x.pack, x.s, x.pack["cg"]
    h = pk.get("hist") or {}
    soc = pk.get("social") or {}
    ch = pk.get("chain") or {}
    t = pk["ticker"]
    cname = ch.get("name") or pk["name"]
    news = pk.get("news") or []
    u = pk.get("unlocks") or {}
    cat, risk = [], []
    if (s.get("fees_accel") or 0) > 15 and s.get("fees_material"):
        cat.append(v.say("cat_fee_accel", t=t, acc=pct(s["fees_accel"], 0)))
    if (s.get("tvl_mom") or 0) > 10:
        cat.append(v.say("cat_tvl_in", t=t, tm=pct(s["tvl_mom"], 0)))
    if (s.get("dex_mom") or 0) > 15:
        cat.append(v.say("cat_dex_up", cname=cname, dm=pct(s["dex_mom"], 0)))
    if (s.get("ma200_gap") or 0) < 0 and (s.get("ma50_gap") or 0) > 0 and h.get("ma200"):
        cat.append(v.say("cat_reclaim", t=t, ma200=price_str(h["ma200"])))
    if soc.get("trending_pos"):
        cat.append(v.say("cat_trending", t=t, pos=soc["trending_pos"]))
    if soc.get("fng") and soc["fng"]["now"] <= 30:
        cat.append(v.say("cat_fear", t=t, fng=f"{soc['fng']['now']:.0f}"))
    if (s.get("rs_sector_30") or 0) > 10:
        cat.append(v.say("cat_sector", t=t, rss=pct(s["rs_sector_30"], 0)))
    if (s.get("chain_fees_mom") or 0) > 15 and (s.get("chain_fees_ann") or 0) >= 0.001 * c["mcap"]:
        cat.append(v.say("cat_chain_fees", cname=cname, fm=pct(s["chain_fees_mom"], 0)))
    if u.get("next90_pct_circ") is not None and u["next90_pct_circ"] <= TH["unlock_light90"]:
        p90 = u["next90_pct_circ"]
        cat.append(v.say("cat_unlock_quiet", t=t, pct90=f"{p90:.2f}" if p90 < 0.1 else f"{p90:.1f}"))
    good = next((n for n in news if set(n.get("tags") or []) & {"product", "listing", "institutional", "funding"}
                 and not set(n.get("tags") or []) & {"security", "regulation"}), None)
    if good:
        cat.append(v.say("cat_headline", t=t, date=good["date"], outlet=good["outlet"], title=good["title"]))
    bad = next((n for n in news if set(n.get("tags") or []) & {"security", "regulation"}), None)
    if bad:
        tg = [k for k in ("security", "regulation") if k in bad["tags"]]
        risk.append(v.say("risk_headline", t=t, date=bad["date"], outlet=bad["outlet"], title=bad["title"],
                          tagz="、".join(NEWS_TAG_ZH[k] for k in tg), tage=", ".join(NEWS_TAG_EN[k] for k in tg)))
    hk = _recent_hack(pk)
    if hk:
        risk.append(v.say("risk_hack", t=t, hname=hk.get("name") or pk["name"], hdate=hk.get("date"), hamt=zh_usd(hk.get("amount")),
                          en=dict(hamt=en_usd(hk.get("amount")))))
    if (u.get("next30_pct_circ") or 0) >= TH["unlock_heavy30"]:
        cl = u.get("next_cliff") or {}
        cz = f"，最近一笔在 {cl['date']}" if cl.get("date") else ""
        ce = f"; next cliff {cl['date']}" if cl.get("date") else ""
        risk.append(v.say("risk_unlock_sched", t=t, pct30=f"{u['next30_pct_circ']:.1f}", usd30=zh_usd(u.get("next30_usd")), cliffz=cz, cliffe=ce,
                          en=dict(usd30=en_usd(u.get("next30_usd")))))
    elif s.get("float") is not None and s["float"] < 0.7 and s.get("pow"):
        risk.append(v.say("risk_issuance", t=t, ovh=zh_usd(s["overhang"]), en=dict(ovh=en_usd(s["overhang"]))))
    elif s.get("float") is not None and s["float"] < 0.7:
        risk.append(v.say("risk_unlock", t=t, ovh=zh_usd(s["overhang"]), ovx=mult(s["overhang"] / c["mcap"]), en=dict(ovh=en_usd(s["overhang"]))))
    if (s.get("infl_1y") or 0) > 8:
        risk.append(v.say("risk_infl", t=t, infl=f"{s['infl_1y']:.0f}"))
    if (s.get("fees_mom") or 0) < -12 and s.get("fees_material"):
        risk.append(v.say("risk_fees_dn", t=t, fm=pct(s["fees_mom"], 0)))
    if (s.get("tvl_mom") or 0) < -10:
        risk.append(v.say("risk_tvl_out", t=t, tm=pct(s["tvl_mom"], 0)))
    if (ch.get("tvl_chg_30d") or 0) < -10 and (s.get("chain_mtvl") or 0) <= 300:
        risk.append(v.say("risk_chain_bleed", cname=cname, tm=pct(ch["tvl_chg_30d"], 0)))
    if (s.get("ma200_gap") or 0) > TH["ext200"]:
        risk.append(v.say("risk_extended", t=t, g200=f"{s['ma200_gap']:.0f}"))
    if (h.get("vol30") or 0) >= TH["vola_high"]:
        risk.append(v.say("risk_vola", t=t, v30=f"{h['vol30']:.0f}", d=f"{h['vol30'] / math.sqrt(365):.1f}"))
    if (s.get("turnover") or 0) >= TH["turn_hot"]:
        risk.append(v.say("risk_froth", t=t, tv=f"{s['turnover']:.0f}"))
    if (c.get("volume") or 0) < 5e6:
        risk.append(v.say("risk_liq", t=t, vol=zh_usd(c.get("volume")), en=dict(vol=en_usd(c.get("volume")))))
    if s["is_meme"]:
        risk.append(v.say("risk_meme", t=t))
    if s.get("capture") is not None and s["capture"] < 10 and s.get("fees_material"):
        risk.append(v.say("risk_capture", t=t, cap=f"{s['capture']:.0f}"))
    if s["profile"] == "market" and not s["is_meme"] and (s.get("chain_fees_ann") or s.get("fees_ann")):
        risk.append(v.say("risk_anchor", t=t))
    elif s["profile"] == "market" and not s["is_meme"]:
        risk.append(v.say("risk_datagap", t=t))
    risk = risk[:5]
    risk.append(v.say("risk_macro", t=t))
    fz, fe = [], []
    if h.get("ma200"):
        above = (s.get("ma200_gap") or 0) > 0
        fz.append(f"{t} {'跌破' if above else '收复'} 200 日均线（{price_str(h['ma200'])}）")
        fe.append(f"{t} {'losing' if above else 'reclaiming'} the 200-day ({price_str(h['ma200'])})")
    if s.get("fees_mom") is not None and s.get("fees_material"):
        fz.append(f"30 日费用环比从 {pct(s['fees_mom'], 0)} 转向")
        fe.append(f"30-day fee momentum flipping from {pct(s['fees_mom'], 0)}")
    cl = (u.get("next_cliff") or {})
    if cl.get("date"):
        fz.append(f"{cl['date']} 的解锁落地后的承接")
        fe.append(f"how the {cl['date']} unlock is absorbed")
    elif s.get("float") is not None and s["float"] < 0.7 and not s.get("pow"):
        fz.append("解锁节奏或回购政策变化"); fe.append("a change in unlock pace or buyback policy")
    if ch.get("tvl") and (s.get("chain_mtvl") or 0) <= 300:
        fz.append(f"{cname} 链上锁仓（现 {zh_usd(ch['tvl'])}）趋势反转"); fe.append(f"{cname} TVL (now {en_usd(ch['tvl'])}) reversing")
    if s.get("rs_btc_30d") is not None and abs(s["rs_btc_30d"]) >= TH["rs30"]:
        fz.append(f"相对比特币的 30 日强弱（现 {pct(s['rs_btc_30d'], 0)}）翻转"); fe.append(f"30-day strength vs Bitcoin (now {pct(s['rs_btc_30d'], 0)}) flipping")
    if bad or good:
        n = bad or good
        fz.append(f"{n['outlet']} 报道事件的后续进展"); fe.append(f"follow-through on the {n['outlet']} story")
    flip = v.say("flip", t=t, items="、".join(fz[:4]), items_en=", ".join(fe[:4]))
    return cat[:4], risk, flip


# ------------------------------------------------------------------ compose

LEAD_SKIP = {"vs_leader", "ath_launch", "sector", "news", "anchor"}


def pangu(text: str) -> str:
    text = re.sub(r"([\u4e00-\u9fff])([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])([\u4e00-\u9fff])", r"\1 \2", text)
    return re.sub(r"([\u4e00-\u9fff])(\d)(?![\d.]*[年月日号])", r"\1 \2", text)


def safe_news(items) -> list[dict]:
    """Headlines go into markdown links verbatim; neutralise characters that would break the link."""
    out = []
    for n in items or []:
        if not (n.get("title") and n.get("url") and n.get("outlet") and n.get("date")):
            continue
        title = re.sub(r"\s+", " ", str(n["title"])).replace("[", "(").replace("]", ")").replace("*", "").replace("|", "/").strip()
        url = str(n["url"]).replace("(", "%28").replace(")", "%29").replace(" ", "%20")
        out.append({**n, "title": title, "url": url, "tags": list(n.get("tags") or [])})
    return out


def compose_note(pack: dict, avoid: list | None = None) -> dict:
    pack = {**pack, "news": safe_news(pack.get("news"))}
    u, i90 = pack.get("unlocks") or {}, (pack.get("hist") or {}).get("circ_chg_90d")
    if u and (u.get("next90_pct_circ") or 0) <= TH["unlock_light90"] and i90 is not None and i90 > 1.5:
        pack["unlocks"] = None  # schedule says "nothing unlocks" while float grew >1.5% in 90 days: not trustworthy
    x = Ctx(pack=pack)
    x.s = signals(pack)
    v = Voice(pack["ticker"] + pack.get("day", ""), avoid)
    market_findings(x, v)
    token_findings(x, v)
    usage_findings(x, v)
    valuation_findings(x, v)
    narr = narrative_findings(x, v)
    news = news_block(x, v)
    kol_head, kol_items, kol_stance = kol_block(x, v)
    total, dims = score(x, kol_stance)
    v_zh, v_en = verdict(total)
    c, t, s, day, name = pack["cg"], pack["ticker"], x.s, pack["day"], pack["name"]
    x.labels["score"] = total

    dim_w = {"usage": 1.2, "valuation": 1.15, "token": 1.0, "market": 0.8}

    def w(f):
        return f.sal * dim_w.get(f.dim, 1)

    ranked = sorted([f for f in x.f if f.dim not in ("narrative", "news") and f.key not in LEAD_SKIP], key=lambda f: -w(f))
    pos = [f for f in ranked if f.tone > 0]
    neg = [f for f in ranked if f.tone < 0]
    top = ranked[0] if ranked else None

    def paren(f, i):
        l, r = ("（", "）") if i == 0 else (" (", ")")
        return "" if (not f.proof[i] or f.proof[i] in f.head[i]) else f"{l}{f.proof[i]}{r}"

    lead: list[tuple[str, str]] = []
    used: set[str] = set()
    if pos and neg and pos[0].sal >= 0.45 and neg[0].sal >= 0.45:
        a, b = (pos[0], neg[0]) if w(pos[0]) >= w(neg[0]) else (neg[0], pos[0])
        j = v.pick("tj", ("，但", ", but "), ("；不过", "; yet "), ("，可是", ", while "))
        title_zh, title_en = f"{t} 研究简报：{a.head[0]}{j[0]}{b.head[0]}", f"{t} research note: {t} is {a.head[1]}{j[1].replace('; ', ', ')}{b.head[1]}"
        lead.append(v.say("lead_pair", t=t, name=name, a=a.head[0], ap=paren(a, 0), b=b.head[0], bp=paren(b, 0),
                          a_en=a.head[1], ap_en=paren(a, 1), b_en=b.head[1], bp_en=paren(b, 1)))
        used = {a.key, b.key}
    elif top:
        title_zh, title_en = f"{t} 研究简报：{top.head[0]}", f"{t} research note: {t} is {top.head[1]}"
        lead.append(v.say("lead_one", t=t, name=name, h=top.head[0], hp=paren(top, 0), h_en=top.head[1], hp_en=paren(top, 1)))
        used = {top.key}
    else:
        title_zh, title_en = f"{t} 研究简报", f"{t} research note"
    LBL = {"valuation": ("估值上", "On valuation", "on valuation"), "usage": ("链上看", "On-chain", "on-chain"),
           "token": ("供给端", "On supply", "on supply"), "market": ("盘面上", "On the tape", "on the tape")}
    extra = []
    for dim in v.pick("leadorder", ("valuation", "usage", "token", "market"), ("usage", "valuation", "market", "token"), ("token", "usage", "valuation", "market")):
        cand = [f for f in ranked if f.dim == dim and f.key not in used]
        if cand:
            extra.append(cand[0])
            used.add(cand[0].key)
        if len(extra) >= 2:
            break
    if len(extra) == 2:
        f1, f2 = extra
        lead.append(v.say("lead_extra2", t=t, l1=LBL[f1.dim][0], l2=LBL[f2.dim][0], h1=f1.head[0], h2=f2.head[0], p1=paren(f1, 0), p2=paren(f2, 0),
                          l1_en=f"{LBL[f1.dim][1]}, {t} is", l2_en=f"{LBL[f2.dim][1]}, it is", l1_lc=f"{LBL[f1.dim][2]} {t} is",
                          l2_lc=f"{LBL[f2.dim][2]} it is", h1_en=f1.head[1], h2_en=f2.head[1], p1_en=paren(f1, 1), p2_en=paren(f2, 1)))
    elif extra:
        f1 = extra[0]
        lead.append(v.say("lead_extra1", t=t, l1=LBL[f1.dim][0], h1=f1.head[0], p1=paren(f1, 0), l1_en=f"{LBL[f1.dim][1]}, {t} is", h1_en=f1.head[1], p1_en=paren(f1, 1)))
    st_slot = "stance_hi" if total >= 6.5 else "stance_mid" if total >= 5.0 else "stance_lo"
    lead.append(v.say(st_slot, t=t, sc=f"{total:.1f}", vz=v_zh, ve=v_en))

    # ---------------- snapshot table
    h, p, ch, soc = pack.get("hist") or {}, pack.get("protocol") or {}, pack.get("chain") or {}, pack.get("social") or {}
    u = pack.get("unlocks") or {}
    rows: list[tuple[str, str, str, str, str]] = []

    def row(zh, en, vz, src, ve=None):
        if vz and not vz.startswith("—"):
            rows.append((zh, en, vz, ve if ve is not None else vz, src))

    row("价格", "Price", price_str(c["price"]), "CoinGecko")
    row("流通市值 / FDV", "Mcap / FDV", f"{en_usd(c['mcap'])} / {en_usd(c.get('fdv'))}" if c.get("fdv") else en_usd(c["mcap"]), "CoinGecko")
    if c.get("rank"):
        row("市值排名", "Rank", f"#{c['rank']}", "CoinGecko")
    if s.get("turnover") is not None:
        row("24h 成交 / 换手", "24h volume / turnover", f"{en_usd(c['volume'])} / {s['turnover']:.1f}%", "CoinGecko")
    row("7 日 / 30 日 / 1 年", "7d / 30d / 1y", f"{pct(c.get('chg_7d'))} / {pct(c.get('chg_30d'))} / {pct(c.get('chg_1y'))}", "CoinGecko")
    if s.get("rs_btc_30d") is not None:
        row("30 日相对比特币", "30d vs BTC", pct(s["rs_btc_30d"]), "计算 / calc")
    if c.get("ath_chg") is not None:
        ad = 1 if abs(c["ath_chg"]) > 99.4 else 0
        if s.get("launch_ath"):
            row("距历史高点", "From ATH", f"{pct(c['ath_chg'], ad)}（{price_str(c.get('ath'))}，{c.get('ath_date')}，上线初期报价）", "CoinGecko",
                f"{pct(c['ath_chg'], ad)} ({price_str(c.get('ath'))}, {c.get('ath_date')}, launch print)")
            if h.get("hi90"):
                row("距 90 日高点", "From 90-day high", f"{pct(s.get('from_hi90'), 0)}（{price_str(h['hi90'])}）", "CoinGecko 365d",
                    f"{pct(s.get('from_hi90'), 0)} ({price_str(h['hi90'])})")
        else:
            row("距历史高点", "From ATH", f"{pct(c['ath_chg'], ad)}（{price_str(c.get('ath'))}，{c.get('ath_date')}）", "CoinGecko",
                f"{pct(c['ath_chg'], ad)} ({price_str(c.get('ath'))}, {c.get('ath_date')})")
    if s.get("ma200_gap") is not None:
        row("相对 200 日均线", "vs 200-day average", pct(s["ma200_gap"], 0), "CoinGecko 365d")
    if h.get("vol30") is not None:
        row("30 日年化波动 / 90 日最大回撤", "30d vol / 90d max drawdown", f"{h['vol30']:.0f}% / {pct(h.get('mdd90'), 0)}", "CoinGecko 365d")
    mx = qty(c.get("max_supply")) if c.get("max_supply") else ("∞" if c.get("max_infinite") else "—")
    row("流通 / 总量 / 上限", "Circ / total / max", f"{qty(c.get('circ'))} / {qty(c.get('total'))} / {mx}", "CoinGecko")
    if s.get("infl_1y") is not None:
        row("一年流通量变化", "1y circulating change", pct(s["infl_1y"]), "CoinGecko 365d")
    if u.get("next30_pct_circ") is not None:
        row("未来 30 / 90 天解锁（占流通）", "Unlocks next 30 / 90d (of float)", f"{u['next30_pct_circ']:.2f}% / {(u.get('next90_pct_circ') or 0):.2f}%", "DefiLlama")
    if p.get("tvl"):
        row("协议 TVL", "Protocol TVL", en_usd(p["tvl"]) + (f"（30 日 {pct(s.get('tvl_mom'), 0)}）" if s.get("tvl_mom") is not None else ""), "DefiLlama",
            en_usd(p["tvl"]) + (f" (30d {pct(s.get('tvl_mom'), 0)})" if s.get("tvl_mom") is not None else ""))
    if p.get("fees30"):
        row("30 日费用 / 收入", "30d fees / revenue", f"{en_usd(p['fees30'])} / {en_usd(p.get('rev30'))}", "DefiLlama")
    if s.get("pf") is not None:
        row("P/F · P/S（年化）", "P/F · P/S (annualised)", f"{mult(s['pf'])} · {mult(s.get('ps'))}", "计算 / calc")
    if ch.get("tvl"):
        row("链上 TVL", "Chain TVL", en_usd(ch["tvl"]) + (f"（30 日 {pct(ch.get('tvl_chg_30d'), 0)}）" if ch.get("tvl_chg_30d") is not None else ""), "DefiLlama",
            en_usd(ch["tvl"]) + (f" (30d {pct(ch.get('tvl_chg_30d'), 0)})" if ch.get("tvl_chg_30d") is not None else ""))
    if ch.get("stables"):
        row("链上稳定币", "Stablecoins on chain", en_usd(ch["stables"]), "DefiLlama")
    if ch.get("dex30"):
        row("链上 DEX 30 日成交", "Chain DEX 30d volume", en_usd(ch["dex30"]), "DefiLlama")
    if ch.get("fees30"):
        row("链级 30 日费用", "Chain 30d fees", en_usd(ch["fees30"]), "DefiLlama")
    if news is not None:
        row("近 30 天点名报道", "Headlines naming it, 30d", f"{len(pack.get('news') or [])} 条", "RSS / Google News", f"{len(pack.get('news') or [])}")
    if soc.get("fng"):
        row("恐惧贪婪指数", "Fear & Greed", f"{soc['fng']['now']:.0f} ({soc['fng']['label']})", "alternative.me")
    if c.get("votes_up") is not None:
        row("社区看涨投票", "Community bullish votes", f"{c['votes_up']:.0f}%", "CoinGecko")
    tbl_zh = ["| 指标 | 数值 | 来源 |", "| --- | --- | --- |"] + [f"| {a} | {vz} | {src} |" for a, _, vz, _, src in rows]
    tbl_en = ["| Metric | Value | Source |", "| --- | --- | --- |"] + [f"| {b} | {ve} | {src} |" for _, b, _, ve, src in rows]

    # ---------------- sections
    by_dim: dict[str, list[Finding]] = {}
    for f in x.f:
        if f.dim in ("narrative", "news"):
            continue
        by_dim.setdefault(f.dim, []).append(f)
    order = sorted(by_dim, key=lambda d: -max(w(f) for f in by_dim[d]))
    if narr:
        order.insert(min(len(order), v.pick("narrpos", 1, 2, 99)), "narrative")
    if news is not None:
        hot_news = news["tone"] < 0 or len(pack.get("news") or []) >= 3
        order.insert(min(len(order), 1 if hot_news else v.pick("newspos", 2, 3, 99)), "news")
    kol_at = min(len(order), v.pick("kolpos", 2, 3, 4))
    tp = v.pick("tp", ("我们的判断：", "Our read: "), ("落到仓位上：", "For positioning: "), ("机构视角：", "Desk view: "))

    blocks: list[tuple] = []
    take = v.pick("take", *TAKE_H)
    blocks.append(("h2", take[0], take[1], "take"))
    blocks.append(("p", f"发布日期：{zh_date(day)}（澳洲珀斯时间）｜数据快照：{pack['as_of']}",
                   f"Published {en_date(day)} (Perth time) | data as of {pack['as_of']}"))
    for a, b in lead:
        blocks.append(("p", a, b))
    blocks.append(("h2", f"数据快照（{day}）", f"Snapshot ({day})", "snap"))
    blocks.append(("table", tbl_zh, tbl_en))
    blocks.append(("p", f"快照时间 {pack['as_of']}。表中只列当场取到的数据，取不到的指标不列。",
                   f"Snapshot taken {pack['as_of']}. Only data actually fetched is listed; missing metrics are left out."))
    sections: list[dict] = []

    def add_kol():
        blocks.append(("h2", f"KOL 视角：{kol_head[0]}", f"KOL angle: {kol_head[1]}", None))
        if v.pick("kolform", True, False):
            blocks.append(("ul", [a for a, _ in kol_items], [b for _, b in kol_items]))
        else:
            for a, b in kol_items:
                blocks.append(("p", a, b))

    for i, dim in enumerate(order):
        if i == kol_at:
            add_kol()
        lbl = DIM_LABEL[dim]
        if dim == "narrative":
            nf = next(f for f in x.f if f.dim == "narrative")
            blocks.append(("h2", f"{lbl[0]}：{nf.head[0]}", f"{lbl[1]}: {nf.head[1]}", None))
            blocks.append(("p", "".join(a for a, _ in narr), " ".join(b for _, b in narr)))
            tz, te, kind = dim_take("narrative", [nf], x, v)
            blocks.append(("p", f"{tp[0]}{tz}", f"{tp[1]}{te}"))
            sections.append({"dim": dim, "head_tone": nf.tone, "take": kind})
            continue
        if dim == "news":
            nf = next(f for f in x.f if f.dim == "news")
            blocks.append(("h2", f"{lbl[0]}：{news['head'][0]}", f"{lbl[1]}: {news['head'][1]}", None))
            for a, b in news["paras"][:1]:
                blocks.append(("p", a, b))
            if news["bullets"]:
                blocks.append(("ul", [a for a, _ in news["bullets"]], [b for _, b in news["bullets"]]))
            for a, b in news["paras"][1:]:
                blocks.append(("p", a, b))
            tz, te, kind = dim_take("news", [nf], x, v)
            blocks.append(("p", f"{tp[0]}{tz}", f"{tp[1]}{te}"))
            sections.append({"dim": dim, "head_tone": nf.tone, "take": kind})
            continue
        fs = sorted(by_dim[dim], key=lambda f: -f.sal)
        blocks.append(("h2", f"{lbl[0]}：{fs[0].head[0]}", f"{lbl[1]}: {fs[0].head[1]}", None))
        body = fs[:4] if dim == "usage" else fs[:3]
        body += [f for f in fs if f.key in used and f not in body]
        if len(body) >= 3 and v.pick(dim + "split", True, False):
            blocks.append(("p", body[0].text[0] + body[1].text[0], body[0].text[1] + " " + body[1].text[1]))
            for f in body[2:]:
                blocks.append(("p", f.text[0], f.text[1]))
        else:
            for f in body:
                blocks.append(("p", f.text[0], f.text[1]))
        if dim == "valuation" and len(pack.get("peers") or []) >= 2:
            peers = pack["peers"]
            has_pf = any(q.get("pf") for q in peers) and (s.get("pf") or s.get("chain_pf"))
            has_mtvl = any(q.get("mtvl") for q in peers) and (s.get("mtvl") or s.get("chain_mtvl"))
            hz = ["代币", "市值", "30 日", "换手"] + (["P/F"] if has_pf else []) + (["市值/TVL"] if has_mtvl else [])
            he = ["Token", "Mcap", "30d", "Turnover"] + (["P/F"] if has_pf else []) + (["Mcap/TVL"] if has_mtvl else [])
            lz = ["| " + " | ".join(hz) + " |", "|" + " --- |" * len(hz)]
            le = ["| " + " | ".join(he) + " |", "|" + " --- |" * len(he)]
            me = {"ticker": f"**{t}**", "mcap": c["mcap"], "chg_30d": c.get("chg_30d"), "turnover": s.get("turnover"),
                  "pf": s.get("pf") or s.get("chain_pf"), "mtvl": s.get("mtvl") or s.get("chain_mtvl")}
            for q in sorted([me] + peers, key=lambda q: -(q.get("mcap") or 0)):
                cells = [q["ticker"], en_usd(q.get("mcap")), pct(q.get("chg_30d")), f"{q['turnover']:.1f}%" if q.get("turnover") is not None else "—"]
                if has_pf:
                    cells.append(mult(q.get("pf")))
                if has_mtvl:
                    cells.append(mult(q.get("mtvl")))
                lz.append("| " + " | ".join(cells) + " |")
                le.append("| " + " | ".join(cells) + " |")
            blocks.append(("table", lz, le))
            sec = pack.get("sector") or {}
            catn = sec.get("cat_name")
            if not catn:
                pass
            elif sec.get("dropped"):
                blocks.append(("p",) + v.say("peer_note", t=t, cat=catn, k=sec["dropped"]))
            else:
                blocks.append(("p",) + v.say("peer_note_clean", t=t, cat=catn))
        tz, te, kind = dim_take(dim, fs, x, v)
        blocks.append(("p", f"{tp[0]}{tz}", f"{tp[1]}{te}"))
        sections.append({"dim": dim, "head_tone": fs[0].tone, "take": kind, "head_key": fs[0].key})
    if kol_at >= len(order):
        add_kol()
    x.labels["sections"] = sections

    cats_, risks_, flip = catalysts_risks(x, v)
    blocks.append(("h2", "催化与风险", "Catalysts and risks", "risk"))
    if cats_:
        blocks.append(("h3", "可能的催化", "Possible catalysts", None))
        blocks.append(("ul", [a for a, _ in cats_], [b for _, b in cats_]))
    blocks.append(("h3", "主要风险", "Main risks", None))
    blocks.append(("ul", [a for a, _ in risks_], [b for _, b in risks_]))
    blocks.append(("p", flip[0], flip[1]))

    sz = ["| 维度 | 权重 | 得分 | 依据 |", "| --- | ---: | ---: | --- |"]
    se_ = ["| Factor | Weight | Score | Basis |", "| --- | ---: | ---: | --- |"]
    for zn, en, wt, val_, nzh, nen in dims:
        sz.append(f"| {zn} | {wt:.0%} | {val_:.1f} | {nzh or '—'} |")
        se_.append(f"| {en} | {wt:.0%} | {val_:.1f} | {nen or '—'} |")
    sz.append(f"| **合计** | **100%** | **{total:.1f}** | **{v_zh}** |")
    se_.append(f"| **Total** | **100%** | **{total:.1f}** | **{v_en}** |")
    blocks.append(("h2", f"买入评分 {total:.1f} / 10", f"Buy score {total:.1f} / 10", "score"))
    blocks.append(("table", sz, se_))
    prof = {"protocol": ("是有可核费用或锁仓的协议，链上使用与估值权重最高", "a protocol with checkable fees or TVL, so usage and valuation weigh most"),
            "chain": ("是公链或二层网络，链上生态与市场结构权重最高", "an L1/L2 network, so ecosystem usage and market structure weigh most"),
            "meme": ("是迷因币，没有协议现金流，市场结构与情绪权重最高", "a meme coin with no protocol cash flow, so market structure and sentiment weigh most"),
            "market": ("缺少可核的链上现金流数据，评分主要依据市场结构、供给与情绪", "lacking checkable on-chain cash-flow data, so the score rests on market structure, supply and sentiment")}[s["profile"]]
    blocks.append(("p", f"评分标准：各维度 1–10 分，按权重加权；6.5 分及以上为谨慎跟踪，5.0–6.4 为观望，5.0 以下为回避。本篇标的{prof[0]}。",
                   f"Scale: each factor 1–10, weighted; 6.5+ cautious watch, 5.0–6.4 hold / wait, below 5.0 avoid. This coin is {prof[1]}."))

    srcs_z = list(dict.fromkeys(pack.get("sources") or ["CoinGecko"]))
    srcs_e = list(srcs_z)
    prof_links = pack.get("profile") or {}
    if prof_links.get("homepage"):
        srcs_z.append(f"[项目官网]({prof_links['homepage']})"); srcs_e.append(f"[Project site]({prof_links['homepage']})")
    if u.get("url"):
        srcs_z.append(f"[DefiLlama 解锁日程]({u['url']})"); srcs_e.append(f"[DefiLlama unlock schedule]({u['url']})")
    if pack.get("hacks"):
        srcs_z.append("[DefiLlama 安全事件库](https://defillama.com/hacks)"); srcs_e.append("[DefiLlama hacks database](https://defillama.com/hacks)")
    for n in pack.get("news") or []:
        srcs_z.append(f"{n['outlet']}，{n['date']}：[{n['title']}]({n['url']})")
        srcs_e.append(f"{n['outlet']}, {n['date']}: [{n['title']}]({n['url']})")
    blocks.append(("h2", "数据来源", "Sources", "src"))
    blocks.append(("ul", srcs_z + [f"快照 {pack['as_of']}"], srcs_e + [f"as of {pack['as_of']}"]))
    blocks.append(("h2", "免责声明", "Disclaimer", "disc"))
    blocks.append(("p",
                   "本报告由 DRLabs 根据公开数据撰写，仅供研究与信息交流，**不构成投资建议、财务建议或法律建议，也不构成任何证券或加密资产的要约或要约邀请**。"
                   f"加密资产价格波动剧烈，可能导致部分或全部本金损失。文中买入评分 {total:.1f}/10 是基于公开数据的主观评估，不是评级机构结论。"
                   "完整条款见[关于 DRLabs](../../about.html#disclaimer)。**仅供参考，投资要理性。**",
                   "Written by DRLabs from public data for research and discussion. **Not investment, financial or legal advice, and not an offer.** "
                   f"Crypto can cause partial or total loss. The {total:.1f}/10 buy score is a subjective reading of public data. "
                   "Full terms: [About DRLabs](../../about.html#disclaimer). **For reference only; invest rationally.**"))

    def fix_zh(text: str) -> str:
        return tidy_zh(pangu(text))

    def render(lang: str) -> str:
        zh = lang == "zh"
        out = []
        for b in blocks:
            kind = b[0]
            if kind == "h2":
                key = b[3]
                if lang not in ("zh", "en") and key in FIXED_H:
                    text = FIXED_H[key][lang] + (f" ({day})" if key == "snap" else f" {total:.1f} / 10" if key == "score" else "")
                elif lang not in ("zh", "en") and key == "take":
                    text = {"ja": "研究結論", "ko": "연구 결론", "fr": "Conclusion", "es": "Conclusión", "ru": "Вывод"}[lang]
                else:
                    text = fix_zh(b[1]) if zh else b[2]
                out.append(f"## {text}")
            elif kind == "h3":
                out.append(f"### {b[1] if zh else b[2]}")
            elif kind == "p":
                out.append(fix_zh(b[1]) if zh else b[2])
            elif kind == "ul":
                out.append("\n".join(f"- {fix_zh(i) if zh else i}" for i in (b[1] if zh else b[2])))
            elif kind == "table":
                out.append("\n".join(b[1] if zh else b[2]))
        return "\n\n".join(out) + "\n"

    def yaml(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')

    conc_zh = fix_zh(lead[0][0] + lead[-1][0].replace("**", "")) if lead else ""
    conc_en = (lead[0][1] + " " + lead[-1][1].replace("**", "")) if lead else ""
    desc_zh = f"截至 {pack['as_of']}，{t} 约 {price_str(c['price'])}、流通市值 {zh_usd(c['mcap'])}" + (f"，排名第 {c['rank']}" if c.get("rank") else "") + f"。买入评分 {total:.1f}/10，{v_zh}。"
    desc_en = f"As of {pack['as_of']}, {t} is about {price_str(c['price'])} with mcap {en_usd(c['mcap'])}" + (f", rank {c['rank']}" if c.get("rank") else "") + f". Buy score {total:.1f}/10, {v_en}."
    titles = {"zh": fix_zh(title_zh), "en": title_en}
    rest = title_en.split(": ", 1)[-1]
    for lang, pre in (("ja", f"{t}リサーチノート："), ("ko", f"{t} 리서치 노트: "), ("fr", f"Note {t} : "), ("es", f"Nota {t}: "), ("ru", f"Записка по {t}: ")):
        titles[lang] = pre + rest
    tags = "\n".join(f"  - {tag}" for tag in pack.get("tags") or ["Other"])

    def fm(lang: str) -> str:
        zh = lang == "zh"
        return ("---\n"
                f"title: \"{yaml(titles[lang])}\"\n"
                f"description: \"{yaml(fix_zh(desc_zh) if zh else desc_en)}\"\n"
                f"date: {day}\n"
                + (f"asOf: \"{pack['as_of']}\"\n" if zh else "")
                + f"ticker: {t}\n"
                + (f"cgId: {pack['cg_id']}\n" if zh else "")
                + f"score: {total:.1f}\n"
                f"tags:\n{tags}\n"
                f"conclusion: \"{yaml(conc_zh if zh else conc_en)}\"\n"
                "---\n\n")

    bodies = {lang: fm(lang) + render(lang) for lang in LANGS}
    blob = "\n".join(bodies.values())
    for phrase in BANNED:
        if phrase in blob:
            raise RuntimeError(f"banned template phrase leaked: {phrase}")
    problems = audit(pack, x, bodies)
    if problems:
        raise RuntimeError("audit failed: " + " | ".join(problems))
    return {"bodies": bodies, "titles": titles, "score": total, "profile": s["profile"], "labels": x.labels,
            "findings": [(f.dim, f.key, f.tone) for f in x.f], "signals": s}


# ------------------------------------------------------------------ audit

QUIET_MARKERS = ("没有 FOMO", "没人吵架", "no-argument zone", "neither FOMO", "几乎没有一致预期", "nowhere near the hot topics")
FOMO_MARKERS = ("FOMO 情绪正在占上风", "FOMO 最容易被放大", "FOMO is taking over", "FOMO compounds")


def independent_crowd(pack: dict, turnover: float | None) -> str:
    """Re-derive the crowd state straight from TH, without calling crowd_state()."""
    c = pack["cg"]
    c30, c7, c1y = c.get("chg_30d"), c.get("chg_7d"), c.get("chg_1y")
    loud = bool((pack.get("social") or {}).get("trending_pos")) or (turnover or 0) >= TH["turn_hot"]
    if ((c30 or 0) >= TH["mom_hot"] or (loud and (c30 or 0) > 0)) and (c7 is None or c7 > TH["pull7"]):
        return "frenzy"
    if (c1y or 0) >= TH["boom1y"]:
        return "pullback" if (c7 or 0) <= TH["pull7"] else "runup"
    if c30 is None:
        return "quiet"
    for state, ok in (("capit", c30 <= TH["mom_capit"]), ("warm", c30 >= TH["mom_warm"]), ("cold", c30 <= TH["mom_cold"]),
                      ("jolt", abs(c7 or 0) >= TH["jolt7"])):
        if ok:
            return state
    return "quiet"


def audit(pack: dict, x: Ctx, bodies: dict) -> list[str]:
    """Check every qualitative label against its number. Returns a list of contradictions."""
    c, s, h = pack["cg"], x.s, pack.get("hist") or {}
    bad: list[str] = []
    zh, en = bodies["zh"], bodies["en"]
    c30, c7 = c.get("chg_30d"), c.get("chg_7d")
    state = independent_crowd(pack, s.get("turnover"))
    if state != x.labels.get("crowd"):
        bad.append(f"crowd label {x.labels.get('crowd')} != {state}")
    if (c30 is not None and abs(c30) >= TH["mom_warm"]) or (c7 is not None and abs(c7) >= TH["jolt7"]):
        for m in QUIET_MARKERS:
            if m in zh or m in en:
                bad.append(f"quiet wording '{m}' with 30d {pct(c30)} / 7d {pct(c7)}")
    if state != "frenzy":
        for m in FOMO_MARKERS:
            if m in zh or m in en:
                bad.append(f"FOMO wording '{m}' outside frenzy")
    vt = s.get("vol_trend")
    if ("放量" in zh or "volume expand" in en) and not (vt is not None and vt >= TH["vol_surge"]):
        bad.append(f"放量 wording with 7d volume trend {pct(vt, 0)}")
    if ("缩量" in zh or "volume dry up" in en) and not (vt is not None and vt <= TH["vol_dry"]):
        bad.append(f"缩量 wording with 7d volume trend {pct(vt, 0)}")
    g200, ath, tv, v30 = s.get("ma200_gap"), c.get("ath_chg"), s.get("turnover"), h.get("vol30")
    fl, infl = s.get("float"), s.get("infl_1y")
    u = pack.get("unlocks") or {}
    btc30 = (pack.get("btc") or {}).get("chg_30d")
    for f in x.f:
        k, tone = f.key, f.tone
        checks = {
            "trend_up": g200 is not None and g200 > 0,
            "trend_down": g200 is not None and g200 < 0,
            "rs_btc": s.get("rs_btc_30d") is not None and abs(s["rs_btc_30d"]) >= TH["rs30"] and (s["rs_btc_30d"] > 0) == (tone > 0),
            "rs_btc_1y": s.get("rs_btc_1y") is not None and abs(s["rs_btc_1y"]) >= TH["rs1y"] and (s["rs_btc_1y"] > 0) == (tone > 0),
            "rs_sector": s.get("rs_sector_30") is not None and (s["rs_sector_30"] > 0) == (tone > 0),
            "ath_deep": ath is not None and ath <= TH["ath_deep"] and not s.get("launch_ath"),
            "ath_near": ath is not None and ath >= TH["ath_near"] and not s.get("launch_ath"),
            "ath_launch": bool(s.get("launch_ath")),
            "pullback7": c7 is not None and c7 <= TH["pull7_finding"],
            "spike7": c7 is not None and c7 >= TH["spike7"],
            "turn_hot": tv is not None and tv >= TH["turn_hot"],
            "turn_thin": tv is not None and tv < TH["turn_thin"],
            "vol_shift": vt is not None and ((vt >= TH["vol_surge"]) if tone > 0 else (vt <= TH["vol_dry"])),
            "volatility": v30 is not None and (v30 >= TH["vola_high"] or v30 <= TH["vola_low"]),
            "overhang": fl is not None and fl < 0.6,
            "issuance": fl is not None and fl < 0.6 and s.get("pow"),
            "full_float": fl is not None and (fl >= 0.93 or (s.get("pow") and fl >= 0.75)),
            "pow_float": fl is not None and s.get("pow") and fl >= 0.6,
            "inflation": infl is not None and ((infl >= 8) if tone < 0 else (infl <= 1)),
            "unlock_sched": u.get("next30_pct_circ") is not None and (
                u["next30_pct_circ"] >= TH["unlock_heavy30"] if tone < 0 else
                (u.get("next90_pct_circ") or 0) <= TH["unlock_light90"] if tone > 0 else True),
            "fees": tone == 0 or (s.get("fees_mom") is not None and ((s["fees_mom"] > 8) if tone > 0 else (s["fees_mom"] < -12))),
            "fees_tiny": not s.get("fees_material"),
            "tvl": tone == 0 or (s.get("tvl_mom") is not None and ((s["tvl_mom"] > 8) if tone > 0 else (s["tvl_mom"] < -10))),
            "sector": tone == 0 or (s.get("sector_temp") is not None and btc30 is not None and all(
                ((val - btc30 > 5) if tone > 0 else (btc30 - val > 5))
                for val in [s["sector_temp"]] + ([s["sector_wavg"]] if s.get("sector_wavg") is not None else []))),
            "vs_leader": bool(s.get("leader")) and s["leader"]["mcap"] > c["mcap"] and (s["is_meme"] or not s["leader"].get("meme")),
        }
        if k in ("ps", "pf", "mtvl") and x.labels.get("val_ratio") is not None and f.dim == "valuation" and "同行" in f.proof[0]:
            r = x.labels["val_ratio"]
            checks[k] = (r < TH["val_cheap"]) if tone > 0 else (r > TH["val_rich"]) if tone < 0 else (TH["val_cheap"] <= r <= TH["val_rich"])
        if k in checks and not checks[k]:
            bad.append(f"finding {f.dim}/{k} (tone {tone}) contradicts its number")
    for sec in x.labels.get("sections") or []:
        ht, kind = sec["head_tone"], sec["take"]
        if (ht > 0 and kind == "down") or (ht < 0 and kind == "up"):
            bad.append(f"section {sec['dim']}: heading tone {ht} but take '{kind}'")
    if not s["is_meme"]:
        for q in pack.get("peers") or []:
            if q.get("meme"):
                bad.append(f"meme peer {q.get('ticker')} in a non-meme note")
    for lang in ("zh", "en"):
        body = bodies[lang]
        if re.search(r"\bNone\b|\bnan\b|\binf\b|\{[a-z_0-9]+\}", body):
            bad.append(f"{lang}: unformatted / None value")
    if "仅供参考，投资要理性" not in zh:
        bad.append("disclaimer line missing")
    if "（澳洲珀斯时间）" not in zh:
        bad.append("Perth date missing")
    return bad

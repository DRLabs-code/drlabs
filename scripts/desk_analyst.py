#!/usr/bin/env python3
"""Compose one DRLabs note from one coin's data pack.

The writer works like a desk analyst, not a form:
  1. derive signals from whatever was actually fetched (market structure, supply,
     on-chain usage, valuation vs peers, crowd sentiment);
  2. turn each signal into a finding with a weight (how unusual it is) and a tone;
  3. build the note around the strongest findings: the title, the order of the
     sections, their headings, the score weights and the KOL take all follow them.
A dimension with no fetched data is left out, never filled with invented numbers.
"""
from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass, field
from datetime import datetime

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
    "kol": ("KOL 视角", "KOL angle"),
}

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
}


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


class Voice:
    """Deterministic phrase choice so two notes on the same day do not share sentences."""

    def __init__(self, seed: str):
        self.seed = seed

    def pick(self, key: str, *options):
        h = int(hashlib.sha256(f"{self.seed}:{key}".encode()).hexdigest(), 16)
        return options[h % len(options)]


@dataclass
class Finding:
    dim: str
    key: str
    sal: float
    tone: int
    head: tuple[str, str]
    text: tuple[str, str]
    proof: tuple[str, str] = ("", "")


@dataclass
class Ctx:
    pack: dict
    s: dict = field(default_factory=dict)
    f: list[Finding] = field(default_factory=list)

    def add(self, *args, **kw):
        self.f.append(Finding(*args, **kw))


# ------------------------------------------------------------------ signals

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
    return s


# ------------------------------------------------------------------ findings: market

def market_findings(x: Ctx, v: Voice) -> None:
    pk, s, c = x.pack, x.s, x.pack["cg"]
    h = pk.get("hist") or {}
    t = pk["ticker"]
    btc = pk.get("btc") or {}
    g200, g50 = s.get("ma200_gap"), s.get("ma50_gap")
    if g200 is not None:
        if g200 > 0 and (g50 is None or g50 > 0):
            x.add("market", "trend_up", min(0.75, 0.45 + g200 / 80), +1,
                  ("价格站在 200 日均线之上", "trading above its 200-day average"),
                  (f"现价 {price_str(c['price'])}，比 200 日均线高 {g200:.0f}%"
                   + (f"、比 50 日均线高 {g50:.0f}%" if g50 is not None else "")
                   + "。" + v.pick("tu", "趋势资金还在场内，回踩均线之前不算破位。", "中期趋势向上，回调更可能被当成加仓点。"),
                   f"At {price_str(c['price'])} it sits {g200:.0f}% above the 200-day average"
                   + (f" and {g50:.0f}% above the 50-day" if g50 is not None else "")
                   + ". " + v.pick("tu", "Trend money is still in; nothing is broken until the averages give way.", "The medium-term trend is up, so dips are more likely to be bought.")),
                  (f"高于 200 日均线 {g200:.0f}%", f"{g200:.0f}% above the 200-day"))
        elif g200 < 0 and (g50 is None or g50 < 0):
            x.add("market", "trend_down", min(0.8, 0.45 + abs(g200) / 80), -1,
                  ("价格仍压在 200 日均线之下", "still pinned under the 200-day average"),
                  (f"现价 {price_str(c['price'])}，低于 200 日均线约 {abs(g200):.0f}%"
                   + (f"，也低于 50 日均线 {abs(g50):.0f}%" if g50 is not None else "")
                   + "。" + v.pick("td", "均线空头排列时，任何好消息都要先消化上方的套牢筹码。", "这是下行趋势里的价格，抄底要付出时间成本。"),
                   f"At {price_str(c['price'])} it is about {abs(g200):.0f}% under the 200-day average"
                   + (f" and {abs(g50):.0f}% under the 50-day" if g50 is not None else "")
                   + ". " + v.pick("td", "With the averages stacked bearishly, any good news first has to chew through trapped supply overhead.", "This is a downtrend print; bottom-fishing costs time.")),
                  (f"低于 200 日均线 {abs(g200):.0f}%", f"{abs(g200):.0f}% under the 200-day"))
        else:
            x.add("market", "trend_mixed", 0.35, 0,
                  ("价格卡在 50 日和 200 日均线之间", "caught between the 50- and 200-day averages"),
                  (f"现价相对 200 日均线 {pct(g200, 0)}，相对 50 日均线 {pct(g50, 0)}。短期和中期信号打架，方向要等其中一条均线被有效突破。",
                   f"Price is {pct(g200, 0)} vs the 200-day and {pct(g50, 0)} vs the 50-day. Short and medium signals disagree; direction waits for one average to break."),
                  (f"200 日均线 {pct(g200, 0)}", f"{pct(g200, 0)} vs 200-day"))
    rs = s.get("rs_btc_30d")
    if rs is not None and abs(rs) >= 6:
        up = rs > 0
        x.add("market", "rs_btc", min(1, 0.35 + abs(rs) / 50), +1 if up else -1,
              ("30 日跑赢比特币" if up else "30 日跑输比特币", "outrunning Bitcoin over 30 days" if up else "lagging Bitcoin over 30 days"),
              (f"近 30 日 {t} {pct(c['chg_30d'])}，同期比特币 {pct(btc.get('chg_30d'))}，相对强弱 {pct(rs)}。"
               + ("资金在主动选择它，而不只是跟着大盘涨。" if up else "大盘的风险偏好没有传导到这里，弱势本身就是信息。"),
               f"Over 30 days {t} is {pct(c['chg_30d'])} vs Bitcoin {pct(btc.get('chg_30d'))}, relative strength {pct(rs)}. "
               + ("Money is choosing it, not just riding beta." if up else "Market risk appetite is not reaching it; weakness is information in itself.")),
              (f"30 日相对比特币 {pct(rs)}", f"{pct(rs)} vs BTC over 30d"))
    rs1y = s.get("rs_btc_1y")
    if rs1y is not None and abs(rs1y) >= 30:
        x.add("market", "rs_btc_1y", min(0.9, 0.3 + abs(rs1y) / 200), +1 if rs1y > 0 else -1,
              ("一年维度跑赢比特币" if rs1y > 0 else "一年维度大幅跑输比特币", "a one-year winner vs Bitcoin" if rs1y > 0 else "a one-year laggard vs Bitcoin"),
              (f"拉长到一年，{t} {pct(c.get('chg_1y'))}，比特币 {pct(btc.get('chg_1y'))}。"
               + ("长周期赢家的回调，通常比长周期输家的反弹更值得研究。" if rs1y > 0 else "一年跑输比特币意味着持有它的机会成本已经很高，反弹要先证明不是死猫跳。"),
               f"Over a year {t} is {pct(c.get('chg_1y'))} vs Bitcoin {pct(btc.get('chg_1y'))}. "
               + ("Pullbacks in long-cycle winners usually deserve more work than bounces in losers." if rs1y > 0 else "A year behind Bitcoin means the opportunity cost of holding it is already high; a bounce has to prove it is not a dead-cat.")),
              (f"一年相对比特币 {pct(rs1y, 0)}", f"{pct(rs1y, 0)} vs BTC over 1y"))
    rss = s.get("rs_sector_30")
    sec = pk.get("sector") or {}
    if rss is not None and abs(rss) >= 8 and sec.get("n", 0) >= 8:
        x.add("market", "rs_sector", min(0.8, 0.3 + abs(rss) / 60), +1 if rss > 0 else -1,
              ("在板块里领涨" if rss > 0 else "在板块里掉队", "leading its sector" if rss > 0 else "trailing its sector"),
              (f"同板块 {sec['n']} 个标的 30 日涨跌中位数 {pct(sec['median_30d'])}，{t} 是 {pct(c['chg_30d'])}。"
               + ("板块内部的超额收益在它身上。" if rss > 0 else "板块没拖累它，是它自己弱。"),
               f"The sector's {sec['n']} names have a 30-day median of {pct(sec['median_30d'])}; {t} is {pct(c['chg_30d'])}. "
               + ("The in-sector alpha is here." if rss > 0 else "The sector is not dragging it; it is weak on its own.")),
              (f"板块内相对 {pct(rss)}", f"{pct(rss)} vs sector"))
    ath = c.get("ath_chg")
    if ath is not None:
        year = (c.get("ath_date") or "")[:4]
        athp = f"{abs(ath):.1f}" if abs(ath) >= 99 else f"{abs(ath):.0f}"
        if ath <= -80:
            x.add("market", "ath_deep", min(0.6, 0.3 + abs(ath) / 400), -1,
                  ("距历史高点仍很远", "still far below its all-time high"),
                  (f"历史高点 {price_str(c.get('ath'))}（{c.get('ath_date')}），现价低 {athp}%。"
                   + v.pick("ath", f"这不是「便宜」的证据：{year} 年的买家还在上方等解套，每次反弹都会遇到卖压。", "深度回撤说明上一轮叙事已经被市场重新定价，新叙事要靠新数据撑。"),
                   f"ATH {price_str(c.get('ath'))} ({c.get('ath_date')}); price is {athp}% below it. "
                   + v.pick("ath", f"That is not proof of cheapness: {year} buyers are still overhead waiting to get out, and each rally meets supply.", "A drawdown this deep means the last cycle's story has been repriced; a new one needs new data.")),
                  (f"距 ATH -{athp}%", f"-{athp}% from ATH"))
        elif ath >= -15:
            x.add("market", "ath_near", 0.7, +1,
                  ("逼近历史高点", "pressing against its all-time high"),
                  (f"现价距历史高点 {price_str(c.get('ath'))} 只差 {abs(ath):.0f}%，上方几乎没有套牢盘。价格发现阶段的波动会放大，追高者要接受更宽的止损。",
                   f"Price is only {abs(ath):.0f}% off the {price_str(c.get('ath'))} ATH, so there is little trapped supply overhead. Price discovery widens swings; chasers need wider stops."),
                  (f"距 ATH {pct(ath, 0)}", f"{pct(ath, 0)} from ATH"))
    tv = s.get("turnover")
    if tv is not None:
        pt = s.get("peer_turn")
        vt = s.get("vol_trend")
        trend_zh = f"，7 日均量较前 30 日 {pct(vt, 0)}" if vt is not None and abs(vt) >= 15 else ""
        trend_en = f"; 7-day average volume is {pct(vt, 0)} vs the prior 30 days" if vt is not None and abs(vt) >= 15 else ""
        peer_zh = f"（同行中位数约 {pt:.1f}%）" if pt is not None else ""
        peer_en = f" (peer median about {pt:.1f}%)" if pt is not None else ""
        if tv >= 35:
            x.add("market", "turn_hot", min(0.9, 0.4 + tv / 150), -1,
                  ("换手过热，筹码在快速易手", "turnover running hot"),
                  (f"24 小时成交 {zh_usd(c['volume'])}，换手率约 {tv:.0f}%{peer_zh}{trend_zh}。这种换手更像交易盘在博弈，不是长线资金在沉淀。",
                   f"24h volume {en_usd(c['volume'])}, turnover about {tv:.0f}%{peer_en}{trend_en}. Turnover like this is traders flipping, not long-term money settling in."),
                  (f"换手 {tv:.0f}%", f"{tv:.0f}% turnover"))
        elif tv < 2:
            x.add("market", "turn_thin", 0.55, -1,
                  ("成交偏冷，流动性是硬约束", "a thin tape, liquidity is a hard constraint"),
                  (f"24 小时成交 {zh_usd(c['volume'])}，换手率只有约 {tv:.1f}%{peer_zh}{trend_zh}。机构仓位进出会明显推动价格，这本身就是折价理由。",
                   f"24h volume {en_usd(c['volume'])}, turnover only about {tv:.1f}%{peer_en}{trend_en}. Institutional size would move the price, which is itself a reason for a discount."),
                  (f"换手 {tv:.1f}%", f"{tv:.1f}% turnover"))
        elif pt and pt > 0 and (tv / pt >= 2.5 or tv / pt <= 0.4):
            hot_rel = tv / pt >= 2.5
            x.add("market", "turn_rel", 0.5, +1 if hot_rel else -1,
                  ("交易活跃度远高于同行" if hot_rel else "交易活跃度明显落后同行", "far more actively traded than peers" if hot_rel else "traded far less than peers"),
                  (f"换手率约 {tv:.1f}%，同行中位数约 {pt:.1f}%{trend_zh}。"
                   + ("资金和注意力在它身上停留的时间更长，这在同市值标的里是稀缺的。" if hot_rel else "同样的市值，资金却不愿意在这里交易，流动性折价会一直存在。"),
                   f"Turnover is about {tv:.1f}% against a peer median of about {pt:.1f}%{trend_en}. "
                   + ("Money and attention linger here longer than at peers of similar size, which is scarce." if hot_rel else "At a similar size, money simply prefers to trade elsewhere; a liquidity discount persists.")),
                  (f"换手 {tv:.1f}% vs 同行 {pt:.1f}%", f"turnover {tv:.1f}% vs peers {pt:.1f}%"))
        elif vt is not None and abs(vt) >= 35:
            x.add("market", "vol_shift", min(0.75, 0.3 + abs(vt) / 200), +1 if vt > 0 else -1,
                  ("成交在放量" if vt > 0 else "成交在缩量", "volume expanding" if vt > 0 else "volume drying up"),
                  (f"近 7 日日均成交较前 30 日 {pct(vt, 0)}，当前换手约 {tv:.1f}%{peer_zh}。"
                   + ("放量配合价格方向，才说明有新资金在表态。" if vt > 0 else "缩量说明分歧在减少，也说明关注度在流失。"),
                   f"7-day average volume is {pct(vt, 0)} vs the prior 30 days; turnover about {tv:.1f}%{peer_en}. "
                   + ("Expansion in the direction of price is new money voting." if vt > 0 else "Shrinking volume means less disagreement, and less attention.")),
                  (f"7 日量能 {pct(vt, 0)}", f"7d volume {pct(vt, 0)}"))
    v30, mdd = h.get("vol30"), h.get("mdd90")
    if v30 is not None and (v30 >= 90 or v30 <= 40):
        hi = v30 >= 90
        x.add("market", "volatility", min(0.6, 0.25 + v30 / 400) if hi else 0.35, 0,
              ("波动率很高，仓位要按风险算" if hi else "波动率处在低位", "volatility is high, size by risk" if hi else "volatility is compressed"),
              (f"30 日年化波动率约 {v30:.0f}%" + (f"，近 90 日最大回撤 {pct(mdd, 0)}" if mdd is not None else "") + "。"
               + ("同样的风险预算，仓位应该只有比特币的一部分。" if hi else "低波动往往出现在大行情之前，方向未定时不适合重仓赌方向。"),
               f"30-day annualised volatility about {v30:.0f}%" + (f", 90-day max drawdown {pct(mdd, 0)}" if mdd is not None else "") + ". "
               + ("For the same risk budget the position should be a fraction of a Bitcoin position." if hi else "Compressed volatility tends to precede big moves; with no direction yet, a heavy directional bet is premature.")),
              (f"年化波动 {v30:.0f}%", f"{v30:.0f}% annualised vol"))


# ------------------------------------------------------------------ findings: token

def token_findings(x: Ctx, v: Voice) -> None:
    pk, s, c = x.pack, x.s, x.pack["cg"]
    t = pk["ticker"]
    fl = s.get("float")
    if fl is not None:
        if fl < 0.6 and s.get("pow"):
            x.add("token", "issuance", min(0.9, 0.45 + (0.6 - fl)), -1,
                  ("区块奖励还远没挖完", "a large share of block rewards is still unmined"),
                  (f"流通 {qty(c.get('circ'))} 枚，上限 {qty(c.get('max_supply'))}，已发行约 {100 * fl:.0f}%。按现价，尚未挖出的部分价值约 {zh_usd(s['overhang'])}。这是协议规则内的挖矿增发，不是团队解锁，但矿工的持续卖出同样构成供给压力。",
                   f"{qty(c.get('circ'))} circulating against a {qty(c.get('max_supply'))} cap, about {100 * fl:.0f}% issued. At spot the unmined remainder is worth about {en_usd(s['overhang'])}. This is rule-based mining issuance, not a team unlock, but steady miner selling is still supply."),
                  (f"已发行 {100 * fl:.0f}%", f"{100 * fl:.0f}% issued"))
        elif fl < 0.6:
            x.add("token", "overhang", min(1, 0.5 + (0.6 - fl)), -1,
                  ("大部分供给还没进流通" if fl < 0.4 else "仍有大块供给未进流通", "most of the supply is not yet circulating" if fl < 0.4 else "a large block of supply is not yet circulating"),
                  (f"流通市值 {zh_usd(c['mcap'])}，完全稀释估值（FDV）{zh_usd(c['fdv'])}，流通占比约 {100 * fl:.0f}%。"
                   f"按现价，尚未流通的部分价值约 {zh_usd(s['overhang'])}，是现有流通市值的 {mult(s['overhang'] / c['mcap'])}。"
                   + v.pick("oh", "解锁是持续的卖压来源，除非需求增长快于释放速度，否则价格很难走出独立行情。", "未流通筹码通常集中在团队、投资人和生态基金手里，他们的成本远低于现价。"),
                   f"Circulating cap {en_usd(c['mcap'])} vs FDV {en_usd(c['fdv'])}: about {100 * fl:.0f}% is circulating. "
                   f"At this price the locked remainder is worth about {en_usd(s['overhang'])}, {mult(s['overhang'] / c['mcap'])} the float. "
                   + v.pick("oh", "Unlocks are a standing source of supply; unless demand grows faster than emissions, an independent rally is hard.", "Locked supply usually sits with team, investors and ecosystem funds whose cost basis is far below spot.")),
                  (f"流通仅 {100 * fl:.0f}%", f"only {100 * fl:.0f}% float"))
        elif fl >= 0.93 or (s.get("pow") and fl >= 0.75):
            if s.get("pow") and c.get("max_supply"):
                x.add("token", "pow_float", 0.4, +1,
                      ("没有解锁悬顶", "no unlock overhang"),
                      (f"流通 {qty(c.get('circ'))} 枚，上限 {qty(c.get('max_supply'))}，已发行约 {100 * fl:.0f}%。剩余供给按挖矿规则缓慢释放，没有团队或投资人的集中解锁。",
                       f"{qty(c.get('circ'))} circulating against a {qty(c.get('max_supply'))} cap, about {100 * fl:.0f}% issued. The rest arrives slowly by mining rules, with no concentrated team or investor unlocks."),
                      (f"已发行 {100 * fl:.0f}%", f"{100 * fl:.0f}% issued"))
            else:
                x.add("token", "full_float", 0.25 if s.get("is_meme") else 0.45, +1,
                      ("流通基本到位，解锁压力不大", "supply essentially fully circulating"),
                      (f"流通市值 {zh_usd(c['mcap'])} 与 FDV {zh_usd(c.get('fdv') or c['mcap'])} 几乎重合（流通约 {100 * fl:.0f}%）。悬在头上的解锁筹码很少，供给端不是主要矛盾。",
                       f"Circulating cap {en_usd(c['mcap'])} and FDV {en_usd(c.get('fdv') or c['mcap'])} nearly coincide (about {100 * fl:.0f}% float). Little unlock supply hangs overhead; supply is not the main issue."),
                      (f"流通约 {100 * fl:.0f}%", f"~{100 * fl:.0f}% float"))
        else:
            x.add("token", "mid_float", 0.4, 0,
                  ("仍有一段解锁尾巴", "an unlock tail remains"),
                  (f"FDV {zh_usd(c['fdv'])}，流通市值 {zh_usd(c['mcap'])}，未流通部分约 {zh_usd(s['overhang'])}。解锁压力存在但不是决定性的，节奏比总量更重要。",
                   f"FDV {en_usd(c['fdv'])} vs circulating {en_usd(c['mcap'])}; about {en_usd(s['overhang'])} is not yet circulating. Unlock pressure exists but is not decisive; pace matters more than size."),
                  (f"流通约 {100 * fl:.0f}%", f"~{100 * fl:.0f}% float"))
    infl = s.get("infl_1y")
    if infl is not None and (infl >= 8 or infl <= 1):
        hi = infl >= 8
        i90 = s.get("infl_90d")
        x.add("token", "inflation", min(0.95, 0.35 + abs(infl) / 40) if hi else 0.4, -1 if hi else +1,
              ("流通量一年明显膨胀" if hi else "流通量一年几乎没变", "circulating supply inflating fast" if hi else "circulating supply barely moved in a year"),
              (f"按 CoinGecko 口径，{t} 的流通量一年变化约 {pct(infl, 0)}" + (f"，最近 90 日 {pct(i90)}" if i90 is not None else "") + "。"
               + ("持币不动也会被稀释这么多，价格要先跑赢这个通胀率才算真赚钱。" if hi else "供给端稳定，价格变化基本就是需求变化。"),
               f"On CoinGecko's count, {t}'s circulating supply changed about {pct(infl, 0)} over a year" + (f", {pct(i90)} in the last 90 days" if i90 is not None else "") + ". "
               + ("A passive holder is diluted by that much; price has to beat this inflation before it is a real gain." if hi else "Supply is stable, so price moves are essentially demand moves.")),
              (f"一年流通 {pct(infl, 0)}", f"supply {pct(infl, 0)}/yr"))
    if c.get("max_infinite"):
        x.add("token", "no_cap", 0.3, -1,
              ("没有供给上限", "no supply cap"),
              ("CoinGecko 显示没有最大供应量上限，长期价值取决于增发和销毁的净值，而不是一个固定的稀缺数字。",
               "CoinGecko shows no maximum supply; long-run value depends on net issuance after burns, not a fixed scarcity number."),
              ("无上限", "uncapped"))
    elif s.get("circ_max") is not None and s["circ_max"] >= 0.9 and fl is None:
        x.add("token", "cap_near", 0.35, +1,
              ("接近供应上限", "close to its supply cap"),
              (f"流通 {qty(c['circ'])} 枚，上限 {qty(c['max_supply'])}，已发行约 {100 * s['circ_max']:.0f}%。",
               f"{qty(c['circ'])} circulating against a {qty(c['max_supply'])} cap, about {100 * s['circ_max']:.0f}% issued."),
              (f"已发行 {100 * s['circ_max']:.0f}%", f"{100 * s['circ_max']:.0f}% issued"))


# ------------------------------------------------------------------ findings: usage

def _tone(val, up, dn):
    if val is None:
        return 0
    return +1 if val > up else -1 if val < dn else 0


def usage_findings(x: Ctx, v: Voice) -> None:
    pk, s = x.pack, x.s
    p = pk.get("protocol") or {}
    ch = pk.get("chain") or {}
    if p:
        name = p.get("name") or pk["name"]
        if p.get("fees30") is not None and not s.get("fees_material"):
            x.add("usage", "fees_tiny", 0.55, -1,
                  ("协议费用小到可以忽略", "protocol fees are too small to matter"),
                  (f"DefiLlama 记录的 {name} 近 30 日费用只有 {zh_usd(p['fees30'])}" + (f"，年化约 {zh_usd(s['fees_ann'])}" if s.get("fees_ann") else "")
                   + f"，对应 {zh_usd(pk['cg']['mcap'])} 的流通市值" + (f"，市值 / 年化费用高达 {mult(s.get('pf'))}" if s.get("pf") else "")
                   + "。这意味着价格几乎完全由预期而不是现有业务支撑；收入占比多高都没有意义，因为基数太小。",
                   f"DefiLlama records only {en_usd(p['fees30'])} of 30-day fees for {name}" + (f", about {en_usd(s['fees_ann'])} annualised" if s.get("fees_ann") else "")
                   + f", against a {en_usd(pk['cg']['mcap'])} cap" + (f": mcap / annualised fees of {mult(s.get('pf'))}" if s.get("pf") else "")
                   + ". Price rests on expectations, not on the current business; the capture ratio is irrelevant at this base."),
                  (f"30 日费用仅 {zh_usd(p['fees30'])}", f"30d fees only {en_usd(p['fees30'])}"))
        if p.get("fees30") and s.get("fees_material"):
            mom, acc = s.get("fees_mom"), s.get("fees_accel")
            tone = _tone(mom, 8, -12)
            hz = "费用在增长" if tone > 0 else "费用在萎缩" if tone < 0 else "费用基本持平"
            he = "fees are growing" if tone > 0 else "fees are shrinking" if tone < 0 else "fees are flat"
            x.add("usage", "fees", 0.55 + min(0.35, abs(mom or 0) / 100) + (0.1 if p["fees30"] > 1e7 else 0), tone,
                  (f"{name} {hz}", f"{name} {he}"),
                  (f"DefiLlama 口径，{name} 近 30 日费用 {zh_usd(p['fees30'])}"
                   + (f"，环比上一个 30 日 {pct(mom, 0)}" if mom is not None else "")
                   + (f"；按最近 7 日的速度折算，月度节奏 {pct(acc, 0)}" if acc is not None and abs(acc) >= 10 else "")
                   + f"。年化约 {zh_usd(s['fees_ann'])}。"
                   + ("用户在为它付费，而且付得越来越多，这是最难伪造的需求信号。" if tone > 0 else "需求在降温，估值里的增长假设需要下调。" if tone < 0 else "需求稳定，但稳定不会自动带来估值扩张。"),
                   f"On DefiLlama, {name} took {en_usd(p['fees30'])} in fees over 30 days"
                   + (f", {pct(mom, 0)} vs the prior 30" if mom is not None else "")
                   + (f"; at the last 7 days' pace the monthly run-rate is {pct(acc, 0)}" if acc is not None and abs(acc) >= 10 else "")
                   + f". Annualised about {en_usd(s['fees_ann'])}. "
                   + ("Users are paying, and paying more; that is the hardest demand signal to fake." if tone > 0 else "Demand is cooling; growth assumptions in the valuation need trimming." if tone < 0 else "Demand is steady, but steady does not expand a multiple by itself.")),
                  (f"30 日费用 {zh_usd(p['fees30'])}" + (f"，环比 {pct(mom, 0)}" if mom is not None else ""),
                   f"30d fees {en_usd(p['fees30'])}" + (f", {pct(mom, 0)} MoM" if mom is not None else "")))
        cap = s.get("capture") if s.get("fees_material") else None
        if cap is not None:
            hs = s.get("holder_share")
            thin = cap < 15
            x.add("usage", "capture", (0.7 if (hs or 0) > 50 else 0.6) if thin or cap > 40 else 0.4, -1 if thin else +1 if cap > 40 else 0,
                  ("协议只留下很薄的一层收入" if thin else "协议留得住收入" if cap > 40 else "收入留存中等",
                   "the protocol keeps only a thin slice" if thin else "the protocol keeps its revenue" if cap > 40 else "revenue retention is middling"),
                  (f"30 日协议收入 {zh_usd(p.get('rev30'))}，占费用约 {cap:.0f}%"
                   + (f"；其中分给代币持有人的约 {zh_usd(p.get('hrev30'))}（收入的 {hs:.0f}%）" if hs is not None and p.get("hrev30") else "")
                   + "。" + ("大部分费用流向了流动性提供者或节点，代币持有人分到的现金流有限。" if thin else "代币和业务之间有真实的价值通道。" if cap > 40 else "代币能分到一部分，但还谈不上现金牛。"),
                   f"30-day protocol revenue {en_usd(p.get('rev30'))}, about {cap:.0f}% of fees"
                   + (f"; holders received about {en_usd(p.get('hrev30'))} ({hs:.0f}% of revenue)" if hs is not None and p.get("hrev30") else "")
                   + ". " + ("Most fees go to LPs or operators; token holders see little cash flow." if thin else "There is a real value channel between the business and the token." if cap > 40 else "The token captures some of it, but it is not a cash cow.")),
                  (f"捕获率 {cap:.0f}%", f"{cap:.0f}% capture"))
        if p.get("tvl") and p["tvl"] > 1e6:
            tm, t90, fy = s.get("tvl_mom"), s.get("tvl_90d"), s.get("fee_yield")
            tone = _tone(tm, 8, -10)
            x.add("usage", "tvl", 0.4 + min(0.4, abs(tm or 0) / 60), tone,
                  ("锁仓在流入" if tone > 0 else "锁仓在流出" if tone < 0 else "锁仓稳定", "TVL flowing in" if tone > 0 else "TVL leaking out" if tone < 0 else "TVL steady"),
                  (f"{name} 锁仓 {zh_usd(p['tvl'])}"
                   + (f"，30 日 {pct(tm, 0)}" if tm is not None else "")
                   + (f"、90 日 {pct(t90, 0)}" if t90 is not None else "")
                   + (f"；年化费用相当于锁仓的 {fy:.1f}%" if fy is not None else "")
                   + "。" + ("资金愿意留在这里，说明产品有粘性。" if tone > 0 else "资金在离开，费用迟早会跟着下来。" if tone < 0 else "锁仓不是代币的资产，但它决定了费用的天花板。"),
                   f"{name} TVL {en_usd(p['tvl'])}"
                   + (f", {pct(tm, 0)} over 30 days" if tm is not None else "")
                   + (f", {pct(t90, 0)} over 90" if t90 is not None else "")
                   + (f"; annualised fees equal {fy:.1f}% of TVL" if fy is not None else "")
                   + ". " + ("Capital is choosing to stay, which says the product is sticky." if tone > 0 else "Capital is leaving; fees will follow sooner or later." if tone < 0 else "TVL is not the token's asset, but it sets the ceiling on fees.")),
                  (f"TVL {zh_usd(p['tvl'])}" + (f"，30 日 {pct(tm, 0)}" if tm is not None else ""),
                   f"TVL {en_usd(p['tvl'])}" + (f", {pct(tm, 0)} 30d" if tm is not None else "")))
    if ch:
        cname = ch.get("name") or pk["name"]
        if ch.get("tvl"):
            tm = ch.get("tvl_chg_30d")
            tone = _tone(tm, 8, -10)
            minor = (s.get("chain_mtvl") or 0) > 300
            sal = (0.45 + min(0.35, abs(tm or 0) / 60)) * (0.5 if minor else 1) * (0.7 if s.get("fees_material") else 1)
            if minor:
                head = (f"{cname} 链上 DeFi 体量很小", f"{cname}'s on-chain DeFi is small")
            elif tone > 0:
                head = (f"{cname} 链上资金在流入", f"capital flowing onto {cname}")
            elif tone < 0:
                head = (f"{cname} 链上资金在流失", f"capital leaving {cname}")
            else:
                head = (f"{cname} 链上锁仓排第 {ch.get('rank')}" if ch.get("rank") else f"{cname} 链上锁仓持平", f"{cname} ranks #{ch.get('rank')} by DeFi TVL" if ch.get("rank") else f"{cname} TVL flat")
            x.add("usage", "chain_tvl", sal, 0 if minor else tone, head,
                  (f"{cname} 链上 DeFi 锁仓 {zh_usd(ch['tvl'])}"
                   + (f"，在 DefiLlama 统计的 {ch.get('n')} 条链里排第 {ch.get('rank')}" if ch.get("rank") else "")
                   + (f"，30 日 {pct(tm, 0)}" if tm is not None else "")
                   + (f"、90 日 {pct(ch.get('tvl_chg_90d'), 0)}" if ch.get("tvl_chg_90d") is not None else "")
                   + (f"；稳定币存量 {zh_usd(ch.get('stables'))}" if ch.get("stables") else "")
                   + "。" + (f"相对 {zh_usd(pk['cg']['mcap'])} 的市值，这个体量可以忽略，链上 DeFi 不是它的价值来源。" if minor else "开发者和资金在往这条链上搬。" if tone > 0 else "生态资金在流失，公链估值最怕这个。" if tone < 0 else "生态在横盘，没有明显的资金迁入或迁出。"),
                   f"{cname} DeFi TVL is {en_usd(ch['tvl'])}"
                   + (f", #{ch.get('rank')} of {ch.get('n')} chains on DefiLlama" if ch.get("rank") else "")
                   + (f", {pct(tm, 0)} over 30 days" if tm is not None else "")
                   + (f" and {pct(ch.get('tvl_chg_90d'), 0)} over 90" if ch.get("tvl_chg_90d") is not None else "")
                   + (f"; stablecoins on chain {en_usd(ch.get('stables'))}" if ch.get("stables") else "")
                   + ". " + (f"Against a {en_usd(pk['cg']['mcap'])} cap this is negligible; on-chain DeFi is not where its value comes from." if minor else "Builders and capital are moving onto the chain." if tone > 0 else "Ecosystem capital is leaving, which is what L1/L2 valuations fear most." if tone < 0 else "The ecosystem is moving sideways, no clear migration in or out.")),
                  (f"链上 TVL {zh_usd(ch['tvl'])}" + (f"，30 日 {pct(tm, 0)}" if tm is not None else ""),
                   f"chain TVL {en_usd(ch['tvl'])}" + (f", {pct(tm, 0)} 30d" if tm is not None else "")))
        if ch.get("dex30"):
            dm = s.get("dex_mom")
            tone = _tone(dm, 10, -15)
            x.add("usage", "chain_dex", (0.35 + min(0.4, abs(dm or 0) / 80)) * (0.7 if s.get("fees_material") else 1), tone,
                  ("链上交易在升温" if tone > 0 else "链上交易在降温" if tone < 0 else "链上交易平稳", "on-chain trading heating up" if tone > 0 else "on-chain trading cooling" if tone < 0 else "on-chain trading steady"),
                  (f"近 30 日 {cname} 上 DEX 成交 {zh_usd(ch['dex30'])}"
                   + (f"，环比 {pct(dm, 0)}" if dm is not None else "")
                   + (f"，约为链上锁仓的 {mult(s.get('dex_turn'))}" if s.get("dex_turn") else "")
                   + "。成交是链上真实活跃度最直接的代理变量。",
                   f"DEX volume on {cname} was {en_usd(ch['dex30'])} over 30 days"
                   + (f", {pct(dm, 0)} month on month" if dm is not None else "")
                   + (f", about {mult(s.get('dex_turn'))} its TVL" if s.get("dex_turn") else "")
                   + ". Volume is the most direct proxy for real on-chain activity."),
                  (f"DEX 30 日 {zh_usd(ch['dex30'])}" + (f"，环比 {pct(dm, 0)}" if dm is not None else ""),
                   f"30d DEX {en_usd(ch['dex30'])}" + (f", {pct(dm, 0)} MoM" if dm is not None else "")))
        if ch.get("fees30"):
            fm = s.get("chain_fees_mom")
            tiny = (s.get("chain_fees_ann") or 0) < 0.001 * pk["cg"]["mcap"]
            tone = 0 if tiny else _tone(fm, 10, -15)
            x.add("usage", "chain_fees", 0.3 if tiny else (0.4 + min(0.3, abs(fm or 0) / 100)) * (0.7 if s.get("fees_material") else 1), tone,
                  ("链上费用相对市值微不足道" if tiny else "链上费用在增长" if tone > 0 else "链上费用在下滑" if tone < 0 else "链上费用持平",
                   "chain fees are tiny next to the cap" if tiny else "chain fees growing" if tone > 0 else "chain fees falling" if tone < 0 else "chain fees flat"),
                  (f"{cname} 近 30 日链级费用 {zh_usd(ch['fees30'])}" + (f"，环比 {pct(fm, 0)}" if fm is not None else "")
                   + (f"，收入 {zh_usd(ch.get('rev30'))}" if ch.get("rev30") else "") + "。"
                   + (f"年化不到市值的 0.1%，变化幅度再大，对 {zh_usd(pk['cg']['mcap'])} 的估值也只是零头。" if tiny else "用户为区块空间付的钱，是公链代币价值的底层来源。"),
                   f"{cname} chain-level fees were {en_usd(ch['fees30'])} over 30 days" + (f", {pct(fm, 0)} month on month" if fm is not None else "")
                   + (f", revenue {en_usd(ch.get('rev30'))}" if ch.get("rev30") else "") + ". "
                   + (f"Annualised it is under 0.1% of market cap, so however fast it moves it is a rounding error against {en_usd(pk['cg']['mcap'])}." if tiny else "What users pay for blockspace is the base layer of an L1/L2 token's value.")),
                  (f"链费 30 日 {zh_usd(ch['fees30'])}", f"30d chain fees {en_usd(ch['fees30'])}"))


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
            cheap, rich = r < 0.75, r > 1.4
            x.add("valuation", key, min(1, 0.45 + abs(r - 1) / 2), +1 if cheap else -1 if rich else 0,
                  ("估值比同行便宜" if cheap else "估值比同行贵" if rich else "估值与同行相当", "cheaper than peers" if cheap else "richer than peers" if rich else "valued in line with peers"),
                  (f"{zh_lbl} 约 {mult(own)}，同行中位数约 {mult(peer)}，约为同行的 {r:.2f} 倍。"
                   + ("同样一块钱的业务，这里买得更便宜；前提是增长和留存不比同行差。" if cheap else "市场已经给了溢价，溢价需要更快的增长或更强的护城河来兑现。" if rich else "价格没有给出明显的错配，超额收益要靠基本面改善而不是估值修复。"),
                   f"{en_lbl} is about {mult(own)} vs a peer median of {mult(peer)}, about {r:.2f}x the peers. "
                   + ("The same dollar of business is cheaper here, provided growth and retention are not worse." if cheap else "The market already pays a premium; it has to be earned by faster growth or a deeper moat." if rich else "No obvious mispricing; excess return has to come from fundamentals, not a re-rating.")),
                  (f"{zh_s} {mult(own)}，同行 {mult(peer)}", f"{en_s} {mult(own)} vs peers {mult(peer)}"))
        elif key == "cpf" and not mismatch and own > 1000:
            x.add("valuation", "anchor", 0.35, 0,
                  ("链上费用不是它的估值锚", "chain fees are not its valuation anchor"),
                  (f"{zh_lbl} 约 {mult(own)}。按这个口径，现在的市值要上千年的链费才能覆盖，所以市场显然不是按区块空间收入给 {t} 定价：它的估值来自货币属性、品牌或叙事溢价。这类资产要看资金和叙事，而不是现金流倍数。",
                   f"{en_lbl} is about {mult(own)}. On that yardstick the market cap equals more than a thousand years of chain fees, so the market is clearly not pricing {t} on blockspace revenue; its value comes from monetary role, brand or narrative premium. For assets like this, flows and narrative matter more than cash-flow multiples."),
                  (f"{zh_s} {mult(own)}", f"{en_s} {mult(own)}"))
        elif key in ("ps", "pf") or (key == "cpf" and not mismatch):
            x.add("valuation", key, 0.4, 0,
                  (f"{zh_s} 约 {mult(own)}", f"{en_s} about {mult(own)}"),
                  (f"{zh_lbl} 约 {mult(own)}。同行里能取到同口径数据的不足两家，这个倍数只能作为绝对水平参考，不足以下「便宜」或「贵」的结论。",
                   f"{en_lbl} is about {mult(own)}. Fewer than two peers have like-for-like data, so this is an absolute reference point, not enough to call it cheap or rich."),
                  (f"{zh_s} {mult(own)}", f"{en_s} {mult(own)}"))
        else:
            continue
        done = True
        break
    if not done and mismatch:
        zl, el, own, peer = mismatch
        x.add("valuation", "anchor", 0.45, 0,
              ("链上数据不是它的估值锚", "on-chain data is not its valuation anchor"),
              (f"{zl} 约 {mult(own)}，同行中位数约 {mult(peer)}，差距超过五倍。这不是「贵五倍」的证据，而是说明市场并不按这个口径给 {t} 定价：它的市值主要来自货币属性、品牌或叙事溢价，而不是链上业务规模。用 DeFi 倍数去估它，会得出没有意义的结论。",
               f"{el} is about {mult(own)} vs a peer median of {mult(peer)}, more than five times apart. That is not evidence of being five times too expensive; it says the market does not price {t} on this yardstick. Its value comes from monetary role, brand or narrative premium rather than on-chain business size, and a DeFi multiple gives a meaningless answer."),
              (f"{zl.split('（')[0]} {mult(own)}", f"{el.split(' (')[0]} {mult(own)}"))
        done = True
    if s.get("fdv_ps") and s.get("float") is not None and s["float"] < 0.7:
        x.add("valuation", "fdv_ps", 0.45, -1,
              ("按完全稀释算，倍数更高", "fully diluted, the multiple is higher"),
              (f"如果按 FDV 计算，市值 / 年化收入会升到约 {mult(s['fdv_ps'])}。解锁一旦兑现，今天看起来的倍数就会被稀释。",
               f"On FDV, mcap / annualised revenue rises to about {mult(s['fdv_ps'])}. As unlocks land, today's multiple gets diluted."),
              (f"FDV/收入 {mult(s['fdv_ps'])}", f"FDV/revenue {mult(s['fdv_ps'])}"))
    leader = s.get("leader")
    if leader and s.get("leader_x") and s["leader_x"] > 1:
        lx = s["leader_x"]
        pos = (pk.get("sector") or {}).get("pos")
        x.add("valuation", "vs_leader", 0.3, 0,
              (f"市值约为板块龙头 {leader['ticker']} 的 {100 / lx:.0f}%" if lx < 50 else f"市值不到板块龙头 {leader['ticker']} 的 2%",
               f"worth about {100 / lx:.0f}% of sector leader {leader['ticker']}" if lx < 50 else f"under 2% of sector leader {leader['ticker']}"),
              (f"板块龙头 {leader['ticker']} 市值 {zh_usd(leader['mcap'])}，是 {t} 的 {mult(lx)}"
               + (f"；{t} 在 CoinGecko 该板块市值排第 {pos}" if pos else "")
               + "。" + v.pick("ldr", "二线标的的上行空间来自份额提升，下行风险来自龙头吸走流动性。", "龙头和追随者的估值差，是市场对份额格局的投票。"),
               f"Sector leader {leader['ticker']} is worth {en_usd(leader['mcap'])}, {mult(lx)} {t}"
               + (f"; {t} ranks #{pos} in the CoinGecko sector list" if pos else "")
               + ". " + v.pick("ldr", "A follower's upside comes from share gains; its downside is the leader soaking up liquidity.", "The gap between leader and follower is the market's vote on market share.")),
              (f"龙头是其 {mult(lx)}", f"leader is {mult(lx)} its size"))


# ------------------------------------------------------------------ findings: narrative

def narrative_findings(x: Ctx, v: Voice) -> None:
    pk, c = x.pack, x.pack["cg"]
    cats = c.get("categories") or []
    sectors = [q for q in cats if not q.endswith("Portfolio") and "Index" not in q and "Ecosystem" not in q and "Made in" not in q][:4]
    eco = [q for q in cats if q.endswith("Ecosystem")][:3]
    backers = [q.replace(" Portfolio", "") for q in cats if q.endswith("Portfolio")][:5]
    if not (sectors or backers):
        return
    zh_sec = "、".join(CAT_ZH.get(q, q) for q in sectors) or "未分类"
    en_sec = ", ".join(sectors) or "uncategorised"
    med = (pk.get("sector") or {}).get("median_30d")
    btc30 = (pk.get("btc") or {}).get("chg_30d")
    hot = med is not None and btc30 is not None and med - btc30 > 5
    cold = med is not None and btc30 is not None and btc30 - med > 5
    zh = f"CoinGecko 把 {pk['ticker']} 归入{zh_sec}" + (f"，生态标签为{'、'.join(CAT_ZH.get(q, q) for q in eco)}" if eco else "") + "。"
    en = f"CoinGecko files {pk['ticker']} under {en_sec}" + (f", ecosystems {', '.join(eco)}" if eco else "") + "."
    if backers:
        zh += f"机构持仓标签包括 {'、'.join(backers)}，早期筹码的成本和退出节奏值得留意。"
        en += f" Backer tags include {', '.join(backers)}; their cost basis and exit pace matter."
    if med is not None and btc30 is not None:
        zh += f"所在板块 30 日涨跌中位数 {pct(med)}，比特币 {pct(btc30)}，" + ("叙事正在被资金追捧。" if hot else "叙事处在冷宫，资金在别处。" if cold else "叙事热度与大盘同步。")
        en += f" The sector's 30-day median is {pct(med)} vs Bitcoin {pct(btc30)}: " + ("the story is in demand." if hot else "the story is out of favour and money is elsewhere." if cold else "the story moves with the market.")
    if c.get("genesis"):
        zh += f"项目创世日期 {c['genesis']}。"
        en += f" Genesis date {c['genesis']}."
    first_zh = zh_sec.split("、")[0]
    first_en = sectors[0] if sectors else "n/a"
    x.add("narrative", "sector", 0.5 if (hot or cold) else 0.3, +1 if hot else -1 if cold else 0,
          ("所在叙事正热" if hot else "所在叙事偏冷" if cold else f"定位在{first_zh}", "its narrative is hot" if hot else "its narrative is cold" if cold else f"seated in {first_en}"),
          (zh, en),
          ("板块跑赢比特币" if hot else "板块跑输比特币" if cold else first_zh, "sector beating BTC" if hot else "sector lagging BTC" if cold else first_en))


# ------------------------------------------------------------------ KOL angle

def kol_block(x: Ctx, v: Voice):
    pk, s, c = x.pack, x.s, x.pack["cg"]
    soc = pk.get("social") or {}
    t = pk["ticker"]
    fng, votes, trend = soc.get("fng"), c.get("votes_up"), soc.get("trending_pos")
    lunar = soc.get("lunar") or {}
    mom = c.get("chg_30d")
    items: list[tuple[str, str]] = []
    mz, me = [], []
    if fng:
        mz.append(f"全市场恐惧贪婪指数 {fng['now']:.0f}（{fng['label']}，30 日均值 {fng['avg30']:.0f}）")
        me.append(f"market Fear & Greed {fng['now']:.0f} ({fng['label']}, 30-day average {fng['avg30']:.0f})")
    if trend:
        mz.append(f"{t} 位列 CoinGecko 热搜第 {trend}")
        me.append(f"{t} is #{trend} on CoinGecko trending search")
    elif soc.get("trending_n"):
        mz.append(f"{t} 不在 CoinGecko 热搜前 {soc['trending_n']}")
        me.append(f"{t} is not in CoinGecko's top-{soc['trending_n']} trending")
    if votes is not None:
        mz.append(f"CoinGecko 社区投票看涨 {votes:.0f}%")
        me.append(f"CoinGecko community votes {votes:.0f}% bullish")
    if c.get("watchlist"):
        mz.append(f"约 {c['watchlist'] / 1e4:.1f} 万用户把它加入自选")
        me.append(f"about {c['watchlist'] / 1e3:.0f}K users have it on a watchlist")
    if lunar.get("dominance") is not None:
        mz.append(f"LunarCrush 社交主导率 {lunar['dominance']:.2f}%")
        me.append(f"LunarCrush social dominance {lunar['dominance']:.2f}%")
    if mz:
        items.append(("**盘口情绪：** " + "；".join(mz) + "。", "**Mood:** " + "; ".join(me) + "."))
    hot = (trend is not None) or (mom is not None and mom > 25) or ((s.get("turnover") or 0) > 35)
    cold = trend is None and mom is not None and mom < -10
    greed = bool(fng and fng["now"] >= 70)
    fear = bool(fng and fng["now"] <= 30)
    if hot:
        items.append((f"**共识怎么想：** 时间线上最容易出现的叙事是「{t} 走出来了」——30 日 {pct(mom, 0)}" + (f"、热搜第 {trend}" if trend else "") + "。这正是 FOMO 最容易被放大的阶段。",
                      f"**The crowd:** the easy timeline story is \"{t} is breaking out\" — {pct(mom, 0)} in 30 days" + (f", #{trend} trending" if trend else "") + ". This is exactly when FOMO compounds."))
    elif cold:
        items.append((f"**共识怎么想：** 一个 30 日 {pct(mom, 0)} 的币很难出现在 KOL 的时间线上，散户的典型反应是「等跌完再说」。",
                      f"**The crowd:** a coin that is {pct(mom, 0)} in 30 days rarely makes a KOL timeline; the typical retail reaction is \"wait until it is done falling\"."))
    else:
        items.append((f"**共识怎么想：** {t} 处在没人吵架的区间，30 日 {pct(mom, 0)}，既没有 FOMO 也没有恐慌，声音主要来自长期持有者。",
                      f"**The crowd:** {t} is in a no-argument zone, {pct(mom, 0)} over 30 days, neither FOMO nor panic; most of the voice comes from long-term holders."))
    dw = {"usage": 1.2, "valuation": 1.15, "token": 1.0, "market": 0.8, "narrative": 0.7}
    pos = sorted([f for f in x.f if f.tone > 0], key=lambda f: -f.sal * dw.get(f.dim, 1))
    neg = sorted([f for f in x.f if f.tone < 0], key=lambda f: -f.sal * dw.get(f.dim, 1))
    if hot and neg:
        items.append((f"**反共识：** 热度越高，越要盯住「{neg[0].head[0]}」（{neg[0].proof[0]}）。情绪推上去的价格，最先被这类数字拉回来。",
                      f"**Contrarian:** the louder it gets, the harder it is to ignore that it is {neg[0].head[1]} ({neg[0].proof[1]}). Prices pushed by mood get pulled back by numbers like this first."))
        stance = -1
    elif cold and pos:
        items.append((f"**反共识：** 没人看的时候反而值得看——「{pos[0].head[0]}」（{pos[0].proof[0]}）。价格跌了，这条数据没有跟着坏。",
                      f"**Contrarian:** the time nobody is looking is the time to look — it is {pos[0].head[1]} ({pos[0].proof[1]}). Price fell; this number did not."))
        stance = +1
    elif pos and neg:
        a, b = (pos[0], neg[0]) if pos[0].sal >= neg[0].sal else (neg[0], pos[0])
        items.append((f"**反共识：** 市场的注意力在「{a.head[0]}」，我们更在意「{b.head[0]}」（{b.proof[0]}），它决定这段走势能走多远。",
                      f"**Contrarian:** the market is focused on it being {a.head[1]}; we care more that it is {b.head[1]} ({b.proof[1]}), which decides how far this move can run."))
        stance = b.tone
    else:
        items.append(("**反共识：** 可核数据太少，任何强烈观点都是在押叙事，我们选择等更多数据。",
                      "**Contrarian:** too little checkable data; any strong view is a bet on narrative, so we wait for more."))
        stance = 0
    if greed and hot:
        items.append(("**情绪温度计：** 大盘已在贪婪区，热门币在这种环境下的回撤通常比大盘更深。",
                      "**Thermometer:** the market is already in greed; hot coins usually draw down harder than the market from here."))
    elif fear and not hot:
        items.append(("**情绪温度计：** 大盘处在恐惧区，这类时段分批建仓通常比追涨性价比更高，前提是标的本身没坏。",
                      "**Thermometer:** the market is in fear; scaling in usually beats chasing in such phases, provided the asset itself is not broken."))
    h = pk.get("hist") or {}
    lz, le = [], []
    if h.get("ma200"):
        lz.append(f"200 日均线 {price_str(h['ma200'])}")
        le.append(f"200-day average {price_str(h['ma200'])}")
    if h.get("hi90") and h.get("lo90"):
        lz.append(f"90 日区间 {price_str(h['lo90'])}–{price_str(h['hi90'])}")
        le.append(f"90-day range {price_str(h['lo90'])}–{price_str(h['hi90'])}")
    if lz:
        above = (s.get("ma200_gap") or 0) > 0
        items.append((f"**交易员盯的位置：** {'；'.join(lz)}。" + ("守住 200 日均线，趋势派不会下车；跌破则情绪会很快反转。" if above else "收复 200 日均线之前，反弹大概率被当成减仓机会。"),
                      f"**Levels traders watch:** {'; '.join(le)}. " + ("Hold the 200-day and trend followers stay on; lose it and sentiment flips fast." if above else "Until the 200-day is reclaimed, rallies are likely to be sold.")))
    if hot and greed:
        head = ("热度很高，反着想", "a hot tape, think the other way")
    elif cold and pos:
        head = ("冷门时段，数据没坏", "out of favour, data intact")
    elif trend:
        head = ("上了热搜，分清资金和噪音", "trending, separate money from noise")
    elif hot:
        head = ("涨幅吸引眼球，先看筹码", "the move draws eyes, check the holders first")
    else:
        head = v.pick("kh", ("共识与反共识", "consensus vs contrarian"), ("情绪站在哪一边", "which side the mood is on"))
    return head, items, stance


# ------------------------------------------------------------------ scoring

def clamp(val: float, lo: float = 1.0, hi: float = 9.5) -> float:
    return max(lo, min(hi, val))


def score(x: Ctx, kol_stance: int):
    pk, s, c = x.pack, x.s, x.pack["cg"]
    h = pk.get("hist") or {}
    rows = []
    m, nz, ne = 5.0, [], []
    if s.get("ma200_gap") is not None:
        m += 1.0 if s["ma200_gap"] > 0 else (-1.0 if s["ma200_gap"] < -20 else -0.4)
        nz.append(f"200 日均线 {pct(s['ma200_gap'], 0)}"); ne.append(f"{pct(s['ma200_gap'], 0)} vs 200d")
    if s.get("rs_btc_30d") is not None:
        m += 0.8 if s["rs_btc_30d"] > 10 else (-0.8 if s["rs_btc_30d"] < -15 else 0)
        nz.append(f"30 日相对比特币 {pct(s['rs_btc_30d'], 0)}"); ne.append(f"{pct(s['rs_btc_30d'], 0)} vs BTC 30d")
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
        if s.get("capture") is not None:
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
            val += 1.6 if r < 0.6 else 0.7 if r < 0.9 else -1.8 if r > 2.5 else -1.0 if r > 1.4 else 0
            nz.append(f"{lz} {mult(own)}，同行 {mult(peer)}"); ne.append(f"{le} {mult(own)} vs peers {mult(peer)}")
            used = True
    if not used and s.get("pf") and not material:
        val -= 1.0
        nz.append(f"费用微小，P/F {mult(s['pf'])}"); ne.append(f"tiny fees, P/F {mult(s['pf'])}")
    elif not used:
        ath = c.get("ath_chg")
        if ath is not None:
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
    nz.append("数据与情绪背离" if kol_stance else "情绪与数据同向"); ne.append("data diverges from mood" if kol_stance else "mood and data agree")
    rows.append(("kol", clamp(se), "；".join(nz), "; ".join(ne)))
    r, nz, ne = 6.0, [], []
    v30 = h.get("vol30")
    if v30 is not None:
        r += -1.5 if v30 > 120 else -0.8 if v30 > 80 else 0.5 if v30 < 50 else 0
        nz.append(f"年化波动 {v30:.0f}%"); ne.append(f"vol {v30:.0f}%")
    if h.get("mdd90") is not None and h["mdd90"] < -50:
        r -= 1.0
        nz.append(f"90 日回撤 {pct(h['mdd90'], 0)}"); ne.append(f"90d drawdown {pct(h['mdd90'], 0)}")
    if (c.get("volume") or 0) < 5e6:
        r -= 1.0
        nz.append("成交偏薄"); ne.append("thin volume")
    if s["is_meme"]:
        r -= 0.5
        nz.append("无协议现金流"); ne.append("no protocol cash flow")
    rows.append(("risk", clamp(r), "；".join(nz) or "波动与流动性中性", "; ".join(ne) or "neutral vol/liquidity"))
    weights = {
        "protocol": {"usage": .25, "valuation": .20, "token": .15, "market": .15, "kol": .10, "risk": .15},
        "chain": {"usage": .25, "valuation": .15, "token": .15, "market": .20, "kol": .10, "risk": .15},
        "meme": {"valuation": .10, "token": .15, "market": .30, "kol": .25, "risk": .20},
        "market": {"valuation": .15, "token": .20, "market": .30, "kol": .15, "risk": .20},
    }[s["profile"]]
    label = {"market": ("市场结构与趋势", "Market structure & trend"), "token": ("代币经济与供给", "Tokenomics & supply"),
             "usage": ("链上使用与现金流", "On-chain usage & cash flow"), "valuation": ("相对估值", "Relative valuation"),
             "kol": ("情绪与 KOL 面", "Sentiment & KOL"), "risk": ("风险（越高越稳）", "Risk (higher = safer)")}
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

def catalysts_risks(x: Ctx):
    pk, s, c = x.pack, x.s, x.pack["cg"]
    h = pk.get("hist") or {}
    soc = pk.get("social") or {}
    cat, risk = [], []
    if (s.get("fees_accel") or 0) > 15:
        cat.append(("最近 7 日费用跑在 30 日均值之上；若持续，下一期费用环比会继续改善。", "Fees over the last 7 days run above the 30-day average; if it holds, next month's MoM improves again."))
    if (s.get("tvl_mom") or 0) > 10:
        cat.append(("锁仓持续流入，费用通常会滞后跟上。", "TVL keeps flowing in; fees usually follow with a lag."))
    if (s.get("dex_mom") or 0) > 15:
        cat.append(("链上 DEX 成交放大，生态活跃度在回升。", "On-chain DEX volume is expanding; ecosystem activity is recovering."))
    if (s.get("ma200_gap") or 0) < 0 and (s.get("ma50_gap") or 0) > 0:
        cat.append(("价格已站上 50 日均线，下一步是挑战 200 日均线，收复后趋势资金可能回补。", "Price is back above the 50-day; next is the 200-day, and reclaiming it could pull trend money back."))
    if soc.get("trending_pos"):
        cat.append(("上了 CoinGecko 热搜，短期注意力和新增买盘在流入。", "On CoinGecko trending: short-term attention and new bids are flowing in."))
    if soc.get("fng") and soc["fng"]["now"] <= 30:
        cat.append(("大盘处于恐惧区，情绪修复本身就是催化。", "The market is in fear; a mood recovery is itself a catalyst."))
    if (s.get("rs_sector_30") or 0) > 10:
        cat.append(("板块内资金正在向它集中。", "In-sector money is concentrating on it."))
    if (s.get("chain_fees_mom") or 0) > 15 and (s.get("chain_fees_ann") or 0) >= 0.001 * c["mcap"]:
        cat.append(("链级费用环比走高，区块空间需求在改善。", "Chain fees are rising month on month; blockspace demand is improving."))
    if s.get("float") is not None and s["float"] < 0.7 and s.get("pow"):
        risk.append((f"增发：尚未挖出的区块奖励按现价约 {zh_usd(s['overhang'])}，矿工卖出是持续供给。", f"Issuance: unmined block rewards worth about {en_usd(s['overhang'])} at spot; miner selling is steady supply."))
    elif s.get("float") is not None and s["float"] < 0.7:
        risk.append((f"解锁：约 {zh_usd(s['overhang'])} 的未流通供给，按现价是流通市值的 {mult(s['overhang'] / c['mcap'])}。", f"Unlocks: about {en_usd(s['overhang'])} not yet circulating, {mult(s['overhang'] / c['mcap'])} the float at spot."))
    if (s.get("infl_1y") or 0) > 8:
        risk.append((f"通胀：过去一年流通量增加约 {s['infl_1y']:.0f}%。", f"Inflation: circulating supply up about {s['infl_1y']:.0f}% in a year."))
    if (s.get("fees_mom") or 0) < -12:
        risk.append((f"需求降温：30 日费用环比 {pct(s['fees_mom'], 0)}。", f"Cooling demand: 30-day fees {pct(s['fees_mom'], 0)} MoM."))
    if (s.get("tvl_mom") or 0) < -10:
        risk.append((f"资金外流：锁仓 30 日 {pct(s['tvl_mom'], 0)}。", f"Outflows: TVL {pct(s['tvl_mom'], 0)} over 30 days."))
    if ((pk.get("chain") or {}).get("tvl_chg_30d") or 0) < -10:
        risk.append((f"生态失血：链上锁仓 30 日 {pct(pk['chain']['tvl_chg_30d'], 0)}。", f"Ecosystem bleed: chain TVL {pct(pk['chain']['tvl_chg_30d'], 0)} over 30 days."))
    if (h.get("vol30") or 0) > 90:
        risk.append((f"波动：30 日年化波动约 {h['vol30']:.0f}%，单日 10% 以上的波动并不罕见。", f"Volatility: about {h['vol30']:.0f}% annualised; 10%+ daily moves are not rare."))
    if (s.get("turnover") or 0) > 35:
        risk.append(("过热：高换手意味着短线筹码多，情绪逆转时踩踏更快。", "Froth: high turnover means short-term holders; reversals cascade faster."))
    if (c.get("volume") or 0) < 5e6:
        risk.append(("流动性：成交薄，大额进出会有明显滑点。", "Liquidity: a thin tape means real slippage for size."))
    if s["is_meme"]:
        risk.append(("迷因属性：价格几乎完全由注意力决定，没有协议现金流兜底。", "Meme risk: price is almost purely attention, with no protocol cash flow underneath."))
    if s.get("capture") is not None and s["capture"] < 10:
        risk.append(("价值捕获：协议赚的钱大多不归代币。", "Value capture: most of what the protocol earns does not reach the token."))
    if s["profile"] == "market" and not s["is_meme"] and (s.get("chain_fees_ann") or s.get("fees_ann")):
        risk.append(("估值锚：链上费用相对市值可以忽略，价格主要由货币属性、叙事和资金流决定，这几样都可能很快转向。", "Valuation anchor: on-chain fees are negligible next to the market cap, so price rests on monetary role, narrative and flows, all of which can turn quickly."))
    elif s["profile"] == "market" and not s["is_meme"]:
        risk.append(("数据盲区：DefiLlama 没有与这个代币对应的协议或链级费用数据，本文的基本面判断只能依靠市场数据。", "Data gap: DefiLlama has no protocol or chain fee data mapped to this token, so fundamentals here rest on market data only."))
    risk.append(("宏观与监管：加密资产与全球流动性和监管预期高度相关，单币研究无法对冲这部分风险。", "Macro and policy: crypto trades with global liquidity and regulation; single-coin work cannot hedge that."))
    fz, fe = [], []
    if h.get("ma200"):
        above = (s.get("ma200_gap") or 0) > 0
        fz.append(f"价格{'跌破' if above else '收复'} 200 日均线（{price_str(h['ma200'])}）")
        fe.append(f"price {'losing' if above else 'reclaiming'} the 200-day ({price_str(h['ma200'])})")
    if s.get("fees_mom") is not None:
        fz.append("30 日费用环比转向"); fe.append("30-day fee momentum flipping")
    if s.get("float") is not None and s["float"] < 0.7 and not s.get("pow"):
        fz.append("解锁节奏或回购政策变化"); fe.append("a change in unlock pace or buyback policy")
    if (pk.get("chain") or {}).get("tvl"):
        fz.append("链上锁仓与稳定币趋势反转"); fe.append("chain TVL and stablecoin trends reversing")
    fz.append("相对比特币的 30 日强弱翻转"); fe.append("30-day relative strength vs Bitcoin flipping")
    flip = ("**什么会改变我们的看法：** " + "、".join(fz) + "。", "**What would change our view:** " + ", ".join(fe) + ".")
    return cat[:4], risk[:5], flip


# ------------------------------------------------------------------ compose

LEAD_LBL = {"valuation": ("估值上", "On valuation"), "usage": ("链上看", "On-chain"), "token": ("供给端", "On supply"),
            "market": ("盘面上", "On the tape"), "narrative": ("叙事上", "On narrative")}


def dim_take(dim: str, fs: list[Finding], profile: str | None = None) -> tuple[str, str]:
    tone = sum(f.tone * f.sal for f in fs)
    if dim == "usage" and profile == "market":
        return ("链上使用撑不起现在的估值，价格靠的是叙事、预期和资金，这部分只能用盘面来跟踪。",
                "On-chain usage cannot carry today's valuation; price runs on narrative, expectations and flows, which can only be tracked on the tape.")
    table = {
        "market": (("盘面在帮忙，顺势比逆势更容易。", "The tape is helping; going with it is easier than fighting it."),
                   ("盘面在拖后腿，耐心比勇气更值钱。", "The tape is a headwind; patience beats courage here."),
                   ("盘面没有给出明确方向，节奏交给数据。", "The tape gives no clear direction; let the data set the pace.")),
        "token": (("供给端是加分项。", "Supply is a plus."),
                  ("供给端是这张票最大的结构性压力，估值必须打折。", "Supply is the biggest structural weight on this ticket; the valuation needs a discount."),
                  ("供给不是主要矛盾，但需要跟踪释放节奏。", "Supply is not the main issue, but the release pace needs tracking.")),
        "usage": (("基本面在改善，这是最值得为之付溢价的变化。", "Fundamentals are improving, the change most worth paying up for."),
                  ("基本面在走弱，价格迟早要反映。", "Fundamentals are weakening; price will reflect it sooner or later."),
                  ("基本面稳定，估值扩张需要新的增长点。", "Fundamentals are steady; multiple expansion needs a new growth driver.")),
        "valuation": (("相对估值有安全边际。", "Relative valuation offers a margin of safety."),
                      ("估值已经提前透支了一部分好消息。", "The valuation already prices in part of the good news."),
                      ("相对估值本身不构成买入或卖出的理由。", "Relative valuation is not a reason to buy or sell by itself.")),
        "narrative": (("叙事是顺风。", "The narrative is a tailwind."),
                      ("叙事是逆风，需要自身数据更硬。", "The narrative is a headwind, so its own data has to be harder."),
                      ("叙事中性，价格更多由自身数据决定。", "The narrative is neutral; the coin's own data drives price.")),
    }
    up, down, flat = table[dim]
    return up if tone > 0.25 else down if tone < -0.25 else flat


def sp(text: str) -> str:
    """Space between a CJK connector and a Latin-led phrase."""
    return f" {text}" if text[:1].isascii() and text[:1].isalnum() else text


def compose_note(pack: dict) -> dict:
    x = Ctx(pack=pack)
    x.s = signals(pack)
    v = Voice(pack["ticker"] + pack.get("day", ""))
    market_findings(x, v)
    token_findings(x, v)
    usage_findings(x, v)
    valuation_findings(x, v)
    narrative_findings(x, v)
    kol_head, kol_items, kol_stance = kol_block(x, v)
    total, dims = score(x, kol_stance)
    v_zh, v_en = verdict(total)
    c, t, s, day, name = pack["cg"], pack["ticker"], x.s, pack["day"], pack["name"]

    dim_w = {"usage": 1.2, "valuation": 1.15, "token": 1.0, "market": 0.8}
    ranked = sorted([f for f in x.f if f.dim != "narrative"], key=lambda f: -f.sal * dim_w.get(f.dim, 1))
    pos = [f for f in ranked if f.tone > 0]
    neg = [f for f in ranked if f.tone < 0]
    top = ranked[0] if ranked else None

    def w(f):
        return f.sal * dim_w.get(f.dim, 1)

    if pos and neg and pos[0].sal >= 0.5 and neg[0].sal >= 0.5:
        a, b = (pos[0], neg[0]) if w(pos[0]) >= w(neg[0]) else (neg[0], pos[0])
        j = v.pick("tj", ("，但", ", but "), ("；不过", "; yet "), ("，可是", ", while "))
        title_zh, title_en = f"{t} 研究简报：{a.head[0]}{j[0]}{sp(b.head[0])}", f"{t} research note: {a.head[1]}{j[1]}{b.head[1]}"
    elif top:
        title_zh, title_en = f"{t} 研究简报：{top.head[0]}", f"{t} research note: {top.head[1]}"
    else:
        title_zh, title_en = f"{t} 研究简报", f"{t} research note"

    lead: list[tuple[str, str]] = []
    def paren(f, i, l, r):
        return "" if (not f.proof[i] or f.proof[i] in f.head[i]) else f"{l}{f.proof[i]}{r}"

    if pos and neg:
        a, b = (pos[0], neg[0]) if w(pos[0]) >= w(neg[0]) else (neg[0], pos[0])
        op = v.pick("op", ("这是一张需要拆开看的票：", "This one needs to be taken apart. On "), ("先说结论：", "Bottom line on "),
                    (f"看 {t} 要同时抓住两件事：", "Two things matter at once for "))
        cn = v.pick("cn", ("但", "but"), ("与此同时", "while at the same time"), ("然而", "yet"))
        lead.append((f"{op[0]}{name}（{t}）{a.head[0]}{paren(a, 0, '（', '）')}，{cn[0]}{sp(b.head[0])}{paren(b, 0, '（', '）')}。",
                     f"{op[1]}{name} ({t}): {a.head[1]}{paren(a, 1, ' (', ')')}, {cn[1]} {b.head[1]}{paren(b, 1, ' (', ')')}."))
        used = {a.key, b.key}
    elif top:
        lead.append((f"{name}（{t}）眼下最突出的特征是{top.head[0]}{paren(top, 0, '（', '）')}。",
                     f"The defining feature of {name} ({t}) right now: {top.head[1]}{paren(top, 1, ' (', ')')}."))
        used = {top.key}
    else:
        used = set()
    extra = []
    for dim in v.pick("leadorder", ("valuation", "usage", "token", "market"), ("usage", "valuation", "market", "token"), ("token", "usage", "valuation", "market")):
        cand = [f for f in ranked if f.dim == dim and f.key not in used]
        if cand:
            extra.append(cand[0])
            used.add(cand[0].key)
        if len(extra) >= 2:
            break
    if extra:
        lead.append(("；".join(f"{LEAD_LBL[f.dim][0]}，{f.head[0]}{paren(f, 0, '（', '）')}" for f in extra) + "。",
                     " ".join(f"{LEAD_LBL[f.dim][1]}, {f.head[1]}{paren(f, 1, ' (', ')')}." for f in extra)))
    if total >= 6.5:
        st = ("数据整体站在多头一边，但仓位应跟着下文的风险项走，而不是一次打满。", "The data leans bullish overall, but sizing should follow the risks below rather than going all in.")
    elif total >= 5.0:
        st = ("多空证据大致抵消，更适合放进观察名单，等关键数据给出方向。", "Bull and bear evidence roughly cancel; it belongs on a watchlist until the key numbers pick a side.")
    else:
        st = ("负面证据占上风，在下文列出的条件改善之前，我们不建议主动建仓。", "Negative evidence dominates; until the conditions below improve we would not initiate a position.")
    lead.append((f"**买入评分 {total:.1f} / 10（{v_zh}）。** {st[0]}", f"**Buy score {total:.1f} / 10 ({v_en}).** {st[1]}"))

    h, p, ch, soc = pack.get("hist") or {}, pack.get("protocol") or {}, pack.get("chain") or {}, pack.get("social") or {}
    rows: list[tuple[str, str, str, str]] = []

    def row(zh, en, val, src):
        if val and "—" not in val.split(" / ")[0][:1]:
            rows.append((zh, en, val, src))

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
        row("距历史高点", "From ATH", f"{pct(c['ath_chg'], 1 if abs(c['ath_chg']) > 99.4 else 0)}（{price_str(c.get('ath'))}，{c.get('ath_date')}）", "CoinGecko")
    if s.get("ma200_gap") is not None:
        row("相对 200 日均线", "vs 200-day average", pct(s["ma200_gap"], 0), "CoinGecko 365d")
    if h.get("vol30") is not None:
        row("30 日年化波动 / 90 日最大回撤", "30d vol / 90d max drawdown", f"{h['vol30']:.0f}% / {pct(h.get('mdd90'), 0)}", "CoinGecko 365d")
    mx = qty(c.get("max_supply")) if c.get("max_supply") else ("∞" if c.get("max_infinite") else "—")
    row("流通 / 总量 / 上限", "Circ / total / max", f"{qty(c.get('circ'))} / {qty(c.get('total'))} / {mx}", "CoinGecko")
    if s.get("infl_1y") is not None:
        row("一年流通量变化", "1y circulating change", pct(s["infl_1y"]), "CoinGecko 365d")
    if p.get("tvl"):
        row("协议 TVL", "Protocol TVL", en_usd(p["tvl"]) + (f"（30 日 {pct(s.get('tvl_mom'), 0)}）" if s.get("tvl_mom") is not None else ""), "DefiLlama")
    if p.get("fees30"):
        row("30 日费用 / 收入", "30d fees / revenue", f"{en_usd(p['fees30'])} / {en_usd(p.get('rev30'))}", "DefiLlama")
    if s.get("pf") is not None:
        row("P/F · P/S（年化）", "P/F · P/S (annualised)", f"{mult(s['pf'])} · {mult(s.get('ps'))}", "计算 / calc")
    if ch.get("tvl"):
        row("链上 TVL", "Chain TVL", en_usd(ch["tvl"]) + (f"（30 日 {pct(ch.get('tvl_chg_30d'), 0)}）" if ch.get("tvl_chg_30d") is not None else ""), "DefiLlama")
    if ch.get("stables"):
        row("链上稳定币", "Stablecoins on chain", en_usd(ch["stables"]), "DefiLlama")
    if ch.get("dex30"):
        row("链上 DEX 30 日成交", "Chain DEX 30d volume", en_usd(ch["dex30"]), "DefiLlama")
    if ch.get("fees30"):
        row("链级 30 日费用", "Chain 30d fees", en_usd(ch["fees30"]), "DefiLlama")
    if soc.get("fng"):
        row("恐惧贪婪指数", "Fear & Greed", f"{soc['fng']['now']:.0f} ({soc['fng']['label']})", "alternative.me")
    if c.get("votes_up") is not None:
        row("社区看涨投票", "Community bullish votes", f"{c['votes_up']:.0f}%", "CoinGecko")
    tbl_zh = ["| 指标 | 数值 | 来源 |", "| --- | --- | --- |"] + [f"| {a} | {val} | {src} |" for a, _, val, src in rows]
    tbl_en = ["| Metric | Value | Source |", "| --- | --- | --- |"] + [f"| {b} | {val.replace('（', ' (').replace('）', ')').replace('，', ', ').replace('30 日', '30d')} | {src} |" for _, b, val, src in rows]

    by_dim: dict[str, list[Finding]] = {}
    for f in x.f:
        by_dim.setdefault(f.dim, []).append(f)
    order = sorted(by_dim, key=lambda d: -max(f.sal for f in by_dim[d]))
    if "narrative" in order:
        order.remove("narrative")
        order.insert(min(len(order), v.pick("narr", 0, 1, 99)), "narrative")
    kol_at = min(len(order), v.pick("kolpos", 2, 3))
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
        fs = sorted(by_dim[dim], key=lambda f: -f.sal)
        lbl = DIM_LABEL[dim]
        blocks.append(("h2", f"{lbl[0]}：{fs[0].head[0]}", f"{lbl[1]}: {fs[0].head[1]}", None))
        body = fs[:4] if dim == "usage" else fs[:3]
        if len(body) >= 3 and v.pick(dim + "split", True, False):
            blocks.append(("p", body[0].text[0] + body[1].text[0], body[0].text[1] + " " + body[1].text[1]))
            blocks.append(("p", body[2].text[0], body[2].text[1]))
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
            for q in [me] + peers:
                cells = [q["ticker"], en_usd(q.get("mcap")), pct(q.get("chg_30d")), f"{q['turnover']:.1f}%" if q.get("turnover") is not None else "—"]
                if has_pf:
                    cells.append(mult(q.get("pf")))
                if has_mtvl:
                    cells.append(mult(q.get("mtvl")))
                lz.append("| " + " | ".join(cells) + " |")
                le.append("| " + " | ".join(cells) + " |")
            blocks.append(("table", lz, le))
        tz, te = dim_take(dim, fs, x.s.get("profile"))
        blocks.append(("p", f"{tp[0]}{tz}", f"{tp[1]}{te}"))
    if kol_at >= len(order):
        add_kol()

    cats_, risks_, flip = catalysts_risks(x)
    blocks.append(("h2", "催化与风险", "Catalysts and risks", "risk"))
    if cats_:
        blocks.append(("h3", "可能的催化", "Possible catalysts", None))
        blocks.append(("ul", [a for a, _ in cats_], [b for _, b in cats_]))
    blocks.append(("h3", "主要风险", "Main risks", None))
    blocks.append(("ul", [a for a, _ in risks_], [b for _, b in risks_]))
    blocks.append(("p", flip[0], flip[1]))

    sz = ["| 维度 | 权重 | 得分 | 依据 |", "| --- | ---: | ---: | --- |"]
    se = ["| Factor | Weight | Score | Basis |", "| --- | ---: | ---: | --- |"]
    for zn, en, w, val_, nzh, nen in dims:
        sz.append(f"| {zn} | {w:.0%} | {val_:.1f} | {nzh or '—'} |")
        se.append(f"| {en} | {w:.0%} | {val_:.1f} | {nen or '—'} |")
    sz.append(f"| **合计** | **100%** | **{total:.1f}** | **{v_zh}** |")
    se.append(f"| **Total** | **100%** | **{total:.1f}** | **{v_en}** |")
    blocks.append(("h2", f"买入评分 {total:.1f} / 10", f"Buy score {total:.1f} / 10", "score"))
    blocks.append(("table", sz, se))
    prof = {"protocol": ("是有可核费用或锁仓的协议，链上使用与估值权重最高", "a protocol with checkable fees or TVL, so usage and valuation weigh most"),
            "chain": ("是公链或二层网络，链上生态与市场结构权重最高", "an L1/L2 network, so ecosystem usage and market structure weigh most"),
            "meme": ("是迷因币，没有协议现金流，市场结构与情绪权重最高", "a meme coin with no protocol cash flow, so market structure and sentiment weigh most"),
            "market": ("缺少可核的链上现金流数据，评分主要依据市场结构、供给与情绪", "lacking checkable on-chain cash-flow data, so the score rests on market structure, supply and sentiment")}[s["profile"]]
    blocks.append(("p", f"评分标准：各维度 1–10 分，按权重加权；6.5 分及以上为谨慎跟踪，5.0–6.4 为观望，5.0 以下为回避。本篇标的{prof[0]}。",
                   f"Scale: each factor 1–10, weighted; 6.5+ cautious watch, 5.0–6.4 hold / wait, below 5.0 avoid. This coin is {prof[1]}."))

    srcs = list(dict.fromkeys(pack.get("sources") or ["CoinGecko"]))
    blocks.append(("h2", "数据来源", "Sources", "src"))
    blocks.append(("ul", srcs + [f"快照 {pack['as_of']}"], srcs + [f"as of {pack['as_of']}"]))
    blocks.append(("h2", "免责声明", "Disclaimer", "disc"))
    blocks.append(("p",
                   "本报告由 DRLabs 根据公开数据撰写，仅供研究与信息交流，**不构成投资建议、财务建议或法律建议，也不构成任何证券或加密资产的要约或要约邀请**。"
                   f"加密资产价格波动剧烈，可能导致部分或全部本金损失。文中买入评分 {total:.1f}/10 是基于公开数据的主观评估，不是评级机构结论。"
                   "完整条款见[关于 DRLabs](../../about.html#disclaimer)。**仅供参考，投资要理性。**",
                   "Written by DRLabs from public data for research and discussion. **Not investment, financial or legal advice, and not an offer.** "
                   f"Crypto can cause partial or total loss. The {total:.1f}/10 buy score is a subjective reading of public data. "
                   "Full terms: [About DRLabs](../../about.html#disclaimer). **For reference only; invest rationally.**"))

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
                    text = b[1] if zh else b[2]
                out.append(f"## {text}")
            elif kind == "h3":
                out.append(f"### {b[1] if zh else b[2]}")
            elif kind == "p":
                out.append(b[1] if zh else b[2])
            elif kind == "ul":
                out.append("\n".join(f"- {i}" for i in (b[1] if zh else b[2])))
            elif kind == "table":
                out.append("\n".join(b[1] if zh else b[2]))
        return "\n\n".join(out) + "\n"

    def yaml(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')

    conc_zh = lead[0][0] + lead[-1][0].replace("**", "") if lead else ""
    conc_en = lead[0][1] + " " + lead[-1][1].replace("**", "") if lead else ""
    desc_zh = f"截至 {pack['as_of']}，{t} 约 {price_str(c['price'])}、流通市值 {zh_usd(c['mcap'])}" + (f"，排名第 {c['rank']}" if c.get("rank") else "") + f"。买入评分 {total:.1f}/10，{v_zh}。"
    desc_en = f"As of {pack['as_of']}, {t} is about {price_str(c['price'])} with mcap {en_usd(c['mcap'])}" + (f", rank {c['rank']}" if c.get("rank") else "") + f". Buy score {total:.1f}/10, {v_en}."
    titles = {"zh": title_zh, "en": title_en}
    rest = title_en.split(": ", 1)[-1]
    for lang, pre in (("ja", f"{t}リサーチノート："), ("ko", f"{t} 리서치 노트: "), ("fr", f"Note {t} : "), ("es", f"Nota {t}: "), ("ru", f"Записка по {t}: ")):
        titles[lang] = pre + rest
    tags = "\n".join(f"  - {tag}" for tag in pack.get("tags") or ["Other"])

    def fm(lang: str) -> str:
        zh = lang == "zh"
        return ("---\n"
                f"title: \"{yaml(titles[lang])}\"\n"
                f"description: \"{yaml(desc_zh if zh else desc_en)}\"\n"
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
    return {"bodies": bodies, "titles": titles, "score": total, "profile": s["profile"]}

#!/usr/bin/env python3
"""Turn a desk snapshot into a per-asset note. Do not reuse one paragraph for every ticker."""
from __future__ import annotations

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
)


def fmt_usd(value: float | None) -> str:
    if value is None:
        return "未披露"
    n = abs(value)
    sign = "-" if value < 0 else ""
    if n >= 1e12:
        return f"{sign}约 {n / 1e12:.2f} 万亿美元" if False else f"{sign}≈ ${n / 1e12:.2f}T"
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
        return "未披露"
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
        return "未披露"
    return f"{value:+.1f}%"


def turn(vol, mcap) -> float | None:
    if vol and mcap and mcap > 0:
        return 100.0 * vol / mcap
    return None


def detect_kind(snap) -> str:
    hotter = [p for p in (snap.peers or []) if p.get("volume") and snap.volume and p["volume"] > snap.volume]
    capture = None
    if snap.fees_30d and snap.rev_30d is not None and snap.fees_30d > 0:
        capture = snap.rev_30d / snap.fees_30d
    own_dex = None
    lead_dex = None
    if snap.dexs:
        lead_dex = max(snap.dexs, key=lambda r: r.get("vol_30d") or 0)
        label = (snap.tvl_label or "").lower()
        for row in snap.dexs:
            if str(row.get("name") or "").lower() in label:
                own_dex = row
    tvl_share = None
    if snap.tvl and snap.chains:
        total = sum((c.get("tvl") or 0) for c in snap.chains)
        if total:
            tvl_share = snap.tvl / total

    if snap.lane == "Meme":
        return "meme_tape_left" if hotter else "meme_liquid"
    if snap.lane == "GameFi":
        if snap.fees_30d is not None and snap.fees_30d < 1e5:
            return "gamefi_empty_fees"
        if snap.tvl and snap.tvl < 5e7:
            return "gamefi_thin_book"
        return "gamefi_peer"
    if snap.lane == "DeFi" or (snap.tvl_label and "TVL" in snap.tvl_label and snap.lane != "major"):
        if capture is not None and capture < 0.12:
            return "defi_thin_capture"
        if snap.tvl and snap.mcap and snap.mcap < 0.05 * snap.tvl:
            return "defi_tvl_not_token"
        return "defi_peer"
    # L1 / major
    if lead_dex and own_dex:
        if (own_dex.get("vol_30d") or 0) < (lead_dex.get("vol_30d") or 0) * 0.75 and (tvl_share or 0) > 0.3:
            return "l1_settle_not_tape"
        if lead_dex.get("name") and str(lead_dex["name"]).lower() in (snap.tvl_label or "").lower() and (tvl_share or 0) < 0.15:
            return "l1_tape_not_settle"
    if snap.tvl and snap.mcap and snap.mcap > 40 * snap.tvl:
        return "l1_reserve"
    return "l1_peer"


def verdict(score: float) -> tuple[str, str]:
    if score >= 6.5:
        return "谨慎跟踪", "cautious watch"
    if score >= 5.0:
        return "观望", "hold / wait"
    return "回避", "avoid"


def score_note(snap) -> tuple[float, list[tuple[str, str, float, float, str, str]]]:
    rank = snap.rank or 180
    if rank <= 5:
        size = 8.6
    elif rank <= 15:
        size = 7.6
    elif rank <= 40:
        size = 6.6
    elif rank <= 80:
        size = 5.6
    else:
        size = 4.6
    vol = snap.volume or 0
    if vol >= 1e9:
        liq = 8.2
    elif vol >= 2e8:
        liq = 7.0
    elif vol >= 5e7:
        liq = 6.0
    else:
        liq = 4.8
    peers = snap.peers or []
    hotter = [p for p in peers if p.get("volume") and snap.volume and p["volume"] > snap.volume]
    if hotter:
        liq = min(liq, 6.2)
    market = (size + liq) / 2

    if snap.rev_30d and snap.rev_30d > 1e6:
        income = 7.0
    elif snap.fees_30d and snap.fees_30d > 1e7:
        income = 6.2
    elif snap.fees_30d and snap.fees_30d > 1e5:
        income = 5.2
    elif snap.tvl and snap.tvl > 1e9:
        income = 5.0
    else:
        income = 3.4

    if snap.max_supply and snap.circ:
        token = 6.6 if (snap.circ / snap.max_supply) >= 0.7 else 5.0
    else:
        token = 4.4
    if snap.chg_30d and snap.chg_30d > 25:
        token = max(4.6, token - 0.8)

    kind = detect_kind(snap)
    product = {
        "l1_reserve": 6.4,
        "l1_settle_not_tape": 7.0,
        "l1_tape_not_settle": 6.8,
        "l1_peer": 6.2,
        "defi_thin_capture": 6.6,
        "defi_tvl_not_token": 6.8,
        "defi_peer": 6.2,
        "gamefi_empty_fees": 5.6,
        "gamefi_thin_book": 5.4,
        "gamefi_peer": 5.8,
        "meme_tape_left": 4.0,
        "meme_liquid": 4.2,
    }.get(kind, 5.6)

    compete = 6.4 if rank <= 20 and not hotter else 5.2 if hotter else 5.6
    risk = 5.8 if snap.lane != "Meme" else 4.2
    if snap.max_supply and snap.circ and snap.circ / snap.max_supply < 0.5:
        risk = min(risk, 5.0)
    option = 6.0 if snap.tvl and snap.tvl > 1e9 else 5.2
    heat = getattr(snap, "lunar", None) or {}
    if heat.get("dominance") and heat["dominance"] >= 5:
        option = min(7.0, option + 0.4)
    if snap.lane == "Meme":
        income = min(income, 3.6)
        product = min(product, 4.4)
        option = min(option, 5.0)

    self_turn = turn(snap.volume, snap.mcap)
    market_note_zh = f"市值第 {rank}" if snap.rank else "市值排名未披露"
    if self_turn is not None:
        market_note_zh += f"，换手约 {self_turn:.1f}%"
    if hotter:
        market_note_zh += f"，成交落后 {hotter[0]['ticker']}"
    market_note_en = market_note_zh.replace("市值第", "rank").replace("，换手约", ", turnover ").replace("%", "%").replace("，成交落后", ", tape trails ")

    if snap.fees_30d is not None and snap.rev_30d is not None and snap.fees_30d > 0:
        cap = 100 * snap.rev_30d / snap.fees_30d
        income_zh = f"30 日费用 {fmt_usd(snap.fees_30d)}，捕获约 {cap:.1f}%"
        income_en = f"30d fees {fmt_usd(snap.fees_30d)}, capture ~{cap:.1f}%"
    elif snap.fees_30d is not None:
        income_zh = f"30 日费用 {fmt_usd(snap.fees_30d)}，收入未披露"
        income_en = f"30d fees {fmt_usd(snap.fees_30d)}, revenue undisclosed"
    else:
        income_zh = "没有可核费用，不写成现金牛"
        income_en = "No sourced fees; not a cash-cow write-up"

    if snap.max_supply and snap.circ:
        token_zh = f"硬顶，流通约 {100 * snap.circ / snap.max_supply:.0f}%"
        token_en = f"Hard cap, float ~{100 * snap.circ / snap.max_supply:.0f}%"
    else:
        token_zh = "无硬顶，稀释是默认风险"
        token_en = "No hard cap; dilution is the default risk"
    if snap.chg_30d is not None:
        token_zh += f"；30 日 {fmt_pct(snap.chg_30d)}"
        token_en += f"; 30d {fmt_pct(snap.chg_30d)}"

    product_map = {
        "l1_reserve": ("产品是储备与结算，不是锁仓", "Product is reserve/settlement, not lockup"),
        "l1_settle_not_tape": ("结算本账还在，成交已经分走", "Settlement book remains; tape already left"),
        "l1_tape_not_settle": ("成交层领先，结算层仍是零头", "Tape leads; settlement is still a fraction"),
        "defi_thin_capture": ("费用池厚，代币只留一薄层", "Fee pool is thick; token keeps a thin slice"),
        "defi_tvl_not_token": ("锁仓是别人的资产，不是代币的", "TVL is other people’s assets, not the token’s"),
        "gamefi_empty_fees": ("链还在，费用科目接近于零", "Chain is there; fee line is near zero"),
        "meme_tape_left": ("迷因只认成交和讨论，这两项都偏弱", "Meme scores tape and chatter; both are weak"),
        "meme_liquid": ("流动性是真的，没有协议现金流", "Liquidity is real; no protocol cash flow"),
    }
    product_zh, product_en = product_map.get(kind, ("按能核的产品位置给分", "Score the checkable product seat"))

    compete_zh = f"同桌 {', '.join(p['ticker'] for p in peers[:3]) or '未取到同行'}"
    if hotter:
        compete_zh += f"；磁带在 {hotter[0]['ticker']}"
    compete_en = compete_zh.replace("同桌", "peers").replace("；磁带在", "; tape at ").replace("未取到同行", "no peers")

    risk_zh = "迷因注意力半衰期短" if snap.lane == "Meme" else "周期与监管，不是模板下调"
    risk_en = "Meme attention half-life is short" if snap.lane == "Meme" else "Cycle and policy risk, not a template cut"
    if snap.max_supply and snap.circ and snap.circ / snap.max_supply < 0.5:
        risk_zh = f"流通只有约 {100 * snap.circ / snap.max_supply:.0f}%，解锁仍厚"
        risk_en = f"Only ~{100 * snap.circ / snap.max_supply:.0f}% circulating; unlock still thick"

    option_zh = "热度能抬短线，不能代替费用"
    option_en = "Heat can lift the tape; it does not replace fees"
    if heat.get("dominance"):
        option_zh = f"LunarCrush 主导率 {heat['dominance']:.2f}%，只作注意力期权"
        option_en = f"LunarCrush dominance {heat['dominance']:.2f}%; attention option only"

    dims = [
        ("市场地位与流动性", "Market position & liquidity", 0.20, market, market_note_zh, market_note_en),
        ("收入与费用捕获", "Fees and capture", 0.15, income, income_zh, income_en),
        ("代币经济与估值", "Token and valuation", 0.15, token, token_zh, token_en),
        ("产品与技术演进", "Product", 0.15, product, product_zh, product_en),
        ("竞争格局", "Competition", 0.15, compete, compete_zh, compete_en),
        ("风险与治理", "Risk", 0.10, risk, risk_zh, risk_en),
        ("增长期权", "Optionality", 0.10, option, option_zh, option_en),
    ]
    raw = sum(weight * value for _, _, weight, value, _, _ in dims)
    total = max(3.0, min(8.2, raw))
    return round(total + 1e-9, 1), dims


def title_pair(snap, kind: str) -> tuple[str, str]:
    peers = snap.peers or []
    hotter = [p for p in peers if p.get("volume") and snap.volume and p["volume"] > snap.volume]
    lead = None
    if snap.dexs:
        lead = max(snap.dexs, key=lambda r: r.get("vol_30d") or 0)["name"]
    mapping = {
        "l1_reserve": ("储备和注意力仍是第一，链上只解释零头", "still first as reserve and attention; the chain only explains a rounding error"),
        "l1_settle_not_tape": ("美元结算还在第一，现货成交已经被切走", "still the dollar settlement book; spot tape already left"),
        "l1_tape_not_settle": ("成交已经是第一，美元结算还只是零头", "turnover already leads; dollar settlement is still a fraction"),
        "l1_peer": (f"市值第 {snap.rank or '—'}，要把成交、锁仓和热度拆开", f"#{snap.rank or '—'} by cap; split tape, lockup and heat"),
        "defi_thin_capture": ("费用池在，代币只留下一薄层", "the fee pool is real; the token keeps a thin slice"),
        "defi_tvl_not_token": ("锁仓很厚，代币只分到费用的一薄层", "the lockup is thick; the token only keeps a fee sliver"),
        "defi_peer": ("协议位置要对照同行成交和捕获率", "protocol seat needs peer tape and capture"),
        "gamefi_empty_fees": ("链还在，费用和磁带已经让给同行", "the chain is still there; fees and tape already left for peers"),
        "gamefi_thin_book": ("锁仓停在千万级，不能写成已经长出来的游戏经济", "lockup is still in the tens of millions; not a grown game economy"),
        "gamefi_peer": ("链游票要先对成交，再对费用", "game tickets: tape first, then fees"),
        "meme_tape_left": (
            f"市值还在，成交已经被 {hotter[0]['ticker']} 抢走" if hotter else "市值还在，成交已经偏弱",
            f"the cap remains; {hotter[0]['ticker']} already took the tape" if hotter else "the cap remains; the tape is already weak",
        ),
        "meme_liquid": ("流动性是真的，没有协议现金流", "liquidity is real; there is no protocol cash flow"),
    }
    return mapping.get(kind, ("对照数字之后再写位置", "write the seat after the prints"))


def heat_block(snap) -> tuple[str, str]:
    lunar = getattr(snap, "lunar", None) or {}
    x = getattr(snap, "x_mentions", None) or {}
    self_x = x.get("self") if isinstance(x, dict) else None
    btc_x = x.get("btc") if isinstance(x, dict) else None
    stale = bool(x.get("stale")) if isinstance(x, dict) else False
    bits_zh, bits_en = [], []
    if lunar.get("dominance") is not None:
        bits_zh.append(f"LunarCrush 社交主导率 **{lunar['dominance']:.2f}%**")
        bits_en.append(f"LunarCrush social dominance **{lunar['dominance']:.2f}%**")
        if lunar.get("sentiment") is not None:
            bits_zh[-1] += f"，情绪 **{lunar['sentiment']:.0f}%**"
            bits_en[-1] += f", sentiment **{lunar['sentiment']:.0f}%**"
        if lunar.get("posts"):
            bits_zh.append(f"24 小时约 **{lunar['posts']}** 帖")
            bits_en.append(f"about **{lunar['posts']}** posts in 24h")
    if self_x and self_x.get("mentions") is not None:
        line = f"AltIndex ${snap.ticker} 日均 cashtag 约 **{self_x['mentions']}** 次"
        line_en = f"AltIndex daily ${snap.ticker} cashtags about **{self_x['mentions']}**"
        if self_x.get("updated"):
            line += f"（更新 {self_x['updated']}）"
            line_en += f" (updated {self_x['updated']})"
        if stale:
            line += "。这组数过期，**不能**和当日比特币样本混比"
            line_en += ". This print is stale and **must not** be mixed with a same-day Bitcoin sample"
        elif btc_x and btc_x.get("mentions") and snap.ticker != "BTC" and not stale:
            line += f"。$BTC 同期约 **{btc_x['mentions']}** 次"
            line_en += f". $BTC is about **{btc_x['mentions']}** in the same series"
        bits_zh.append(line)
        bits_en.append(line_en)
    if not bits_zh:
        zh = f"公开页没有 ${snap.ticker} 的可核社交主导率或当日 cashtag。热度按未披露处理，不编帖数。热度对短线价格很重要，缺了就少一个维度，不能假装没有这个市场。"
        en = f"No checkable social dominance or same-day cashtag for ${snap.ticker}. Heat stays undisclosed; post counts are not invented. Heat moves the tape; a missing print is a missing dimension, not a reason to ignore the market."
        return zh, en
    zh = "。".join(bits_zh) + "。"
    en = ". ".join(bits_en) + "."
    if lunar.get("dominance") and snap.rank and snap.rank > 20 and lunar["dominance"] < 0.2:
        zh += "讨论量接近于零，30 日涨跌就不能写成「全网在看」。"
        en += " Chatter is near zero, so a 30-day bounce is not “the whole tape is watching.”"
    elif lunar.get("dominance") and lunar["dominance"] >= 8:
        zh += "社交份额已经很厚，短线价格里有注意力溢价，回落时也会更快。"
        en += " Social share is already thick: the tape has an attention premium, and it can fall faster too."
    else:
        zh += "热度是定价的一个维度，不折成现金流，但忽略它会看错短线。"
        en += " Heat is a pricing dimension. It does not discount into cash flow, but ignoring it misreads the short tape."
    return zh, en


def yaml_escape(text: str) -> str:
    return text.replace('"', '\\"')


def table(rows_zh, rows_en) -> tuple[str, str]:
    zh = ["| 指标 | 数值 | 口径 |", "| --- | --- | --- |"]
    en = ["| Metric | Value | Source |", "| --- | --- | --- |"]
    for a, b in zip(rows_zh, rows_en):
        zh.append(f"| {a[0]} | {a[1]} | {a[2]} |")
        en.append(f"| {b[0]} | {b[1]} | {b[2]} |")
    return "\n".join(zh), "\n".join(en)


def heading_pack(zh: str, en: str) -> dict[str, str]:
    return {
        "zh": zh,
        "en": en,
        "ja": zh if False else en,
        "ko": en,
        "fr": en,
        "es": en,
        "ru": en,
    }


SECTION_H = {
    "take": heading_pack("研究结论", "Research take"),
    "score": None,  # filled later
    "risk": heading_pack("主要风险", "Main risks"),
    "watch": heading_pack("跟踪清单", "What to track"),
    "src": heading_pack("数据来源", "Sources"),
    "disc": heading_pack("免责声明", "Disclaimer"),
}

JA_KO_FR = {
    "take": {"ja": "研究結論", "ko": "연구 결론", "fr": "Conclusion", "es": "Conclusión", "ru": "Вывод"},
    "snap": {"ja": "データスナップショット", "ko": "데이터 스냅샷", "fr": "Instantané", "es": "Instantánea", "ru": "Снимок"},
    "score": {"ja": "買いスコア", "ko": "매수 점수", "fr": "Score d’achat", "es": "Puntuación de compra", "ru": "Оценка покупки"},
    "risk": {"ja": "主なリスク", "ko": "주요 위험", "fr": "Principaux risques", "es": "Riesgos principales", "ru": "Главные риски"},
    "watch": {"ja": "ウォッチリスト", "ko": "추적 목록", "fr": "À suivre", "es": "Lista de seguimiento", "ru": "Что отслеживать"},
    "src": {"ja": "出典", "ko": "출처", "fr": "Sources", "es": "Fuentes", "ru": "Источники"},
    "disc": {"ja": "免責", "ko": "면책", "fr": "Avertissement", "es": "Aviso", "ru": "Отказ от ответственности"},
}


def localize_fixed(key: str, zh: str, en: str, extra: str = "") -> dict[str, str]:
    loc = JA_KO_FR.get(key, {})
    out = {"zh": zh + extra, "en": en + extra}
    for lang in ("ja", "ko", "fr", "es", "ru"):
        if key == "snap":
            out[lang] = f"{loc.get(lang, en)}{extra}"
        elif key == "score":
            out[lang] = f"{loc.get(lang, en)}{extra}"
        else:
            out[lang] = loc.get(lang, en)
    return out


def mech_titles(kind: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    catalog = {
        "l1_reserve": (
            ("储备层：市值第一买的不是锁仓", "Reserve: rank 1 is not the lockup"),
            ("成交层：美元和换手都不在这条链", "Tape: dollars and turnover are not on this chain"),
            ("X：讨论量仍是这个标的的行情", "X: chatter is still this tape"),
        ),
        "l1_settle_not_tape": (
            ("结算层：锁仓和美元还在这里", "Settlement: lockup and dollars still sit here"),
            ("成交层：忙的已经是别人", "Execution: someone else is busy"),
            ("X：热度跟不跟得上价格", "X: whether heat still matches the print"),
        ),
        "l1_tape_not_settle": (
            ("执行层：成交和费用已经领先", "Execution: volume and fees already lead"),
            ("结算层：锁仓和美元仍是零头", "Settlement: lockup and dollars are still a fraction"),
            ("X：社交份额比市值份额厚不厚", "X: whether social share is thicker than cap share"),
        ),
        "l1_peer": (
            ("同行对照：市值排序不是磁带排序", "Peers: cap rank is not tape rank"),
            ("链上：锁仓、稳定币和费用落在谁手里", "On-chain: who holds TVL, stables and fees"),
            ("X：互联网上的声音能不能解释这段涨跌", "X: whether internet heat explains the move"),
        ),
        "defi_thin_capture": (
            ("费用：池子很大，代币分到的很少", "Fees: a thick pool, a thin token slice"),
            ("同行：同一张桌上的市值和成交", "Peers: cap and tape on one table"),
            ("X：讨论是事件还是持续热度", "X: a pulse, or a heat step"),
        ),
        "defi_tvl_not_token": (
            ("锁仓：本账很厚，并不等于代币资产", "Lockup: a thick book is not the token’s asset"),
            ("捕获：费用留下多少给持有人", "Capture: how much of the fee stays with holders"),
            ("X：热度有没有给这张薄层加价", "X: whether heat is bidding up the thin slice"),
        ),
        "defi_peer": (
            ("协议对照：TVL、费用和成交", "Protocol tape: TVL, fees and volume"),
            ("代币：流通、硬顶和 30 日涨幅", "Token: float, cap and the 30-day move"),
            ("X：注意力在不在这张票上", "X: whether attention is on this ticket"),
        ),
        "gamefi_empty_fees": (
            ("磁带：同档票谁还在被交易", "Tape: who in the band is still traded"),
            ("链上：锁仓和费用是不是已经长出来", "On-chain: whether lockup and fees have grown"),
            ("X：游戏叙事有没有变成可核讨论", "X: whether the games story is checkable chatter"),
        ),
        "gamefi_thin_book": (
            ("锁仓：还停在哪个量级", "Lockup: which order of magnitude it still sits in"),
            ("同行成交：票好不好卖", "Peer tape: whether the ticket still sells"),
            ("X：圈子热度还是全网热度", "X: in-circle heat or a global tape"),
        ),
        "gamefi_peer": (
            ("成交对照：链游票先看磁带", "Tape first among game tickets"),
            ("费用与锁仓：有没有离开叙事", "Fees and lockup: whether they left the story"),
            ("X：讨论量能不能托住价格", "X: whether chatter can hold the print"),
        ),
        "meme_tape_left": (
            ("磁带：市值排序和成交排序已经错位", "Tape: cap rank and volume rank already split"),
            ("供应：有没有硬顶，增发谁来吸收", "Supply: hard cap or not, and who eats issuance"),
            ("X：热度是不是已经去了别的迷因", "X: whether heat already left for another meme"),
        ),
        "meme_liquid": (
            ("流动性：能买进卖出，不等于能持有", "Liquidity: tradable is not holdable"),
            ("现金流：框架不能作弊", "Cash flow: the frame cannot cheat"),
            ("X：注意力是不是唯一的基本面", "X: whether attention is the only fundamental"),
        ),
    }
    a, b, c = catalog.get(kind, catalog["l1_peer"])

    def pack(pair):
        zh, en = pair
        return {"zh": zh, "en": en, "ja": en, "ko": en, "fr": en, "es": en, "ru": en}

    return pack(a), pack(b), pack(c)


def take_paragraphs(snap, kind: str, score: float) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str]]:
    v_zh, v_en = verdict(score)
    peers = snap.peers or []
    hotter = [p for p in peers if p.get("volume") and snap.volume and p["volume"] > snap.volume]
    self_t = turn(snap.volume, snap.mcap)
    from_ath = None
    if snap.price and snap.ath:
        from_ath = 100 * (snap.price / snap.ath - 1)
    lead = None
    if snap.dexs:
        lead = max(snap.dexs, key=lambda r: r.get("vol_30d") or 0)
    capture = None
    if snap.fees_30d and snap.rev_30d is not None and snap.fees_30d > 0:
        capture = 100 * snap.rev_30d / snap.fees_30d
    peer_zh = "；".join(
        f"{p['ticker']} 市值 {fmt_usd(p.get('mcap'))}、成交 {fmt_usd(p.get('volume'))}" for p in peers[:3]
    )
    peer_en = "; ".join(
        f"{p['ticker']} cap {fmt_usd(p.get('mcap'))}, volume {fmt_usd(p.get('volume'))}" for p in peers[:3]
    )

    p1 = {
        "l1_reserve": (
            f"{snap.name} 的市值 {fmt_usd(snap.mcap)} 和链上锁仓 {fmt_usd(snap.tvl)} 不是同一本账。"
            f"买 {snap.ticker} 买的是储备、硬顶和流动性，不是 {fmt_usd(snap.tvl)} 的存款。"
            + (f"近 30 日 DEX 龙头是 {lead['name']}（{fmt_usd(lead.get('vol_30d'))}），不在这条链。" if lead else ""),
            f"{snap.name} cap {fmt_usd(snap.mcap)} and lockup {fmt_usd(snap.tvl)} are not the same book. "
            f"Buying {snap.ticker} is reserve, a hard cap and liquidity, not {fmt_usd(snap.tvl)} of deposits."
            + (f" 30-day DEX lead is {lead['name']} ({fmt_usd(lead.get('vol_30d'))}), not this chain." if lead else ""),
        ),
        "l1_settle_not_tape": (
            f"结算账还在 {snap.name}：锁仓 {fmt_usd(snap.tvl)}"
            + (f"，稳定币 {fmt_usd(snap.stables)}" if snap.stables is not None else "")
            + "。"
            + (f"成交账已经不在：近 30 日 DEX 龙头是 {lead['name']}（{fmt_usd(lead.get('vol_30d'))}）。" if lead else "")
            + f"市值 {fmt_usd(snap.mcap)} 买的是停美元的位置，不是全网最忙的执行层。",
            f"The settlement book is still {snap.name}: TVL {fmt_usd(snap.tvl)}"
            + (f", stables {fmt_usd(snap.stables)}" if snap.stables is not None else "")
            + ". "
            + (f"The execution book is not: 30-day DEX lead is {lead['name']} ({fmt_usd(lead.get('vol_30d'))}). " if lead else "")
            + f"Cap {fmt_usd(snap.mcap)} buys parked dollars, not the busiest venue.",
        ),
        "l1_tape_not_settle": (
            f"{snap.name} 已经拿走成交：近 30 日 DEX 龙头是它自己"
            + (f"（{fmt_usd(lead.get('vol_30d'))}）" if lead else "")
            + f"。结算仍薄：锁仓 {fmt_usd(snap.tvl)}"
            + (f"，稳定币 {fmt_usd(snap.stables)}" if snap.stables is not None else "")
            + f"。买 {snap.ticker} 买的是换手，不是停美元。",
            f"{snap.name} already took the tape"
            + (f" ({fmt_usd(lead.get('vol_30d'))} over 30 days)" if lead else "")
            + f". Settlement is still thin: TVL {fmt_usd(snap.tvl)}"
            + (f", stables {fmt_usd(snap.stables)}" if snap.stables is not None else "")
            + f". Buying {snap.ticker} is turnover, not parked dollars.",
        ),
        "l1_peer": (
            f"{snap.name} 市值 {fmt_usd(snap.mcap)}"
            + (f"，排名第 {snap.rank}" if snap.rank else "")
            + f"，24 小时成交 {fmt_usd(snap.volume)}。"
            + (f"对照：{peer_zh}。" if peer_zh else "")
            + "市值排序、成交排序和锁仓排序可能是三件事，必须拆开再写位置。",
            f"{snap.name} cap {fmt_usd(snap.mcap)}"
            + (f", rank {snap.rank}" if snap.rank else "")
            + f", 24h volume {fmt_usd(snap.volume)}. "
            + (f"Peers: {peer_en}. " if peer_en else "")
            + "Cap rank, tape rank and lockup rank can be three different seats.",
        ),
        "defi_thin_capture": (
            f"{snap.name} 的费用池是真的：近 30 日费用 {fmt_usd(snap.fees_30d)}"
            + (f"，协议收入 {fmt_usd(snap.rev_30d)}，捕获约 {capture:.1f}%。" if capture is not None else "。")
            + f"市值 {fmt_usd(snap.mcap)} 买的是治理和尚未加厚的分成，不是已经入袋的分红。",
            f"{snap.name} has a real fee pool: 30-day fees {fmt_usd(snap.fees_30d)}"
            + (f", revenue {fmt_usd(snap.rev_30d)}, capture about {capture:.1f}%." if capture is not None else ".")
            + f" Cap {fmt_usd(snap.mcap)} buys governance and an unthickened split, not cash already in the pocket.",
        ),
        "defi_tvl_not_token": (
            f"{snap.tvl_label or 'TVL'} {fmt_usd(snap.tvl)}，市值只有 {fmt_usd(snap.mcap)}。"
            "这个倍数看起来极便宜，是因为锁仓往往是别人的抵押品，不是代币持有人的资产。"
            + (f"近 30 日费用 {fmt_usd(snap.fees_30d)}，收入 {fmt_usd(snap.rev_30d)}。" if snap.fees_30d else ""),
            f"{snap.tvl_label or 'TVL'} {fmt_usd(snap.tvl)} against a {fmt_usd(snap.mcap)} cap. "
            "The multiple looks cheap because the lockup is usually someone else’s collateral, not the token’s asset. "
            + (f"30-day fees {fmt_usd(snap.fees_30d)}, revenue {fmt_usd(snap.rev_30d)}." if snap.fees_30d else ""),
        ),
        "defi_peer": (
            f"{snap.name} 市值 {fmt_usd(snap.mcap)}，成交 {fmt_usd(snap.volume)}。"
            + (f"对照：{peer_zh}。" if peer_zh else "")
            + (f"{snap.tvl_label} {fmt_usd(snap.tvl)}。" if snap.tvl else "")
            + "协议位置只认能核的费用和锁仓，不认叙事。",
            f"{snap.name} cap {fmt_usd(snap.mcap)}, volume {fmt_usd(snap.volume)}. "
            + (f"Peers: {peer_en}. " if peer_en else "")
            + (f"{snap.tvl_label} {fmt_usd(snap.tvl)}. " if snap.tvl else "")
            + "The protocol seat is sourced fees and lockup, not a story.",
        ),
        "gamefi_empty_fees": (
            f"{snap.name} 还有能核的链/锁仓 {fmt_usd(snap.tvl)}，但近 30 日费用 {fmt_usd(snap.fees_30d) if snap.fees_30d is not None else '未披露'}。"
            + (f"同档成交已经被 {hotter[0]['ticker']} 抢走。" if hotter else "")
            + f"市值 {fmt_usd(snap.mcap)} 仍是一张 GameFi 票，不是现金牛。",
            f"{snap.name} still has a checkable chain/lockup {fmt_usd(snap.tvl)}, but 30-day fees "
            f"{fmt_usd(snap.fees_30d) if snap.fees_30d is not None else 'are undisclosed'}. "
            + (f"{hotter[0]['ticker']} already took the tape in-band. " if hotter else "")
            + f"Cap {fmt_usd(snap.mcap)} is still a GameFi ticket, not a cash cow.",
        ),
        "gamefi_thin_book": (
            f"{snap.name} 锁仓 {fmt_usd(snap.tvl)}，市值 {fmt_usd(snap.mcap)}。"
            "千万美元量级的锁仓说明产品还在，不说明游戏经济已经长出来。"
            + (f"对照：{peer_zh}。" if peer_zh else ""),
            f"{snap.name} lockup {fmt_usd(snap.tvl)}, cap {fmt_usd(snap.mcap)}. "
            "Tens of millions of TVL means the product exists, not that a game economy has grown. "
            + (f"Peers: {peer_en}." if peer_en else ""),
        ),
        "gamefi_peer": (
            f"{snap.name} 市值 {fmt_usd(snap.mcap)}，成交 {fmt_usd(snap.volume)}。"
            + (f"对照：{peer_zh}。" if peer_zh else "")
            + "链游票先看谁还在被交易，再看费用有没有离开叙事。",
            f"{snap.name} cap {fmt_usd(snap.mcap)}, volume {fmt_usd(snap.volume)}. "
            + (f"Peers: {peer_en}. " if peer_en else "")
            + "Game tickets: who is still traded, then whether fees left the story.",
        ),
        "meme_tape_left": (
            f"{snap.name} 市值 {fmt_usd(snap.mcap)} 还在，24 小时成交 {fmt_usd(snap.volume)}"
            + (f"，换手约 {self_t:.1f}%" if self_t is not None else "")
            + "。"
            + (f"对照：{peer_zh}。成交已经被抢走，市值第二档也可以是磁带第三档。" if hotter else f"对照：{peer_zh}。"),
            f"{snap.name} still has cap {fmt_usd(snap.mcap)} and 24h volume {fmt_usd(snap.volume)}"
            + (f", turnover about {self_t:.1f}%" if self_t is not None else "")
            + ". "
            + (f"Peers: {peer_en}. The tape already left; a second-tier cap can be a third-tier book." if hotter else f"Peers: {peer_en}."),
        ),
        "meme_liquid": (
            f"{snap.name} 的质量几乎全部来自流动性和品牌：市值 {fmt_usd(snap.mcap)}，成交 {fmt_usd(snap.volume)}。"
            "没有协议收入科目。迷因可以交易，不能用现金流框架去抬分。",
            f"{snap.name} quality is almost all liquidity and brand: cap {fmt_usd(snap.mcap)}, volume {fmt_usd(snap.volume)}. "
            "There is no protocol-revenue line. Memes are tradable; they do not get a cash-flow lift.",
        ),
    }.get(kind, (
        f"{snap.name} 价格 {fmt_usd(snap.price)}，市值 {fmt_usd(snap.mcap)}。"
        + (f"对照：{peer_zh}。" if peer_zh else "")
        + "下面按成交、锁仓、费用和热度拆开写，不复述一行快照。",
        f"{snap.name} is {fmt_usd(snap.price)} with cap {fmt_usd(snap.mcap)}. "
        + (f"Peers: {peer_en}. " if peer_en else "")
        + "Split tape, lockup, fees and heat below; do not restate one snapshot row.",
    ))

    p2_zh = (
        f"价格 {fmt_usd(snap.price)}"
        + (f"，较 ATH {fmt_usd(snap.ath)}（{snap.ath_date}）约 {from_ath:.0f}%" if from_ath is not None else "")
        + f"。7 日 {fmt_pct(snap.chg_7d)}，30 日 {fmt_pct(snap.chg_30d)}。"
    )
    p2_en = (
        f"Price {fmt_usd(snap.price)}"
        + (f", about {from_ath:.0f}% vs ATH {fmt_usd(snap.ath)} ({snap.ath_date})" if from_ath is not None else "")
        + f". 7d {fmt_pct(snap.chg_7d)}, 30d {fmt_pct(snap.chg_30d)}."
    )
    if snap.chg_30d and snap.chg_30d > 20 and snap.chg_7d is not None and snap.chg_7d < 5:
        p2_zh += "反弹的大头已经走过，剩下的不是「还能不能再涨一轮叙事」，是热度和费用还在不在。"
        p2_en += " The easy leg of the bounce is done. What is left is whether heat and fees are still there."
    heat_zh, heat_en = heat_block(snap)
    p2_zh += heat_zh
    p2_en += " " + heat_en

    p3_zh = f"**买入评分 {score:.1f} / 10（{v_zh}）。** 分数跟的是这一个标的的位置：成交、锁仓、费用和互联网热度拆开之后的结果。不是买卖指令。"
    p3_en = f"**Buy score {score:.1f} / 10 ({v_en}).** The score is this ticket’s seat after tape, lockup, fees and internet heat are split. Not a trade order."
    return p1, (p2_zh, p2_en), (p3_zh, p3_en)


def mech_paragraphs(snap, kind: str) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str], tuple[str, str]]:
    peers = snap.peers or []
    hotter = [p for p in peers if p.get("volume") and snap.volume and p["volume"] > snap.volume]
    self_t = turn(snap.volume, snap.mcap)
    lead = max(snap.dexs, key=lambda r: r.get("vol_30d") or 0) if snap.dexs else None
    capture = None
    if snap.fees_30d and snap.rev_30d is not None and snap.fees_30d > 0:
        capture = 100 * snap.rev_30d / snap.fees_30d
    peer_zh = "；".join(
        f"{p['ticker']} {fmt_usd(p.get('mcap'))} / {fmt_usd(p.get('volume'))}"
        + (f"（换手约 {turn(p.get('volume'), p.get('mcap')):.1f}%）" if turn(p.get("volume"), p.get("mcap")) else "")
        for p in peers[:4]
    )
    peer_en = "; ".join(
        f"{p['ticker']} {fmt_usd(p.get('mcap'))} / {fmt_usd(p.get('volume'))}"
        + (f" (turnover ~{turn(p.get('volume'), p.get('mcap')):.1f}%)" if turn(p.get("volume"), p.get("mcap")) else "")
        for p in peers[:4]
    )
    chain_zh = "，".join(f"{c.get('name')} {fmt_usd(c.get('tvl'))}" for c in (snap.chains or [])[:5])
    chain_en = ", ".join(f"{c.get('name')} {fmt_usd(c.get('tvl'))}" for c in (snap.chains or [])[:5])
    dex_zh = "，".join(f"{d.get('name')} {fmt_usd(d.get('vol_30d'))}" for d in (snap.dexs or []))
    dex_en = ", ".join(f"{d.get('name')} {fmt_usd(d.get('vol_30d'))}" for d in (snap.dexs or []))

    a1 = (
        f"{snap.ticker} 市值 {fmt_usd(snap.mcap)}，24 小时成交 {fmt_usd(snap.volume)}"
        + (f"，换手约 {self_t:.1f}%。" if self_t is not None else "。")
        + (f"对照：{peer_zh}。" if peer_zh else "")
        + (f"成交已经被 {hotter[0]['ticker']} 抢走，市值排序不能当成磁带排序。" if hotter else "同桌里它还不是最冷的，但排序要以成交为准。"),
        f"{snap.ticker} cap {fmt_usd(snap.mcap)}, 24h volume {fmt_usd(snap.volume)}"
        + (f", turnover about {self_t:.1f}%." if self_t is not None else ".")
        + (f" Peers: {peer_en}." if peer_en else "")
        + (f" {hotter[0]['ticker']} already took the tape — cap rank is not tape rank." if hotter else " Not the coldest seat at the table; rank still follows the tape."),
    )
    if kind.startswith("l1") and (chain_zh or dex_zh):
        a1 = (
            (f"公链 TVL：{chain_zh}。" if chain_zh else "")
            + (f"近 30 日 DEX：{dex_zh}。" if dex_zh else "")
            + (f"{snap.name} 锁仓 {fmt_usd(snap.tvl)}。" if snap.tvl else "")
            + (f"稳定币 {fmt_usd(snap.stables)}。" if snap.stables is not None else "")
            + ("谁在停美元、谁在换手，要看这两列，不看市值一行。" if chain_zh or dex_zh else ""),
            (f"Chain TVL: {chain_en}. " if chain_en else "")
            + (f"30-day DEX: {dex_en}. " if dex_en else "")
            + (f"{snap.name} lockup {fmt_usd(snap.tvl)}. " if snap.tvl else "")
            + (f"Stables {fmt_usd(snap.stables)}. " if snap.stables is not None else "")
            + ("Who parks dollars and who turns tickets is in these columns, not the cap row." if chain_en or dex_en else ""),
        )
    if kind.startswith("defi") and snap.fees_30d is not None:
        a1 = (
            f"近 30 日费用 {fmt_usd(snap.fees_30d)}"
            + (f"，协议收入 {fmt_usd(snap.rev_30d)}" if snap.rev_30d is not None else "")
            + (f"，捕获约 {capture:.1f}%。" if capture is not None else "。")
            + (f"{snap.tvl_label} {fmt_usd(snap.tvl)}。" if snap.tvl else "")
            + "费用大部分通常付给流动性提供者；代币拿到的是治理和尚未稳定的分成。",
            f"30-day fees {fmt_usd(snap.fees_30d)}"
            + (f", revenue {fmt_usd(snap.rev_30d)}" if snap.rev_30d is not None else "")
            + (f", capture about {capture:.1f}%." if capture is not None else ".")
            + (f" {snap.tvl_label} {fmt_usd(snap.tvl)}." if snap.tvl else "")
            + " Fees usually go to LPs; the token gets governance and an unstable split.",
        )

    a2 = (
        f"30 日币价 {fmt_pct(snap.chg_30d)} 只当风险偏好。谁把涨幅直接加成基本面，需要先看到成交或费用同步变厚。",
        f"The 30-day {fmt_pct(snap.chg_30d)} is risk appetite. Anyone adding it straight onto fundamentals needs the tape or the fees to thicken with it.",
    )

    if snap.max_supply and snap.circ:
        b1 = (
            f"上限 {fmt_qty(snap.max_supply)}，流通 {fmt_qty(snap.circ)}，占比约 {100 * snap.circ / snap.max_supply:.0f}%。"
            "有硬顶只说明稀释上限可核对，不说明现在便宜。",
            f"Max {fmt_qty(snap.max_supply)}, circulating {fmt_qty(snap.circ)}, about {100 * snap.circ / snap.max_supply:.0f}% float. "
            "A hard cap makes the dilution ceiling checkable. It does not make the print cheap.",
        )
    else:
        b1 = (
            f"CoinGecko 未给出硬顶。流通 {fmt_qty(snap.circ)}，总量 {fmt_qty(snap.total)}。没有上限时，长期稀释是默认风险。",
            f"CoinGecko lists no hard cap. Circulating {fmt_qty(snap.circ)}, total {fmt_qty(snap.total)}. "
            "With no ceiling, long-run dilution is the default risk.",
        )
    if kind.startswith("l1") and lead:
        b1 = (
            f"近 30 日 DEX 龙头 {lead['name']} {fmt_usd(lead.get('vol_30d'))}。"
            + (f"{snap.name} 锁仓 {fmt_usd(snap.tvl)}。" if snap.tvl else "")
            + (f"稳定币 {fmt_usd(snap.stables)}。" if snap.stables is not None else "")
            + (f"近 30 日费用 {fmt_usd(snap.fees_30d)}，收入 {fmt_usd(snap.rev_30d)}。" if snap.fees_30d is not None else "")
            + "成交第一不等于结算第一，锁仓第一也不等于费用第一。",
            f"30-day DEX lead {lead['name']} {fmt_usd(lead.get('vol_30d'))}. "
            + (f"{snap.name} lockup {fmt_usd(snap.tvl)}. " if snap.tvl else "")
            + (f"Stables {fmt_usd(snap.stables)}. " if snap.stables is not None else "")
            + (f"30-day fees {fmt_usd(snap.fees_30d)}, revenue {fmt_usd(snap.rev_30d)}. " if snap.fees_30d is not None else "")
            + "Tape first is not settlement first, and lockup first is not fee first.",
        )
    if kind.startswith("gamefi"):
        b1 = (
            (f"能核的锁仓是 {fmt_usd(snap.tvl)}（{snap.tvl_label}）。" if snap.tvl else "本次没有可核协议 TVL。")
            + (f"近 30 日费用 {fmt_usd(snap.fees_30d)}。" if snap.fees_30d is not None else "没有费用口径，就不写成已经产品化的现金牛。")
            + (f"对照：{peer_zh}。" if peer_zh else ""),
            (f"Sourced lockup is {fmt_usd(snap.tvl)} ({snap.tvl_label}). " if snap.tvl else "No sourced protocol TVL. ")
            + (f"30-day fees {fmt_usd(snap.fees_30d)}. " if snap.fees_30d is not None else "No fee print, so this is not a cash-cow write-up. ")
            + (f"Peers: {peer_en}." if peer_en else ""),
        )
    if kind.startswith("meme"):
        b1 = (
            (f"{snap.tvl_label} {fmt_usd(snap.tvl)}。" if snap.tvl else "没有可核的协议 TVL。")
            + "迷因的链上部分只承认锁仓和费用；转账话题如果不成费用，就只是声音。声音要写，但不能冒充收入。",
            (f"{snap.tvl_label} {fmt_usd(snap.tvl)}. " if snap.tvl else "No sourced protocol TVL. ")
            + "On-chain, only TVL and fees count. Chatter that does not become a fee is still a voice — write it, do not book it as income.",
        )

    b2 = (
        "研究判断：这一节只回答「钱停在哪 / 费用留给谁」，不回答明天涨跌。",
        "Take: this section answers where the money sits and who keeps the fee, not tomorrow’s print.",
    )
    h1, h2 = heat_block(snap)
    heat2_zh = "研究判断：热度对币价是真维度。没有序列就写未披露；有序列就要拿来对照市值和成交，不能因为「不是基本面」就删掉。"
    heat2_en = "Take: heat is a real pricing dimension. No series stays undisclosed. A series must be sat next to cap and volume — do not delete it because it is “not fundamental.”"
    return a1, a2, b1, (h1 + heat2_zh, h2 + " " + heat2_en)


def risks_and_watch(snap, kind: str) -> tuple[list[str], list[str], list[str], list[str]]:
    risks_zh = [
        f"**价格波动：** 24 小时成交 {fmt_usd(snap.volume)}，短线可以大过任何评分。",
        f"**快照时效：** 数字只对 {snap.as_of} 负责。",
    ]
    risks_en = [
        f"**Volatility:** 24h volume {fmt_usd(snap.volume)}; a tape can move more than any score.",
        f"**Stale prints:** Figures are only good as of {snap.as_of}.",
    ]
    if kind.startswith("meme"):
        risks_zh.insert(0, "**没有协议现金流：** 注意力可以交易，不能折成持有人收入。")
        risks_en.insert(0, "**No protocol cash flow:** Attention is tradable; it does not become holder income.")
    if kind in {"defi_thin_capture", "defi_tvl_not_token"}:
        risks_zh.insert(0, "**捕获层过薄：** 费用池再厚，也不自动等于代币现金流。")
        risks_en.insert(0, "**Thin capture:** A fat fee pool is not automatically token cash flow.")
    if kind.startswith("l1_tape"):
        risks_zh.insert(0, "**结算跟不上成交：** 执行溢价可以在一周内被拆掉。")
        risks_en.insert(0, "**Settlement does not follow tape:** an execution premium can be taken apart in a week.")
    if kind.startswith("l1_settle"):
        risks_zh.insert(0, "**成交持续外流：** 结算溢价会被重新定价。")
        risks_en.insert(0, "**Flow keeps leaving:** the settlement premium gets repriced.")
    if not snap.max_supply:
        risks_zh.append("**无硬顶：** 长期持有人份额会被持续摊薄。")
        risks_en.append("**No hard cap:** long-term holders keep getting diluted.")
    if snap.max_supply and snap.circ and snap.circ / snap.max_supply < 0.55:
        risks_zh.append(f"**解锁厚度：** 流通约 {100 * snap.circ / snap.max_supply:.0f}%，剩余供给仍厚。")
        risks_en.append(f"**Unlock thickness:** about {100 * snap.circ / snap.max_supply:.0f}% circulating; leftover supply is still thick.")
    lunar = getattr(snap, "lunar", None) or {}
    if lunar.get("dominance") and lunar["dominance"] >= 8:
        risks_zh.append("**社交热度透支：** 讨论比基本面厚，回落时跌得也会快。")
        risks_en.append("**Social heat prepaid:** discussion is thicker than the book; it can fall faster too.")
    if getattr(snap, "x_mentions", None) and snap.x_mentions.get("stale"):
        risks_zh.append("**过期 cashtag：** 旧的 AltIndex 不能当今日热度。")
        risks_en.append("**Stale cashtag:** an old AltIndex print is not today’s heat.")
    while len(risks_zh) < 5:
        risks_zh.append("**口径不要混用：** 市值、TVL、费用、收入、热度各算各的。")
        risks_en.append("**Do not mix ledgers:** cap, TVL, fees, revenue and heat each get their own column.")
    risks_zh, risks_en = risks_zh[:5], risks_en[:5]

    watch_zh = [
        "24 小时成交与换手是否还撑得住当前流动性假设。",
        "流通量、总量与上限（如有）有没有突然跳变。",
    ]
    watch_en = [
        "Whether 24h volume and turnover still support the liquidity seat.",
        "Whether circulating, total and max supply (if any) jump.",
    ]
    if snap.tvl:
        watch_zh.append(f"{snap.tvl_label} 是回升、横盘还是失血。")
        watch_en.append(f"Whether {snap.tvl_label} is rising, flat or bleeding.")
    if snap.fees_30d is not None:
        watch_zh.append("近 30 日费用与捕获率有没有离开本次快照。")
        watch_en.append("Whether 30-day fees and capture leave this snapshot.")
    watch_zh.append("LunarCrush 主导率或 AltIndex cashtag 是否还在、是否过期、是否和成交同向。")
    watch_en.append("Whether LunarCrush dominance or AltIndex cashtags are still live, stale, or move with the tape.")
    if snap.peers:
        watch_zh.append("同桌成交比有没有反转（谁抢走磁带）。")
        watch_en.append("Whether in-band volume ratios flip (who takes the tape).")
    watch_zh, watch_en = watch_zh[:5], watch_en[:5]
    return risks_zh, risks_en, watch_zh, watch_en


def draft_note(snap, score: float, dims, day: str) -> dict:
    kind = detect_kind(snap)
    take_zh, take_en = title_pair(snap, kind)
    v_zh, v_en = verdict(score)
    titles = {
        "zh": f"{snap.ticker} 研究简报：{take_zh}",
        "en": f"{snap.ticker} research note: {take_en}",
        "ja": f"{snap.ticker}リサーチノート：{take_en}",
        "ko": f"{snap.ticker} 리서치 노트: {take_en}",
        "fr": f"Note {snap.ticker} : {take_en}",
        "es": f"Nota {snap.ticker}: {take_en}",
        "ru": f"Записка по {snap.ticker}: {take_en}",
    }
    p1, p2, p3 = take_paragraphs(snap, kind, score)
    h_zh, h_en = heat_block(snap)
    desc = {
        "zh": (
            f"截至 {snap.as_of}，{snap.ticker} 约 {fmt_usd(snap.price)}、流通市值 {fmt_usd(snap.mcap)}"
            + (f"，排名第 {snap.rank}" if snap.rank else "")
            + (f"。{snap.tvl_label} {fmt_usd(snap.tvl)}" if snap.tvl else "")
            + f"。买入评分 {score:.1f}/10，{v_zh}。"
        ),
        "en": (
            f"As of {snap.as_of}, {snap.ticker} is about {fmt_usd(snap.price)} with circulating mcap {fmt_usd(snap.mcap)}"
            + (f", rank {snap.rank}" if snap.rank else "")
            + (f"; {snap.tvl_label} {fmt_usd(snap.tvl)}" if snap.tvl else "")
            + f". Buy score {score:.1f}/10, {v_en}."
        ),
    }
    conclusions = {"zh": p1[0] + p3[0].replace("**", ""), "en": p1[1] + " " + p3[1].replace("**", "")}

    from_ath = None
    if snap.price and snap.ath and snap.ath > 0:
        from_ath = 100 * (snap.price / snap.ath - 1)
    mcap_tvl = (snap.mcap / snap.tvl) if snap.mcap and snap.tvl else None
    capture = None
    if snap.fees_30d and snap.rev_30d is not None and snap.fees_30d > 0:
        capture = 100 * snap.rev_30d / snap.fees_30d
    self_t = turn(snap.volume, snap.mcap)
    rows_zh = [
        (f"{snap.ticker} 价格", fmt_usd(snap.price), "CoinGecko"),
        ("流通市值 / FDV", f"{fmt_usd(snap.mcap)} / {fmt_usd(snap.fdv)}", "CoinGecko"),
        ("流通 / 总量 / 上限", f"{fmt_qty(snap.circ)} / {fmt_qty(snap.total)} / {fmt_qty(snap.max_supply)}", "CoinGecko"),
        ("市值排名", str(snap.rank) if snap.rank else "未披露", "CoinGecko"),
        ("距 ATH", f"{fmt_usd(snap.ath)}" + (f"（{snap.ath_date}），{from_ath:.0f}%" if from_ath is not None else ""), "CoinGecko"),
        ("7 日 / 30 日涨跌", f"{fmt_pct(snap.chg_7d)} / {fmt_pct(snap.chg_30d)}", "CoinGecko"),
        ("24h 成交 / 换手", f"{fmt_usd(snap.volume)}" + (f" / ≈ {self_t:.1f}%" if self_t is not None else ""), "CoinGecko"),
    ]
    rows_en = [
        (f"{snap.ticker} price", fmt_usd(snap.price), "CoinGecko"),
        ("Circulating mcap / FDV", f"{fmt_usd(snap.mcap)} / {fmt_usd(snap.fdv)}", "CoinGecko"),
        ("Circ / total / max", f"{fmt_qty(snap.circ)} / {fmt_qty(snap.total)} / {fmt_qty(snap.max_supply)}", "CoinGecko"),
        ("Market-cap rank", str(snap.rank) if snap.rank else "undisclosed", "CoinGecko"),
        ("Vs ATH", f"{fmt_usd(snap.ath)}" + (f" ({snap.ath_date}), {from_ath:.0f}%" if from_ath is not None else ""), "CoinGecko"),
        ("7d / 30d", f"{fmt_pct(snap.chg_7d)} / {fmt_pct(snap.chg_30d)}", "CoinGecko"),
        ("24h volume / turnover", f"{fmt_usd(snap.volume)}" + (f" / ≈ {self_t:.1f}%" if self_t is not None else ""), "CoinGecko"),
    ]
    if snap.tvl:
        rows_zh.append((snap.tvl_label or "TVL", fmt_usd(snap.tvl), "DefiLlama"))
        rows_en.append((snap.tvl_label or "TVL", fmt_usd(snap.tvl), "DefiLlama"))
    if mcap_tvl is not None:
        rows_zh.append(("市值 / TVL", f"≈ {mcap_tvl:.2f}×", "计算"))
        rows_en.append(("Mcap / TVL", f"≈ {mcap_tvl:.2f}×", "calculated"))
    if snap.fees_30d is not None:
        rows_zh.append(("近 30 日费用", fmt_usd(snap.fees_30d), "DefiLlama fees"))
        rows_en.append(("30-day fees", fmt_usd(snap.fees_30d), "DefiLlama fees"))
    if snap.rev_30d is not None:
        rows_zh.append(("近 30 日协议收入", fmt_usd(snap.rev_30d), "DefiLlama revenue"))
        rows_en.append(("30-day protocol revenue", fmt_usd(snap.rev_30d), "DefiLlama revenue"))
    if capture is not None:
        rows_zh.append(("费用捕获率", f"≈ {capture:.1f}%", "收入 / 费用"))
        rows_en.append(("Fee capture", f"≈ {capture:.1f}%", "revenue / fees"))
    lunar = getattr(snap, "lunar", None) or {}
    if lunar.get("dominance") is not None:
        rows_zh.append(("LunarCrush 社交主导率", f"{lunar['dominance']:.2f}%", "LunarCrush"))
        rows_en.append(("LunarCrush social dominance", f"{lunar['dominance']:.2f}%", "LunarCrush"))
    tbl_zh, tbl_en = table(rows_zh, rows_en)

    score_zh = ["| 维度 | 权重 | 单项 | 加权 | 要点 |", "| --- | ---: | ---: | ---: | --- |"]
    score_en = ["| Factor | Weight | Score | Weighted | Note |", "| --- | ---: | ---: | ---: | --- |"]
    weighted_sum = 0.0
    for zh_n, en_n, weight, value, zh_note, en_note in dims:
        w = weight * value
        weighted_sum += w
        score_zh.append(f"| {zh_n} | {weight:.0%} | {value:.1f} | {w:.2f} | {zh_note} |")
        score_en.append(f"| {en_n} | {weight:.0%} | {value:.1f} | {w:.2f} | {en_note} |")
    score_zh.append(f"| **合计** | **100%** | | **{weighted_sum:.2f}** | **{v_zh}** |")
    score_en.append(f"| **Total** | **100%** | | **{weighted_sum:.2f}** | **{v_en}** |")

    a1, a2, b1, heat = mech_paragraphs(snap, kind)
    t1, t2, t3 = mech_titles(kind)
    risks_zh, risks_en, watch_zh, watch_en = risks_and_watch(snap, kind)
    src_items = list(dict.fromkeys(snap.sources or ["CoinGecko"]))
    src_zh = "\n".join(f"- {s}" for s in src_items) + f"\n- 快照 {snap.as_of}"
    src_en = "\n".join(f"- {s}" for s in src_items) + f"\n- as-of {snap.as_of}"
    disc_zh = (
        f"本报告由 DRLabs 撰写，仅供研究与信息交流，**不构成投资建议、财务建议、法律建议，亦不构成任何证券或加密资产的要约或要约邀请**。"
        f"加密资产价格波动剧烈，可能造成部分或全部本金损失。文中买入评分 {score:.1f}/10 是基于公开数据的主观评估，不是评级机构结论。"
        "完整条款见[关于 DRLabs](../../about.html#disclaimer)。"
    )
    disc_en = (
        f"Written by DRLabs for research and discussion. **Not investment, financial or legal advice, and not an offer.** "
        f"Crypto can cause partial or total loss. The {score:.1f}/10 buy score is a subjective reading of public data. "
        "Full terms: [About DRLabs](../../about.html#disclaimer)."
    )
    score_note_zh = f"{score:.1f} 跟的是这一篇的对照，不是套用赛道底分。成交、费用和互联网热度会拉单项。"
    score_note_en = f"{score:.1f} follows this note’s ledger, not a lane floor. Tape, fees and internet heat move the line items."

    snap_h = localize_fixed("snap", f"数据快照（{day}）", f"Snapshot ({day})")
    score_h = localize_fixed("score", f"买入评分 {score:.1f} / 10", f"Buy score {score:.1f} / 10")
    take_h = localize_fixed("take", "研究结论", "Research take")
    risk_h = localize_fixed("risk", "主要风险", "Main risks")
    watch_h = localize_fixed("watch", "跟踪清单", "What to track")
    src_h = localize_fixed("src", "数据来源", "Sources")
    disc_h = localize_fixed("disc", "免责声明", "Disclaimer")

    def fm(lang: str) -> str:
        extra = f"asOf: \"{snap.as_of}\"\n" if lang == "zh" else ""
        tags = "\n".join(f"  - {tag}" for tag in snap.tags)
        return (
            "---\n"
            f"title: \"{yaml_escape(titles.get(lang) or titles['en'])}\"\n"
            f"description: \"{yaml_escape(desc.get(lang) or desc['en'])}\"\n"
            f"date: {day}\n{extra}"
            f"ticker: {snap.ticker}\n"
            f"score: {score:.1f}\n"
            f"tags:\n{tags}\n"
            f"conclusion: \"{yaml_escape(conclusions.get(lang) or conclusions['en'])}\"\n"
            "---\n\n"
        )

    def body(lang: str) -> str:
        zh = lang == "zh"
        def pair(p):
            return p[0] if zh else p[1]
        risk = risks_zh if zh else risks_en
        watch = watch_zh if zh else watch_en
        return (
            f"## {take_h[lang]}\n\n{pair(p1)}\n\n{pair(p2)}\n\n{pair(p3)}\n\n"
            f"## {snap_h[lang]}\n\n{(tbl_zh if zh else tbl_en)}\n\n"
            f"{'快照 ' + snap.as_of + '。没有来源的格子不填。' if zh else 'As-of ' + snap.as_of + '. Empty cells stay empty.'}\n\n"
            f"## {t1[lang]}\n\n{pair(a1)}\n\n{pair(a2)}\n\n"
            f"## {t2[lang]}\n\n{pair(b1)}\n\n"
            f"{'研究判断：供给和费用只回答稀释与分成，不回答叙事。' if zh else 'Take: supply and fees answer dilution and split, not the story.'}\n\n"
            f"## {t3[lang]}\n\n{pair((h_zh, h_en))}\n\n{pair(('研究判断：热度对币价是真维度。缺序列就写未披露，有序列就要对照成交。', 'Take: heat is a real pricing dimension. Missing series stay undisclosed; a live series must sit next to volume.'))}\n\n"
            f"## {score_h[lang]}\n\n{(chr(10).join(score_zh) if zh else chr(10).join(score_en))}\n\n"
            f"{score_note_zh if zh else score_note_en}\n\n"
            f"## {risk_h[lang]}\n\n" + "\n".join(f"- {x}" for x in risk) + "\n\n"
            f"## {watch_h[lang]}\n\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(watch, 1)) + "\n\n"
            f"## {src_h[lang]}\n\n{(src_zh if zh else src_en)}\n\n"
            f"## {disc_h[lang]}\n\n{(disc_zh if zh else disc_en)}\n"
        )

    bodies = {lang: fm(lang) + body(lang) for lang in LANGS}
    blob = "\n".join(bodies.values())
    for phrase in BANNED:
        if phrase in blob:
            raise RuntimeError(f"banned template phrase leaked: {phrase}")
    return {"bodies": bodies, "titles": titles, "desc": desc, "conclusions": conclusions, "kind": kind}

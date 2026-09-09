#!/usr/bin/env python3
"""Publish one major note and one rotating DeFi/GameFi/Meme note from public data."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("DRLABS_ROOT", "/tmp/drlabs-live"))
ASTRO_CONTENT = Path(os.environ.get("ASTRO_CONTENT", "/workspace/src/content/research"))
HERE = Path(__file__).resolve().parent
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


def score_note(snap: Snap) -> tuple[float, list[tuple[str, str, float, float, str, str]]]:
    rank = snap.rank or 180
    if rank <= 5:
        size = 8.4
    elif rank <= 15:
        size = 7.6
    elif rank <= 40:
        size = 6.8
    elif rank <= 80:
        size = 5.8
    else:
        size = 4.6
    vol = snap.volume or 0
    if vol >= 1e9:
        liq = 8.0
    elif vol >= 2e8:
        liq = 7.0
    elif vol >= 5e7:
        liq = 6.0
    else:
        liq = 4.8
    market = (size + liq) / 2

    if snap.rev_30d and snap.rev_30d > 1e6:
        income = 7.0
    elif snap.fees_30d and snap.fees_30d > 1e7:
        income = 5.8
    elif snap.tvl and snap.tvl > 1e9:
        income = 5.4
    else:
        income = 3.6

    if snap.max_supply and snap.circ:
        token = 6.4 if (snap.circ / snap.max_supply) >= 0.7 else 5.4
    else:
        token = 4.2

    if snap.lane == "major":
        product = 6.6
    elif snap.lane == "DeFi":
        product = 6.2
    elif snap.lane == "GameFi":
        product = 5.2
    else:
        product = 4.0
    compete = 6.2 if rank <= 20 else 5.4
    risk = 5.8 if snap.lane != "Meme" else 4.2
    option = 6.0 if snap.tvl else 5.2

    if snap.lane == "Meme":
        income = min(income, 3.8)
        product = min(product, 4.4)
        option = min(option, 5.0)

    dims = [
        ("市场地位与流动性", "Market position & liquidity", 0.20, market, "市值排名与 24h 成交", "Rank and 24h volume"),
        ("收入与费用捕获", "Fees and capture", 0.15, income, "协议收入或费用，没有就下调", "Revenue or fees; cut if absent"),
        ("代币经济与估值", "Token and valuation", 0.15, token, "是否有硬顶、流通占比", "Hard cap and float"),
        ("产品与技术演进", "Product", 0.15, product, "按赛道给底，不编功能进度", "Lane floor; no invented roadmap"),
        ("竞争格局", "Competition", 0.15, compete, "排名越后竞争分越低", "Weaker rank, weaker score"),
        ("风险与治理", "Risk", 0.10, risk, "迷因资产额外下调", "Extra cut for memes"),
        ("增长期权", "Optionality", 0.10, option, "有可核 TVL 才加分", "TVL only if sourced"),
    ]
    raw = sum(weight * value for _, _, weight, value, _, _ in dims)
    total = max(3.0, min(8.2, raw))
    return round(total + 1e-9, 1), dims


def verdict(score: float) -> tuple[str, str]:
    if score >= 6.5:
        return "谨慎跟踪", "cautious watch"
    if score >= 5.0:
        return "观望", "hold / wait"
    return "回避", "avoid"


def title_take(snap: Snap, score: float) -> tuple[str, str]:
    v_zh, v_en = verdict(score)
    if snap.lane == "Meme":
        return "流动性在，基本面进不了跟踪带", "liquidity is real, fundamentals stay below the watch band"
    if snap.tvl and snap.mcap and snap.mcap > 5 * snap.tvl:
        return "定价厚，链上锁仓只解释一部分", "the price tag is thick; on-chain TVL only explains a slice"
    if snap.fees_30d and snap.rev_30d and snap.rev_30d < 0.2 * snap.fees_30d:
        return "费用池在，代币只分到一薄层", "the fee pool is real; the token still takes a thin slice"
    if snap.rank and snap.rank <= 15:
        return f"市值第 {snap.rank}，基本面要单独核算", f"#{snap.rank} by cap; fundamentals still need their own ledger"
    return f"公开数据能核的部分写在下面（{v_zh}）", f"what public data can support is below ({v_en})"


def yaml_escape(text: str) -> str:
    return text.replace('"', '\\"')


def frontmatter(lang: str, snap: Snap, score: float, titles: dict[str, str], desc: dict[str, str], conclusions: dict[str, str], day: str) -> str:
    title = titles.get(lang) or titles["en"]
    description = desc.get(lang) or desc["en"]
    conclusion = conclusions.get(lang) or conclusions["en"]
    tags = "\n".join(f"  - {tag}" for tag in snap.tags)
    extra = ""
    if lang == "zh":
        extra = f"asOf: \"{snap.as_of}\"\n"
    return (
        "---\n"
        f"title: \"{yaml_escape(title)}\"\n"
        f"description: \"{yaml_escape(description)}\"\n"
        f"date: {day}\n"
        f"{extra}"
        f"ticker: {snap.ticker}\n"
        f"score: {score:.1f}\n"
        f"tags:\n{tags}\n"
        f"conclusion: \"{yaml_escape(conclusion)}\"\n"
        "---\n\n"
    )


def table(rows_zh: list[tuple[str, str, str]], rows_en: list[tuple[str, str, str]]) -> tuple[str, str]:
    zh = ["| 指标 | 数值 | 口径 |", "| --- | --- | --- |"]
    en = ["| Metric | Value | Source |", "| --- | --- | --- |"]
    for a, b in zip(rows_zh, rows_en):
        zh.append(f"| {a[0]} | {a[1]} | {a[2]} |")
        en.append(f"| {b[0]} | {b[1]} | {b[2]} |")
    return "\n".join(zh), "\n".join(en)


def headings(key: str, snap: Snap, score: float, day: str) -> dict[str, str]:
    catalog = {
        "take": {
            "zh": "研究结论",
            "en": "Research take",
            "ja": "研究結論",
            "ko": "연구 결론",
            "fr": "Conclusion",
            "es": "Conclusión",
            "ru": "Вывод",
        },
        "snap": {
            "zh": f"数据快照（{day}）",
            "en": f"Snapshot ({day})",
            "ja": f"データスナップショット（{day}）",
            "ko": f"데이터 스냅샷（{day}）",
            "fr": f"Instantané ({day})",
            "es": f"Instantánea ({day})",
            "ru": f"Снимок ({day})",
        },
        "pos": {
            "zh": "市场位置：能核的规模",
            "en": "Market position: scale we can check",
            "ja": "市場位置：検証できる規模",
            "ko": "시장 위치: 확인할 수 있는 규모",
            "fr": "Position de marché : l’échelle vérifiable",
            "es": "Posición de mercado: la escala comprobable",
            "ru": "Позиция: проверяемый масштаб",
        },
        "token": {
            "zh": "代币：供给比口号重要",
            "en": "Token: supply over slogans",
            "ja": "トークン：供給がスローガンより大事",
            "ko": "토큰: 구호보다 공급",
            "fr": "Jeton : l’offre avant les slogans",
            "es": "Token: la oferta importa más que el eslogan",
            "ru": "Токен: предложение важнее лозунга",
        },
        "biz": {
            "zh": "链上业务：有数字才写",
            "en": "On-chain business: only what the numbers show",
            "ja": "オンチェーン：数字があるものだけ",
            "ko": "온체인: 숫자 있는 것만",
            "fr": "On-chain : uniquement les chiffres",
            "es": "On-chain: solo lo que muestran los números",
            "ru": "Ончейн: только то, что в цифрах",
        },
        "score": {
            "zh": f"买入评分 {score:.1f} / 10",
            "en": f"Buy score {score:.1f} / 10",
            "ja": f"買いスコア {score:.1f} / 10",
            "ko": f"매수 점수 {score:.1f} / 10",
            "fr": f"Score d’achat {score:.1f} / 10",
            "es": f"Puntuación de compra {score:.1f} / 10",
            "ru": f"Оценка покупки {score:.1f} / 10",
        },
        "risk": {
            "zh": "主要风险",
            "en": "Main risks",
            "ja": "主なリスク",
            "ko": "주요 위험",
            "fr": "Risques principaux",
            "es": "Riesgos principales",
            "ru": "Основные риски",
        },
        "watch": {
            "zh": "跟踪清单",
            "en": "Watch list",
            "ja": "ウォッチリスト",
            "ko": "추적 목록",
            "fr": "Liste de suivi",
            "es": "Lista de seguimiento",
            "ru": "Список наблюдения",
        },
        "src": {
            "zh": "数据来源",
            "en": "Sources",
            "ja": "出典",
            "ko": "출처",
            "fr": "Sources",
            "es": "Fuentes",
            "ru": "Источники",
        },
        "disc": {
            "zh": "免责声明",
            "en": "Disclaimer",
            "ja": "免責",
            "ko": "면책",
            "fr": "Avertissement",
            "es": "Aviso legal",
            "ru": "Отказ от ответственности",
        },
    }
    return catalog[key]


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


def draft_note(snap: Snap, score: float, dims, day: str) -> dict[str, str]:
    v_zh, v_en = verdict(score)
    take_zh, take_en = title_take(snap, score)
    titles = {
        "zh": f"{snap.ticker} 研究简报：{take_zh}",
        "en": f"{snap.ticker} research note: {take_en}",
        "ja": f"{snap.ticker}リサーチノート：{take_en}",
        "ko": f"{snap.ticker} 리서치 노트: {take_en}",
        "fr": f"Note {snap.ticker} : {take_en}",
        "es": f"Nota {snap.ticker}: {take_en}",
        "ru": f"Записка по {snap.ticker}: {take_en}",
    }
    rank_zh = f"第 {snap.rank}" if snap.rank else "未披露"
    rank_en = str(snap.rank) if snap.rank else "not disclosed"
    mcap_tvl = None
    if snap.mcap and snap.tvl:
        mcap_tvl = snap.mcap / snap.tvl
    capture = None
    if snap.fees_30d and snap.rev_30d and snap.fees_30d > 0:
        capture = 100 * snap.rev_30d / snap.fees_30d
    from_ath = None
    if snap.price and snap.ath and snap.ath > 0:
        from_ath = 100 * (snap.price / snap.ath - 1)

    desc = {
        "zh": (
            f"截至 {snap.as_of}，{snap.ticker} 约 {fmt_usd(snap.price)}、流通市值 {fmt_usd(snap.mcap)}"
            + (f"，排名 {rank_zh}" if snap.rank else "")
            + (f"；{snap.tvl_label} {fmt_usd(snap.tvl)}" if snap.tvl else "")
            + f"。买入评分 {score:.1f}/10，{v_zh}。"
        ),
        "en": (
            f"As of {snap.as_of}, {snap.ticker} is about {fmt_usd(snap.price)} with circulating mcap {fmt_usd(snap.mcap)}"
            + (f", rank {rank_en}" if snap.rank else "")
            + (f"; {snap.tvl_label} {fmt_usd(snap.tvl)}" if snap.tvl else "")
            + f". Buy score {score:.1f}/10, {v_en}."
        ),
    }
    conclusions = {
        "zh": (
            f"{snap.name}（{snap.ticker}）在公开市值与成交里站得住："
            f"价格 {fmt_usd(snap.price)}，流通市值 {fmt_usd(snap.mcap)}。"
            + (f"{snap.tvl_label} 为 {fmt_usd(snap.tvl)}。" if snap.tvl else "没有可核的协议 TVL，就不把它写成基本面支柱。")
            + (f"近 30 日费用 {fmt_usd(snap.fees_30d)}，协议收入 {fmt_usd(snap.rev_30d)}。" if snap.fees_30d or snap.rev_30d else "")
            + f"综合买入评分 {score:.1f}/10，{v_zh}。本文不是买入建议。"
        ),
        "en": (
            f"{snap.name} ({snap.ticker}) clears the public-market screen: "
            f"price {fmt_usd(snap.price)}, circulating mcap {fmt_usd(snap.mcap)}. "
            + (f"{snap.tvl_label} is {fmt_usd(snap.tvl)}. " if snap.tvl else "There is no sourced protocol TVL, so it is not treated as a fundamental pillar. ")
            + (f"30-day fees {fmt_usd(snap.fees_30d)}, protocol revenue {fmt_usd(snap.rev_30d)}. " if snap.fees_30d or snap.rev_30d else "")
            + f"Buy score {score:.1f}/10, {v_en}. This is not a buy recommendation."
        ),
    }

    rows_zh = [
        (f"{snap.ticker} 价格", fmt_usd(snap.price), "CoinGecko"),
        ("流通市值 / FDV", f"{fmt_usd(snap.mcap)} / {fmt_usd(snap.fdv)}", "CoinGecko"),
        ("流通 / 总量 / 上限", f"{fmt_qty(snap.circ)} / {fmt_qty(snap.total)} / {fmt_qty(snap.max_supply)}", "CoinGecko"),
        ("市值排名", rank_zh if snap.rank else "未披露", "CoinGecko"),
        ("距 ATH", f"{fmt_usd(snap.ath)}" + (f"（{snap.ath_date}），{from_ath:.0f}%" if from_ath is not None and snap.ath_date else ""), "CoinGecko"),
        ("7 日 / 30 日涨跌", f"{fmt_pct(snap.chg_7d)} / {fmt_pct(snap.chg_30d)}", "CoinGecko"),
        ("24h 成交", fmt_usd(snap.volume), "CoinGecko"),
    ]
    rows_en = [
        (f"{snap.ticker} price", fmt_usd(snap.price), "CoinGecko"),
        ("Circulating mcap / FDV", f"{fmt_usd(snap.mcap)} / {fmt_usd(snap.fdv)}", "CoinGecko"),
        ("Circ / total / max", f"{fmt_qty(snap.circ)} / {fmt_qty(snap.total)} / {fmt_qty(snap.max_supply)}", "CoinGecko"),
        ("Market-cap rank", rank_en, "CoinGecko"),
        ("Vs ATH", f"{fmt_usd(snap.ath)}" + (f" ({snap.ath_date}), {from_ath:.0f}%" if from_ath is not None and snap.ath_date else ""), "CoinGecko"),
        ("7d / 30d", f"{fmt_pct(snap.chg_7d)} / {fmt_pct(snap.chg_30d)}", "CoinGecko"),
        ("24h volume", fmt_usd(snap.volume), "CoinGecko"),
    ]
    if snap.tvl:
        rows_zh.append((snap.tvl_label or "TVL", fmt_usd(snap.tvl), "DefiLlama"))
        rows_en.append((snap.tvl_label or "TVL", fmt_usd(snap.tvl), "DefiLlama"))
    if mcap_tvl is not None:
        rows_zh.append(("市值 / TVL", f"≈ {mcap_tvl:.2f}×", "计算 / calculated"))
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

    if snap.lane == "Meme":
        pos_zh = (
            f"{snap.name} 的公开市场位置清楚：流通市值 {fmt_usd(snap.mcap)}"
            + (f"，排名 {rank_zh}" if snap.rank else "")
            + f"，24 小时成交 {fmt_usd(snap.volume)}。这只说明它能被交易，不说明它有协议收入或货币纪律。"
        )
        pos_en = (
            f"{snap.name} has a clear public-market slot: circulating mcap {fmt_usd(snap.mcap)}"
            + (f", rank {rank_en}" if snap.rank else "")
            + f", 24h volume {fmt_usd(snap.volume)}. That is tradability, not protocol income or monetary discipline."
        )
        biz_zh = "迷因资产的业务就是注意力和流动性。本文不把社交媒体热度写成基本面，也不编用户数或游戏流水。"
        biz_en = "A meme asset’s ‘business’ is attention plus liquidity. This note does not treat social heat as fundamentals, and it does not invent user counts or game revenue."
    elif snap.lane == "GameFi":
        pos_zh = (
            f"{snap.name} 按市值 {fmt_usd(snap.mcap)}、24 小时成交 {fmt_usd(snap.volume)} 进入本次样本。"
            "链游代币要先分清：交易的是治理/积分票，还是已经能核的游戏流水。"
        )
        pos_en = (
            f"{snap.name} enters this sample on mcap {fmt_usd(snap.mcap)} and 24h volume {fmt_usd(snap.volume)}. "
            "For game tokens, separate the traded ticket from sourced game cash flow."
        )
        biz_zh = (
            (f"DefiLlama 能核的锁仓是 {fmt_usd(snap.tvl)}（{snap.tvl_label}）。" if snap.tvl else "本次快照没有可核的协议 TVL。")
            + "在看到稳定的链上费用或工作室披露之前，不把 GameFi 写成已经产品化的现金牛。"
        )
        biz_en = (
            (f"Sourced lockup is {fmt_usd(snap.tvl)} ({snap.tvl_label}). " if snap.tvl else "This snapshot has no sourced protocol TVL. ")
            + "Until fees or studio disclosure are stable, GameFi is not written up as a cash cow."
        )
    else:
        pos_zh = (
            f"{snap.name} 流通市值 {fmt_usd(snap.mcap)}"
            + (f"，排名 {rank_zh}" if snap.rank else "")
            + f"。24 小时成交 {fmt_usd(snap.volume)}。"
            + ("近 30 日和 7 日涨跌只当风险偏好，不当基本面台阶。" if snap.chg_30d is not None else "")
        )
        pos_en = (
            f"{snap.name} circulating mcap is {fmt_usd(snap.mcap)}"
            + (f", rank {rank_en}" if snap.rank else "")
            + f". 24h volume {fmt_usd(snap.volume)}. "
            + ("7-day and 30-day moves are risk appetite, not a step-change in fundamentals." if snap.chg_30d is not None else "")
        )
        if snap.tvl or snap.fees_30d or snap.rev_30d:
            biz_zh = (
                (f"{snap.tvl_label} 为 {fmt_usd(snap.tvl)}。" if snap.tvl else "")
                + (f"近 30 日费用 {fmt_usd(snap.fees_30d)}。" if snap.fees_30d is not None else "")
                + (f"近 30 日协议收入 {fmt_usd(snap.rev_30d)}。" if snap.rev_30d is not None else "")
                + ("费用不等于持有人分红；捕获率单独算。" if snap.fees_30d is not None else "没有费用口径时，锁仓只说明资金停在那里，不说明代币能收租。")
            )
            biz_en = (
                (f"{snap.tvl_label} is {fmt_usd(snap.tvl)}. " if snap.tvl else "")
                + (f"30-day fees {fmt_usd(snap.fees_30d)}. " if snap.fees_30d is not None else "")
                + (f"30-day protocol revenue {fmt_usd(snap.rev_30d)}. " if snap.rev_30d is not None else "")
                + ("Fees are not holder dividends; capture is scored separately." if snap.fees_30d is not None else "With no fee print, TVL only shows capital parked, not rent collected by the token.")
            )
        else:
            biz_zh = f"这次快照没有可核的协议 TVL 或费用。{snap.ticker} 的定价先按流动性和供给来看，不编链上收入。"
            biz_en = f"This snapshot has no sourced protocol TVL or fees. {snap.ticker} is priced off liquidity and supply, not invented on-chain income."

    if snap.max_supply:
        float_pct = (100 * snap.circ / snap.max_supply) if snap.circ else None
        token_zh = (
            f"总量 {fmt_qty(snap.total)}，上限 {fmt_qty(snap.max_supply)}"
            + (f"，流通占比约 {float_pct:.0f}%。" if float_pct is not None else "。")
            + "有硬顶不等于低估，只说明稀释上限是可核对的。"
        )
        token_en = (
            f"Total supply {fmt_qty(snap.total)}, max {fmt_qty(snap.max_supply)}"
            + (f", float about {float_pct:.0f}%." if float_pct is not None else ".")
            + " A hard cap is not undervaluation; it only makes the dilution ceiling checkable."
        )
    else:
        token_zh = (
            f"CoinGecko 未给出供应上限。流通 {fmt_qty(snap.circ)}，总量 {fmt_qty(snap.total)}。"
            "没有硬顶时，研究上把长期稀释当成默认风险，而不是暂时的疏忽。"
        )
        token_en = (
            f"CoinGecko lists no max supply. Circulating {fmt_qty(snap.circ)}, total {fmt_qty(snap.total)}. "
            "With no hard cap, long-run dilution is treated as the default risk, not a temporary omission."
        )

    risks_zh = [
        f"**价格波动：** 24 小时成交 {fmt_usd(snap.volume)}，短线波动可以大过任何评分。",
        "**数据口径：** 市值、TVL、费用、收入不可混用；缺的格子写成未披露，不补故事。",
        "**快照时效：** 数字只对 " + snap.as_of + " 这一刻负责。",
    ]
    risks_en = [
        f"**Volatility:** 24h volume {fmt_usd(snap.volume)}; a tape can move more than any score.",
        "**Definitions:** Market cap, TVL, fees and revenue are not interchangeable. Empty cells stay undisclosed.",
        f"**Stale prints:** Figures are only good as of {snap.as_of}.",
    ]
    if snap.lane == "Meme":
        risks_zh.insert(0, "**没有协议现金流：** 注意力可以交易，不能折成持有人收入。")
        risks_en.insert(0, "**No protocol cash flow:** Attention is tradable; it does not discount into holder income.")
    if not snap.max_supply:
        risks_zh.append("**无限供给：** 没有硬顶时，长期持有人份额会被持续摊薄。")
        risks_en.append("**Uncapped supply:** With no hard cap, long-term holders keep getting diluted.")
    if snap.tvl and snap.mcap and snap.mcap > 5 * snap.tvl:
        risks_zh.append("**市值远厚于锁仓：** 定价里有很大一块不是链上业务能解释的。")
        risks_en.append("**Mcap dwarfs TVL:** A large slice of the price tag is not explained by on-chain books.")

    watch_zh = [
        "CoinGecko 市值排名与 24 小时成交是否还撑得住当前流动性假设。",
        "流通量、总量与上限（如有）有没有突然跳变。",
    ]
    watch_en = [
        "Whether CoinGecko rank and 24h volume still support the liquidity assumption.",
        "Whether circulating, total and max supply (if any) jump without explanation.",
    ]
    if snap.tvl:
        watch_zh.append(f"{snap.tvl_label} 是回升、横盘还是失血。")
        watch_en.append(f"Whether {snap.tvl_label} is rising, flat or bleeding.")
    if snap.fees_30d is not None or snap.rev_30d is not None:
        watch_zh.append("近 30 日费用与协议收入，捕获率有没有离开本次快照。")
        watch_en.append("Whether 30-day fees, revenue and capture leave this snapshot.")
    watch_zh.append("同赛道新发布研报里的对比数字，而不是社交媒体热度。")
    watch_en.append("Comparable prints in later notes, not social heat.")

    src_zh = f"- " + "；".join(snap.sources) + f"（快照 {snap.as_of}）"
    src_en = f"- " + "; ".join(snap.sources) + f" (as-of {snap.as_of})"
    disc_zh = (
        f"本报告由 DRLabs 撰写，仅供研究与信息交流，**不构成投资建议、财务建议、法律建议，亦不构成任何证券或加密资产的要约或要约邀请**。"
        f"加密资产价格波动剧烈，可能造成部分或全部本金损失。文中买入评分 {score:.1f}/10 是基于公开数据的主观评估，不是评级机构结论。"
        "完整条款见[关于 DRLabs](../../about.html#disclaimer)。"
    )
    disc_en = (
        f"Written by DRLabs for research and discussion. **Not investment, financial or legal advice, and not an offer.** "
        f"Crypto can cause partial or total loss. The {score:.1f}/10 buy score is a subjective reading of public data, not an agency rating. "
        "Full terms: [About DRLabs](../../about.html#disclaimer)."
    )

    closer_zh = f"**买入评分 {score:.1f} / 10（{v_zh}）。** 只对上面能核的数字负责。本文不是买入建议。"
    closer_en = f"**Buy score {score:.1f} / 10 ({v_en}).** Only the sourced figures above are in play. This is not a buy recommendation."
    score_note_zh = f"{score:.1f} 是加权四舍五入。缺数据的维度按保守分，不因为叙事补分。"
    score_note_en = f"{score:.1f} is the rounded weighted total. Missing data is scored conservatively; narrative does not add points."

    bodies: dict[str, str] = {}
    para = {
        "take1": {"zh": conclusions["zh"], "en": conclusions["en"]},
        "take2": {"zh": closer_zh, "en": closer_en},
        "after_tbl": {
            "zh": f"数据时区按快照时刻 UTC（{snap.as_of}）。没有来源的格子不填。",
            "en": f"Timezone is the snapshot UTC stamp ({snap.as_of}). Empty cells stay empty.",
        },
        "pos": {"zh": pos_zh, "en": pos_en},
        "token": {"zh": token_zh, "en": token_en},
        "biz": {"zh": biz_zh, "en": biz_en},
        "score_note": {"zh": score_note_zh, "en": score_note_en},
        "src": {"zh": src_zh, "en": src_en},
        "disc": {"zh": disc_zh, "en": disc_en},
    }

    def section(lang: str) -> str:
        def h(key: str) -> str:
            return headings(key, snap, score, day)[lang]

        def p(key: str) -> str:
            return para[key].get(lang) or para[key]["en"]

        risk_items = risks_zh if lang == "zh" else risks_en
        watch_items = watch_zh if lang == "zh" else watch_en
        risk_md = "\n".join(f"- {item}" for item in risk_items)
        watch_md = "\n".join(f"{i}. {item}" for i, item in enumerate(watch_items, 1))
        tbl = tbl_zh if lang == "zh" else tbl_en
        score_tbl = "\n".join(score_zh) if lang == "zh" else "\n".join(score_en)
        return (
            f"## {h('take')}\n\n{p('take1')}\n\n{p('take2')}\n\n"
            f"## {h('snap')}\n\n{tbl}\n\n{p('after_tbl')}\n\n"
            f"## {h('pos')}\n\n{p('pos')}\n\n"
            f"## {h('token')}\n\n{p('token')}\n\n"
            f"## {h('biz')}\n\n{p('biz')}\n\n"
            f"## {h('score')}\n\n{score_tbl}\n\n{p('score_note')}\n\n"
            f"## {h('risk')}\n\n{risk_md}\n\n"
            f"## {h('watch')}\n\n{watch_md}\n\n"
            f"## {h('src')}\n\n{p('src')}\n\n"
            f"## {h('disc')}\n\n{p('disc')}\n"
        )

    for lang in LANGS:
        bodies[lang] = frontmatter(lang, snap, score, titles, desc, conclusions, day) + section(lang)
    return {"bodies": bodies, "titles": titles, "desc": desc, "conclusions": conclusions}


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

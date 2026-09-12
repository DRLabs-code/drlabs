#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE))
from desk_write import BANNED, detect_kind, draft_note, score_note
from i18n_build import parse_blocks, LANGS


def snap(**kwargs):
    base = dict(
        ticker="X",
        name="Example",
        cg_id="example",
        tags=["L1"],
        lane="major",
        as_of="2026-09-12 00:20 UTC",
        price=100.0,
        mcap=6e10,
        fdv=6.5e10,
        volume=4e9,
        rank=7,
        circ=5.8e8,
        total=6.3e8,
        max_supply=None,
        ath=300.0,
        ath_date="2025-01-19",
        chg_7d=0.6,
        chg_30d=35.0,
        tvl=5.9e9,
        tvl_label="Solana DeFi TVL",
        fees_30d=2.27e7,
        rev_30d=2.35e6,
        sources=["CoinGecko", "DefiLlama", "LunarCrush"],
        peers=[
            {"ticker": "ETH", "mcap": 3.07e11, "volume": 2.5e10, "rank": 2, "chg_30d": 34.0},
            {"ticker": "BTC", "mcap": 1.57e12, "volume": 3.5e10, "rank": 1, "chg_30d": 22.0},
        ],
        chains=[
            {"name": "Ethereum", "tvl": 5.0e10},
            {"name": "Solana", "tvl": 5.9e9},
        ],
        dexs=[
            {"name": "Solana", "vol_24h": 2.9e9, "vol_30d": 7.25e10},
            {"name": "Ethereum", "vol_24h": 1.4e9, "vol_30d": 3.88e10},
        ],
        stables=1.615e10,
        x_mentions={"self": {"mentions": 200, "updated": "Sep 12, 2026", "sentiment": 80}, "btc": {"mentions": 356}, "stale": False},
        lunar={"dominance": 13.8, "sentiment": 84, "posts": "12.2K"},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def kinds_of(text: str) -> list[str]:
    return [k for k, _ in parse_blocks(text)]


def test_pair(name, s):
    kind = detect_kind(s)
    score, dims = score_note(s)
    drafted = draft_note(s, score, dims, "2026-09-12")
    zh = kinds_of(drafted["bodies"]["zh"])
    assert zh, name
    for lang in LANGS:
        got = kinds_of(drafted["bodies"][lang])
        assert got == zh, (name, lang, got, zh)
    blob = "\n".join(drafted["bodies"].values())
    for phrase in BANNED:
        assert phrase not in blob, (name, phrase)
    assert "LunarCrush" in drafted["bodies"]["zh"] or "未披露" in drafted["bodies"]["zh"]
    print(f"OK {name} kind={kind} score={score} title={drafted['titles']['zh']} blocks={len(zh)}")
    return kind, drafted["titles"]["zh"]


def main() -> None:
    k1, t1 = test_pair("sol", snap())
    k2, t2 = test_pair(
        "btc",
        snap(
            ticker="BTC",
            name="Bitcoin",
            tags=["L1"],
            mcap=1.57e12,
            tvl=4.24e9,
            tvl_label="Bitcoin DeFi TVL",
            volume=3.5e10,
            rank=1,
            max_supply=2.1e7,
            circ=2.008e7,
            total=2.008e7,
            dexs=[{"name": "Solana", "vol_30d": 7.25e10}, {"name": "Ethereum", "vol_30d": 3.88e10}],
            stables=None,
            lunar={"dominance": 27.8, "sentiment": 69},
            chg_30d=22.5,
        ),
    )
    k3, t3 = test_pair(
        "shib",
        snap(
            ticker="SHIB",
            name="Shiba Inu",
            lane="Meme",
            tags=["Meme"],
            mcap=3.0e9,
            volume=8.2e7,
            rank=33,
            tvl=None,
            tvl_label="",
            fees_30d=None,
            rev_30d=None,
            dexs=[],
            chains=[],
            stables=None,
            peers=[
                {"ticker": "DOGE", "mcap": 1.3e10, "volume": 8e8},
                {"ticker": "PEPE", "mcap": 1.4e9, "volume": 2.7e8},
            ],
            lunar={"dominance": 0.21, "sentiment": 50},
        ),
    )
    k4, t4 = test_pair(
        "ldo",
        snap(
            ticker="LDO",
            name="Lido DAO",
            lane="DeFi",
            tags=["DeFi"],
            mcap=3.09e8,
            volume=4.3e7,
            rank=137,
            tvl=2.44e10,
            tvl_label="Lido TVL",
            fees_30d=4.495e7,
            rev_30d=2.79e6,
            dexs=[],
            chains=[],
            max_supply=1e9,
            circ=8.34e8,
            total=1e9,
            peers=[{"ticker": "UNI", "mcap": 3.75e9, "volume": 6.8e8}, {"ticker": "AAVE", "mcap": 1.93e9, "volume": 2.2e8}],
            lunar={"dominance": 0.028, "sentiment": 58},
        ),
    )
    assert k1 != k2
    assert t1 != t2
    assert "定价厚" not in t2
    print("different kinds", k1, k2, k3, k4)


if __name__ == "__main__":
    main()

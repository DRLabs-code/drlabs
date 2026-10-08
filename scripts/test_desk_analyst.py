#!/usr/bin/env python3
"""Offline checks for desk_analyst: seven language blocks align, banned phrases never leak,
disclaimer + Perth date are present, missing data is omitted instead of invented, and two
different coins do not come out as the same note."""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from desk_analyst import BANNED, LANGS, compose_note  # noqa: E402
from i18n_build import parse_blocks  # noqa: E402

BASE = {
    "ticker": "ARB", "name": "Arbitrum", "cg_id": "arbitrum", "lane": "L2", "tags": ["L2"], "slug": "arb",
    "as_of": "2026-10-08 00:20 UTC", "day": "2026-10-08",
    "cg": {"price": 0.186, "mcap": 1.26e9, "fdv": 1.86e9, "volume": 2.1e8, "rank": 80, "circ": 6.8e9, "total": 1e10,
           "max_supply": 1e10, "max_infinite": False, "ath": 2.39, "ath_date": "2024-01-12", "ath_chg": -92.2,
           "chg_7d": -3.0, "chg_30d": -12.0, "chg_1y": -56.0, "chg_200d": -20.0, "votes_up": 71.0, "watchlist": 215586,
           "categories": ["Layer 2 (L2)", "Rollup", "Ethereum Ecosystem", "Pantera Capital Portfolio"], "hashing": None},
    "hist": {"vol30": 70.0, "mdd90": -35.0, "ma50": 0.2, "ma200": 0.26, "hi90": 0.31, "lo90": 0.17, "vol7_avg": 2.4e8,
             "vol30_avg": 1.6e8, "circ_chg_365d": 38.0, "circ_chg_90d": 6.0},
    "btc": {"chg_7d": 1.0, "chg_30d": 5.0, "chg_1y": -32.0, "chg_200d": 3.0},
    "sector": {"median_30d": -4.0, "n": 40, "pos": 2},
    "peers": [{"ticker": "MNT", "cg": "mantle", "mcap": 2.1e9, "volume": 9e7, "chg_30d": 2.0, "leader": True, "chain_tvl": 4e8, "fees30": 2e5},
              {"ticker": "OP", "cg": "optimism", "mcap": 7e8, "volume": 1e8, "chg_30d": -15.0, "chain_tvl": 3e8, "fees30": 3e5}],
    "protocol": None,
    "chain": {"name": "Arbitrum", "tvl": 2.4e9, "rank": 6, "n": 330, "tvl_chg_30d": -8.0, "tvl_chg_90d": -20.0, "stables": 3.1e9,
              "dex30": 3.0e9, "dex_prev30": 3.8e9, "fees30": 6.6e5, "fees_prev30": 7.2e5},
    "social": {"fng": {"now": 64, "label": "Greed", "avg30": 67}, "trending_pos": None, "trending_n": 15, "lunar": None},
    "sources": ["CoinGecko", "DefiLlama"],
}


def check(pack: dict) -> dict:
    d = compose_note(pack)
    zh = [k for k, _ in parse_blocks(d["bodies"]["zh"])]
    for lang in LANGS:
        got = [k for k, _ in parse_blocks(d["bodies"][lang])]
        assert got == zh, (pack["ticker"], lang)
    blob = "\n".join(d["bodies"].values())
    for phrase in BANNED:
        assert phrase not in blob, phrase
    body = d["bodies"]["zh"]
    assert "仅供参考，投资要理性" in body
    assert "澳洲珀斯时间" in body.split("## ", 2)[1]
    assert not re.search(r"\b(None|nan|inf)\b", blob), re.search(r".{30}\b(None|nan|inf)\b.{30}", blob)
    assert 3.0 <= d["score"] <= 8.2
    print(f"OK {pack['ticker']} {d['profile']} {d['score']} {d['titles']['zh']}")
    return d


def main() -> None:
    a = check(copy.deepcopy(BASE))
    meme = copy.deepcopy(BASE)
    meme.update(ticker="FART", name="Fartcoin", cg_id="fartcoin", lane="Meme", tags=["Meme"], chain=None, peers=[])
    meme["cg"].update(categories=["Meme", "Solana Ecosystem"], fdv=None, max_supply=None, chg_30d=48.0, volume=6e8, mcap=1.1e9)
    meme["hist"] = {}
    meme["social"]["trending_pos"] = 3
    b = check(meme)
    assert "DefiLlama" not in b["bodies"]["zh"].split("## 数据来源")[0].split("数据快照")[1].split("快照时间")[0]
    proto = copy.deepcopy(BASE)
    proto.update(ticker="AERO", name="Aerodrome", cg_id="aerodrome-finance", lane="DeFi", tags=["DeFi"], chain=None)
    proto["protocol"] = {"name": "Aerodrome", "tvl": 5e8, "tvl_chg_30d": 12.0, "fees30": 2.4e7, "fees_prev30": 1.9e7, "fees7": 7e6,
                         "rev30": 2.2e7, "hrev30": 2.2e7}
    c = check(proto)
    assert a["bodies"]["zh"] != b["bodies"]["zh"] != c["bodies"]["zh"]
    assert a["titles"]["zh"] != c["titles"]["zh"]
    print("all good")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Offline checks for the desk note writer (no network).

  python3 scripts/test_desk_analyst.py        # or: python3 -m pytest scripts/test_desk_analyst.py

What is checked:
  * structure: 7 language bodies align block-for-block, disclaimer + Perth date present,
    no banned template phrase, no None/nan/unformatted placeholder, score inside 3.0-8.2;
  * wording: across ~17 cached coin packs (scripts/fixtures/desk_packs/*.json) no
    non-boilerplate sentence repeats between two notes, and for every pair of coins a note
    composed "on the same day" as another shares no sentence skeleton with it;
  * calls: every qualitative label matches its number (audit), including the known failure
    cases (ILV +16% / 30d described as "no FOMO", FLOKI as GameFi leader, ZEC launch-day ATH,
    a sector called cold off a median of tiny coins), plus a randomised perturbation test;
  * phrasebook: every slot has >= 2 variants and every variant carries a coin-specific field.
"""
from __future__ import annotations

import copy
import itertools
import json
import random
import re
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import desk_sources as ds  # noqa: E402
from desk_analyst import BANNED, LANGS, TH, audit, compose_note, skeleton, split_sentences  # noqa: E402
from desk_phrases import BOILERPLATE_SLOTS, P  # noqa: E402
from i18n_build import parse_blocks  # noqa: E402

FIX = HERE / "fixtures" / "desk_packs"

BASE = {
    "ticker": "ARB", "name": "Arbitrum", "cg_id": "arbitrum", "lane": "L2", "tags": ["L2"], "slug": "arb",
    "as_of": "2026-10-08 00:20 UTC", "day": "2026-10-08",
    "cg": {"price": 0.186, "mcap": 1.26e9, "fdv": 1.86e9, "volume": 2.1e8, "rank": 80, "circ": 6.8e9, "total": 1e10,
           "max_supply": 1e10, "max_infinite": False, "ath": 2.39, "ath_date": "2024-01-12", "ath_chg": -92.2,
           "chg_7d": -3.0, "chg_30d": -12.0, "chg_1y": -56.0, "chg_200d": -20.0, "votes_up": 71.0, "watchlist": 215586,
           "categories": ["Layer 2 (L2)", "Rollup", "Ethereum Ecosystem", "Pantera Capital Portfolio"], "hashing": None,
           "genesis": "2023-03-23"},
    "hist": {"vol30": 70.0, "mdd90": -35.0, "ma50": 0.2, "ma200": 0.26, "hi90": 0.31, "lo90": 0.17, "vol7_avg": 2.4e8,
             "vol30_avg": 1.6e8, "circ_chg_365d": 38.0, "circ_chg_90d": 6.0},
    "btc": {"chg_7d": 1.0, "chg_30d": 5.0, "chg_1y": -32.0, "chg_200d": 3.0},
    "sector": {"median_30d": -4.0, "wavg_ex_30d": -6.0, "n": 40, "pos": 2, "cat_name": "Layer 2 (L2)", "dropped": 3},
    "peers": [{"ticker": "MNT", "cg": "mantle", "mcap": 2.1e9, "volume": 9e7, "chg_30d": 2.0, "leader": True, "chain_tvl": 4e8, "fees30": 2e5},
              {"ticker": "OP", "cg": "optimism", "mcap": 7e8, "volume": 1e8, "chg_30d": -15.0, "chain_tvl": 3e8, "fees30": 3e5}],
    "protocol": None,
    "chain": {"name": "Arbitrum", "tvl": 2.4e9, "rank": 6, "n": 330, "tvl_chg_30d": -8.0, "tvl_chg_90d": -20.0, "stables": 3.1e9,
              "dex30": 3.0e9, "dex_prev30": 3.8e9, "fees30": 6.6e5, "fees_prev30": 7.2e5},
    "social": {"fng": {"now": 64, "label": "Greed", "avg30": 67}, "trending_pos": None, "trending_n": 15, "lunar": None},
    "news": [{"title": "Arbitrum DAO votes on [treasury] plan", "url": "https://example.org/a(b)", "outlet": "CoinDesk",
              "date": "2026-10-01", "tags": ["institutional"]}],
    "news_checked": True,
    "unlocks": {"slug": "arbitrum", "url": "https://defillama.com/unlocks/arbitrum", "next30": 9.2e7, "next90": 2.8e8,
                "next30_pct_circ": 1.35, "next90_pct_circ": 4.1, "next30_usd": 1.7e7, "next90_usd": 5.2e7,
                "schedule_ends": "2027-03-16", "next_cliff": {"date": "2026-10-16", "tokens": 9.2e7, "label": "Team", "pct_circ": 1.35}},
    "hacks": [],
    "profile": {"about": "Arbitrum is a Layer 2 scaling solution for Ethereum.", "homepage": "https://arbitrum.io"},
    "sources": ["CoinGecko", "DefiLlama"],
}

SKIP_LINES = ("发布日期", "Published ", "快照时间", "Snapshot taken", "评分标准", "Scale:", "本报告由", "Written by DRLabs")


def fixtures() -> list[dict]:
    packs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIX.glob("*.json"))]
    assert len(packs) >= 15, f"need >= 15 fixture packs in {FIX}, found {len(packs)}"
    return packs


def body_sentences(md: str, lang: str) -> list[str]:
    """Analytical sentences only: no front matter, headings, tables, sources, headline bullets or disclaimer."""
    text = md.split("\n---\n", 1)[1] if md.startswith("---") else md
    out, section = [], ""
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("## "):
            section = s
            continue
        if s.startswith(("#", "|")) or s.startswith(SKIP_LINES):
            continue
        if any(k in section for k in ("数据来源", "Sources", "免责声明", "Disclaimer", "买入评分", "Buy score")):
            continue
        if s.startswith("- ") and re.match(r"- \d{4}-\d{2}-\d{2} · ", s):
            continue  # verbatim headline bullet
        s = s[2:] if s.startswith("- ") else s
        for sent in split_sentences(s):
            if len(sent) >= 12:
                out.append(sent)
    return out


def boilerplate() -> set[str]:
    """Skeletons of slots allowed to repeat (macro disclaimer-style risk line)."""
    out = set()
    for slot in BOILERPLATE_SLOTS:
        for zh, en in P[slot]:
            out.add(skeleton(zh.format(t="X"), "zh"))
            out.add(skeleton(en.format(t="X"), "en"))
    return out


def check(pack: dict, avoid=None) -> dict:
    d = compose_note(pack, avoid=avoid)
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
    assert not re.search(r"\{[a-z_0-9]+\}", blob), re.search(r".{20}\{[a-z_0-9]+\}.{20}", blob)
    assert "万美元 的" not in body and "亿美元 的" not in body
    assert 3.0 <= d["score"] <= 8.2
    return d


# ------------------------------------------------------------------ tests

def test_phrasebook():
    f = string.Formatter()
    for slot, variants in P.items():
        assert len(variants) >= 2, f"{slot}: only {len(variants)} variant(s)"
        for zh, en in variants:
            for txt in (zh, en):
                fields = {x[1] for x in f.parse(txt) if x[1]}
                assert fields, f"{slot}: variant without any coin-specific field: {txt[:40]}"


def test_structure_synthetic():
    a = check(copy.deepcopy(BASE))
    srcs = a["bodies"]["zh"].split("## 数据来源")[1]
    assert "[Arbitrum DAO votes on (treasury) plan](https://example.org/a%28b%29)" in srcs  # brackets neutralised
    meme = copy.deepcopy(BASE)
    meme.update(ticker="FART", name="Fartcoin", cg_id="fartcoin", lane="Meme", tags=["Meme"], chain=None, peers=[], unlocks=None, news=[])
    meme["cg"].update(categories=["Meme", "Solana Ecosystem"], fdv=None, max_supply=None, chg_30d=48.0, volume=6e8, mcap=1.1e9)
    meme["hist"] = {}
    meme["social"]["trending_pos"] = 3
    b = check(meme)
    assert "DefiLlama" not in b["bodies"]["zh"].split("数据快照")[1].split("快照时间")[0]
    assert a["bodies"]["zh"] != b["bodies"]["zh"]


def test_fixtures_compose():
    for pk in fixtures():
        d = check(pk)
        print(f"OK {pk['ticker']:<9} {d['profile']:<8} {d['score']:.1f} {d['titles']['zh']}")


def test_no_repeated_sentences_across_notes():
    seen: dict[str, str] = {}
    bp = boilerplate()
    dupes = []
    for pk in fixtures():
        d = compose_note(pk)
        for lang in ("zh", "en"):
            for sent in set(body_sentences(d["bodies"][lang], lang)):
                if skeleton(sent, lang) in bp:
                    continue
                key = f"{lang}:{sent}"
                if key in seen and seen[key] != pk["ticker"]:
                    dupes.append((seen[key], pk["ticker"], sent))
                seen.setdefault(key, pk["ticker"])
    assert not dupes, "repeated sentences:\n" + "\n".join(f"{a} / {b}: {s}" for a, b, s in dupes[:20])


def test_same_day_pairs_share_no_skeleton():
    packs = fixtures()
    bp = boilerplate()
    first = {pk["ticker"]: compose_note(pk) for pk in packs}
    bad = []
    for a, b in itertools.permutations(packs, 2):
        da = first[a["ticker"]]
        db = compose_note(b, avoid=[da["bodies"]])
        for lang in ("zh", "en"):
            ska = {skeleton(s, lang) for s in body_sentences(da["bodies"][lang], lang)}
            for s in body_sentences(db["bodies"][lang], lang):
                sk = skeleton(s, lang)
                if len(sk) >= 8 and sk in ska and sk not in bp:
                    bad.append((a["ticker"], b["ticker"], lang, s))
    assert not bad, f"{len(bad)} shared skeletons, e.g.:\n" + "\n".join(f"{x} -> {y} [{l}] {s}" for x, y, l, s in bad[:15])


def test_ilv_like_is_not_quiet():
    pk = copy.deepcopy(BASE)
    pk.update(ticker="ILV", name="Illuvium", cg_id="illuvium")
    pk["cg"].update(chg_30d=15.7, chg_7d=0.7, chg_1y=-73.0)
    d = check(pk)
    blob = d["bodies"]["zh"] + d["bodies"]["en"]
    assert d["labels"]["crowd"] == "warm"
    for bad in ("没有 FOMO", "没人吵架", "neither FOMO", "no-argument zone"):
        assert bad not in blob, bad


def test_volume_words_follow_threshold():
    pk = copy.deepcopy(BASE)
    pk["hist"].update(vol7_avg=1.2e8, vol30_avg=1.0e8)  # +20%: not a surge
    d = check(pk)
    assert "放量" not in d["bodies"]["zh"] and "缩量" not in d["bodies"]["zh"]
    pk["cg"]["volume"] = 5e7  # turnover ~4%: normal band, so the volume-trend finding can show
    pk["hist"].update(vol7_avg=2.0e8, vol30_avg=1.0e8)  # +100%
    d = check(pk)
    if "放量" in d["bodies"]["zh"]:
        assert d["signals"]["vol_trend"] >= TH["vol_surge"]


def test_zec_like_launch_ath_and_pullback():
    pk = copy.deepcopy(BASE)
    pk.update(ticker="ZEC", name="Zcash", cg_id="zcash", unlocks=None, peers=[], protocol=None)
    pk["cg"].update(price=1205, mcap=2.0e10, fdv=2.0e10, ath=3192, ath_date="2016-10-28", genesis="2016-10-28", ath_chg=-62,
                    chg_7d=-14, chg_30d=5, chg_1y=765, hashing="Equihash", circ=1.7e7, max_supply=2.1e7, categories=["Privacy Coins"])
    pk["hist"].update(ma200=624, ma50=1160, hi90=1653, lo90=457)
    pk["sector"] = {"median_30d": -1.2, "wavg_ex_30d": 6.2, "n": 12, "cat_name": "Privacy Coins", "dropped": 0}
    d = check(pk)
    zh = d["bodies"]["zh"]
    assert d["labels"]["crowd"] == "pullback"
    assert "上线初期报价" in zh and "距历史高点仍很远" not in zh
    assert "所在叙事偏冷" not in zh  # median of tiny coins says cold, cap-weighted says in line: no cold call


def test_audit_catches_contradictions():
    pk = copy.deepcopy(BASE)
    d = compose_note(pk)
    bodies = dict(d["bodies"])
    bodies["zh"] += "\nARB 处在没人吵架的区间，既没有 FOMO 也没有恐慌。"
    pk2 = copy.deepcopy(BASE)
    pk2["cg"]["chg_30d"] = 16.0
    from desk_analyst import Ctx, signals
    x = Ctx(pack=pk2)
    x.s = signals(pk2)
    x.labels["crowd"] = x.s["crowd"]
    assert any("quiet wording" in p for p in audit(pk2, x, bodies))
    meme_peer = copy.deepcopy(BASE)
    meme_peer["peers"][0]["meme"] = True
    try:
        compose_note(meme_peer)
    except RuntimeError as exc:
        assert "meme" in str(exc)
    else:
        raise AssertionError("meme peer in a non-meme note was not flagged")


def test_sector_fit_rules():
    rows = [{"cg": c, "ticker": t, "name": n, "mcap": m} for c, t, n, m in (
        ("floki", "FLOKI", "FLOKI", 2.6e8), ("the-sandbox", "SAND", "The Sandbox", 2.1e8), ("illuvium", "ILV", "Illuvium", 3.2e7),
        ("carv", "CARV", "CARV", 2.9e7), ("rollbit-coin", "RLB", "Rollbit Coin", 9e7), ("bora", "BORA", "BORA", 3.1e7),
        ("some-ai-agent", "AGNT", "Neural AI Agent", 3e7))]
    kept, dropped = ds.sector_fit(rows, "gaming", "illuvium", {"floki"}, False)
    ids = {r["cg"] for r in kept}
    assert {"floki", "carv", "rollbit-coin", "some-ai-agent"} <= set(dropped) and "floki" not in ids
    core = ds.sector_core("gaming", {"lanes": {}}, "GameFi")
    chosen, leader = ds.choose_peers(kept, "illuvium", 3.2e7, core)
    assert leader and leader["cg"] == "the-sandbox"
    assert "Smart Contract Platform" not in ds.drop_categories("zcash", ["Smart Contract Platform", "Privacy Coins"], None)


def test_headline_helpers():
    assert ds.mentions("Zcash ETF tops $1 billion", "Zcash", "ZEC")
    assert not ds.mentions("Gas fees fall on Ethereum", "Gas", "GAS")
    assert ds.JUNK_TITLE.search("We Asked ChatGPT Whether Zcash Holds $1,000")
    assert ds.clean_title("A [b] *c* | d") == "A (b) c / d"
    assert "security" in ds.tag_headline("Protocol drained in $4M exploit")


def test_random_perturbations_pass_audit():
    rnd = random.Random(7)
    packs = fixtures()
    for i in range(240):
        pk = copy.deepcopy(rnd.choice(packs))
        c = pk["cg"]
        c["chg_30d"] = rnd.uniform(-45, 60)
        c["chg_7d"] = rnd.uniform(-30, 30)
        c["chg_1y"] = rnd.uniform(-90, 900)
        c["volume"] = (c.get("mcap") or 1e8) * rnd.uniform(0.003, 0.8)
        h = pk.setdefault("hist", {})
        if h.get("vol30_avg"):
            h["vol7_avg"] = h["vol30_avg"] * rnd.uniform(0.4, 2.2)
        if h.get("ma200"):
            h["ma200"] = c["price"] / rnd.uniform(0.4, 2.5)
        pk["social"]["trending_pos"] = rnd.choice([None, None, None, 4])
        compose_note(pk)  # raises if any label contradicts its number


def main() -> None:
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()

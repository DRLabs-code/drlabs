# Aave (AAVE) research report

**DRLabs crypto research**  
**Published / data date: 7 September 2026 (Asia/Shanghai, UTC+8 / reader-local PT)**  
**Stance: research-neutral (not investment advice)**

> **One-line takeaway:** Aave is still the scale and brand leader in on-chain lending. V3 holds the bulk of liquidity; V4 (Hub & Spoke) went live on Ethereum mainnet in March 2026 and is still in a conservative-cap phase. Fundamentals hinge on the rate cycle, cross-chain share and DAO–Labs alignment — not a short-term token-price story.

---

## 1. Project overview

Aave is a decentralized, non-custodial liquidity protocol: users deposit assets into pools to earn interest, or borrow against over-collateralization. Smart contracts match supply and demand and liquidate risky positions without a custodian. The name comes from Finnish for “ghost”, a nod to transparent, invisible infrastructure.

**Problem it solves:** Traditional credit relies on intermediaries and underwriting. On-chain markets have long faced fragmented liquidity and collateral/risk parameters that are hard to extend modularly. Aave replaced early peer-to-peer matching with a pool model and kept iterating on risk isolation, multi-chain deployment and a native stablecoin (GHO).

**Positioning:** Core DeFi “money market” infrastructure. On DefiLlama, the Aave family (especially V3) has long led lending TVL. Official materials claim cumulative originations above the $1 trillion mark and more than half of decentralized lending (official-blog definition — cross-check against third-party TVL share).

**Brief history:** In 2017 Stani Kulechov (now Aave Labs CEO) launched peer-to-peer lending as ETHLend; the project later moved to liquidity pools, rebranded to Aave, and went live on Ethereum mainnet around early 2020. In October 2020 LEND migrated 100:1 into the AAVE governance token. Then came V2, multi-chain V3, GHO, Safety Module→Umbrella, and the 2026 V4 mainnet launch.

---

## 2. Product and mechanics

### 2.1 Lending markets and the rate model

- **Supply / borrow:** Suppliers receive interest-bearing receipts. Borrowing requires over-collateralization. Rates follow a utilization curve (flatter below optimal utilization, steep above). Supply rates are borrower interest minus protocol fees, shared among suppliers.
- **V3 architecture:** Liquidity is isolated by market (e.g. Ethereum Core / Prime). Pools on the same chain do not reuse funds across markets — better risk isolation, but new markets must bootstrap liquidity on their own.
- **eMode (Efficiency Mode):** Raises borrowing power for highly correlated assets (stable pairs, ETH/LST) and improves capital efficiency.
- **aToken:** V3 supply receipts are mostly rebasing aTokens; balances grow with interest and can be composed elsewhere in DeFi.

### 2.2 Liquidations

Positions with Health Factor below 1 can be liquidated. Liquidators repay part of the debt and receive collateral plus a bonus. The protocol depends on oracle prices; liquidation congestion, bad debt and oracle lag are the core tail risks in stress.

### 2.3 Aave V4 (status per official sources)

**Launch:** Official blog dated **30 March 2026** for V4 on Ethereum mainnet.

**Core change — Hub & Spoke:**

| Component | Role |
|------|------|
| Liquidity Hub | On-chain unified liquidity and accounting hub; sets credit/debit limits for Spokes |
| Spoke | User-facing entry; can set its own collateral, risk parameters and liquidation rules |
| Risk Premium | Extra borrow premium on top of the utilization rate, by collateral quality |
| Liquidation engine | Target Health Factor replaces a fixed close factor; variable bonuses; dust rules |

Official note: V4 launched with several Liquidity Hubs (Core / Prime / Plus and similar narratives). **Supply and borrow caps were deliberately conservative**, to be raised by the DAO after watching production. The UI side launched **Aave Pro** for V4. On security, official materials cite about 345 cumulative audit days, multiple firms and a Sherlock public contest (see the audit repo).

**Accounting:** Community and technical write-ups generally describe V4 moving toward ERC-4626 share accounting (versus V3 rebasing aTokens). Product UX follows official docs and the UI.

**Relationship to V3:** Official and governance materials are explicit that **V3 will keep running as long as it is needed**. V4 is the next unified-liquidity architecture; migration and share shift are a medium-term process.

### 2.4 Multi-chain deployment

Aave is live on Ethereum plus multiple L2s/sidechains and newer L1s (DefiLlama chain mix below). The official V4 path: prove it on Ethereum mainnet, then let the DAO add Spokes, raise caps, and push more networks.

### 2.5 GHO and savings products

**GHO** is Aave’s native, over-collateralized USD-pegged stablecoin: users mint (borrow) GHO against collateral and burn it on repay. Borrow interest mostly flows to the DAO treasury. DefiLlama stablecoin data around **7 September 2026** puts GHO circulating market cap at about **$698 million**, price about **$0.999**, close to $1.

![GHO circulating supply](charts/05_gho_circulating.png)

**Read:** GHO has a near-$700 million float and a stable peg so far. Versus USDT/USDC and newer yield-bearing stables it is still mid-sized. Growth depends on borrow demand, sGHO competitiveness and cross-chain liquidity.

**sGHO / Aave Savings Rate (ASR):** Governance is moving the savings side to an ERC-4626 vault (sGHO). In an August 2026 GHO Stewards proposal, ASR was discussed at about **4.50%** (with some chain GHO borrow rates raised in parallel) to match competing savings rates and retention. Execution follows on-chain parameters and the UI.

**GSM and other stability tools:** Used for peg defense and liquidity buffers. Depegs, cross-chain basis and rate mismatch remain product-level risks.

---

## 3. Token economics (AAVE)

| Item | Data (7 September 2026) | Source |
|------|----------------------|------|
| Max / total supply | 16,000,000 AAVE | Public token params / Etherscan |
| Circulating (implied) | ~15.54M (~97.1%) | DefiLlama mcap ÷ spot |
| Price | ~$134.55 | DefiLlama coins API |
| Circulating mcap | ~$2.09B | DefiLlama protocol mcap |
| FDV (at 16M) | ~$2.15B | Spot × max supply |
| 30-day change | ~+49% (draft CoinGecko print; not re-checked after API throttle) | CoinGecko (historical cite) |
| 1-year change | ~−55% (same) | CoinGecko (historical cite) |

![AAVE market cap and FDV](charts/04_aave_mcap_fdv.png)

**Read:** Circulation is close to fully diluted; mcap and FDV gap is small (~3%). The usual “unlock overhang” story is weak. Token elasticity comes more from governance premium, expected DAO revenue and risk appetite than from supply squeeze.

**Uses:**

1. **Governance:** Aave DAO (forum → TEMP CHECK / ARFC → AIP) votes on parameters, listings, fees and treasury spend.  
2. **Safety and incentives:** The historical Safety Module used **stkAAVE** and similar assets for slashing risk plus incentives. It has been upgraded to **Umbrella** (aTokens / related assets covering bad debt, with automated slashing). stkAAVE may keep some utility and incentives in the transition, but the official help center says it is no longer the preferred bad-debt cover asset.  
3. **Value-capture narrative:** The **“Aave Will Win” framework** passed around April 2026 directs Aave-branded product revenue to the DAO treasury, strengthening “holding AAVE ≈ economic rights in the protocol and brand”. Paths for app-layer revenue (Aave Pro / App and similar) into the treasury follow governance execution.

**Unlocks:** Fixed 16 million supply, almost all circulating; remainder mainly in ecosystem reserve/incentive contracts. **No material cliff unlock found.** Near-term supply pressure is more from incentive emissions and treasury ops than classic vesting.

---

## 4. Market and fundamentals

> Note: data vendors define “TVL” differently. DefiLlama protocol TVL is usually close to “net locked” (supply minus borrows and similar adjustments). Aavescan also shows supply, borrows and net TVL. Charts here use **DefiLlama’s auditable API**. Aavescan is front-end rendered and could not be scraped stably this round, so it is not used for standalone charts.

### 4.1 Scale

| Metric | Value | Date / source |
|------|------|-----------|
| Aave protocol TVL (DefiLlama parent) | ~**$18.40B** | 2026-09-07, [DefiLlama API](https://defillama.com/protocol/aave) |
| Supply (est.) / borrows / net TVL | ~**$31.2B / $12.85B / $18.4B** | DefiLlama: supply ≈ net TVL + Borrowed |
| Aave V3 TVL | ~**$17.64B** | DefiLlama protocols |
| Aave V4 TVL | ~**$0.384B** | Same (conservative caps after launch; still small) |
| Aave V2 TVL | ~**$0.112B** | Same (legacy) |

![Aave TVL by version](charts/01_aave_tvl_versions.png)

**Read:** Of ~$18.4B parent net TVL, V3 is about 96%. V4 is about $384M — conservative caps plus early migration. The architecture story is live; liquidity has not switched yet.

![Supply, borrows and net TVL](charts/02_aave_supply_borrow_net.png)

**Read:** Borrows ~$12.9B and net TVL ~$18.4B put utilization in a fee-producing range. Supply-side (net + borrowed) ~$31.2B shows the protocol’s balance-sheet scale.

![Aave net TVL trend](charts/07_aave_tvl_trend.png)

**Read:** Net TVL over the past year rolled over from a late-2025 peak, stepped down mid-2026, then recovered in August–September to about $18.4B — **still the scale leader, clearly cyclical**, tightly tied to risk assets and stablecoin flows.

### 4.2 Revenue and fees (DefiLlama Fees)

| Metric | Approx. | Source |
|------|------|------|
| Protocol fees, 30d | ~**$32.8M** | DefiLlama fees/aave, 2026-09-07 |
| Protocol revenue, 30d | ~**$4.57M** | Same (dailyRevenue) |
| Fees / revenue, all-time | ~**$2.28B / $309M** | Same |

![30-day fees vs protocol revenue](charts/03_aave_fees_vs_revenue_30d.png)

**Read:** Last 30 days ~$32.8M fees and ~$4.57M protocol revenue, a capture rate of about **13.9%** (the rest mostly to suppliers). Fee scale leads lending, but token-layer capture still depends on reserve factor, GHO interest and “Aave Will Win” execution — not the fee headline alone.

**Note:** The last day of a daily revenue series may be incomplete; prefer 7/30-day aggregates.

### 4.3 Competitive share (DefiLlama, 7 September 2026)

| Protocol | Approx. TVL |
|------|----------|
| Aave V3 | $17.6B |
| Morpho Blue | $9.8B |
| SparkLend | $4.5B |
| Compound V3 | $1.4B |
| Fluid Lending | $0.75B |
| Aave V4 | $0.38B |
| Euler V2 | $0.35B |

![Lending competitor TVL](charts/06_lending_competitors_tvl.png)

**Read:** Aave V3 still leads by a wide margin. Morpho Blue at ~$9.8B is the closest follower, competing on yield and capital efficiency. Compound V3 share has shrunk. Spark sits in the Sky orbit and is both competitor and complement to Aave liquidity.

### 4.4 Chain mix (DefiLlama currentChainTvls, excluding borrowed/staking/pool2)

About **84.8%** of net TVL is on **Ethereum** (~$15.6B); then Base, Plasma, Arbitrum, Monad, Avalanche, BSC, Polygon and others. Total borrows ~**$12.85B**. Multi-chain expansion is underway, but risk and revenue remain highly concentrated on Ethereum.

---

## 5. Governance, team / foundation background

- **Aave Labs:** Product and R&D entity led by founder **Stani Kulechov**, covering protocol iteration, front ends and brand work.  
- **Aave DAO:** AAVE holders and delegates manage parameters, listings, treasury and major upgrades via [governance.aave.com](https://governance.aave.com) and on-chain governance.  
- **Service-provider stack:** Historically BGD Labs, risk providers, ACI and others contributed to development and governance ops. Around 2026, public friction over funding and power (some providers reduced or stopped contributing) is a governance watch item.  
- **“Aave Will Win” framework (~passed April 2026):** Directs Aave-branded product revenue to the DAO; gives Labs about a one-year budget; commits to a follow-on proposal for brand/IP to sit in a community-protection vehicle (foundation-like). CoinDesk and others called it a milestone ending the “who gets revenue” fight, while also raising centralization and accountability questions.  
- **Risk and parameter ops:** Risk Steward, GHO Stewards and similar roles can tweak rates inside a mandate — faster response, more delegated risk.

Public information does not show a single traditional foundation fully replacing Labs. The final legal structure of any foundation/IP vehicle follows later AIPs. **This note flags: framework passed, details still to watch.**

---

## 6. Competition and moat

**Moat (relatively sturdy):**

1. **Liquidity network effects and brand trust:** Deep pools cut large-size slippage and rate shock; institutions and treasuries prefer battle-tested venues.  
2. **Multi-chain and product matrix:** V3 multi-market + GHO + Umbrella + Horizon (RWA lending, listed separately on DefiLlama) + V4 modular Spokes.  
3. **Liquidation and risk experience:** Multiple crypto stress cycles; official materials stress production pressure-test history.  
4. **Governance and integration breadth:** Default wiring cost for wallets, aggregators and structured products.

**Challenges:**

- **Morpho and peers:** Higher capital efficiency and curated yield can siphon marginal deposits.  
- **V4 migration friction:** Dual-version split; conservative caps keep V4 share small near term.  
- **DAO–Labs tension:** Affects predictability of external contributors and upgrade cadence.  
- **Stablecoin wars:** sUSDS, Ethena and other savings products squeeze GHO/sGHO growth.

---

## 7. Risks (exposures only, no exploit detail)

| Category | Exposure |
|------|--------|
| Smart contracts | V3/V4/Umbrella/GHO complexity; attack surface widens at new-architecture launch; depends on ongoing audits and formal methods |
| Oracles | Lag or manipulation can cause bad liquidations or bad debt; multi-chain multiplies oracle dependence |
| Governance | Malicious or rushed proposals, parameter errors, delegate concentration; Steward permission edges |
| Regulation | Lending and stables face securities/stablecoin uncertainty by jurisdiction; front end and Labs entity domicile |
| GHO / stables | Depeg, thin cross-chain liquidity, unsustainable savings rate, GSM exhaustion |
| Liquidity and black swans | Cascade liquidations, stable depegs, LST discounts, bridge risk, related-protocol contagion |
| Ops and politics | Provider exits, brand/IP disputes, incentives too thin vs target coverage |

Umbrella aligns slashed assets with potential bad-debt assets and adds a deficit buffer. Official help-center language says the historical Safety Module long went without an actual slash — **that is not a promise of zero in the future**.

---

## 8. Catalysts and tracking metrics

**Potential catalysts:**

- V4 cap raises, new Spokes (institution/RWA/eMode-like) and more chain deploys  
- GHO float and sGHO deposits breaking out; ASR and borrow-rate policy effectiveness  
- DAO revenue-routing execution and any “buyback / incentive / dividend” proposals (evaluate separately if they appear)  
- Brand-foundation details landing, cooling the governance-split narrative  
- A rising-rate cycle lifting fees and revenue

**Suggested weekly metrics:**

1. DefiLlama: Aave parent / V3 / V4 TVL and chain mix  
2. Fees and revenue (7d/30d) plus utilization  
3. GHO circulating mcap, peg deviation, sGHO TVL, ASR  
4. Umbrella stake by asset versus target coverage  
5. Morpho / Spark / Compound TVL relative share  
6. Governance forum: V4 parameters, Risk Steward, provider budgets and foundation proposals  
7. AAVE circulating supply and treasury holdings (on-chain)

---

## 9. Conclusion and watchlist

**Conclusion:** In 2026 Aave is still DeFi lending’s “systemic protocol”: net TVL around $18B, fee scale in the lead, V4 live but not yet carrying core liquidity. On the token, supply is nearly fully circulating; value is more bound to DAO revenue rights and a governance premium. The 2026 governance framework strengthened “revenue to the DAO”, but execution quality and contributor-stack stability still need proof. For research-oriented readers, Aave fits as a **lending-sector benchmark holding and infrastructure watch**. Trading decisions need a separate view of macro rates, risk appetite and competitive leakage.

**Watchlist:**

- [ ] Whether V4 net TVL keeps breaking out (migration slope versus V3)  
- [ ] Whether 30-day protocol revenue recovers with utilization (versus 2025 peaks)  
- [ ] Whether GHO stays near $1 with net inflows on the savings side  
- [ ] Whether Umbrella coverage hits governance targets without odd deficits  
- [ ] Whether DAO–Labs relations and external contributors restabilize  
- [ ] Whether Morpho and others keep eating marginal growth

---

## 10. Objective summary and buy score

**As-of date: 7 September 2026 (Asia/Shanghai, UTC+8)**

This section is a structured score under DRLabs’ internal research framework, used to compare relative attractiveness inside the same sector. **It is not a buy, hold or sell recommendation for any reader** (see the disclaimer at the end).

### 10.1 Score scale (1–10)

| Score | Meaning (research definition) |
|------|------------------|
| 1 | Fundamentals badly impaired or a structural flaw that is hard to accept; framework leans avoid |
| 2–3 | Major uncertainty dominates; negatives clearly outweigh moat and cash-flow logic |
| 4–5 | Watchable but limited appeal; only for very high risk appetite or event-driven size |
| 6 | Acceptable fundamentals with clear debate points; discuss as a watch or small satellite |
| 7 | Sector position and fundamentals lean positive, still constrained by competition, governance or valuation |
| 8 | Stronger relative appeal; several factors score high; remainder is mostly execution and macro |
| 9 | Evidence chain is very strong, negatives limited; framework leans high-confidence overweight discussion |
| 10 | Extremely scarce “must own” case; moat, growth, capture and valuation almost without a major hole |

### 10.2 Factors and weights

| Factor | Weight | Score (1–10) | Brief basis (2026-09-07) |
|------|------|-------------|------------------------|
| Fundamentals / moat | 25% | **8.0** | Net TVL ~$18.4B, brand and integrations lead; deep liquidation and multi-chain experience |
| Growth and share | 20% | **6.5** | Still #1, but Morpho Blue ~$9.8B is close; V4 share still small |
| Token value capture | 20% | **6.5** | “Aave Will Win” strengthens DAO revenue; 30d revenue/fees ~13.9%; execution pace unproven |
| Risk (higher = more contained) | 20% | **5.5** | Contract and cross-chain complexity, governance friction, regulation and stablecoin competition are real constraints |
| Valuation and timing | 15% | **6.5** | Near fully circulating, small mcap/FDV gap; large 1y drawdown then a bounce — timing room exists, not extreme undervaluation proof |

**Weighted score:**  
`0.25×8.0 + 0.20×6.5 + 0.20×6.5 + 0.20×5.5 + 0.15×6.5 = 6.675` → **final buy score: 6.7 / 10**

### 10.3 Why 6.7, not higher or lower

- **Not 8+:** Morpho and peers can contest marginal share; V4 liquidity migration is slow; DAO–Labs and provider relations still noisy; protocol revenue capture versus fees is limited, and governance execution is path-dependent.  
- **Not below 5:** Scale, fee volume and brand trust still lead Compound and other legacy peers; supply is clean; GHO plus revenue-to-DAO is a medium-term option; TVL has repaired from the mid-year low.  
- **Debatable:** Readers who overweight “token = cash flow” and want higher capture certainty may print 5–6; readers who overweight systemic-infra scarcity and institutional adoption may print 7–7.5. This note takes the weighted center **6.7** — “a positively biased sector-benchmark watch, not an unconditional overweight”.

---

## 11. Disclaimer

This report is compiled by DRLabs from public information and is **for general information and research discussion only**. It is not, and should not be read as, investment advice, a recommendation, an offer, a solicitation or any form of commitment regarding securities, digital assets or other financial products.

Crypto assets and DeFi protocols are highly volatile and uncertain. Prices and protocol parameters can move violently in a short time. Investors can lose part or all of their principal. Readers should judge independently based on their finances, risk tolerance and objectives, and consult qualified advisers if needed. **Any decision based on this report, and its consequences, is the reader’s own.**

The “buy score” and factor scores are **subjective quantifications** under a stated framework and public-data constraints, used for internal comparison and discussion. **They are not a buy or sell recommendation on any digital asset** and do not guarantee future market performance.

Data, charts and third-party sources cited (including but not limited to DefiLlama, official docs and governance forums) may differ in definition, be delayed, incomplete or wrong. DRLabs and the author make no express or implied warranty of accuracy, completeness, timeliness or fitness, and are not liable for any direct or indirect loss from using or relying on this report. Markets and protocol state change quickly; re-check original sources and on-chain state before citing.

---

## 12. Sources

1. [Aave V4 Overview (official docs)](https://aave.com/docs/aave-v4)  
2. [Understanding Aave V4’s Architecture (official blog)](https://aave.com/blog/understanding-aave-v4s-architecture)  
3. [Aave V4 is Live on Ethereum (official blog, 2026-03-30)](https://aave.com/blog/aave-v4-live-ethereum)  
4. [Aave website](https://aave.com)  
5. [DefiLlama — Aave](https://defillama.com/protocol/aave)  
6. [DefiLlama — Aave V3](https://defillama.com/protocol/aave-v3)  
7. [DefiLlama — GHO stablecoin](https://defillama.com/stablecoin/gho)  
8. [Aavescan Protocol Totals](https://aavescan.com/protocol/totals) (not used for charts this round)  
9. [CoinGecko — Aave](https://www.coingecko.com/en/coins/aave) (some return figures are historical cites; API throttled on chart day)  
10. [Umbrella help](https://aave.com/help/umbrella/umbrella)  
11. [BGD: Safety Module — Umbrella (governance forum)](https://governance.aave.com/t/bgd-aave-safety-module-umbrella/18366)  
12. [GHO Stewards August 2026 rate and ASR update](https://governance.aave.com/t/gho-stewards-august-2026-gho-borrow-rate-and-aave-savings-rate-update/25534)  
13. [stkGHO → sGHO migration tool proposal](https://governance.aave.com/t/direct-to-aip-stkgho-sgho-migration-tool/25250)  
14. [[ARFC] Aave Will Win Framework](https://governance.aave.com/t/arfc-aave-will-win-framework/24352)  
15. [CoinDesk: Aave Will Win vote](https://www.coindesk.com/tech/2026/04/13/aave-passes-landmark-vote-ending-months-long-fight-over-who-controls-protocol-revenue)  
16. [DL News: DAO vs Labs friction](https://www.dlnews.com/articles/defi/aave-dao-members-accuse-stani-kulechov-of-power-grab/)  
17. [Aave V4 GitHub overview](https://github.com/aave/aave-v4/blob/main/docs/overview.md)  
18. [Wikipedia — Aave (background)](https://en.wikipedia.org/wiki/Aave)  
19. [Etherscan — AAVE Token](https://etherscan.io/token/0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDAE9)  
20. [Aave governance forum](https://governance.aave.com)  
21. DefiLlama API: `/protocol/aave`, `/protocols`, `/summary/fees/aave`, `coins.llama.fi`, `stablecoins.llama.fi` (chart pull 2026-09-07)

---

*Report version: 7 September 2026 (Asia/Shanghai). Chart folder: `charts/`. Do not use this text for illegal activity or market manipulation.*

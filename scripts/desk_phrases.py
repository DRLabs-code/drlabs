"""Phrasebook for desk notes. Every slot has several (zh, en) variants; desk_analyst.Voice picks
one deterministically per coin/day and skips any variant whose sentence skeleton already appears
in another note published the same day. Every variant carries at least one coin-specific field
(ticker, name, a number), so two notes never print the same sentence.

Wording rules (checked by tests): "FOMO" only in the frenzy crowd slots, 放量 / 缩量 only in the
volume slots, 过热 only when turnover is hot, 跑赢 / 跑输 only in the relative-strength slots.
"""

P: dict[str, list[tuple[str, str]]] = {}

# ------------------------------------------------------------------ market: trend
P["trend_up"] = [
    ("{t} 现价 {p}，高出 200 日均线 {g200}%{g50z}。只要 {t} 回踩不破均线，中期上行结构就还在。",
     "{t} trades at {p}, {g200}% above its 200-day average{g50e}. As long as {t}'s pullbacks hold the average, the medium-term uptrend stands."),
    ("价格 {p} 位于 200 日均线上方 {g200}%{g50z}，{t} 的趋势资金没有离场迹象，回调更可能被当作加仓窗口。",
     "At {p}, {t} sits {g200}% over the 200-day{g50e}; trend money shows no sign of leaving, so dips are more likely to be bought."),
    ("以 {p} 计，{t} 领先 200 日均线 {g200}%{g50z}。均线多头排列时，{t} 破位的标准是有效跌回均线，而不是一两根阴线。",
     "At {p} {t} leads its 200-day by {g200}%{g50e}. With the averages stacked bullishly, a break for {t} means closing back under the average, not one red candle."),
    ("{t} 在 200 日均线之上 {g200}%（现价 {p}{g50z}），中期方向仍在多头手里。",
     "{t} is {g200}% above the 200-day (spot {p}{g50e}); the medium-term direction still belongs to buyers."),
]
P["trend_up_ext"] = [
    ("{t} 现价 {p}，比 200 日均线高出 {g200}%{g50z}。偏离度本身就是 {t} 的风险：哪怕只回归一半，也对应约 {half}% 的回撤空间。",
     "{t} at {p} is {g200}% above its 200-day{g50e}. The gap itself is a risk for {t}: reverting even half of it means roughly a {half}% drawdown."),
    ("{t} 价格 {p} 已把 200 日均线甩开 {g200}%{g50z}。{t} 的趋势向上没有疑问，但离均线越远，追高的赔率越差，回撤一半偏离就是 {half}% 左右。",
     "At {p}, {t} has left the 200-day {g200}% behind{g50e}. The {t} trend is plainly up, but the further from the mean, the worse the odds for chasers; giving back half the gap is about {half}%."),
    ("{t} 高出 200 日均线 {g200}%（现价 {p}{g50z}），属于明显的趋势延伸。在 {t} 这样的延伸行情里，向均线回归约 {half}% 是常见的休整，并不等于趋势结束。",
     "{t} sits {g200}% over the 200-day (spot {p}{g50e}), a clear trend extension. In an extension like {t}'s, a ~{half}% drift back toward the mean is a routine pause, not the end of the trend."),
]
P["trend_down"] = [
    ("{t} 现价 {p}，仍低于 200 日均线约 {g200}%{g50z}。在均线压制之下，{t} 的利好要先消化上方的套牢筹码。",
     "{t} trades at {p}, about {g200}% under its 200-day average{g50e}. Under the averages, any good news on {t} first has to absorb trapped supply overhead."),
    ("价格 {p} 距 200 日均线还差 {g200}%{g50z}，{t} 处在下行趋势中，左侧抄底要付出时间成本。",
     "At {p}, {t} is still {g200}% short of the 200-day{g50e}; it is in a downtrend, and bottom-fishing costs time."),
    ("{t} 被 200 日均线压在下方 {g200}%（现价 {p}{g50z}），收复均线之前，反弹更容易被当作离场机会。",
     "{t} is held {g200}% below the 200-day (spot {p}{g50e}); until the average is reclaimed, rallies are more likely to be used as exits."),
    ("以 {p} 计，{t} 落后 200 日均线 {g200}%{g50z}。趋势派不会在这里买 {t}，承接主要来自逆向资金。",
     "At {p}, {t} trails its 200-day by {g200}%{g50e}. Trend followers will not buy {t} here; support comes mainly from contrarian money."),
]
P["trend_mixed"] = [
    ("{t} 现价 {p}，相对 200 日均线 {g200s}、相对 50 日均线 {g50s}。{t} 的短期和中期信号打架，方向要等其中一条均线被有效突破。",
     "{t} at {p} is {g200s} vs the 200-day and {g50s} vs the 50-day. {t}'s short and medium signals disagree; direction waits for one average to give way."),
    ("价格 {p} 夹在两条均线之间（200 日 {g200s}，50 日 {g50s}），{t} 眼下没有趋势可跟，只有区间可做。",
     "At {p}, {t} is wedged between the averages (200-day {g200s}, 50-day {g50s}); there is no trend to follow, only a range to trade."),
    ("{t} 的均线信号互相矛盾：200 日 {g200s}，50 日 {g50s}（现价 {p}）。{t} 这种结构通常以一次方向选择收场。",
     "{t}'s averages contradict each other: 200-day {g200s}, 50-day {g50s} (spot {p}). Setups like {t}'s usually end with a decisive break one way."),
]
# ------------------------------------------------------------------ market: relative strength
P["rs30_up"] = [
    ("近 30 日 {t} {c30}，同期比特币 {b30}，相对强弱 {rs}。资金在主动选择 {t}，而不只是跟着大盘走。",
     "Over 30 days {t} is {c30} vs Bitcoin {b30}, relative strength {rs}. Money is choosing {t}, not just riding beta."),
    ("{t} 30 日 {c30}，比特币 {b30}，{deg}跑赢 {rs}。超额收益说明有增量买盘专门冲着 {t} 来。",
     "{t} is {c30} over 30 days against Bitcoin's {b30}, {deg_en} ahead by {rs}. Excess return means some buyers are here specifically for {t}."),
    ("拿比特币做基准，{t} 过去 30 日多走了 {rs}（{c30} 对 {b30}）。{t} 跑赢的这部分，比特币的贝塔解释不了。",
     "Benchmarked to Bitcoin, {t} gained an extra {rs} over 30 days ({c30} vs {b30}). Bitcoin beta does not explain that excess on {t}."),
]
P["rs30_dn"] = [
    ("近 30 日 {t} {c30}，同期比特币 {b30}，相对强弱 {rs}。大盘的风险偏好没有传导到 {t}，弱势本身就是信息。",
     "Over 30 days {t} is {c30} vs Bitcoin {b30}, relative strength {rs}. Market risk appetite is not reaching {t}; the weakness is information."),
    ("{t} 30 日 {c30}，比特币 {b30}，{deg}跑输 {rsabs}。资金在别处，{t} 需要自己的理由把它们拉回来。",
     "{t} is {c30} over 30 days vs Bitcoin's {b30}, {deg_en} behind by {rsabs}. Money is elsewhere; {t} needs its own reason to win it back."),
    ("以比特币为基准，{t} 30 日少走了 {rsabs}（{c30} 对 {b30}）。像 {t} 这样持续跑输，往往先于基本面坏消息出现。",
     "Against Bitcoin, {t} lost {rsabs} of relative ground in 30 days ({c30} vs {b30}). Persistent underperformance like {t}'s often shows up before the bad fundamental news does."),
]
P["rs1y_up"] = [
    ("拉长到一年，{t} {c1y}，比特币 {b1y}。长周期赢家的回调，通常比长周期输家的反弹更值得研究，{t} 属于前者。",
     "Over a year {t} is {c1y} vs Bitcoin {b1y}. Pullbacks in long-cycle winners usually deserve more work than bounces in losers, and {t} is in the first group."),
    ("一年维度 {t} {c1y}，同期比特币 {b1y}，{deg}跑赢 {rs}。这种量级的超额，说明市场给 {t} 换了一套估值逻辑。",
     "Over twelve months {t} is {c1y} against Bitcoin's {b1y}, {deg_en} ahead by {rs}. Outperformance of that size means the market has re-rated {t}'s story."),
    ("{t} 过去一年 {c1y}，比特币 {b1y}。{t} 的持有者账面浮盈很厚，后面要防的是获利盘兑现，而不是缺买盘。",
     "{t} is {c1y} over a year vs Bitcoin {b1y}. {t} holders sit on fat gains; the thing to watch is profit-taking, not a lack of bids."),
]
P["rs1y_dn"] = [
    ("拉长到一年，{t} {c1y}，比特币 {b1y}。持有 {t} 的机会成本已经很高，反弹要先证明不是死猫跳。",
     "Over a year {t} is {c1y} vs Bitcoin {b1y}. The opportunity cost of holding {t} is already high; a bounce must prove it is not a dead-cat."),
    ("一年维度 {t} {c1y}，同期比特币 {b1y}，{deg}跑输 {rsabs}。{t} 的长期持有者大多在亏损，反弹途中的解套卖盘会很密。",
     "Over twelve months {t} is {c1y} against Bitcoin's {b1y}, {deg_en} behind by {rsabs}. Most long-term {t} holders are under water, so rallies meet dense break-even selling."),
    ("{t} 过去一年 {c1y}，比特币 {b1y}。这条长期曲线说明，{t} 的上一轮叙事已被市场{deg}折价。",
     "{t} is {c1y} over a year vs Bitcoin {b1y}. That long curve says the market has marked down {t}'s last story."),
]
P["rss_up"] = [
    ("同板块 {n} 个标的 30 日涨跌{basis} {med}，{t} 是 {c30}，领先 {rs}。板块内的超额收益在 {t} 身上。",
     "The sector's {n} names have a 30-day {basis_en} of {med}; {t} is {c30}, ahead by {rs}. The in-sector alpha sits with {t}."),
    ("放到 {n} 个同行里看，{t} 30 日 {c30}，高出板块{basis} {rs}（板块 {med}）。资金在板块内部向 {t} 集中。",
     "Among {n} peers, {t} is {c30} over 30 days, {rs} above the sector {basis_en} ({med}). Money inside the sector is concentrating on {t}."),
]
P["rss_dn"] = [
    ("同板块 {n} 个标的 30 日涨跌{basis} {med}，{t} 是 {c30}，落后 {rsabs}。板块没有拖累它，是 {t} 自己弱。",
     "The sector's {n} names have a 30-day {basis_en} of {med}; {t} is {c30}, behind by {rsabs}. The sector is not dragging it; {t} is weak on its own."),
    ("放到 {n} 个同行里看，{t} 30 日 {c30}，比板块{basis}低 {rsabs}（板块 {med}）。资金在板块内部绕开了 {t}。",
     "Among {n} peers, {t} is {c30} over 30 days, {rsabs} below the sector {basis_en} ({med}). Money inside the sector is going around {t}."),
]
# ------------------------------------------------------------------ market: ATH
P["ath_deep"] = [
    ("{t} 的历史高点 {ath}（{athd}），现价低 {athp}%。这不是 {t} 便宜的证据：{year} 年的买家还在上方等解套，每次反弹都会遇到卖压。",
     "{t}'s ATH is {ath} ({athd}); price is {athp}% below it. That is not proof {t} is cheap: {year} buyers are still overhead waiting to get out, and each rally meets supply."),
    ("距 {athd} 的历史高点 {ath}，{t} 已回撤 {athp}%。{t} 上一轮的叙事已被市场重新定价，新叙事要靠新数据来撑。",
     "From its {ath} ATH on {athd}, {t} is down {athp}%. {t}'s last-cycle story has been repriced; a new one needs new data."),
    ("{t} 现价只有 {athd} 高点 {ath} 的零头（回撤 {athp}%）。{t} 的反弹空间看起来大，但每一段都要穿过历史套牢区。",
     "{t} trades at a fraction of its {athd} high of {ath} (down {athp}%). {t} looks like it has room to run, but every leg up passes through old trapped supply."),
]
P["ath_near"] = [
    ("{t} 现价距历史高点 {ath} 只差 {athp}%，上方几乎没有套牢盘。{t} 进入价格发现阶段后波动会放大，追高要接受更宽的止损。",
     "{t} is only {athp}% off its {ath} ATH, so there is little trapped supply overhead. Price discovery widens {t}'s swings; chasers need wider stops."),
    ("离 {ath} 的历史高点还有 {athp}%，{t} 进入少有阻力的区域；真正的考验是创新高后能否站稳。",
     "{athp}% from the {ath} ATH, {t} is in a zone with little resistance; the real test is whether it holds after a new high."),
]
P["ath_launch"] = [
    ("CoinGecko 记录的 {t} 历史高点 {ath} 出现在 {athd}，紧挨上线日 {genesis}，属于流动性极低时的成交价，参考意义有限。衡量 {t} 更有用的参照是近 90 日高点 {hi90}，现价距其 {from_hi}。",
     "CoinGecko's {t} ATH of {ath} printed on {athd}, right after the {genesis} launch, an illiquid opening trade of limited use. A better reference for {t} is the 90-day high of {hi90}; price is {from_hi} from it."),
    ("{t} 的“历史高点” {ath}（{athd}）是上线初期（创世 {genesis}）的极端报价，不代表可交易的筹码成本。我们改用 {t} 近 90 日高点 {hi90} 衡量位置，现价距其 {from_hi}。",
     "{t}'s 'ATH' of {ath} ({athd}) is a launch-week print (genesis {genesis}), not a tradable cost basis. We use {t}'s 90-day high of {hi90} instead; price is {from_hi} from it."),
]
# ------------------------------------------------------------------ market: short-term swings
P["pullback7"] = [
    ("不过最近 7 日 {t} 回落 {c7abs}，这是在{ctx}之后的第一次明显降温，多空分歧会在这里放大。",
     "Over the last 7 days, though, {t} fell {c7abs}, the first clear cooling after {ctx_en}; this is where bulls and bears disagree most."),
    ("短线上 {t} 7 日 {c7}。{ctx}之后的这类回撤，通常用来检验 {t} 新买家的持有意愿。",
     "Short term, {t} is {c7} over 7 days. A pullback like this after {ctx_en} tests how committed {t}'s new buyers are."),
]
P["spike7"] = [
    ("短线上 {t} 7 日 {c7}，加速明显，短期获利盘会随时兑现。",
     "Short term {t} is {c7} over 7 days, a sharp acceleration; short-term profit-takers can hit the bid at any time."),
    ("最近 7 日 {t} 急拉 {c7}，节奏快于 30 日趋势（{c30}），追入的风险收益比在变差。",
     "{t} jumped {c7} in 7 days, faster than its 30-day trend ({c30}); the risk/reward for chasing is getting worse."),
]
# ------------------------------------------------------------------ market: turnover / volume
P["turn_hot"] = [
    ("{t} 24 小时成交 {vol}，换手率约 {tv}%{peerz}{trendz}。{t} 这种换手更像交易盘在博弈，长线资金并没有沉淀下来。",
     "{t} printed {vol} in 24h volume, about {tv}% turnover{peere}{trende}. Turnover like {t}'s is traders flipping, not long-term money settling in."),
    ("一天换手约 {tv}%（成交 {vol}{peerz}{trendz}），{t} 的筹码在快速易手，价格对消息和情绪都极度敏感。",
     "About {tv}% of {t} changed hands in a day ({vol}{peere}{trende}); holders rotate fast and price is hypersensitive to news and mood."),
]
P["turn_thin"] = [
    ("{t} 24 小时成交 {vol}，换手率只有约 {tv}%{peerz}{trendz}。机构级仓位进出 {t} 会明显推动价格，这本身就是折价理由。",
     "{t} did {vol} in 24h volume, only about {tv}% turnover{peere}{trende}. Institutional size would move {t}'s price, which is itself a reason for a discount."),
    ("换手仅约 {tv}%（成交 {vol}{peerz}{trendz}），{t} 的流动性是硬约束：想进容易，想按计划出很难。",
     "Turnover is only about {tv}% ({vol}{peere}{trende}); liquidity is a hard constraint for {t}: easy to get in, hard to get out on schedule."),
]
P["turn_rel_hot"] = [
    ("{t} 换手率约 {tv}%，同行中位数约 {pt}%{trendz}。资金和注意力在 {t} 身上停留得更久，这在同市值标的里不多见。",
     "{t} turns over about {tv}% vs a peer median of about {pt}%{trende}. Money and attention linger on {t} longer than at most peers of similar size."),
    ("同样的市值档位，{t} 的换手（约 {tv}%）是同行中位数（约 {pt}%）的 {x} 倍{trendz}，交易者明显更偏爱它。",
     "At a similar size, {t}'s turnover (~{tv}%) is {x}x the peer median (~{pt}%){trende}; traders clearly prefer it."),
]
P["turn_rel_cold"] = [
    ("{t} 换手率约 {tv}%，同行中位数约 {pt}%{trendz}。同样的市值，资金却不愿意交易 {t}，流动性折价会一直存在。",
     "{t} turns over about {tv}% against a peer median of about {pt}%{trende}. At a similar size, money prefers to trade elsewhere than {t}; a liquidity discount persists."),
    ("{t} 的换手（约 {tv}%）只有同行中位数（约 {pt}%）的一小部分{trendz}，交易深度是它和同行之间实打实的差距。",
     "{t}'s turnover (~{tv}%) is a fraction of the peer median (~{pt}%){trende}; depth is a real gap between it and its peers."),
]
P["vol_up"] = [
    ("{t} 近 7 日日均成交较前 30 日 {vt}，属于明显放量，当前换手约 {tv}%{peerz}。放量要配合 {t} 的价格方向，才说明有新资金在表态。",
     "{t}'s 7-day average volume is {vt} vs the prior 30 days, a clear expansion; turnover about {tv}%{peere}. Volume expanding in the direction of {t}'s price is new money voting."),
    ("成交在放量：{t} 7 日均量比前 30 日 {vt}（换手约 {tv}%{peerz}）。{t} 的关注度回来了，接下来看价格能否跟上。",
     "Volume is expanding: {t}'s 7-day average is {vt} vs the prior 30 days (turnover ~{tv}%{peere}). Attention on {t} is back; next is whether price follows."),
]
P["vol_dn"] = [
    ("{t} 近 7 日日均成交较前 30 日 {vt}，明显缩量，换手约 {tv}%{peerz}。{t} 缩量说明分歧在减少，也说明关注度在流失。",
     "{t}'s 7-day average volume is {vt} vs the prior 30 days, a clear contraction; turnover about {tv}%{peere}. Less {t} volume means less disagreement, and less attention."),
    ("成交在缩量：{t} 7 日均量比前 30 日 {vt}（换手约 {tv}%{peerz}）。没人交易的时候，{t} 的价格往往由少数大单决定。",
     "Volume is contracting: {t}'s 7-day average is {vt} vs the prior 30 days (turnover ~{tv}%{peere}). When few trade {t}, a handful of large orders sets the price."),
]
P["vola_hi"] = [
    ("{t} 30 日年化波动率约 {v30}%{mddz}。同样的风险预算，{t} 的仓位应该只有比特币仓位的一小部分。",
     "{t}'s 30-day annualised volatility is about {v30}%{mdde}. For the same risk budget, a {t} position should be a fraction of a Bitcoin position."),
    ("波动率很高：{t} 30 日年化约 {v30}%，折合单日约 {d}%{mddz}。{t} 的仓位按波动倒推，而不是按信心。",
     "Volatility is high: {t} runs about {v30}% annualised over 30 days, roughly {d}% a day{mdde}. Size {t} by volatility, not conviction."),
]
P["vola_lo"] = [
    ("{t} 30 日年化波动率约 {v30}%，处在低位{mddz}。低波动往往出现在大行情之前，{t} 方向未定时不宜重仓押方向。",
     "{t}'s 30-day annualised volatility is about {v30}%, compressed{mdde}. Compressed volatility tends to precede big moves; with no direction yet in {t}, a heavy directional bet is premature."),
    ("波动率处在低位：{t} 30 日年化只有约 {v30}%{mddz}。{t} 安静的盘面适合分批，不适合一次性下注。",
     "Volatility is compressed: {t} runs only about {v30}% annualised over 30 days{mdde}. {t}'s quiet tape suits scaling in, not one big bet."),
]
# ------------------------------------------------------------------ token
P["issuance"] = [
    ("{t} 流通 {circ} 枚，上限 {maxs}，已发行约 {fl}%。按现价，{t} 尚未挖出的部分价值约 {ovh}。这是 {t} 协议规则内的挖矿增发，不是团队解锁，但矿工持续卖出同样构成供给压力。",
     "{t} has {circ} circulating against a {maxs} cap, about {fl}% issued. At spot the unmined {t} remainder is worth about {ovh}. This is {t}'s rule-based mining issuance, not a team unlock, but steady miner selling is still supply."),
    ("{t} 还有约 {rest}% 的供给要靠挖矿释放（已发行 {fl}%，流通 {circ} / 上限 {maxs}），按现价约 {ovh}。{t} 的增发节奏透明，但不会停。",
     "About {rest}% of {t}'s supply is still to be mined ({fl}% issued, {circ} of {maxs}), worth about {ovh} at spot. {t}'s schedule is transparent, but it does not stop."),
]
P["overhang"] = [
    ("{t} 流通市值 {mc}，完全稀释估值（FDV）{fdv}，流通占比约 {fl}%。按现价，{t} 未流通部分约 {ovh}，是现有流通市值的 {ovx}。除非 {t} 的需求增长快于释放速度，解锁就是持续的卖压来源。",
     "{t}'s circulating cap is {mc} vs FDV {fdv}: about {fl}% is circulating. At this price the locked {t} remainder is worth about {ovh}, {ovx} the float. Unlocks are standing supply for {t} unless demand outgrows emissions."),
    ("{t} 只有约 {fl}% 的代币在流通（市值 {mc}，FDV {fdv}）。剩下约 {ovh} 的 {t} 筹码通常在团队、投资人和生态基金手里，成本远低于现价，相当于流通市值的 {ovx}。",
     "Only about {fl}% of {t} circulates (cap {mc}, FDV {fdv}). The remaining ~{ovh} of {t}, {ovx} the float, usually sits with team, investors and ecosystem funds whose cost is far below spot."),
]
P["pow_float"] = [
    ("{t} 流通 {circ} 枚，上限 {maxs}，已发行约 {fl}%。{t} 的剩余供给按挖矿规则缓慢释放，没有团队或投资人的集中解锁。",
     "{t} has {circ} circulating against a {maxs} cap, about {fl}% issued. The rest of {t} arrives slowly by mining rules, with no concentrated team or investor unlocks."),
    ("{t} 已发行约 {fl}%（{circ} / {maxs}），剩下的部分只能靠挖矿慢慢释放，供给端没有解锁悬顶。",
     "About {fl}% of {t} is issued ({circ} of {maxs}); the rest can only be mined out slowly, so there is no unlock overhang."),
]
P["full_float"] = [
    ("{t} 流通市值 {mc} 与 FDV {fdv} 几乎重合（流通约 {fl}%）。悬在 {t} 头上的解锁筹码很少，供给端不是主要矛盾。",
     "{t}'s circulating cap {mc} and FDV {fdv} nearly coincide (about {fl}% float). Little unlock supply hangs over {t}; supply is not the main issue."),
    ("约 {fl}% 的 {t} 已在流通（市值 {mc}，FDV {fdv}），价格变化基本就是供需本身，不受解锁日历干扰。",
     "About {fl}% of {t} already circulates (cap {mc}, FDV {fdv}); price is plain supply and demand, not an unlock calendar."),
]
P["mid_float"] = [
    ("{t} FDV {fdv}，流通市值 {mc}，未流通部分约 {ovh}（流通约 {fl}%）。{t} 的解锁压力存在但不是决定性的，节奏比总量更重要。",
     "{t}'s FDV is {fdv} vs circulating {mc}; about {ovh} is not yet circulating ({fl}% float). {t}'s unlock pressure exists but is not decisive; pace matters more than size."),
    ("{t} 还有约 {ovh} 的代币未进入流通（流通约 {fl}%，FDV {fdv}）。{t} 这条解锁尾巴不长，但要跟踪它落在什么时间点。",
     "About {ovh} of {t} is not yet circulating ({fl}% float, FDV {fdv}). {t}'s unlock tail is short, but its timing needs tracking."),
]
P["infl_hi"] = [
    ("按 CoinGecko 口径，{t} 的流通量一年变化约 {infl}{i90z}。持有 {t} 不动也会被稀释这么多，价格要先跑过这个通胀率才算真赚钱。",
     "On CoinGecko's count, {t}'s circulating supply changed about {infl} in a year{i90e}. A passive {t} holder is diluted by that much; price must beat it before it is a real gain."),
    ("{t} 一年流通量增加约 {infl}{i90z}，这是实打实的稀释，任何估值比较都要先把它扣掉。",
     "{t}'s circulating supply rose about {infl} in a year{i90e}; that dilution has to be netted out of any valuation comparison."),
]
P["infl_lo"] = [
    ("按 CoinGecko 口径，{t} 的流通量一年只变了约 {infl}{i90z}。{t} 的供给端稳定，价格变化基本就是需求变化。",
     "On CoinGecko's count, {t}'s circulating supply moved only about {infl} in a year{i90e}. {t}'s supply is stable, so price moves are essentially demand moves."),
    ("{t} 一年流通量变化约 {infl}{i90z}，几乎没有新增稀释。",
     "{t}'s circulating supply changed about {infl} in a year{i90e}, close to no new dilution."),
]
P["no_cap"] = [
    ("CoinGecko 显示 {t} 没有最大供应量上限，长期价值取决于增发和销毁的净值，而不是一个固定的稀缺数字。",
     "CoinGecko shows no maximum supply for {t}; long-run value depends on net issuance after burns, not a fixed scarcity number."),
    ("{t} 不设供应上限，稀缺性要靠销毁和需求增长去争取，而不是写在规则里。",
     "{t} has no supply cap; scarcity has to be earned through burns and demand growth, not written into the rules."),
]
P["cap_near"] = [
    ("{t} 流通 {circ} 枚，上限 {maxs}，已发行约 {cm}%。", "{t} has {circ} circulating against a {maxs} cap, about {cm}% issued."),
    ("{t} 的供给接近封顶：{circ} / {maxs}（约 {cm}%）。", "{t}'s supply is close to its cap: {circ} of {maxs} (about {cm}%)."),
]
P["unlock_heavy"] = [
    ("DefiLlama 解锁日程显示，{t} 未来 30 天约有 {n30} 枚解锁，相当于当前流通量的 {pct30}%，按现价约 {usd30}{cliffz}。这是 {t} 可以排进日历的卖压。",
     "DefiLlama's unlock schedule shows about {n30} {t} unlocking in the next 30 days, {pct30}% of circulating supply, roughly {usd30} at spot{cliffe}. That is {t} supply you can put on a calendar."),
    ("按 DefiLlama 的解锁表，{t} 接下来 30 天要释放约 {pct30}% 的流通量（{n30} 枚，约 {usd30}{cliffz}）。解锁窗口前后，{t} 的价格通常先承压。",
     "Per DefiLlama's schedule, {t} releases about {pct30}% of its float over the next 30 days ({n30} tokens, ~{usd30}{cliffe}). {t}'s price usually feels it around the window."),
]
P["unlock_light"] = [
    ("DefiLlama 解锁日程显示，{t} 未来 90 天新增解锁约 {n90} 枚，只占流通量的 {pct90}%{endz}。短期内 {t} 的供给端没有排队的卖压。",
     "DefiLlama's unlock schedule shows only about {n90} {t} unlocking over the next 90 days, {pct90}% of circulating supply{ende}. No queued {t} supply in the near term."),
    ("按 DefiLlama 的解锁表，{t} 接下来 90 天只释放约 {pct90}% 的流通量（{n90} 枚{endz}），解锁不是眼下的变量。",
     "Per DefiLlama's schedule, {t} releases just {pct90}% of its float over the next 90 days ({n90} tokens{ende}); unlocks are not today's variable."),
]
P["unlock_mid"] = [
    ("DefiLlama 解锁日程显示，{t} 未来 90 天约解锁 {n90} 枚，占流通量的 {pct90}%（约 {usd90}{cliffz}）。{t} 这部分解锁量不算大，但节奏要盯。",
     "DefiLlama's unlock schedule shows about {n90} {t} unlocking over 90 days, {pct90}% of circulating supply (~{usd90}{cliffe}). Not a large amount for {t}, but the pace needs watching."),
    ("按 DefiLlama 的解锁表，{t} 接下来 90 天释放约 {pct90}% 的流通量（{n90} 枚，约 {usd90}{cliffz}），属于温和的持续供给。",
     "Per DefiLlama's schedule, {t} releases about {pct90}% of its float over 90 days ({n90} tokens, ~{usd90}{cliffe}), a mild, steady supply."),
]
# ------------------------------------------------------------------ usage: protocol
P["fees_tiny"] = [
    ("DefiLlama 记录的 {name} 近 30 日费用只有 {f30}{fannz}，对应 {mc} 的流通市值{pfz}。{t} 的价格几乎完全由预期而不是现有业务支撑，收入占比多高都没有意义，因为基数太小。",
     "DefiLlama records only {f30} of 30-day fees for {name}{fanne}, against a {mc} cap{pfe}. {t}'s price rests on expectations, not the current business; the capture ratio is irrelevant at this base."),
    ("{name} 在 DefiLlama 上的 30 日费用是 {f30}{fannz}，放在 {mc} 的市值面前{pfz}，几乎可以忽略。{t} 的定价依据显然不在链上收入。",
     "{name}'s 30-day fees on DefiLlama are {f30}{fanne}, close to nothing next to a {mc} cap{pfe}. {t} is clearly not priced on on-chain revenue."),
    ("链上收入撑不起 {t}：{name} 近 30 日费用 {f30}{fannz}，流通市值 {mc}{pfz}。{t} 更像一份期权，而不是现金流资产。",
     "On-chain revenue cannot carry {t}: {name} took {f30} in 30-day fees{fanne} against a {mc} cap{pfe}. Treat {t} as an option, not a cash-flow asset."),
]
P["fees_up"] = [
    ("DefiLlama 口径，{name} 近 30 日费用 {f30}{momz}{accz}，年化约 {fann}。用户在为 {t} 背后的产品付费，而且付得越来越多，这是最难伪造的需求信号。",
     "On DefiLlama, {name} took {f30} in fees over 30 days{mome}{acce}, about {fann} annualised. Users are paying for the product behind {t}, and paying more; that is the hardest demand signal to fake."),
    ("{name} 的费用在增长：30 日 {f30}{momz}{accz}，年化约 {fann}。收入曲线往上走，{t} 的估值才有扩张的理由。",
     "{name}'s fees are growing: {f30} over 30 days{mome}{acce}, about {fann} annualised. A rising revenue line is what justifies a higher multiple for {t}."),
]
P["fees_dn"] = [
    ("DefiLlama 口径，{name} 近 30 日费用 {f30}{momz}{accz}，年化约 {fann}。需求在降温，{t} 估值里的增长假设需要下调。",
     "On DefiLlama, {name} took {f30} in fees over 30 days{mome}{acce}, about {fann} annualised. Demand is cooling; growth assumptions in {t}'s valuation need trimming."),
    ("{name} 的费用在萎缩：30 日 {f30}{momz}{accz}（年化约 {fann}）。收入下滑时，{t} 的低倍数也可能是价值陷阱。",
     "{name}'s fees are shrinking: {f30} over 30 days{mome}{acce} (~{fann} annualised). With revenue falling, a low multiple on {t} can still be a value trap."),
]
P["fees_flat"] = [
    ("DefiLlama 口径，{name} 近 30 日费用 {f30}{momz}{accz}，年化约 {fann}。需求稳定，但稳定本身不会让 {t} 的估值扩张。",
     "On DefiLlama, {name} took {f30} in fees over 30 days{mome}{acce}, about {fann} annualised. Demand is steady, but steady does not expand {t}'s multiple by itself."),
    ("{name} 的费用基本持平：30 日 {f30}{momz}{accz}，年化约 {fann}。{t} 的业务在，但还缺一个新的增长点。",
     "{name}'s fees are roughly flat: {f30} over 30 days{mome}{acce}, about {fann} annualised. {t}'s business is there; a new growth driver is missing."),
]
P["cap_thin"] = [
    ("{name} 30 日协议收入 {rev}，只占费用约 {cap}%{hsz}。大部分费用流向流动性提供者或节点，{t} 持有人分到的现金流有限。",
     "{name}'s 30-day protocol revenue is {rev}, only about {cap}% of fees{hse}. Most fees go to LPs or operators; {t} holders see little cash flow."),
    ("{t} 的价值捕获偏薄：{name} 只把约 {cap}% 的费用留成收入（30 日 {rev}{hsz}）。",
     "{t}'s value capture is thin: {name} keeps only about {cap}% of fees as revenue (30-day {rev}{hse})."),
]
P["cap_keep"] = [
    ("{name} 30 日协议收入 {rev}，占费用约 {cap}%{hsz}。{t} 和业务之间有真实的价值通道。",
     "{name}'s 30-day protocol revenue is {rev}, about {cap}% of fees{hse}. There is a real value channel between the business and {t}."),
    ("{name} 留得住钱：约 {cap}% 的费用变成协议收入（30 日 {rev}{hsz}），这是 {t} 估值的硬底。",
     "{name} keeps its money: about {cap}% of fees become protocol revenue (30-day {rev}{hse}), a hard floor under {t}'s valuation."),
]
P["cap_mid"] = [
    ("{name} 30 日协议收入 {rev}，占费用约 {cap}%{hsz}。{t} 能分到一部分，但还谈不上现金牛。",
     "{name}'s 30-day protocol revenue is {rev}, about {cap}% of fees{hse}. {t} captures some of it, but it is not a cash cow."),
    ("{name} 的收入留存中等（约 {cap}%，30 日 {rev}{hsz}），{t} 的现金流故事成立，但不够厚。",
     "{name}'s retention is middling (about {cap}%, 30-day {rev}{hse}); {t}'s cash-flow story holds, but it is not thick."),
]
P["tvl_in"] = [
    ("{name} 锁仓 {tvl}{tmz}{t90z}{fyz}。资金愿意留在这里，说明 {t} 背后的产品有粘性。",
     "{name} holds {tvl} TVL{tme}{t90e}{fye}. Capital is choosing to stay, which says the product behind {t} is sticky."),
    ("锁仓在流入：{name} 目前 {tvl}{tmz}{t90z}{fyz}。{t} 的费用通常会滞后跟上。",
     "TVL is flowing in: {name} now holds {tvl}{tme}{t90e}{fye}. {t}'s fees usually follow with a lag."),
]
P["tvl_out"] = [
    ("{name} 锁仓 {tvl}{tmz}{t90z}{fyz}。资金在离开，{t} 的费用迟早会跟着下来。",
     "{name} holds {tvl} TVL{tme}{t90e}{fye}. Capital is leaving; {t}'s fees will follow sooner or later."),
    ("锁仓在流出：{name} 目前 {tvl}{tmz}{t90z}{fyz}。TVL 是 {t} 费用的天花板，天花板在往下压。",
     "TVL is leaking out: {name} now holds {tvl}{tme}{t90e}{fye}. TVL is the ceiling on {t}'s fees, and the ceiling is coming down."),
]
P["tvl_flat"] = [
    ("{name} 锁仓 {tvl}{tmz}{t90z}{fyz}。锁仓不是 {t} 的资产，但它决定了费用的天花板。",
     "{name} holds {tvl} TVL{tme}{t90e}{fye}. TVL is not {t}'s asset, but it sets the ceiling on fees."),
    ("{name} 锁仓大体稳定在 {tvl}{tmz}{t90z}{fyz}，没有明显的资金迁入或迁出。",
     "{name}'s TVL is broadly stable at {tvl}{tme}{t90e}{fye}, with no clear migration in or out."),
]
# ------------------------------------------------------------------ usage: chain
P["ctvl_minor"] = [
    ("{cname} 链上 DeFi 锁仓 {tvl}{rankz}{tmz}{t90z}{stz}。相对 {mc} 的市值，这个体量可以忽略，链上 DeFi 不是 {t} 的价值来源。",
     "{cname} DeFi TVL is {tvl}{ranke}{tme}{t90e}{ste}. Against a {mc} cap this is negligible; on-chain DeFi is not where {t}'s value comes from."),
    ("{cname} 上的 DeFi 只有 {tvl}{rankz}{tmz}{t90z}{stz}，和 {t} {mc} 的市值不在一个量级。",
     "DeFi on {cname} is only {tvl}{ranke}{tme}{t90e}{ste}, a different order of magnitude from {t}'s {mc} cap."),
]
P["ctvl_in"] = [
    ("{cname} 链上 DeFi 锁仓 {tvl}{rankz}{tmz}{t90z}{stz}。开发者和资金在往 {cname} 搬。",
     "{cname} DeFi TVL is {tvl}{ranke}{tme}{t90e}{ste}. Builders and capital are moving onto {cname}."),
    ("资金在流入 {cname}：链上锁仓 {tvl}{rankz}{tmz}{t90z}{stz}。生态扩张是 {t} 估值最直接的支撑。",
     "Capital is flowing onto {cname}: TVL {tvl}{ranke}{tme}{t90e}{ste}. Ecosystem growth is the most direct support for {t}'s valuation."),
]
P["ctvl_out"] = [
    ("{cname} 链上 DeFi 锁仓 {tvl}{rankz}{tmz}{t90z}{stz}。{t} 的生态资金在流失，公链估值最怕这个。",
     "{cname} DeFi TVL is {tvl}{ranke}{tme}{t90e}{ste}. {t}'s ecosystem capital is leaving, which is what L1/L2 valuations fear most."),
    ("资金在离开 {cname}：链上锁仓 {tvl}{rankz}{tmz}{t90z}{stz}。{t} 的价格迟早要面对这条曲线。",
     "Capital is leaving {cname}: TVL {tvl}{ranke}{tme}{t90e}{ste}. {t}'s price will have to face that curve."),
]
P["ctvl_flat"] = [
    ("{cname} 链上 DeFi 锁仓 {tvl}{rankz}{tmz}{t90z}{stz}。{t} 的生态在横盘，没有明显的资金迁入或迁出。",
     "{cname} DeFi TVL is {tvl}{ranke}{tme}{t90e}{ste}. {t}'s ecosystem is moving sideways, no clear migration in or out."),
    ("{cname} 的链上资金大体稳定（锁仓 {tvl}{rankz}{tmz}{t90z}{stz}），{t} 的生态面既不加分也不减分。",
     "{cname}'s on-chain capital is broadly stable (TVL {tvl}{ranke}{tme}{t90e}{ste}); the ecosystem neither adds to nor subtracts from {t}."),
]
P["dex_up"] = [
    ("近 30 日 {cname} 上 DEX 成交 {dex}{dmz}{dtz}，链上交易在升温。对 {t} 来说，链上成交是真实活跃度最直接的代理变量。",
     "DEX volume on {cname} was {dex} over 30 days{dme}{dte}; on-chain trading is heating up. For {t}, on-chain volume is the most direct proxy for real activity."),
    ("{cname} 的链上交易在升温：30 日 DEX 成交 {dex}{dmz}{dtz}。", "On-chain trading on {cname} is heating up: {dex} of 30-day DEX volume{dme}{dte}."),
]
P["dex_dn"] = [
    ("近 30 日 {cname} 上 DEX 成交 {dex}{dmz}{dtz}，链上交易在降温。", "DEX volume on {cname} was {dex} over 30 days{dme}{dte}; on-chain trading is cooling."),
    ("{cname} 的链上交易在降温：30 日 DEX 成交 {dex}{dmz}{dtz}，活跃度跟不上价格。",
     "On-chain trading on {cname} is cooling: {dex} of 30-day DEX volume{dme}{dte}; activity is not keeping up with price."),
]
P["dex_flat"] = [
    ("近 30 日 {cname} 上 DEX 成交 {dex}{dmz}{dtz}，链上交易平稳。", "DEX volume on {cname} was {dex} over 30 days{dme}{dte}; on-chain trading is steady."),
    ("{cname} 30 日 DEX 成交 {dex}{dmz}{dtz}，链上活跃度没有明显变化。", "{cname} did {dex} of 30-day DEX volume{dme}{dte}; on-chain activity shows no clear change."),
]
P["cfee_tiny"] = [
    ("{cname} 近 30 日链级费用 {f30}{fmz}{revz}。年化不到市值的 0.1%，变化幅度再大，对 {mc} 的估值也只是零头。",
     "{cname} chain-level fees were {f30} over 30 days{fme}{reve}. Annualised it is under 0.1% of market cap, so however fast it moves it is a rounding error against {mc}."),
    ("{cname} 的链费 30 日只有 {f30}{fmz}{revz}，年化不及 {t} 市值（{mc}）的千分之一，可以视作零头。",
     "{cname}'s 30-day chain fees are only {f30}{fme}{reve}; annualised, less than a thousandth of {t}'s {mc} cap, a rounding error."),
]
P["cfee_up"] = [
    ("{cname} 近 30 日链级费用 {f30}{fmz}{revz}。用户为区块空间付的钱在增加，这是 {t} 价值的底层来源。",
     "{cname} chain-level fees were {f30} over 30 days{fme}{reve}. What users pay for blockspace is rising, the base layer of {t}'s value."),
    ("{cname} 的链费在增长：30 日 {f30}{fmz}{revz}，区块空间需求在改善。", "{cname}'s chain fees are growing: {f30} over 30 days{fme}{reve}; blockspace demand is improving."),
]
P["cfee_dn"] = [
    ("{cname} 近 30 日链级费用 {f30}{fmz}{revz}，区块空间需求在走弱，{t} 的基本面支撑随之变薄。",
     "{cname} chain-level fees were {f30} over 30 days{fme}{reve}; blockspace demand is weakening and {t}'s fundamental support thins with it."),
    ("{cname} 的链费在下滑：30 日 {f30}{fmz}{revz}。", "{cname}'s chain fees are falling: {f30} over 30 days{fme}{reve}."),
]
P["cfee_flat"] = [
    ("{cname} 近 30 日链级费用 {f30}{fmz}{revz}，区块空间需求持平。", "{cname} chain-level fees were {f30} over 30 days{fme}{reve}; blockspace demand is flat."),
    ("{cname} 的链费基本持平（30 日 {f30}{fmz}{revz}），{t} 的链上收入没有给出新方向。",
     "{cname}'s chain fees are roughly flat ({f30} over 30 days{fme}{reve}); {t}'s on-chain revenue gives no new direction."),
]
# ------------------------------------------------------------------ valuation
P["val_cheap"] = [
    ("{t} 的{lbl}约 {own}，同行中位数约 {peer}，约为同行的 {r} 倍。同样一块钱的业务，在 {t} 这里买得更便宜，前提是增长和留存不比同行差。",
     "{t}'s {lbl_en} is about {own} vs a peer median of {peer}, about {r}x the peers. The same dollar of business is cheaper in {t}, provided growth and retention are not worse."),
    ("按{lbl}，{t}（约 {own}）只有同行中位数（约 {peer}）的 {r} 倍。{t} 的估值有折价，要排除的是便宜有便宜的原因。",
     "On {lbl_en}, {t} (~{own}) is just {r}x the peer median (~{peer}). {t} trades at a discount; the work is ruling out that it is cheap for a reason."),
]
P["val_rich"] = [
    ("{t} 的{lbl}约 {own}，同行中位数约 {peer}，约为同行的 {r} 倍。市场已经给了 {t} 溢价，溢价要靠更快的增长或更深的护城河来兑现。",
     "{t}'s {lbl_en} is about {own} vs a peer median of {peer}, about {r}x the peers. The market already pays a premium for {t}; it has to be earned by faster growth or a deeper moat."),
    ("按{lbl}，{t}（约 {own}）是同行中位数（约 {peer}）的 {r} 倍。{t} 的溢价本身不是问题，溢价缩水才是。",
     "On {lbl_en}, {t} (~{own}) is {r}x the peer median (~{peer}). {t}'s premium is not the problem; the premium shrinking is."),
]
P["val_inline"] = [
    ("{t} 的{lbl}约 {own}，同行中位数约 {peer}（{r} 倍）。{t} 的价格没有明显错配，超额收益要靠基本面改善，而不是估值修复。",
     "{t}'s {lbl_en} is about {own} vs a peer median of {peer} ({r}x). No obvious mispricing in {t}; excess return has to come from fundamentals, not a re-rating."),
    ("按{lbl}，{t}（约 {own}）和同行中位数（约 {peer}）基本持平，估值本身给不出方向。",
     "On {lbl_en}, {t} (~{own}) is in line with the peer median (~{peer}); valuation alone gives no direction."),
]
P["val_anchor_cpf"] = [
    ("{t} 的{lbl}约 {own}。按这个口径，{t} 现在的市值要上千年的链费才能覆盖，市场显然不是按区块空间收入定价：它的估值来自货币属性、品牌或叙事溢价，要看资金和叙事，而不是现金流倍数。",
     "{t}'s {lbl_en} is about {own}: the market cap equals more than a thousand years of chain fees, so it is clearly not priced on blockspace revenue. {t}'s value comes from monetary role, brand or narrative; flows and narrative matter more than cash-flow multiples."),
    ("{t} 的{lbl}高达 {own}，链费根本不是它的定价锚。{t} 这类资产的估值来自货币溢价和叙事，跟踪资金流比跟踪倍数更有用。",
     "{t}'s {lbl_en} is as high as {own}; chain fees are simply not its anchor. Assets like {t} are valued on monetary premium and narrative, so tracking flows beats tracking multiples."),
]
P["val_abs"] = [
    ("{t} 的{lbl}约 {own}。{t} 的同行里能取到同口径数据的不足两家，这个倍数只能作为绝对水平参考，不足以判断便宜还是贵。",
     "{t}'s {lbl_en} is about {own}. Fewer than two of {t}'s peers have like-for-like data, so this is an absolute reference, not enough to call it cheap or rich."),
    ("{t} 的{lbl}约 {own}，但缺少足够的同口径同行，暂时只能当作绝对水平来看。",
     "{t}'s {lbl_en} is about {own}, but there are too few like-for-like peers; treat it as an absolute level for now."),
]
P["val_mismatch"] = [
    ("{t} 的{lbl}约 {own}，同行中位数约 {peer}，差距超过五倍。这不是贵五倍的证据，而是说明市场不按这个口径给 {t} 定价，用 DeFi 倍数去估它会得出没有意义的结论。",
     "{t}'s {lbl_en} is about {own} vs a peer median of {peer}, more than five times apart. That is not evidence of being five times too expensive; the market does not price {t} on this yardstick, and a DeFi multiple gives a meaningless answer."),
    ("{t} 的{lbl}（约 {own}）和同行中位数（约 {peer}）差了五倍以上，说明这个指标对 {t} 失效了，估值要回到资金和叙事上看。",
     "{t}'s {lbl_en} (~{own}) is more than five times off the peer median (~{peer}); the metric does not work for {t}, and valuation falls back to flows and narrative."),
]
P["fdv_ps"] = [
    ("如果按 FDV 计算，{t} 的市值 / 年化收入会升到约 {fps}。{t} 的解锁一旦兑现，今天看起来的倍数就会被稀释。",
     "On FDV, {t}'s mcap / annualised revenue rises to about {fps}. As {t}'s unlocks land, today's multiple gets diluted."),
    ("换成完全稀释口径，{t} 的收入倍数约 {fps}，这才是长期持有者真正面对的价格。",
     "Fully diluted, {t}'s revenue multiple is about {fps}, the price a long-term holder actually pays."),
]
P["vs_leader"] = [
    ("板块龙头 {ldr} 市值 {lmc}，是 {t} 的 {lx}{posz}。{t} 作为二线标的，上行空间来自份额提升，下行风险来自龙头吸走流动性。",
     "Sector leader {ldr} is worth {lmc}, {lx} {t}{pose}. As a follower, {t}'s upside comes from share gains; its downside is the leader soaking up liquidity."),
    ("和板块龙头 {ldr}（{lmc}）相比，{t} 的体量只有对方的 {lpct}%{posz}。{t} 与龙头的估值差，是市场对份额格局的投票。",
     "Next to sector leader {ldr} ({lmc}), {t} is about {lpct}% of its size{pose}. The valuation gap between {t} and the leader is the market's vote on market share."),
]
# ------------------------------------------------------------------ narrative
P["narr_cats"] = [
    ("CoinGecko 把 {t} 归入{secs}{ecoz}。", "CoinGecko files {t} under {secs_en}{ecoe}."),
    ("从分类看，{t} 属于{secs}{ecoz}。", "By category, {t} sits in {secs_en}{ecoe}."),
    ("{t} 的赛道标签是{secs}{ecoz}。", "{t}'s sector tags are {secs_en}{ecoe}."),
]
P["narr_backers"] = [
    ("{t} 的机构持仓标签包括 {backers}，早期筹码的成本和退出节奏值得留意。",
     "{t}'s backer tags include {backers}; their cost basis and exit pace matter."),
    ("早期投资方标签有 {backers}，他们的成本远低于现价，退出节奏是 {t} 的隐性供给。",
     "Early backer tags include {backers}; their cost is far below spot, and their exit pace is hidden supply for {t}."),
]
P["narr_hot"] = [
    ("{t} 所在板块 30 日{basis} {med}，比特币 {b30}，叙事正被资金追捧。",
     "{t}'s sector shows a 30-day {basis_en} of {med} vs Bitcoin {b30}: the story is in demand."),
    ("板块层面也在帮忙：{t} 的同行 30 日{basis} {med}，强于比特币的 {b30}。",
     "The sector helps too: {t}'s peers show a 30-day {basis_en} of {med}, ahead of Bitcoin's {b30}."),
]
P["narr_cold"] = [
    ("{t} 所在板块 30 日{basis} {med}，比特币 {b30}，叙事处在冷宫，资金在别处。",
     "{t}'s sector shows a 30-day {basis_en} of {med} vs Bitcoin {b30}: the story is out of favour and money is elsewhere."),
    ("板块层面是逆风：{t} 的同行 30 日{basis} {med}，弱于比特币的 {b30}。",
     "The sector is a headwind: {t}'s peers show a 30-day {basis_en} of {med}, behind Bitcoin's {b30}."),
]
P["narr_sync"] = [
    ("{t} 所在板块 30 日{basis} {med}，比特币 {b30}，叙事热度与大盘同步。",
     "{t}'s sector shows a 30-day {basis_en} of {med} vs Bitcoin {b30}: the story moves with the market."),
    ("{t} 的同行 30 日{basis} {med}，和比特币（{b30}）相差不大，板块没有给出额外的顺风或逆风。",
     "{t}'s peers show a 30-day {basis_en} of {med}, close to Bitcoin's {b30}; the sector adds neither tailwind nor headwind."),
]
P["narr_about"] = [
    ("项目方在 CoinGecko 上的英文自述是：“{about}” 这是 {t} 自己的定位，不代表我们的判断。",
     "The project's own CoinGecko description reads: \u201c{about}\u201d That is {t}'s self-positioning, not our assessment."),
    ("{t} 对自己的描述（CoinGecko 英文简介原文）：“{about}” 自述只说明想做什么，数据才说明做到了多少。",
     "{t} describes itself (CoinGecko, verbatim): \u201c{about}\u201d A self-description says what it wants to be; the data says how far it got."),
]
P["narr_genesis"] = [
    ("{t} 的创世日期是 {genesis}。", "{t}'s genesis date is {genesis}."),
    ("项目创世于 {genesis}（{t}）。", "{t} launched (genesis) on {genesis}."),
]
# ------------------------------------------------------------------ news
P["news_lead"] = [
    ("近 {days} 天，我们在 CoinDesk、Cointelegraph、The Block、Decrypt 等公开渠道检索到 {n} 条点名 {t} 的报道{tagz}。以下只列 {t} 相关报道的原标题和出处，不做转述。",
     "Over the last {days} days we found {n} headlines naming {t} in public outlets such as CoinDesk, Cointelegraph, The Block and Decrypt{tage}. {t} headlines are listed verbatim with their sources, without paraphrase."),
    ("公开新闻源里，近 {days} 天点名 {t} 的报道有 {n} 条{tagz}。{t} 相关标题原文如下，判断以数据为准。",
     "Public news feeds carried {n} headlines naming {t} in the last {days} days{tage}. Original {t} headlines below; our calls rest on the data."),
]
P["news_one"] = [
    ("近 {days} 天公开渠道只检索到 1 条点名 {t} 的报道{tagz}，媒体关注度很低。",
     "Only one headline naming {t} turned up in public outlets over the last {days} days{tage}; media attention is low."),
    ("{t} 近 {days} 天只出现在 1 条公开报道里{tagz}，消息面相当安静。",
     "{t} appeared in just one public headline over the last {days} days{tage}; the news flow is quiet."),
]
P["news_quiet"] = [
    ("我们检索了 CoinDesk、Cointelegraph、The Block、Decrypt、CryptoSlate 及 Google 新闻，近 {days} 天没有点名 {t} 的报道。没有新闻本身也是信息：{t} 当前的价格变化缺少消息面解释。",
     "We searched CoinDesk, Cointelegraph, The Block, Decrypt, CryptoSlate and Google News: no headline named {t} in the last {days} days. No news is information too: {t}'s price action has no news-flow explanation."),
    ("近 {days} 天，主流加密媒体和 Google 新闻里都没有点名 {t} 的报道，消息面空白，价格更多由资金和情绪驱动。",
     "In the last {days} days neither the main crypto outlets nor Google News carried a headline naming {t}; with a blank news flow, price is driven more by flows and mood."),
]
P["hack_hist"] = [
    ("DefiLlama 的安全事件库记录过 {t} 相关项目 {hname} 在 {hdate} 被攻击，损失约 {hamt}（{htech}）。历史事件不等于 {t} 现在不安全，但它决定了风控团队看这个标的的起点。",
     "DefiLlama's hack database records an incident at {hname} ({t}-related) on {hdate}, about {hamt} lost ({htech}). Past incidents do not mean {t} is unsafe now, but they set where a risk desk starts."),
    ("安全记录方面，DefiLlama 记载 {hname} 曾在 {hdate} 遭遇攻击，损失约 {hamt}（{htech}），这是 {t} 尽调里绕不开的一页。",
     "On security, DefiLlama records {hname} being exploited on {hdate}, about {hamt} lost ({htech}), a page no {t} due diligence can skip."),
]
# ------------------------------------------------------------------ KOL
P["mood_fng"] = [
    ("{t} 所处的大环境：全市场恐惧贪婪指数 {fng}（{fngl}，30 日均值 {fnga}）", "the backdrop for {t}: market Fear & Greed {fng} ({fngl}, 30-day average {fnga})"),
    ("大盘情绪方面，恐惧贪婪指数 {fng}（{fngl}），30 日均值 {fnga}，这是 {t} 交易的背景", "market mood behind {t}: Fear & Greed {fng} ({fngl}), 30-day average {fnga}"),
]
P["mood_trend_in"] = [
    ("{t} 位列 CoinGecko 热搜第 {pos}", "{t} is #{pos} on CoinGecko trending search"),
    ("CoinGecko 热搜榜上 {t} 排第 {pos}", "CoinGecko's trending list has {t} at #{pos}"),
]
P["mood_trend_out"] = [
    ("{t} 不在 CoinGecko 热搜前 {n}", "{t} is not in CoinGecko's top-{n} trending"),
    ("CoinGecko 热搜前 {n} 里没有 {t}", "CoinGecko's top-{n} trending list does not include {t}"),
]
P["mood_votes"] = [
    ("{t} 的 CoinGecko 社区投票看涨 {votes}%", "CoinGecko community votes on {t} are {votes}% bullish"),
    ("CoinGecko 上 {votes}% 的投票者看涨 {t}", "{votes}% of CoinGecko voters are bullish on {t}"),
]
P["mood_watch"] = [
    ("约 {wl} 万用户把 {t} 加入自选", "about {wle}K users have {t} on a watchlist"),
    ("{t} 的 CoinGecko 自选人数约 {wl} 万", "{t} sits on about {wle}K CoinGecko watchlists"),
]
P["mood_lunar"] = [
    ("LunarCrush 显示 {t} 社交主导率 {dom}%", "LunarCrush shows {t} at {dom}% social dominance"),
    ("{t} 在 LunarCrush 的社交主导率为 {dom}%", "{t}'s LunarCrush social dominance is {dom}%"),
]
P["mood_wrap"] = [
    ("**盘口情绪：** {items}。", "**Mood:** {items_en}."),
    ("**情绪读数：** {items}。", "**Mood readings:** {items_en}."),
]
P["crowd_frenzy"] = [
    ("**共识怎么想：** 时间线上最容易出现的叙事是“{t} 走出来了”：30 日 {c30}{trendz}。这正是 {t} 的 FOMO 最容易被放大的阶段。",
     "**The crowd:** the easy timeline story is \"{t} is breaking out\": {c30} in 30 days{trende}. This is exactly when FOMO around {t} compounds."),
    ("**共识怎么想：** {t} 30 日 {c30}{trendz}，散户和 KOL 的讨论会集中在“还能涨多少”，FOMO 情绪正在占上风。",
     "**The crowd:** with {t} {c30} in 30 days{trende}, retail and KOL chatter centres on \"how much higher\"; FOMO is taking over."),
]
P["crowd_pullback"] = [
    ("**共识怎么想：** {t} 一年 {c1y}，最近 7 日却回落 {c7abs}。{t} 的多头会说这是大涨后的正常换手，空头会说顶部已现，这是分歧最大的位置。",
     "**The crowd:** {t} is {c1y} over a year but {c7} over the last 7 days. {t} bulls call it healthy rotation after a big run, bears call the top; this is where disagreement peaks."),
    ("**共识怎么想：** 一年 {c1y} 之后，{t} 7 日 {c7}。KOL 圈会分成两派：一派喊 {t} 上车机会，一派提示获利了结，散户最容易在这里来回挨打。",
     "**The crowd:** after {c1y} in a year, {t} is {c7} over 7 days. KOLs split into \"buy the {t} dip\" and \"take profits\" camps, and retail tends to get whipsawed here."),
]
P["crowd_runup"] = [
    ("**共识怎么想：** {t} 一年 {c1y}，30 日 {c30}，属于大涨后的高位整理。{t} 的早期持有者在考虑兑现，新买家在等回调，讨论热度不低但方向分裂。",
     "**The crowd:** {t} is {c1y} over a year and {c30} over 30 days, consolidating after a big run. Early {t} holders weigh taking profits, new buyers wait for a dip; chatter is loud but split."),
    ("**共识怎么想：** 一年 {c1y} 的 {t} 不缺关注，30 日 {c30} 的横盘让多空都有话说：有人看作蓄势，有人看作派发。",
     "**The crowd:** a coin that is {c1y} in a year never lacks attention; {t}'s {c30} sideways month lets both sides talk: accumulation to some, distribution to others."),
]
P["crowd_warm"] = [
    ("**共识怎么想：** {t} 30 日 {c30}，已经开始有人注意，但还没到满屏喊单的程度；这一段通常是早期跟随者和获利盘的拉锯。",
     "**The crowd:** {t} is {c30} over 30 days; people are starting to notice, but timelines are not full of calls yet. For {t}, this phase is usually a tug-of-war between early followers and profit-takers."),
    ("**共识怎么想：** 30 日 {c30} 让 {t} 重新出现在部分交易员的观察名单里，讨论在升温，但远谈不上一致看多。",
     "**The crowd:** {c30} in 30 days puts {t} back on some traders' watchlists; chatter is warming, but far from a consensus long."),
]
P["crowd_cold"] = [
    ("**共识怎么想：** 一个 30 日 {c30} 的币很难出现在 KOL 的时间线上，散户对 {t} 的典型反应是等跌完再说。",
     "**The crowd:** a coin that is {c30} in 30 days rarely makes a KOL timeline; the typical retail reaction to {t} is \"wait until it is done falling\"."),
    ("**共识怎么想：** {t} 30 日 {c30}，讨论在降温，留下来的多是被套的持有者，新资金普遍在观望。",
     "**The crowd:** with {t} {c30} in 30 days, chatter is fading; those left are mostly trapped holders while new money waits."),
]
P["crowd_capit"] = [
    ("**共识怎么想：** 30 日 {c30} 之后，{t} 的社区情绪接近投降，常见的声音是“归零”“不碰”。{t} 的情绪极端本身就是一个数据点。",
     "**The crowd:** after {c30} in 30 days, sentiment around {t} is close to capitulation, with \"going to zero\" and \"never touching it\" common. Extreme mood around {t} is a data point in itself."),
    ("**共识怎么想：** {t} 一个月跌了 {c30abs}，KOL 基本噤声，散户在割肉，大多数人此时只想离场。",
     "**The crowd:** {t} lost {c30abs} in a month; KOLs have gone quiet and retail is cutting losses. Most {t} holders only want out."),
]
P["crowd_quiet"] = [
    ("**共识怎么想：** {t} 处在没人吵架的区间，30 日 {c30}、7 日 {c7}，既没有 FOMO 也没有恐慌，声音主要来自长期持有者。",
     "**The crowd:** {t} is in a no-argument zone, {c30} over 30 days and {c7} over 7, neither FOMO nor panic; most of the voice comes from long-term holders."),
    ("**共识怎么想：** 30 日 {c30} 的 {t} 不会出现在热门讨论里，市场对它几乎没有一致预期，这种安静本身就是定价的一部分。",
     "**The crowd:** at {c30} over 30 days, {t} is nowhere near the hot topics; there is little consensus either way, and that quiet is part of the price."),
]
P["contra_hot_neg"] = [
    ("**反共识：** 热度越高，越要盯住 {t} 的“{h}”（{hp}）。情绪推上去的价格，最先被这类数字拉回来，{t} 也不例外。",
     "**Contrarian:** the louder it gets, the harder it is to ignore that {t} is {h_en} ({hp_en}). Prices pushed by mood get pulled back by numbers like this first, and {t} is no exception."),
    ("**反共识：** 讨论升温的时候，{t} 最被忽视的数据是“{h}”（{hp}）。{t} 的行情能走多远，取决于市场什么时候重新注意到它。",
     "**Contrarian:** as the chatter warms up, the most ignored data point on {t} is that it is {h_en} ({hp_en}). How far {t}'s move runs depends on when the market notices."),
]
P["contra_cold_pos"] = [
    ("**反共识：** 没人看的时候反而值得看：{t} 的“{h}”（{hp}）没有跟着价格变坏。",
     "**Contrarian:** the time nobody is looking is the time to look: {t} is {h_en} ({hp_en}), and that did not deteriorate with price."),
    ("**反共识：** 价格冷了，但 {t} 的“{h}”（{hp}）还在。情绪和数据背离的时候，往往是研究 {t} 的好时机。",
     "**Contrarian:** price went cold, but {t} is still {h_en} ({hp_en}). When mood and data diverge on {t}, it is usually a good time to do the work."),
]
P["contra_mixed"] = [
    ("**反共识：** 市场的注意力在 {t} 的“{a}”，我们更在意“{h}”（{hp}），它决定这段走势能走多远。",
     "**Contrarian:** the market is focused on {t} being {a_en}; we care more that it is {h_en} ({hp_en}), which decides how far this move can run."),
    ("**反共识：** 大家在讨论 {t} 的“{a}”，真正该被定价的却是“{h}”（{hp}）。",
     "**Contrarian:** everyone discusses {t} being {a_en}; what should really be priced is that it is {h_en} ({hp_en})."),
]
P["contra_none"] = [
    ("**反共识：** {t} 可核数据太少，任何强烈观点都是在押叙事，我们选择等更多数据。",
     "**Contrarian:** there is too little checkable data on {t}; any strong view is a bet on narrative, so we wait for more."),
    ("**反共识：** 关于 {t}，现在最诚实的立场是不站队：证据两边都不够。",
     "**Contrarian:** on {t}, the most honest stance right now is no stance: the evidence is thin on both sides."),
]
P["thermo_greed"] = [
    ("**情绪温度计：** 大盘恐贪指数 {fng}，已在贪婪区，{t} 这类热门标的在这种环境下的回撤通常比大盘更深。",
     "**Thermometer:** market Fear & Greed is {fng}, in greed; hot names like {t} usually draw down harder than the market from here."),
    ("**情绪温度计：** 恐贪指数 {fng} 叠加 {t} 自身的热度，情绪双重偏热，仓位应比平时更轻。",
     "**Thermometer:** Fear & Greed at {fng} on top of {t}'s own heat means doubly warm mood; size lighter than usual."),
]
P["thermo_fear"] = [
    ("**情绪温度计：** {t} 所在的大盘恐贪指数为 {fng}，处在恐惧区。这类时段分批买 {t} 通常比追涨性价比更高，前提是标的本身没坏。",
     "**Thermometer:** the market Fear & Greed reading around {t} is {fng}, in fear. Scaling into {t} in such phases usually beats chasing, provided the asset itself is not broken."),
    ("**情绪温度计：** 恐贪指数只有 {fng}，市场整体偏恐慌，{t} 的价格里已经包含了一部分悲观预期。",
     "**Thermometer:** Fear & Greed is only {fng}; the market is fearful, and {t}'s price already embeds some pessimism."),
]
P["levels_above"] = [
    ("**交易员盯的位置：** {lv}；{t} 守住 200 日均线，趋势派不会下车；跌破则情绪会很快反转。",
     "**Levels traders watch:** {lv_en}; if {t} holds the 200-day, trend followers stay on; lose it and sentiment flips fast."),
    ("**交易员盯的位置：** {lv}；对 {t} 来说，200 日均线是多头的最后一道防线。",
     "**Levels traders watch:** {lv_en}; for {t}, the 200-day is the bulls' last line."),
]
P["levels_below"] = [
    ("**交易员盯的位置：** {lv}；{t} 收复 200 日均线之前，反弹大概率被当成减仓机会。",
     "**Levels traders watch:** {lv_en}; until {t} reclaims the 200-day, rallies are likely to be sold."),
    ("**交易员盯的位置：** {lv}；{t} 需要先站回 200 日均线，趋势资金才会重新考虑它。",
     "**Levels traders watch:** {lv_en}; {t} has to get back above the 200-day before trend money reconsiders it."),
]
P["views"] = [
    ("**公开观点：** 近 30 天可查到的、点名 {t} 的观点类报道包括{items}。我们只列 {t} 相关标题和出处，不转述作者立场，也不代表我们的判断。",
     "**Public views:** opinion-type pieces naming {t} in the last 30 days include {items_en}. We list {t} titles and sources only, without paraphrasing the authors or adopting their views."),
    ("**公开观点：** 媒体和分析师近期对 {t} 的公开讨论可见于{items}。{t} 相关标题原文照录，立场以原文为准。",
     "**Public views:** recent public commentary on {t} can be found in {items_en}. {t} titles are verbatim; the authors' positions are their own."),
]
# ------------------------------------------------------------------ dimension takes
P["take_market_up"] = [
    ("{t} 的盘面在帮忙，顺势比逆势更容易。", "{t}'s tape is helping; going with it is easier than fighting it."),
    ("盘面是 {t} 的加分项，趋势没坏之前不必和它作对。", "The tape is a plus for {t}; no need to fight it while the trend holds."),
    ("{t} 的价格结构偏强，节奏上以回调介入为主。", "{t}'s price structure is strong; entries are better on pullbacks."),
]
P["take_market_down"] = [
    ("{t} 的盘面在拖后腿，耐心比勇气更值钱。", "{t}'s tape is a headwind; patience beats courage here."),
    ("盘面对 {t} 不友好，等趋势修复再谈仓位。", "The tape is unfriendly to {t}; talk sizing once the trend repairs."),
    ("{t} 的价格结构偏弱，抄底的胜率不高。", "{t}'s price structure is weak; bottom-fishing has poor odds."),
]
P["take_market_flat"] = [
    ("{t} 的盘面没有给出明确方向，节奏交给数据。", "{t}'s tape gives no clear direction; let the data set the pace."),
    ("盘面上 {t} 多空均衡，等待突破比预判方向更划算。", "On the tape {t} is balanced; waiting for a break beats guessing it."),
]
P["take_market_mixed"] = [
    ("{t} 的盘面是“{hp}”与“{hn}”并存：短期信号偏强，长期包袱还在，仓位要比纯趋势票更轻。",
     "{t}'s tape mixes \"{hp_en}\" with \"{hn_en}\": the near-term signal is strong while the long-term baggage remains, so size below a clean trend name."),
    ("盘面上，{t} 同时有“{hp}”和“{hn}”两股力量，强弱要看哪一条先被打破。",
     "On the tape, {t} carries both \"{hp_en}\" and \"{hn_en}\"; what matters is which one breaks first."),
]
P["take_market_mixed_rev"] = [
    ("{t} 的盘面是“{hn}”压着“{hp}”：长期结构偏强，短线在降温，回调中的承接力度是关键。",
     "{t}'s tape has \"{hn_en}\" weighing on \"{hp_en}\": the long structure is strong while the short term cools; how dips are absorbed is the key."),
    ("盘面上，{t} 长线有“{hp}”托底，短线有“{hn}”拖累，节奏上等短线企稳再说。",
     "On the tape, {t} has \"{hp_en}\" underneath and \"{hn_en}\" dragging short term; wait for the short term to settle."),
]
P["take_token_up"] = [
    ("供给端是 {t} 的加分项。", "Supply is a plus for {t}."),
    ("{t} 的供给结构干净，没有明显的稀释压力。", "{t}'s supply structure is clean, with no obvious dilution pressure."),
]
P["take_token_down"] = [
    ("供给端是 {t} 最大的结构性压力，估值必须打折。", "Supply is the biggest structural weight on {t}; the valuation needs a discount."),
    ("{t} 的供给在持续稀释持有人，任何买入理由都要先过这一关。", "{t}'s supply keeps diluting holders; any buy case has to clear that first."),
]
P["take_token_flat"] = [
    ("供给不是 {t} 的主要矛盾，但需要跟踪释放节奏。", "Supply is not {t}'s main issue, but the release pace needs tracking."),
    ("{t} 的供给端中性，关键是解锁和增发的节奏不要突然加快。", "{t}'s supply side is neutral; the key is that unlocks and issuance do not suddenly speed up."),
]
P["take_token_mixed"] = [
    ("{t} 的供给端一好一坏：“{hp}”，但“{hn}”，两者要一起算。", "{t}'s supply side cuts both ways: {hp_en}, but {hn_en}; net them together."),
    ("供给上 {t} 有“{hp}”的利好，也有“{hn}”的压力。", "On supply, {t} has the plus of \"{hp_en}\" and the weight of \"{hn_en}\"."),
]
P["take_usage_up"] = [
    ("{t} 的基本面在改善，这是最值得为之付溢价的变化。", "{t}'s fundamentals are improving, the change most worth paying up for."),
    ("链上数据站在 {t} 一边，需求在真实增长。", "On-chain data sides with {t}; demand is growing for real."),
]
P["take_usage_down"] = [
    ("{t} 的基本面在走弱，价格迟早要反映。", "{t}'s fundamentals are weakening; price will reflect it sooner or later."),
    ("链上数据在给 {t} 降温，估值需要跟着调整。", "On-chain data is cooling {t}; the valuation needs to follow."),
]
P["take_usage_flat"] = [
    ("{t} 的基本面稳定，估值扩张需要新的增长点。", "{t}'s fundamentals are steady; multiple expansion needs a new growth driver."),
    ("链上使用没有给 {t} 新的信号，基本面维持原样。", "On-chain usage gives {t} no new signal; fundamentals hold where they were."),
]
P["take_usage_mixed"] = [
    ("{t} 的链上数据分化：“{hp}”，同时“{hn}”。", "{t}'s on-chain data is split: {hp_en}, while {hn_en}."),
    ("链上看，{t} 有“{hp}”的亮点，也有“{hn}”的隐忧。", "On-chain, {t} has the bright spot of \"{hp_en}\" and the worry of \"{hn_en}\"."),
]
P["take_usage_market"] = [
    ("链上使用撑不起 {t} 现在的估值，价格靠的是叙事、预期和资金，这部分只能用盘面来跟踪。",
     "On-chain usage cannot carry {t}'s valuation; price runs on narrative, expectations and flows, which can only be tracked on the tape."),
    ("{t} 的链上业务和市值不在一个量级，基本面分析在这里帮不上太多忙，要看资金流向。",
     "{t}'s on-chain business and market cap are orders of magnitude apart; fundamentals help little here, flows matter more."),
]
P["take_valuation_up"] = [
    ("{t} 的相对估值有安全边际。", "{t}'s relative valuation offers a margin of safety."),
    ("和同行比，{t} 的价格给了折扣。", "Against peers, {t}'s price comes at a discount."),
]
P["take_valuation_down"] = [
    ("{t} 的估值已经提前透支了一部分好消息。", "{t}'s valuation already prices in part of the good news."),
    ("{t} 的溢价需要后续数据来兑现，容错率不高。", "{t}'s premium needs follow-through in the data; there is little room for error."),
]
P["take_valuation_flat"] = [
    ("{t} 的相对估值本身不构成买入或卖出的理由。", "{t}'s relative valuation is not a reason to buy or sell by itself."),
    ("估值层面 {t} 没有明显错配，决定胜负的是基本面和资金。", "On valuation {t} shows no obvious mispricing; fundamentals and flows decide."),
    ("{t} 缺少可比的现金流倍数，估值判断只能退回到市场结构上。", "{t} lacks comparable cash-flow multiples, so valuation falls back on market structure."),
]
P["take_valuation_mixed"] = [
    ("{t} 的估值信号互相抵消：“{hp}”，但“{hn}”。", "{t}'s valuation signals offset: {hp_en}, but {hn_en}."),
    ("估值上 {t} 有“{hp}”，也有“{hn}”，结论偏中性。", "On valuation {t} shows \"{hp_en}\" and \"{hn_en}\"; net neutral."),
]
P["take_narrative_up"] = [
    ("叙事是 {t} 的顺风。", "The narrative is a tailwind for {t}."),
    ("{t} 所在的赛道正受资金青睐。", "{t}'s sector is in favour with money."),
]
P["take_narrative_down"] = [
    ("叙事是 {t} 的逆风，需要自身数据更硬。", "The narrative is a headwind for {t}, so its own data has to be harder."),
    ("{t} 所在的赛道暂时失宠，单靠叙事很难翻身。", "{t}'s sector is out of favour for now; narrative alone will not turn it."),
]
P["take_narrative_flat"] = [
    ("叙事对 {t} 是中性的，价格更多由自身数据决定。", "The narrative is neutral for {t}; its own data drives price."),
    ("{t} 所在赛道没有给出统一方向，既谈不上顺风，也谈不上逆风。", "{t}'s sector gives no single direction: neither a tailwind nor a headwind."),
]
P["take_news_up"] = [
    ("消息面对 {t} 偏正面，但标题不是数据，仍以链上和盘面为准。", "The news flow leans positive for {t}, but headlines are not data; the tape and chain still decide."),
    ("{t} 的消息面提供了一些催化，能否兑现要看后续数据。", "{t}'s news flow offers some catalysts; whether they land shows up in later data."),
]
P["take_news_down"] = [
    ("{t} 的消息面有风险信号，需要等事件落地再评估。", "{t}'s news flow carries risk flags; wait for the events to resolve before re-assessing."),
    ("负面标题在 {t} 的报道里占比不低，风控上要先把它们核实清楚。", "Negative headlines make up a real share of {t}'s coverage; verify them before sizing."),
]
P["take_news_flat"] = [
    ("消息面对 {t} 没有方向性影响。", "The news flow has no directional effect on {t}."),
    ("{t} 的新闻多是常规报道，不足以改变判断。", "{t}'s coverage is mostly routine and not enough to change the call."),
]
# ------------------------------------------------------------------ lead
P["lead_pair"] = [
    ("这是一张需要拆开看的票：{name}（{t}）{a}{ap}，但{b}{bp}。", "{name} ({t}) needs to be taken apart: {a_en}{ap_en}, but {b_en}{bp_en}."),
    ("先说结论：{name}（{t}）{a}{ap}，与此同时{b}{bp}。", "Bottom line on {name} ({t}): {a_en}{ap_en}, while at the same time {b_en}{bp_en}."),
    ("看 {t} 要同时抓住两件事：{a}{ap}；然而{b}{bp}。", "Two things matter at once for {t}: {a_en}{ap_en}; yet {b_en}{bp_en}."),
    ("{name}（{t}）眼下的矛盾很清楚：一边是{a}{ap}，一边是{b}{bp}。", "The tension in {name} ({t}) is clear: on one side {a_en}{ap_en}, on the other {b_en}{bp_en}."),
]
P["lead_one"] = [
    ("{name}（{t}）眼下最突出的特征是{h}{hp}。", "The defining feature of {name} ({t}) right now: {h_en}{hp_en}."),
    ("如果只用一句话概括 {name}（{t}）：{h}{hp}。", "If {name} ({t}) had to be summed up in one line: {h_en}{hp_en}."),
    ("{name}（{t}）这份简报的主线是{h}{hp}。", "The through-line of this note on {name} ({t}): {h_en}{hp_en}."),
]
P["lead_extra2"] = [
    ("{l1}，{h1}{p1}；{l2}，{h2}{p2}。", "{l1_en} {h1_en}{p1_en}. {l2_en} {h2_en}{p2_en}."),
    ("{t} 的其余维度里，{l1}{h1}{p1}，{l2}{h2}{p2}。", "Elsewhere, {l1_lc} {h1_en}{p1_en}, and {l2_lc} {h2_en}{p2_en}."),
    ("关于 {t}，另外两点值得记下：{h1}{p1}；{h2}{p2}。", "Two more points worth noting: {t} is {h1_en}{p1_en}; it is also {h2_en}{p2_en}."),
]
P["lead_extra1"] = [
    ("{l1}，{h1}{p1}。", "{l1_en} {h1_en}{p1_en}."),
    ("关于 {t}，另外值得记下的是：{h1}{p1}。", "Also worth noting: {t} is {h1_en}{p1_en}."),
]
P["stance_hi"] = [
    ("**买入评分 {sc} / 10（{vz}）：** {t} 的数据整体站在多头一边，但仓位应跟着下文的风险项走，而不是一次打满。",
     "**Buy score {sc} / 10 ({ve}):** {t}'s data leans bullish overall, but sizing should follow the risks below rather than going all in."),
    ("**买入评分 {sc} / 10（{vz}）：** 证据偏向 {t}，适合小仓位跟踪，并用下文的条件做加减仓依据。",
     "**Buy score {sc} / 10 ({ve}):** The evidence favours {t}; a small tracking position fits, with the conditions below as add/trim triggers."),
]
P["stance_mid"] = [
    ("**买入评分 {sc} / 10（{vz}）：** {t} 的多空证据大致抵消，更适合放进观察名单，等关键数据给出方向。",
     "**Buy score {sc} / 10 ({ve}):** Bull and bear evidence on {t} roughly cancel; it belongs on a watchlist until the key numbers pick a side."),
    ("**买入评分 {sc} / 10（{vz}）：** 对 {t} 我们暂不下注，先盯住下文列出的几个触发条件。",
     "**Buy score {sc} / 10 ({ve}):** No bet on {t} yet; we watch the triggers listed below first."),
    ("**买入评分 {sc} / 10（{vz}）：** {t} 有看点也有硬伤，现阶段观察比行动更有价值。",
     "**Buy score {sc} / 10 ({ve}):** {t} has merits and flaws; at this stage watching is worth more than acting."),
]
P["stance_lo"] = [
    ("**买入评分 {sc} / 10（{vz}）：** {t} 的负面证据占上风，在下文条件改善之前，我们不建议主动建仓。",
     "**Buy score {sc} / 10 ({ve}):** Negative evidence dominates on {t}; until the conditions below improve we would not initiate a position."),
    ("**买入评分 {sc} / 10（{vz}）：** 对 {t}，现在说便宜还太早，风险项没有出清。",
     "**Buy score {sc} / 10 ({ve}):** It is too early to call {t} cheap; the risk items have not cleared."),
]
# ------------------------------------------------------------------ catalysts
P["cat_fee_accel"] = [
    ("{t} 最近 7 日费用跑在 30 日均值之上（月度节奏 {acc}）；若持续，下一期费用环比会继续改善。", "{t}'s fees over the last 7 days run above the 30-day average ({acc} run-rate); if it holds, next month's MoM improves again."),
    ("费用在加速：按最近 7 日折算，{t} 的月度费用节奏 {acc}。", "Fees are accelerating: at the last 7 days' pace, {t}'s monthly fee run-rate is {acc}."),
]
P["cat_tvl_in"] = [
    ("{t} 锁仓 30 日 {tm}，资金持续流入，费用通常会滞后跟上。", "{t}'s TVL is {tm} over 30 days; inflows usually pull fees up with a lag."),
    ("锁仓 30 日 {tm}，{t} 的费用天花板在抬高。", "With TVL {tm} over 30 days, {t}'s fee ceiling is rising."),
]
P["cat_dex_up"] = [
    ("{cname} 链上 DEX 成交环比 {dm}，生态活跃度在回升。", "DEX volume on {cname} is {dm} month on month; ecosystem activity is recovering."),
    ("{cname} 的 DEX 成交 30 日环比 {dm}，链上交易需求在回来。", "{cname}'s DEX volume is {dm} MoM; on-chain trading demand is returning."),
]
P["cat_reclaim"] = [
    ("{t} 已站上 50 日均线，下一步是挑战 200 日均线（{ma200}），收复后趋势资金可能回补。", "{t} is back above the 50-day; next is the 200-day ({ma200}), and reclaiming it could pull trend money back."),
    ("短期均线已经收复，{t} 若再站上 200 日均线（{ma200}），技术面会从空头转为中性偏多。", "The short average is reclaimed; if {t} also clears the 200-day ({ma200}), the technical picture turns neutral-to-bullish."),
]
P["cat_trending"] = [
    ("{t} 上了 CoinGecko 热搜（第 {pos}），短期注意力和新增买盘在流入。", "{t} is on CoinGecko trending (#{pos}); short-term attention and new bids are flowing in."),
    ("热搜第 {pos} 给 {t} 带来了新的眼球，关注能否转化为成交。", "Trending at #{pos} brings {t} fresh eyes; watch whether attention turns into volume."),
]
P["cat_fear"] = [
    ("大盘恐贪指数 {fng}，处在恐惧区，情绪修复本身就是 {t} 的催化。", "Market Fear & Greed is {fng}, in fear; a mood recovery is itself a catalyst for {t}."),
    ("恐贪指数 {fng} 偏低，一旦情绪回暖，{t} 这类弹性标的会先受益。", "Fear & Greed is low at {fng}; when mood warms, high-beta names like {t} benefit first."),
]
P["cat_sector"] = [
    ("板块内资金正在向 {t} 集中（30 日领先板块 {rss}）。", "In-sector money is concentrating on {t} (30-day lead over the sector {rss})."),
    ("{t} 30 日跑在板块前面 {rss}，板块内部的强势惯性可能延续。", "{t} leads its sector by {rss} over 30 days; momentum inside a sector tends to persist."),
]
P["cat_chain_fees"] = [
    ("{cname} 链级费用环比 {fm}，区块空间需求在改善。", "{cname} chain fees are {fm} MoM; blockspace demand is improving."),
    ("{cname} 的链费 30 日环比 {fm}，用户在为区块空间多付钱。", "{cname}'s chain fees are {fm} MoM; users are paying more for blockspace."),
]
P["cat_unlock_quiet"] = [
    ("{t} 未来 90 天解锁只占流通量的 {pct90}%（DefiLlama），供给端短期没有排队的卖压。", "{t}'s next-90-day unlocks are only {pct90}% of float (DefiLlama); no queued supply near term."),
    ("DefiLlama 解锁表显示 {t} 90 天内只释放 {pct90}% 的流通量，供给窗口相对干净。", "DefiLlama's schedule shows {t} releasing only {pct90}% of float in 90 days; the supply window is relatively clean."),
]
P["cat_headline"] = [
    ("事件线索：{outlet} {date} 报道《{title}》，后续进展值得跟踪（{t}）。", "Event thread: {outlet} on {date}: \"{title}\"; worth tracking for {t}."),
    ("{t} 的事件线索：《{title}》（{outlet}，{date}）。", "Event thread for {t}: \"{title}\" ({outlet}, {date})."),
]
# ------------------------------------------------------------------ risks
P["risk_issuance"] = [
    ("增发：{t} 尚未挖出的区块奖励按现价约 {ovh}，矿工卖出是持续供给。", "Issuance: {t}'s unmined block rewards are worth about {ovh} at spot; miner selling is steady supply."),
    ("挖矿供给：{t} 还有约 {ovh} 的区块奖励待释放。", "Mining supply: about {ovh} of {t} block rewards are still to come."),
]
P["risk_unlock"] = [
    ("解锁：{t} 约 {ovh} 的未流通供给，按现价是流通市值的 {ovx}。", "Unlocks: about {ovh} of {t} is not yet circulating, {ovx} the float at spot."),
    ("未流通筹码：{t} 还有约 {ovh}（流通市值的 {ovx}）没进入市场。", "Locked supply: about {ovh} of {t} ({ovx} the float) has yet to reach the market."),
]
P["risk_unlock_sched"] = [
    ("解锁日程：{t} 未来 30 天约解锁流通量的 {pct30}%（约 {usd30}）{cliffz}。", "Unlock calendar: {t} unlocks about {pct30}% of float in the next 30 days (~{usd30}){cliffe}."),
    ("{t} 的近期解锁：30 天内约 {pct30}% 的流通量（约 {usd30}）{cliffz}。", "{t}'s near-term unlocks: about {pct30}% of float within 30 days (~{usd30}){cliffe}."),
]
P["risk_infl"] = [
    ("通胀：{t} 过去一年流通量增加约 {infl}%。", "Inflation: {t}'s circulating supply rose about {infl}% in a year."),
    ("稀释：{t} 一年新增流通约 {infl}%，持有人要先跑过这个数。", "Dilution: {t} added about {infl}% to circulation in a year; holders must beat that first."),
]
P["risk_fees_dn"] = [
    ("需求降温：{t} 30 日费用环比 {fm}。", "Cooling demand: {t}'s 30-day fees are {fm} MoM."),
    ("{t} 的费用 30 日环比 {fm}，需求端在走弱。", "{t}'s 30-day fees are {fm} MoM; demand is weakening."),
]
P["risk_tvl_out"] = [
    ("资金外流：{t} 锁仓 30 日 {tm}。", "Outflows: {t}'s TVL is {tm} over 30 days."),
    ("{t} 锁仓 30 日 {tm}，资金在撤离。", "{t}'s TVL is {tm} over 30 days; capital is pulling out."),
]
P["risk_chain_bleed"] = [
    ("生态失血：{cname} 链上锁仓 30 日 {tm}。", "Ecosystem bleed: {cname} TVL is {tm} over 30 days."),
    ("{cname} 链上锁仓 30 日 {tm}，生态资金在流失。", "{cname} TVL is {tm} over 30 days; ecosystem capital is draining."),
]
P["risk_vola"] = [
    ("波动：{t} 30 日年化波动约 {v30}%，折合单日约 {d}%，单日 10% 以上的波动并不罕见。", "Volatility: {t} runs about {v30}% annualised, roughly {d}% a day; 10%+ daily moves are not rare."),
    ("高波动：{t} 年化约 {v30}%（单日约 {d}%），止损和仓位都要按这个幅度设。", "High volatility: {t} runs about {v30}% annualised (~{d}% a day); stops and size must be set for that range."),
]
P["risk_froth"] = [
    ("过热：{t} 换手约 {tv}%，短线筹码多，情绪逆转时踩踏更快。", "Froth: {t} turns over about {tv}%; short-term holders dominate and reversals cascade faster."),
    ("{t} 换手约 {tv}%，属于过热区间，筹码稳定性差。", "{t} turns over about {tv}%, in froth territory; the holder base is unstable."),
]
P["risk_liq"] = [
    ("流动性：{t} 24 小时成交只有约 {vol}，大额进出会有明显滑点。", "Liquidity: {t} trades only about {vol} a day; size will see real slippage."),
    ("{t} 的绝对成交额约 {vol}/天，机构级仓位很难不惊动价格。", "{t}'s absolute volume is about {vol} a day; institutional size cannot move without moving price."),
]
P["risk_meme"] = [
    ("迷因属性：{t} 的价格几乎完全由注意力决定，没有协议现金流兜底。", "Meme risk: {t}'s price is almost purely attention, with no protocol cash flow underneath."),
    ("{t} 是迷因资产，注意力一旦转移，价格没有基本面支撑。", "{t} is a meme asset; when attention moves on, there is no fundamental floor."),
]
P["risk_capture"] = [
    ("价值捕获：{t} 背后的协议只把约 {cap}% 的费用留成收入。", "Value capture: the protocol behind {t} keeps only about {cap}% of fees as revenue."),
    ("{t} 的协议收入只占费用约 {cap}%，代币分到的很少。", "{t}'s protocol revenue is only about {cap}% of fees; little reaches the token."),
]
P["risk_anchor"] = [
    ("估值锚：{t} 的链上费用相对市值可以忽略，价格主要由货币属性、叙事和资金流决定，这几样都可能很快转向。", "Valuation anchor: {t}'s on-chain fees are negligible next to its cap, so price rests on monetary role, narrative and flows, all of which can turn quickly."),
    ("{t} 缺少现金流锚，叙事或资金一旦转向，价格没有业务支撑。", "{t} has no cash-flow anchor; if narrative or flows turn, there is no business underneath."),
]
P["risk_datagap"] = [
    ("数据盲区：DefiLlama 没有与 {t} 对应的协议或链级费用数据，本文的基本面判断只能依靠市场数据。", "Data gap: DefiLlama has no protocol or chain fee data mapped to {t}, so fundamentals here rest on market data only."),
    ("{t} 没有可核的链上收入数据，基本面判断的置信度偏低。", "{t} has no checkable on-chain revenue data, so confidence in the fundamental read is low."),
]
P["risk_hack"] = [
    ("安全记录：{hname} 曾在 {hdate} 被攻击，损失约 {hamt}（DefiLlama，{t} 相关）。", "Security record: {hname} ({t}-related) was exploited on {hdate}, about {hamt} lost (DefiLlama)."),
    ("历史安全事件：{hdate} {hname} 损失约 {hamt}（DefiLlama 记录，涉及 {t}）。", "Past incident: {hname} lost about {hamt} on {hdate} (per DefiLlama, {t}-related)."),
]
P["risk_headline"] = [
    ("消息面风险：{outlet} {date} 报道《{title}》，涉及{tagz}，需要跟踪后续（{t}）。", "Headline risk for {t}: {outlet} on {date}: \"{title}\" ({tage}); needs follow-up."),
    ("{t} 的{tagz}类报道：《{title}》（{outlet}，{date}），事件结果落地前应保守。", "{t} {tage} headline: \"{title}\" ({outlet}, {date}); stay conservative until it resolves."),
]
P["risk_extended"] = [
    ("偏离过大：{t} 高出 200 日均线 {g200}%，均值回归本身就是风险。", "Overextension: {t} is {g200}% above its 200-day; mean reversion is itself a risk."),
    ("{t} 距 200 日均线 {g200}%，任何利空都可能触发较深的回撤。", "{t} sits {g200}% over its 200-day; any bad news can trigger a deep pullback."),
]
P["risk_macro"] = [
    ("宏观与监管：{t} 和整个加密市场一样，与全球流动性和监管预期高度相关，单币研究无法对冲这部分风险。", "Macro and policy: like all crypto, {t} trades with global liquidity and regulation; single-coin work cannot hedge that."),
    ("宏观与监管：流动性收紧或监管转向会同时压低所有加密资产，{t} 也不例外。", "Macro and policy: tighter liquidity or a regulatory turn hits all crypto at once, {t} included."),
]
P["flip"] = [
    ("**什么会改变我们对 {t} 的看法：** {items}。", "**What would change our view on {t}:** {items_en}."),
    ("**{t} 的观点切换条件：** {items}。", "**Triggers that would flip our {t} view:** {items_en}."),
]

# slots whose output is legal / structural boilerplate and may repeat across notes
BOILERPLATE_SLOTS = {"risk_macro"}
P["crowd_jolt"] = [
    ("**共识怎么想：** {t} 30 日 {c30} 看似平静，7 日 {c7} 的波动却把它重新推到交易员眼前，短线资金在进出，长线资金还在看。",
     "**The crowd:** {t} looks calm at {c30} over 30 days, but a {c7} week has pushed it back in front of traders; short-term money is moving, long-term money is still watching."),
    ("**共识怎么想：** 月度看 {t} 没怎么动（{c30}），可最近 7 日 {c7}，讨论随之起伏，还谈不上形成共识。",
     "**The crowd:** month on month {t} barely moved ({c30}), but the last 7 days were {c7}; chatter swings with it and no consensus has formed."),
]
P["peer_note"] = [
    ("{t} 的同行取自 CoinGecko “{cat}”板块，已剔除 {k} 个迷因或非本赛道代币；赛道核心项目优先，其余按市值远近补足，龙头按筛选后的市值确定。",
     "{t}'s peers come from CoinGecko's \"{cat}\" list with {k} memecoins or off-sector tokens removed; core sector projects come first, the rest are filled by market-cap distance, and the leader is the largest after filtering."),
    ("同行组说明：从 CoinGecko “{cat}”列表出发，去掉 {k} 个迷因或跑题代币，先放赛道核心项目，再按与 {t} 的市值远近补足。",
     "Peer set: starting from CoinGecko's \"{cat}\" list, {k} memecoins or off-topic tokens were dropped; core sector names go first and the rest are filled by market-cap distance from {t}."),
]
P["peer_note_clean"] = [
    ("{t} 的同行取自 CoinGecko “{cat}”板块，赛道核心项目优先，其余按市值远近补足；体量差距大的同行只作方向参考。",
     "{t}'s peers come from CoinGecko's \"{cat}\" list, core sector projects first and the rest by market-cap distance; peers of very different size are a directional reference only."),
    ("同行组说明：取自 CoinGecko “{cat}”列表，先放赛道核心项目，再按与 {t} 的市值远近补足，体量悬殊时只看方向不看倍数。",
     "Peer set: from CoinGecko's \"{cat}\" list, core sector names first, then the rest by market-cap distance from {t}; where sizes differ widely, read direction, not multiples."),
]

P["take_market_mixed_same"] = [
    ("盘面上，{t} 同时有“{hp}”和“{hn}”两股力量，强弱要看哪一条先被打破。",
     "On the tape, {t} carries both \"{hp_en}\" and \"{hn_en}\"; what matters is which one breaks first."),
    ("{t} 的走势里，“{hp}”和“{hn}”互相抵消，单看盘面给不出方向，仓位上宁轻勿重。",
     "In {t}'s chart, \"{hp_en}\" and \"{hn_en}\" offset each other; the tape alone gives no direction, so size light."),
]
P["contra_stretched"] = [
    ("**反共识：** 抄底的声音会越来越多，但 {t} 仍{h}（{hp}），均值回归还没走完之前，回调不一定就是机会。",
     "**Contrarian:** dip-buying calls will get louder, but {t} is still {h_en} ({hp_en}); until mean reversion plays out, a pullback is not automatically an opportunity."),
    ("**反共识：** 市场在争论 {t} 是不是见顶，我们更在意的是它仍{h}（{hp}）：偏离本身就是要消化的风险。",
     "**Contrarian:** the market argues over whether {t} has topped; we care more that it is still {h_en} ({hp_en}), and that gap is itself a risk to digest."),
]

P["narr_split"] = [
    ("{t} 的同行 30 日涨跌中位数 {m}，按市值加权（不含本币）却是 {w}，比特币 {b30}：大市值和小市值同行走势分化，板块整体谈不上顺风或逆风。",
     "{t}'s peers show a 30-day median change of {m} but a cap-weighted (ex-self) change of {w}, vs Bitcoin {b30}: large and small peers are diverging, so the sector is neither tailwind nor headwind."),
    ("板块信号是分裂的：{t} 所在板块 30 日中位数 {m}，市值加权（不含本币）{w}，对照比特币 {b30}，头部和尾部同行没有走在一起。",
     "The sector signal is split: {t}'s sector has a 30-day median of {m} and a cap-weighted (ex-self) change of {w}, against Bitcoin's {b30}; the head and the tail of the peer group are not moving together."),
]

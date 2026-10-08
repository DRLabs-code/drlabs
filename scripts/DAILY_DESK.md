# 日更研报（内部）

此文件只给维护用，不要做成公开页面，也不要写进导航、关于或首页。

## 做什么

每天 **00:00 UTC**（珀斯 / 新加坡 08:00）GitHub Action 尝试发新研报并重建静态站：

1. **一篇主流**：先看 `desk_universe.json` 的 `majors`；写完了就自动扩到 CoinGecko 市值前 200（市值 ≥ 1 亿美元）里还没写过的币。
2. **一篇卫星**：按一年中的第几天轮转 `DeFi → GameFi → Meme → L2`。先用 `desk_universe.json` 里的名单，写完了就用 CoinGecko 对应板块列表（市值 ≥ 2,500 万美元、24h 成交 ≥ 50 万美元）。该赛道空了或接口失败，顺延下一赛道。

- 已写过的 ticker / slug / CoinGecko id（`research/*/report.md`）永不重写。
- 稳定币、包装币、质押凭证、成交太薄（< 30 万美元）的币自动跳过。
- **没得写就不写**：一篇都写不出来时，脚本打一条 `::warning::` 后以 0 退出，不提交、不重建、不发失败邮件。当天已有两篇也直接退出。

## 怎么写（desk_analyst.py + desk_phrases.py）

不是填空模板。脚本先拉一个数据包（`daily_desk.py build_pack`），再由 `desk_analyst.py` 从多个维度生成「发现」，按显著性排序决定标题、导语和章节顺序：

- 市场结构：200 日均线、30 日 / 1 年相对比特币、相对板块、换手（含同行对比）、量能变化、波动、距 ATH。ATH 出现在上线 45 天内的（如 ZEC 2016 年开盘价）标成「上线初期报价」，改用 90 日高点做参照。
- 代币与供给：流通率、FDV 悬空、一年流通量变化、PoW 发行，以及 DefiLlama 解锁日程（未来 30 / 90 天占流通量、下一笔集中解锁）。
- 链上使用（DefiLlama）：协议费用 / 收入 / 持币人收入、TVL 趋势、公链 TVL / DEX / 链费用。费用太小会明确写成「可以忽略」。
- 估值与同行：P/F、P/S、市值/TVL 对比同行；倍数离谱时改写成「锚不住」，不硬比。
- 叙事：CoinGecko 分类、项目方英文自述（原文引用并注明是自述）、机构持仓标签、板块温度（中位数和市值加权（不含本币）都要同向才叫「热 / 冷」）。
- 消息面：近 30 天点名该币的报道，原标题 + 媒体 + 日期 + 链接，不转述；按关键词打标签（安全、监管、上架、ETF/机构、融资、代币经济、产品、观点、价格）。负面标签进风险，产品/机构类进催化。DefiLlama 安全事件库有记录的写进消息面和风险。
- KOL 视角：恐贪指数、热搜、社区投票、自选人数、LunarCrush；共识状态由明确阈值决定（见下），反共识、交易员盯的价位；有观点类报道时只列标题和出处。
- 催化与风险、什么会改变看法；评分 3.0–8.2，按标的类型调整权重，评分标准写在文中。

### 阈值（desk_analyst.TH，audit() 逐条复核）

共识状态按顺序判断：（30 日 ≥ +25%，或上热搜 / 换手 ≥ 35% 且 30 日为正）且 7 日没有跌超 10% → 过热；一年 ≥ +200% 且 7 日 ≤ -10% → 大涨后回调；一年 ≥ +200% → 高位整理；30 日 ≤ -25% → 接近投降；30 日 ≥ +10% → 回暖；30 日 ≤ -10% → 冷；|7 日| ≥ 12% → 短线波动；其余才是「安静 / 没有 FOMO」。放量 / 缩量只在 7 日均量较前 30 日 ≥ +35% / ≤ -35% 时出现；估值便宜 / 贵 = 同行倍数的 < 0.75× / > 1.4×。每篇稿子发布前 `audit()` 用独立代码把每个标签和它的数字再对一遍，章节结论不许和章节标题反向；对不上就不发（`::warning::` 跳过）。

### 同行（desk_sectors.json）

同行来自 CoinGecko 板块列表，但先剔除：CoinGecko 迷因列表（前 250）、名字像迷因的、`exclude` 名单（如 GameFi 里的 FLOKI、APE、GMT、CARV、Rollbit 等）、赌场 / AI 类名字。优先选 `core`（人工维护的赛道核心）和 `desk_universe.json` 的赛道名单；龙头 = 筛选后市值最大的核心项目。文中注明板块名和剔除了几个。`category_drop` 去掉不适用的分类（如 ZEC 的「智能合约平台」）。

### 措辞不重复

`desk_phrases.py` 里每个句位至少 2 个写法，每个写法都含币种专属字段。按「币种 + 日期」确定顺序；同一天第二篇会把第一篇（以及当天已发布的稿子）的句子骨架（数字、名称抹掉后的句型）当作禁用表，挑不重复的写法。

### 免费数据源

CoinGecko（行情、365 天图、板块、迷因列表、热搜、项目简介和链接）、DefiLlama（协议 / 链 / 费用 / DEX / 稳定币、`/hacks`、`defillama-datasets.llama.fi/emissions/<slug>` 解锁日程）、alternative.me 恐贪指数、LunarCrush 公开页、RSS（CoinDesk、Cointelegraph、The Block、Decrypt、CryptoSlate）+ Google 新闻 RSS 搜索（只收白名单媒体；白名单一条都没有时才用二线行业媒体补最多 3 条）。全部免 key、零费用；任何一个源失败，对应段落直接不写。

### 测试

改动后跑 `python3 scripts/test_desk_analyst.py`（离线，不联网）：七语块对齐、禁句、免责声明、珀斯日期、无 None/NaN/未填字段、评分区间；`scripts/fixtures/desk_packs/` 里 17 个币的缓存数据包两两组合不共享句型、全体不出现重复句；ILV（30 日 +16% 不许写「没有 FOMO」）、FLOKI 当链游龙头、ZEC 上线价 ATH、板块冷热误判等回归用例；随机扰动 240 次全部过 audit。

刷新缓存数据包：`python3 scripts/daily_desk.py --coin <id> --lane <lane> --dry-run --dump scripts/fixtures/desk_packs`。

局限：拿不到 X / Telegram 的真实 KOL 原话（免费渠道不可用），只列公开报道标题；解锁日程只覆盖 DefiLlama 收录的约 370 个项目；Google 新闻链接是跳转链接；报道标签按关键词判断。

## 本地

```bash
export DRLABS_ROOT=/tmp/drlabs-live
python3 scripts/daily_desk.py --dry-run          # 只打印标题和评分，不写文件
python3 scripts/daily_desk.py --dump /tmp/packs  # 另存 <slug>.json 数据包 + <slug>.zh.md / .en.md
python3 scripts/daily_desk.py                    # 真写稿；今天已有两篇会停
python3 scripts/i18n_build.py
```

单币重写（绕过每日两篇上限，同 slug 覆盖）：

```bash
python3 scripts/daily_desk.py --coin illuvium --lane GameFi --dump /tmp/packs
python3 scripts/daily_desk.py --from-pack /tmp/packs/ilv.json   # 不联网，用存下的数据包重排
python3 scripts/i18n_build.py
```

`--dump DIR` 写 `DIR/<slug>.json`：完整数据包（cg、hist、btc、eth、peers、sector、protocol、chain、social、news、news_checked、unlocks、hacks、profile、sources、slug、as_of、day），以及 `DIR/<slug>.zh.md`、`DIR/<slug>.en.md` 两份稿子。

强制补发（一般不用）：`python3 scripts/daily_desk.py --force`

## 线上

仓库：`DRLabs-code/drlabs`  
工作流：`.github/workflows/daily-desk.yml`  
可在 Actions 里 `workflow_dispatch` 手跑。公开站不写「日更」之类的流程说明。

## 更新后通知

站点内容一旦写上线，必须在对话里用中文告诉用户，并附上链接：

- 首页：https://drlabs-code.github.io/drlabs/
- 目录：https://drlabs-code.github.io/drlabs/research/
- 每篇新研报：https://drlabs-code.github.io/drlabs/research/\<slug\>/

本地打印当日链接：

```bash
python3 scripts/daily_desk.py --status
```

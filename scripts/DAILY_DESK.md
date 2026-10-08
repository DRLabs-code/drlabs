# 日更研报（内部）

此文件只给维护用，不要做成公开页面，也不要写进导航、关于或首页。

## 做什么

每天 **00:00 UTC**（珀斯 / 新加坡 08:00）GitHub Action 尝试发新研报并重建静态站：

1. **一篇主流**：先看 `desk_universe.json` 的 `majors`；写完了就自动扩到 CoinGecko 市值前 200（市值 ≥ 1 亿美元）里还没写过的币。
2. **一篇卫星**：按一年中的第几天轮转 `DeFi → GameFi → Meme → L2`。先用 `desk_universe.json` 里的名单，写完了就用 CoinGecko 对应板块列表（市值 ≥ 2,500 万美元、24h 成交 ≥ 50 万美元）。该赛道空了或接口失败，顺延下一赛道。

- 已写过的 ticker / slug / CoinGecko id（`research/*/report.md`）永不重写。
- 稳定币、包装币、质押凭证、成交太薄（< 30 万美元）的币自动跳过。
- **没得写就不写**：一篇都写不出来时，脚本打一条 `::warning::` 后以 0 退出，不提交、不重建、不发失败邮件。当天已有两篇也直接退出。

## 怎么写（desk_analyst.py）

不是填空模板。脚本先拉一个数据包（`daily_desk.py build_pack`），再由 `desk_analyst.py` 从多个维度生成「发现」，按显著性排序决定标题、导语和章节顺序：

- 市场结构：200 日均线、30 日 / 1 年相对比特币、相对板块、换手（含同行对比）、量能变化、波动、距 ATH。
- 代币与供给：流通率、FDV 悬空、一年流通量变化（由市值 / 价格推算）、PoW 发行。
- 链上使用（DefiLlama）：协议费用 / 收入 / 持币人收入、TVL 趋势、公链 TVL / DEX / 链费用。费用太小会被明确写成「可以忽略」，不会当亮点。
- 估值与同行：P/F、P/S、市值/TVL 对板块龙头和近邻；倍数离谱时改写成「锚不住」，不硬比。
- 叙事、KOL 视角（恐贪指数、热搜、社区投票、自选人数、LunarCrush，加上共识与反共识）、催化与风险、什么会改变看法。
- 评分 3.0–8.2，按标的类型（协议 / 公链 / 迷因 / 纯市场）调整权重。≥ 6.5 谨慎跟踪，5.0–6.4 观望，< 5 回避。

取不到的数据整维度省略，不编数。正文开头写发布日期（澳洲珀斯时间），结尾是免责声明，含「仅供参考，投资要理性」。

改动后跑 `python3 scripts/test_desk_analyst.py`（离线：七语块对齐、禁句、免责声明、日期、无 None/NaN、评分区间）。（工作流加 workflow 权限后可以先跑它再写稿，见 daily-desk.yml 待改项。）

局限：免费接口拿不到新闻、解锁日历、真实 KOL 原话，这部分不写，避免编造。

## 本地

```bash
export DRLABS_ROOT=/tmp/drlabs-live
python3 scripts/daily_desk.py --dry-run          # 只打印标题和评分，不写文件
python3 scripts/daily_desk.py --dump /tmp/packs  # 另存数据包 JSON，方便调写法
python3 scripts/daily_desk.py                    # 真写稿；今天已有两篇会停
python3 scripts/i18n_build.py
```

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

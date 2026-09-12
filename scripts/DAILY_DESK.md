# 日更两篇（内部）

此文件只给维护用，不要做成公开页面，也不要写进导航、关于或首页。

## 做什么

每天 **00:00 UTC**（新加坡 08:00）GitHub Action 发两篇新研报并重建静态站：

1. **一篇主流**：`desk_universe.json` 的 `majors` 里第一个还没写过、且 CoinGecko 能拉到价的标的。
2. **一篇卫星**：按一年中的第几天轮转 `DeFi → GameFi → Meme`。该赛道空了或接口失败，顺延下一赛道。

已写过的 ticker（`research/*/report.md`）不会重写。当天若已有两篇，任务直接退出。

## 数字与写法

- 只写当场能核的数：CoinGecko、DefiLlama、LunarCrush、AltIndex 公开页。
- **不要套模板。** `desk_write.py` 按标的类型选论点（储备 / 结算不在 / 成交领先 / 费用薄层 / 迷因磁带被抢等）。标题、机制节、评分要点都要跟着这一个票变。
- 必须对照同行：市值、24h 成交、换手；L1 再对照公链 TVL、稳定币、DEX、链费用。
- **热度是必写维度。** LunarCrush 主导率、AltIndex cashtag 能抓到就写，并对照成交。没有就写未披露。过期 cashtag 不和当日比特币样本混比。跟踪清单里要盯热度还在不在。
- 禁止再输出「定价厚，链上锁仓只解释一部分」这类套话。
- 快照时刻写 UTC。缺的格子写「未披露」。
- 评分夹在约 3.0–8.2。迷因没有协议现金流才下调，不是无脑减分。
- 成稿后用 `python3 scripts/test_desk_write.py` 检查七语块对齐和禁句。

## 本地

```bash
export DRLABS_ROOT=/tmp/drlabs-live
python3 scripts/daily_desk.py --dry-run
python3 scripts/daily_desk.py          # 真写稿；今天已有两篇会停
python3 scripts/i18n_build.py
```

强制补发（一般不用）：

```bash
python3 scripts/daily_desk.py --force
```

## 线上

仓库：`DRLabs-code/drlabs`  
工作流：`.github/workflows/daily-desk.yml`  
可在 Actions 里 `workflow_dispatch` 手跑。公开站不写「日更两篇」。

## 更新后通知

站点内容一旦写上线，必须在对话里用中文告诉用户，并附上链接：

- 首页：https://drlabs-code.github.io/drlabs/
- 目录：https://drlabs-code.github.io/drlabs/research/
- 每篇新研报：https://drlabs-code.github.io/drlabs/research/\<slug\>/

本地打印当日链接：

```bash
python3 scripts/daily_desk.py --status
```

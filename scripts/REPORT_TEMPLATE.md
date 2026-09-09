# 内部研报模板

此文件只给写稿用，不要放到公开站点。

1. 只写公开数据。记下快照时刻（UTC）和来源（CoinGecko / DefiLlama / 文档）。
2. 在 `/tmp/drlabs-live/research/<ticker>/` 新建 `report.md` + `report.{en,ja,ko,fr,es,ru}.md`。
3. **七语块结构必须一致**（标题、段落、表、列表、图的数量与顺序相同）。
4. **表格单元格只保留中英**。不要把日韩法西俄写进表内。
5. 生成图表后拷到 `assets/<ticker>/` 与 `public/research/<ticker>/`。
6. 跑 `python3 /workspace/scripts/i18n_build.py`。
7. 推送 GitHub Pages 的 `main`，再同步 Astro 预览。

最低章节（保持这个顺序，生成器才不会错位）：

1. 研究结论
2. 数据快照（表）
3. 2–3 个机制章节（可含图）
4. 买入评分（表）
5. 主要风险（无序列表）
6. 跟踪清单（有序列表）
7. 数据来源
8. 免责声明

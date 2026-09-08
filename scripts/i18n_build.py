#!/usr/bin/env python3
"""Build bilingual static HTML for the live DRLabs GitHub Pages site."""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path("/tmp/drlabs-live")
ASTRO_GEN = Path("/workspace/src/generated")

BOOT = """<script>
(function(){try{var k='drlabs-lang';var l=localStorage.getItem(k);
if(l!=='zh'&&l!=='en'){l=((navigator.language||'zh')+'').toLowerCase().indexOf('zh')===0?'zh':'en';}
document.documentElement.setAttribute('data-lang',l);
document.documentElement.setAttribute('lang',l==='zh'?'zh-CN':'en');}catch(e){}})();
</script>"""


def md_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def has_cjk(s: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", s or ""))


def split_table_row(line: str) -> list[str]:
    line = line.strip().strip("|")
    return [c.strip() for c in line.split("|")]


def is_sep_row(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-+:?", c.replace(" ", "").replace("–", "-")) for c in cells)


def bilingual_cell(zh: str, en: str) -> str:
    zh_s, en_s = (zh or "").strip(), (en or "").strip()
    if not zh_s and not en_s:
        return ""
    if not en_s:
        return md_inline(zh_s)
    if not zh_s:
        return md_inline(en_s)
    if zh_s == en_s:
        return md_inline(zh_s)
    # numeric / ticker cells: keep one line
    if not has_cjk(zh_s) and not has_cjk(en_s):
        return md_inline(zh_s)
    return f'{md_inline(zh_s)}<br><span class="bi">{md_inline(en_s)}</span>'


def table_html(zh_lines: list[str], en_lines: list[str] | None = None) -> str:
    zh_rows = [split_table_row(l) for l in zh_lines if l.strip() and not is_sep_row(l)]
    en_rows = [split_table_row(l) for l in en_lines if l.strip() and not is_sep_row(l)] if en_lines else None
    if not zh_rows:
        return ""
    header = zh_rows[0]
    en_header = en_rows[0] if en_rows else header
    body_zh = zh_rows[1:]
    body_en = en_rows[1:] if en_rows and len(en_rows) > 1 else body_zh
    n = max(len(header), len(en_header))
    thead = "".join(
        f"<th>{bilingual_cell(header[i] if i < len(header) else '', en_header[i] if i < len(en_header) else '')}</th>"
        for i in range(n)
    )
    tbody = []
    for i, zrow in enumerate(body_zh):
        erow = body_en[i] if i < len(body_en) else zrow
        m = max(len(zrow), len(erow))
        tds = "".join(
            f"<td>{bilingual_cell(zrow[j] if j < len(zrow) else '', erow[j] if j < len(erow) else '')}</td>"
            for j in range(m)
        )
        tbody.append(f"<tr>{tds}</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>{"".join(tbody)}</tbody></table></div>'


def strip_frontmatter(md: str) -> str:
    md = md.replace("\r\n", "\n")
    if md.startswith("---\n"):
        end = md.find("\n---\n", 4)
        if end != -1:
            return md[end + 5 :]
    return md


def parse_blocks(md: str) -> list[tuple[str, object]]:
    lines = strip_frontmatter(md).split("\n")
    blocks: list[tuple[str, object]] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.strip() == "---":
            blocks.append(("hr", None))
            i += 1
            continue
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
            i += 1
            continue
        if line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            i += 1
            continue
        if line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
            i += 1
            continue
        if line.strip().startswith("<figure"):
            chunk = [line]
            i += 1
            while i < n and "</figure>" not in chunk[-1]:
                chunk.append(lines[i])
                i += 1
            blob = "\n".join(chunk)
            src_m = re.search(r'src="([^"]+)"', blob)
            alt_m = re.search(r'alt="([^"]*)"', blob)
            cap_m = re.search(r"<figcaption>(.*?)</figcaption>", blob, re.S)
            src = src_m.group(1) if src_m else ""
            alt = alt_m.group(1) if alt_m else ""
            cap = cap_m.group(1).strip() if cap_m else alt
            blocks.append(("img", (alt, src, cap)))
            continue
        if line.startswith("!["):
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
            if m:
                blocks.append(("img", (m.group(1), m.group(2), m.group(1))))
            i += 1
            continue
        if line.strip().startswith("|"):
            tbl = []
            while i < n and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            blocks.append(("table", tbl))
            continue
        if line.startswith("> "):
            q = [line[2:]]
            i += 1
            while i < n and lines[i].startswith("> "):
                q.append(lines[i][2:])
                i += 1
            blocks.append(("quote", "\n".join(q)))
            continue
        if re.match(r"^[-*] (\[[ xX]\] )?", line):
            items = []
            while i < n and re.match(r"^[-*] ", lines[i]):
                items.append(re.sub(r"^[-*] ", "", lines[i]))
                i += 1
            blocks.append(("ul", items))
            continue
        if re.match(r"^\d+\. ", line):
            items = []
            while i < n and re.match(r"^\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i]))
                i += 1
            blocks.append(("ol", items))
            continue
        para = [line]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not lines[i].startswith(("#", "|", ">", "!", "-", "*"))
            and lines[i].strip() != "---"
            and not re.match(r"^\d+\. ", lines[i])
            and not lines[i].strip().startswith("<figure")
        ):
            para.append(lines[i])
            i += 1
        blocks.append(("p", " ".join(x.strip() for x in para if x.strip())))
    return blocks


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return (text[:48] or "section").lower()


def rewrite_img(src: str, kind: str) -> str:
    name = Path(src).name
    if kind == "aave":
        return f"../../assets/aave/{name}"
    if kind == "bnb":
        return f"../../assets/bnb/{name}"
    return src


def rewrite_img_astro(src: str, slug: str) -> str:
    name = Path(src).name
    aave_map = {
        "01_aave_tvl_versions.png": "tvl-versions.png",
        "02_aave_supply_borrow_net.png": "supply-borrow-net.png",
        "03_aave_fees_vs_revenue_30d.png": "fees-vs-revenue-30d.png",
        "04_aave_mcap_fdv.png": "mcap-fdv.png",
        "05_gho_circulating.png": "gho-circulating.png",
        "06_lending_competitors_tvl.png": "competitor-tvl-comparison.png",
        "07_aave_tvl_trend.png": "tvl-trend.png",
    }
    if slug.startswith("aave"):
        name = aave_map.get(name, name)
        return f"../aave/{name}"
    return f"../bnb/{name}"


def render_pair(kind: str, zh_val, en_val, img_rewriter) -> str:
    if kind == "hr":
        return "<hr />"
    if kind == "table":
        return table_html(zh_val, en_val if isinstance(en_val, list) else None)
    if kind == "img":
        alt, src, cap = zh_val if len(zh_val) == 3 else (zh_val[0], zh_val[1], zh_val[0])
        en_alt, en_src, en_cap = en_val if isinstance(en_val, tuple) and len(en_val) == 3 else (alt, src, cap)
        src = img_rewriter(src)
        return (
            f'<figure><img src="{html.escape(src)}" alt="{html.escape(alt)}">'
            f'<figcaption class="lang-zh">{md_inline(cap)}</figcaption>'
            f'<figcaption class="lang-en">{md_inline(en_cap)}</figcaption></figure>'
        )
    if kind == "h1":
        return f'<h1 class="lang-zh">{md_inline(zh_val)}</h1><h1 class="lang-en">{md_inline(en_val)}</h1>'
    if kind == "h2":
        sid = slugify(str(zh_val))
        return (
            f'<h2 id="{html.escape(sid)}" class="lang-zh">{md_inline(zh_val)}</h2>'
            f'<h2 class="lang-en">{md_inline(en_val)}</h2>'
        )
    if kind == "h3":
        return f'<h3 class="lang-zh">{md_inline(zh_val)}</h3><h3 class="lang-en">{md_inline(en_val)}</h3>'
    if kind == "p":
        return f'<p class="lang-zh">{md_inline(zh_val)}</p><p class="lang-en">{md_inline(en_val)}</p>'
    if kind == "quote":
        zh_html = "<br>".join(md_inline(x) for x in str(zh_val).split("\n") if x.strip())
        en_html = "<br>".join(md_inline(x) for x in str(en_val).split("\n") if x.strip())
        return f'<blockquote class="lang-zh">{zh_html}</blockquote><blockquote class="lang-en">{en_html}</blockquote>'
    if kind == "ul":
        zh_li = "".join(f"<li>{md_inline(x)}</li>" for x in zh_val)
        en_li = "".join(f"<li>{md_inline(x)}</li>" for x in en_val)
        return f'<ul class="lang-zh">{zh_li}</ul><ul class="lang-en">{en_li}</ul>'
    if kind == "ol":
        zh_li = "".join(f"<li>{md_inline(x)}</li>" for x in zh_val)
        en_li = "".join(f"<li>{md_inline(x)}</li>" for x in en_val)
        return f'<ol class="lang-zh">{zh_li}</ol><ol class="lang-en">{en_li}</ol>'
    return ""


def article_from_md(zh_md: str, en_md: str, img_rewriter, label: str) -> str:
    zb = parse_blocks(zh_md)
    eb = parse_blocks(en_md)
    kinds_z = [k for k, _ in zb]
    kinds_e = [k for k, _ in eb]
    if kinds_z != kinds_e:
        print(f"[warn] {label} block mismatch")
        print(" zh", kinds_z)
        print(" en", kinds_e)
        # still try to zip by kind with a pointer walk
    out = []
    zi = ei = 0
    while zi < len(zb) and ei < len(eb):
        zk, zv = zb[zi]
        ek, ev = eb[ei]
        if zk == ek:
            out.append(render_pair(zk, zv, ev, img_rewriter))
            zi += 1
            ei += 1
            continue
        print(f"[warn] {label} diverge at zh[{zi}]={zk} en[{ei}]={ek}")
        out.append(render_pair(zk, zv, zv, img_rewriter))
        zi += 1
    while zi < len(zb):
        zk, zv = zb[zi]
        out.append(render_pair(zk, zv, zv, img_rewriter))
        zi += 1
    while ei < len(eb):
        ek, ev = eb[ei]
        out.append(render_pair(ek, ev, ev, img_rewriter))
        ei += 1
    print(f"[ok] {label} zh_blocks={len(zb)} en_blocks={len(eb)} html_parts={len(out)}")
    return "\n".join(x for x in out if x)


def nav(prefix: str) -> str:
    home = f"{prefix}"
    research = f"{prefix}research/"
    about = f"{prefix}about.html"
    login = f"{prefix}login.html"
    return f"""<header class="nav">
  <a class="brand" href="{home}">DRLabs</a>
  <a href="{home}"><span class="lang-zh">首页</span><span class="lang-en">Home</span></a>
  <a href="{research}"><span class="lang-zh">研究报告</span><span class="lang-en">Research</span></a>
  <a href="{about}"><span class="lang-zh">关于</span><span class="lang-en">About</span></a>
  <span class="spacer"></span>
  <a class="lang-btn" href="#" onclick="cycleLang();return false;" id="langLabel" title="Language / 语言">中文 · EN</a>
  <a class="theme-btn" href="#" onclick="cycleTheme();return false;" id="themeLabel">皮肤:自动</a>
  <span id="authSlot" data-login="{login}"></span>
</header>"""


def footer() -> str:
    return """<footer>
  <span class="lang-zh">内容仅供研究参考，不构成投资建议。加密资产风险极高，投资请理性。</span>
  <span class="lang-en">For research only. Not investment advice. Crypto can result in partial or total loss.</span>
</footer>"""


def page(title_zh: str, title_en: str, prefix: str, body: str) -> str:
    css = f"{prefix}assets/site.css"
    js = f"{prefix}assets/site.js"
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-title-zh="{html.escape(title_zh)}" data-title-en="{html.escape(title_en)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title_zh)}</title>
<link rel="stylesheet" href="{css}">
{BOOT}
</head>
<body>
<div class="wrap">
{nav(prefix)}
<main>
{body}
</main>
{footer()}
</div>
<script src="{js}"></script>
</body>
</html>
"""


HOME_BODY = """
  <p class="muted lang-zh">DRLabs 首席研究 · 数据驱动</p>
  <p class="muted lang-en">DRLabs chief research · data first</p>
  <h1 class="lang-zh">把链上复杂事，写成能读懂的研报</h1>
  <h1 class="lang-en">Turn on-chain complexity into reports you can actually read</h1>
  <p class="lang-zh">覆盖 DeFi、GameFi、Meme 与关键技术范式。右上角可切换中文 / English；表格单元格始终中英对照。</p>
  <p class="lang-en">Coverage: DeFi, GameFi, memes and core tech patterns. Switch Chinese / English at top right. Table cells stay bilingual.</p>
  <div class="card">
    <span class="badge">6.6 / 10</span>
    <h2 style="margin:8px 0"><a href="research/bnb/"><span class="lang-zh">BNB 研究简报：百亿美元定价，链上锁仓只解释一小部分</span><span class="lang-en">BNB research note: a $100B price tag that on-chain TVL only partly explains</span></a></h2>
    <p class="muted"><span class="lang-zh">2026年9月8日 · BNB</span><span class="lang-en">8 Sep 2026 · BNB</span></p>
    <p class="lang-zh">市值第四、BSC 仍然很忙；千亿定价主要来自平台与燃烧，链上 TVL 只能解释一小部分。</p>
    <p class="lang-en">Fourth by market cap, BSC is still busy; the $100B valuation is mainly platform plus burn. On-chain TVL only explains a slice.</p>
  </div>
  <div class="card">
    <span class="badge">6.7 / 10</span>
    <h2 style="margin:8px 0"><a href="research/aave/"><span class="lang-zh">Aave 研究简报：借贷龙头仍在，V4 仍处早期</span><span class="lang-en">Aave research note: lending leader still, V4 still early</span></a></h2>
    <p class="muted"><span class="lang-zh">2026年9月7日 · AAVE</span><span class="lang-en">7 Sep 2026 · AAVE</span></p>
    <p class="lang-zh">仍是借贷赛道规模与品牌龙头；V3 扛主力，V4 已上线但保守放量。</p>
    <p class="lang-en">Still the scale and brand leader in lending. V3 carries the book; V4 is live with conservative caps.</p>
  </div>
  <p><a href="research/"><span class="lang-zh">阅读全部研究报告 →</span><span class="lang-en">All research notes →</span></a></p>
"""

RESEARCH_BODY = """
  <h1 class="lang-zh">研究报告</h1>
  <h1 class="lang-en">Research</h1>
  <p class="muted lang-zh">按发布日期倒序。摘要可公开浏览，正文需登录。表格为中英对照。</p>
  <p class="muted lang-en">Newest first. Abstracts are public; full text requires login. Tables stay bilingual.</p>
  <div class="card">
    <span class="badge">6.6 / 10</span>
    <h2 style="margin:8px 0"><a href="bnb/"><span class="lang-zh">BNB 研究简报：百亿美元定价，链上锁仓只解释一小部分</span><span class="lang-en">BNB research note: a $100B price tag that on-chain TVL only partly explains</span></a></h2>
    <p class="muted"><span class="lang-zh">2026年9月8日 · BNB</span><span class="lang-en">8 Sep 2026 · BNB</span></p>
    <p class="lang-zh">市值第四、BSC 仍然很忙；千亿定价主要来自平台与燃烧，链上 TVL 只能解释一小部分。</p>
    <p class="lang-en">Fourth by market cap, BSC is still busy; the $100B valuation is mainly platform plus burn. On-chain TVL only explains a slice.</p>
  </div>
  <div class="card">
    <span class="badge">6.7 / 10</span>
    <h2 style="margin:8px 0"><a href="aave/"><span class="lang-zh">Aave 研究简报：借贷龙头仍在，V4 仍处早期</span><span class="lang-en">Aave research note: lending leader still, V4 still early</span></a></h2>
    <p class="muted"><span class="lang-zh">2026年9月7日 · AAVE</span><span class="lang-en">7 Sep 2026 · AAVE</span></p>
    <p class="lang-zh">仍是借贷赛道规模与品牌龙头；V3 扛主力，V4 已上线但保守放量。</p>
    <p class="lang-en">Still the scale and brand leader in lending. V3 carries the book; V4 is live with conservative caps.</p>
  </div>
"""

ABOUT_BODY = """
  <h1 class="lang-zh">关于 DRLabs</h1>
  <h1 class="lang-en">About DRLabs</h1>
  <p class="lang-zh">DRLabs 发布加密货币与链上协议研究报告，侧重 DeFi、GameFi、Meme 与技术范式拆解，并以多平台内容服务社区读者。</p>
  <p class="lang-en">DRLabs publishes crypto and on-chain protocol research, focused on DeFi, GameFi, memes and tech patterns, and serves community readers across platforms.</p>
  <h2 class="lang-zh">语言</h2>
  <h2 class="lang-en">Language</h2>
  <p class="lang-zh">右上角可切换中文 / English。正文与导航随语言切换；表格单元格同时保留中英对照，切换后数字仍可对照。</p>
  <p class="lang-en">Use the top-right control to switch Chinese / English. Prose and navigation switch with the UI. Table cells keep both languages so numbers stay comparable.</p>
  <div id="disclaimer">
  <h2 class="lang-zh">免责声明</h2>
  <h2 class="lang-en">Disclaimer</h2>
  <p class="lang-zh">本站内容基于公开信息整理，仅供一般性信息参考与研究讨论，不构成投资建议、要约或承诺。加密资产波动剧烈，可能导致部分或全部本金损失。读者应独立判断并自行承担决策后果。文中买入评分为主观量化结果，不代表买卖推荐。数据可能存在延迟、口径差异或错误，DRLabs 不保证其完整性与时效性。</p>
  <p class="lang-en">Site content is compiled from public information for general reference and research discussion. It is not investment advice, an offer or a commitment. Crypto is volatile and can cause partial or total loss of principal. Readers should judge independently and own the consequences. Buy scores are subjective quantifications, not trade recommendations. Data may be delayed, differently defined or wrong; DRLabs does not warrant completeness or timeliness.</p>
  </div>
"""

LOGIN_BODY = """
<div class="gate card">
  <h1 class="lang-zh">登录 / 注册</h1>
  <h1 class="lang-en">Log in / Sign up</h1>
  <p class="muted lang-zh">使用手机号 + 密码。阅读研报前需登录。我们仅保存手机号与密码哈希，用于阅读权限；不出售数据。</p>
  <p class="muted lang-en">Use phone number + password. Login is required before full reports. We store only the phone number and a password hash for reading access. We do not sell data.</p>
  <div>
    <label><span class="lang-zh">手机号</span><span class="lang-en">Phone</span></label>
    <input id="phone" type="tel" data-i18n-placeholder="auth.phonePh" autocomplete="username">
    <label><span class="lang-zh">密码</span><span class="lang-en">Password</span></label>
    <input id="password" type="password" data-i18n-placeholder="auth.passwordPh" autocomplete="new-password">
    <p id="msg" class="err"></p>
    <p>
      <button class="btn" type="button" onclick="doLogin()"><span class="lang-zh">登录</span><span class="lang-en">Log in</span></button>
      <button class="btn secondary" type="button" onclick="doRegister()"><span class="lang-zh">注册</span><span class="lang-en">Sign up</span></button>
    </p>
  </div>
</div>
"""


def article_shell(prefix: str, meta_zh: str, meta_en: str, article_html: str) -> str:
    login = f"{prefix}login.html"
    return f"""
  <div id="loginNeeded" class="login-needed card" style="display:none">
    <p><strong class="lang-zh">登录后阅读完整研报</strong><strong class="lang-en">Log in to read the full report</strong></p>
    <p class="muted lang-zh">未登录不展示正文，避免只看到图片预览。</p>
    <p class="muted lang-en">The body is hidden until you log in, so the charts are not shown as a free preview.</p>
    <p class="muted lang-zh">注册只需手机号 + 密码（无短信费用）。</p>
    <p class="muted lang-en">Sign up with phone number + password. No SMS fee.</p>
    <p><a class="btn" href="{login}"><span class="lang-zh">去登录 / 注册</span><span class="lang-en">Log in / Sign up</span></a></p>
  </div>
  <article id="article" data-locked="1">
  <p class="muted"><span class="lang-zh">{html.escape(meta_zh)}</span><span class="lang-en">{html.escape(meta_en)}</span></p>
{article_html}
  </article>
"""


def main() -> None:
    aave_zh = (ROOT / "research/aave/report.md").read_text(encoding="utf-8")
    aave_en = (ROOT / "research/aave/report.en.md").read_text(encoding="utf-8")
    bnb_zh = (ROOT / "research/bnb/report.md").read_text(encoding="utf-8")
    bnb_en = (ROOT / "research/bnb/report.en.md").read_text(encoding="utf-8")

    (ROOT / "index.html").write_text(
        page("DRLabs — 加密货币研究", "DRLabs — Crypto Research", "./", HOME_BODY), encoding="utf-8"
    )
    (ROOT / "research/index.html").write_text(
        page("研究报告 · DRLabs", "Research · DRLabs", "../", RESEARCH_BODY), encoding="utf-8"
    )
    (ROOT / "about.html").write_text(
        page("关于 · DRLabs", "About · DRLabs", "./", ABOUT_BODY), encoding="utf-8"
    )
    (ROOT / "login.html").write_text(
        page("登录/注册 · DRLabs", "Log in / Sign up · DRLabs", "./", LOGIN_BODY), encoding="utf-8"
    )

    aave_html = article_from_md(aave_zh, aave_en, lambda s: rewrite_img(s, "aave"), "aave")
    bnb_html = article_from_md(bnb_zh, bnb_en, lambda s: rewrite_img(s, "bnb"), "bnb")

    (ROOT / "research/aave/index.html").write_text(
        page(
            "Aave 研报 · DRLabs",
            "Aave report · DRLabs",
            "../../",
            article_shell(
                "../../",
                "发布 / 数据日期：2026年9月7日 · AAVE · 6.7 / 10",
                "Published / as-of: 7 Sep 2026 · AAVE · 6.7 / 10",
                aave_html,
            ),
        ),
        encoding="utf-8",
    )
    (ROOT / "research/bnb/index.html").write_text(
        page(
            "BNB 研报 · DRLabs",
            "BNB report · DRLabs",
            "../../",
            article_shell(
                "../../",
                "发布 / 数据日期：2026年9月8日 · BNB · 6.6 / 10",
                "Published / as-of: 8 Sep 2026 · BNB · 6.6 / 10",
                bnb_html,
            ),
        ),
        encoding="utf-8",
    )

    if ASTRO_GEN.parent.exists():
        ASTRO_GEN.mkdir(parents=True, exist_ok=True)
        aave_astro = article_from_md(
            aave_zh, aave_en, lambda s: rewrite_img_astro(s, "aave-2026-09-07"), "aave-astro"
        )
        bnb_astro = article_from_md(
            bnb_zh, bnb_en, lambda s: rewrite_img_astro(s, "bnb-2026-09-08"), "bnb-astro"
        )
        (ASTRO_GEN / "aave-2026-09-07.html").write_text(aave_astro, encoding="utf-8")
        (ASTRO_GEN / "bnb-2026-09-08.html").write_text(bnb_astro, encoding="utf-8")
        print("wrote astro fragments")

    print("done")


if __name__ == "__main__":
    main()

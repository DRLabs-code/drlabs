#!/usr/bin/env python3
"""Build bilingual static HTML for the live DRLabs GitHub Pages site."""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path("/tmp/drlabs-live")
ASTRO_GEN = Path("/workspace/src/generated")

LANGS = ("zh", "en", "ja", "ko", "fr", "es", "ru")
LANG_HTML = {"zh": "zh-CN", "en": "en", "ja": "ja", "ko": "ko", "fr": "fr", "es": "es", "ru": "ru"}
LANG_LABEL = {
    "zh": "中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "es": "Español",
    "ru": "Русский",
}

BOOT = """<script>
(function(){try{var k='drlabs-lang';var allow=['zh','en','ja','ko','fr','es','ru'];
var l=localStorage.getItem(k);var n=((navigator.language||'zh')+'').toLowerCase();
if(allow.indexOf(l)<0){l=n.indexOf('zh')===0?'zh':n.indexOf('ja')===0?'ja':n.indexOf('ko')===0?'ko':n.indexOf('fr')===0?'fr':n.indexOf('es')===0?'es':n.indexOf('ru')===0?'ru':'en';}
var map={zh:'zh-CN',en:'en',ja:'ja',ko:'ko',fr:'fr',es:'es',ru:'ru'};
document.documentElement.setAttribute('data-lang',l);
document.documentElement.setAttribute('lang',map[l]||'en');
var th=localStorage.getItem('drlabs-theme');
var h=new Date().getHours();
document.documentElement.setAttribute('data-theme',(th==='light'||th==='dark')?th:(h>=6&&h<18?'light':'dark'));
}catch(e){}})();
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
    folder = {"aave": "aave", "bnb": "bnb", "uni": "uni", "doge": "doge"}.get(kind)
    if folder:
        return f"../../assets/{folder}/{name}"
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
    if slug.startswith("uni"):
        return f"../uni/{name}"
    if slug.startswith("doge"):
        return f"../doge/{name}"
    return f"../bnb/{name}"


def bundle(tag: str, texts: dict[str, str], cls: str = "") -> str:
    parts = []
    for lang in LANGS:
        if lang not in texts:
            continue
        classes = f"lang-{lang}" + (f" {cls}" if cls else "")
        parts.append(f'<{tag} class="{classes}">{html.escape(texts[lang])}</{tag}>')
    return "\n".join(parts)


def spans(texts: dict[str, str]) -> str:
    return "".join(f'<span class="lang-{lang}">{html.escape(texts[lang])}</span>' for lang in LANGS if lang in texts)


def md_tags(tag: str, texts: dict[str, str], extra_for: dict[str, str] | None = None) -> str:
    parts = []
    extra_for = extra_for or {}
    for lang in LANGS:
        if lang not in texts:
            continue
        extra = extra_for.get(lang, "")
        parts.append(f"<{tag} class=\"lang-{lang}\"{extra}>{md_inline(str(texts[lang]))}</{tag}>")
    return "".join(parts)


def render_langs(kind: str, vals: dict[str, object], img_rewriter) -> str:
    if kind == "hr":
        return "<hr />"
    if kind == "table":
        zh = vals.get("zh")
        en = vals.get("en")
        return table_html(zh if isinstance(zh, list) else [], en if isinstance(en, list) else None)
    if kind == "img":
        zh_val = vals.get("zh") or next(iter(vals.values()))
        alt, src, cap = zh_val if isinstance(zh_val, tuple) and len(zh_val) == 3 else (zh_val[0], zh_val[1], zh_val[0])
        src = img_rewriter(src)
        caps = []
        for lang in LANGS:
            v = vals.get(lang, zh_val)
            c = v[2] if isinstance(v, tuple) and len(v) == 3 else cap
            caps.append(f'<figcaption class="lang-{lang}">{md_inline(str(c))}</figcaption>')
        return f'<figure><img src="{html.escape(src)}" alt="{html.escape(alt)}">{"".join(caps)}</figure>'
    texts = {lang: str(vals[lang]) for lang in LANGS if lang in vals}
    if kind == "h1":
        return md_tags("h1", texts)
    if kind == "h2":
        sid = slugify(str(vals.get("zh") or next(iter(vals.values()))))
        extra = {lang: f' id="{html.escape(sid)}"' if lang == "zh" else "" for lang in texts}
        return md_tags("h2", texts, extra)
    if kind == "h3":
        return md_tags("h3", texts)
    if kind == "p":
        return md_tags("p", texts)
    if kind == "quote":
        parts = []
        for lang in LANGS:
            if lang not in vals:
                continue
            inner = "<br>".join(md_inline(x) for x in str(vals[lang]).split("\n") if x.strip())
            parts.append(f'<blockquote class="lang-{lang}">{inner}</blockquote>')
        return "".join(parts)
    if kind in ("ul", "ol"):
        parts = []
        for lang in LANGS:
            items = vals.get(lang)
            if not isinstance(items, list):
                continue
            lis = "".join(f"<li>{md_inline(x)}</li>" for x in items)
            parts.append(f"<{kind} class=\"lang-{lang}\">{lis}</{kind}>")
        return "".join(parts)
    return ""


def article_from_mds(mds: dict[str, str], img_rewriter, label: str) -> str:
    parsed = {lang: parse_blocks(text) for lang, text in mds.items()}
    driver = parsed["zh"]
    for lang, blocks in parsed.items():
        kinds = [k for k, _ in blocks]
        if kinds != [k for k, _ in driver]:
            print(f"[warn] {label} {lang} kinds differ (len {len(kinds)} vs zh {len(driver)})")
    out = []
    for i, (kind, _) in enumerate(driver):
        vals = {}
        for lang, blocks in parsed.items():
            if i < len(blocks) and blocks[i][0] == kind:
                vals[lang] = blocks[i][1]
            elif i < len(blocks):
                vals[lang] = blocks[i][1]
            else:
                vals[lang] = driver[i][1]
        out.append(render_langs(kind, vals, img_rewriter))
    print(f"[ok] {label} langs={list(parsed)} blocks={len(driver)}")
    return "\n".join(x for x in out if x)


def lang_menu() -> str:
    buttons = "".join(
        f'<button type="button" data-set-lang="{lang}">{html.escape(label)}</button>'
        for lang, label in LANG_LABEL.items()
    )
    return f"""<div class="lang-wrap">
  <button type="button" class="lang-btn" id="langLabel" onclick="toggleLangMenu();return false;" aria-haspopup="listbox" aria-expanded="false">中文</button>
  <div class="lang-menu" id="langMenu" hidden role="listbox">{buttons}</div>
</div>"""


def nav(prefix: str) -> str:
    home = f"{prefix}"
    research = f"{prefix}research/"
    about = f"{prefix}about.html"
    login = f"{prefix}login.html"
    return f"""<header class="nav">
  <a class="brand" href="{home}">DRLabs</a>
  <a href="{home}">{spans({"zh": "首页", "en": "Home", "ja": "ホーム", "ko": "홈", "fr": "Accueil", "es": "Inicio", "ru": "Главная"})}</a>
  <a href="{research}">{spans({"zh": "研究报告", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"})}</a>
  <a href="{about}">{spans({"zh": "关于", "en": "About", "ja": "概要", "ko": "소개", "fr": "À propos", "es": "Acerca de", "ru": "О нас"})}</a>
  <span class="spacer"></span>
  {lang_menu()}
  <button type="button" class="theme-btn" id="themeToggle" onclick="cycleTheme();return false;" aria-label="Toggle theme">
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
      <g class="sun"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="M4.93 4.93l1.41 1.41"/><path d="M17.66 17.66l1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="M4.93 19.07l1.41-1.41"/><path d="M17.66 6.34l1.41-1.41"/></g>
      <g class="moon"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></g>
    </svg>
  </button>
  <span id="authSlot" data-login="{login}"></span>
</header>"""


def footer(prefix: str = "./") -> str:
    return (
        "<footer class=\"site-footer\">\n"
        "<div class=\"footer-grid\">\n<div>\n"
        + bundle("p", {"zh": "DRLabs", "en": "DRLabs", "ja": "DRLabs", "ko": "DRLabs", "fr": "DRLabs", "es": "DRLabs", "ru": "DRLabs"}, cls="footer-title")
        + bundle("p", {
            "zh": "分布式加密项目研究室。成员在新加坡、澳大利亚与英国。",
            "en": "Distributed crypto research lab. Members in Singapore, Australia and the United Kingdom.",
            "ja": "分散型暗号プロジェクト研究室。メンバーはシンガポール、オーストラリア、英国。",
            "ko": "분산형 암호화 프로젝트 연구실. 구성원은 싱가포르, 호주, 영국.",
            "fr": "Laboratoire crypto distribué. Membres à Singapour, en Australie et au Royaume-Uni.",
            "es": "Laboratorio cripto distribuido. Miembros en Singapur, Australia y Reino Unido.",
            "ru": "Распределённая криптолаборатория. Участники в Сингапуре, Австралии и Великобритании.",
        }, cls="muted")
        + "</div>\n<div>\n"
        + bundle("p", {"zh": "目录", "en": "Index", "ja": "目次", "ko": "목차", "fr": "Index", "es": "Índice", "ru": "Содержание"}, cls="footer-title")
        + f'<p><a href="{prefix}research/">{spans({"zh": "研究报告", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"})}</a>'
        + f' · <a href="{prefix}about.html">{spans({"zh": "关于", "en": "About", "ja": "概要", "ko": "소개", "fr": "À propos", "es": "Acerca de", "ru": "О нас"})}</a>'
        + f' · <a href="{prefix}rss.xml">RSS</a></p>\n</div>\n<div>\n'
        + bundle("p", {"zh": "联系", "en": "Contact", "ja": "連絡", "ko": "연락", "fr": "Contact", "es": "Contacto", "ru": "Контакты"}, cls="footer-title")
        + f'<p><a href="https://github.com/DRLabs-code" rel="noreferrer">DRLabs-code</a>'
        + f' · <a href="{prefix}about.html#disclaimer">{spans({"zh": "免责声明", "en": "Disclaimer", "ja": "免責", "ko": "면책", "fr": "Avertissement", "es": "Aviso", "ru": "Отказ"})}</a></p>'
        + bundle("p", {
            "zh": "内容仅供研究参考，不构成投资建议。加密资产风险极高，投资请理性。",
            "en": "For research only. Not investment advice. Crypto can result in partial or total loss.",
            "ja": "研究目的のみ。投資助言ではありません。暗号資産は元本の一部または全部を失う可能性があります。",
            "ko": "연구 참고용이며 투자 자문이 아닙니다. 암호화폐는 원금 일부 또는 전액 손실이 날 수 있습니다.",
            "fr": "Recherche uniquement. Pas un conseil d’investissement. Les cryptoactifs peuvent entraîner une perte partielle ou totale.",
            "es": "Solo investigación. No es consejo de inversión. Los criptoactivos pueden causar pérdida parcial o total.",
            "ru": "Только для исследования, не инвестиционная рекомендация. Криптоактивы могут привести к частичной или полной потере средств.",
        }, cls="muted")
        + "</div>\n</div>\n</footer>"
    )


def archive_item(href: str, topics: str, ticker: str, dates: dict[str, str], as_of: str, titles: dict[str, str], summary: dict[str, str], score: str) -> str:
    chips = "".join(f'<span class="chip">{html.escape(topic)}</span>' for topic in topics.split())
    return f"""
<article class="archive-item" data-topics="{html.escape(topics)}">
  <p class="archive-meta"><span class="ticker">{html.escape(ticker)}</span>{chips} {spans(dates)} · as-of {html.escape(as_of)}</p>
  <h2><a href="{href}">{spans(titles)}</a></h2>
  {bundle("p", summary)}
  <p class="muted archive-foot">{html.escape(score)} / 10</p>
</article>
"""


def filter_bar() -> str:
    return f"""
<div class="filter-bar" data-filter-bar>
  <button type="button" data-filter-topic="all" aria-pressed="true">{spans({"zh": "全部", "en": "All", "ja": "すべて", "ko": "전체", "fr": "Tout", "es": "Todas", "ru": "Все"})}</button>
  <button type="button" data-filter-topic="DeFi" aria-pressed="false">DeFi</button>
  <button type="button" data-filter-topic="GameFi" aria-pressed="false">GameFi</button>
  <button type="button" data-filter-topic="Meme" aria-pressed="false">Meme</button>
  <button type="button" data-filter-topic="L1" aria-pressed="false">L1</button>
</div>
"""


def page(titles: dict[str, str], prefix: str, body: str) -> str:
    css = f"{prefix}assets/site.css"
    js = f"{prefix}assets/site.js"
    attrs = " ".join(f'data-title-{lang}="{html.escape(text)}"' for lang, text in titles.items())
    return f"""<!DOCTYPE html>
<html lang="zh-CN" {attrs}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titles.get("zh", "DRLabs"))}</title>
<link rel="stylesheet" href="{css}">
{BOOT}
</head>
<body>
<div class="wrap">
{nav(prefix)}
<main>
{body}
</main>
{footer(prefix)}
</div>
<script src="{js}"></script>
</body>
</html>
"""


BNB_TITLE = {
    "zh": "BNB 研究简报：百亿美元定价，链上锁仓只解释一小部分",
    "en": "BNB research note: a $100B price tag that on-chain TVL only partly explains",
    "ja": "BNBリサーチノート：オンチェーンTVLだけでは部分的にしか説明できない1000億ドルの価格",
    "ko": "BNB 리서치 노트: 온체인 TVL이 일부만 설명하는 1000억 달러 가격",
    "fr": "Note BNB : une valorisation de 100 Md$ que la TVL on-chain n’explique qu’en partie",
    "es": "Nota BNB: una etiqueta de 100 000 M$ que el TVL on-chain solo explica en parte",
    "ru": "Записка по BNB: оценка $100 млрд, которую ончейн-TVL объясняет лишь частично",
}
BNB_SUM = {
    "zh": "市值第四、BSC 仍然很忙；千亿定价主要来自平台与燃烧，链上 TVL 只能解释一小部分。",
    "en": "Fourth by market cap, BSC is still busy; the $100B valuation is mainly platform plus burn. On-chain TVL only explains a slice.",
    "ja": "時価総額4位でBSCは依然活発。1000億ドルの価格は主にプラットフォームとバーン。オンチェーンTVLは一部しか説明しない。",
    "ko": "시가총액 4위, BSC는 여전히 분주합니다. 1000억 달러 가치는 주로 플랫폼과 소각이며, 온체인 TVL은 일부만 설명합니다.",
    "fr": "4e en capitalisation, BSC reste actif ; les 100 Md$ viennent surtout de la plateforme et du burn. La TVL n’explique qu’une part.",
    "es": "Cuarto por capitalización; BSC sigue activo. Los 100 000 M$ vienen sobre todo de la plataforma y el burn; el TVL solo explica una parte.",
    "ru": "4-е место по капитализации, BSC по-прежнему активен. Оценка $100 млрд — в основном платформа и сжигание; TVL объясняет лишь часть.",
}
BNB_DATE = {
    "zh": "2026年9月8日",
    "en": "8 Sep 2026",
    "ja": "2026年9月8日",
    "ko": "2026년 9월 8일",
    "fr": "8 sept. 2026",
    "es": "8 sep 2026",
    "ru": "8 сен 2026",
}
AAVE_TITLE = {
    "zh": "Aave 研究简报：借贷龙头仍在，V4 仍处早期",
    "en": "Aave research note: lending leader still, V4 still early",
    "ja": "Aaveリサーチノート：レンディングの盟主は健在、V4はまだ初期",
    "ko": "Aave 리서치 노트: 대출 선두는 유지, V4는 아직 초기",
    "fr": "Note Aave : toujours leader du lending, V4 encore au début",
    "es": "Nota Aave: sigue siendo líder de préstamos, V4 aún temprano",
    "ru": "Записка по Aave: лидер кредитования на месте, V4 ещё ранний",
}
AAVE_SUM = {
    "zh": "仍是借贷赛道规模与品牌龙头；V3 扛主力，V4 已上线但保守放量。",
    "en": "Still the scale and brand leader in lending. V3 carries the book; V4 is live with conservative caps.",
    "ja": "レンディングの規模とブランドで依然首位。主力はV3、V4は稼働済みだが上限は保守的。",
    "ko": "대출 규모와 브랜드에서 여전히 선두. V3가 본장이고 V4는 출시됐지만 한도는 보수적입니다.",
    "fr": "Toujours leader en taille et en marque. V3 porte le livre ; V4 est live avec des plafonds prudents.",
    "es": "Sigue siendo líder en escala y marca. V3 carga el libro; V4 está vivo con techos conservadores.",
    "ru": "По-прежнему лидер по масштабу и бренду. V3 несёт основную книгу; V4 запущен с консервативными лимитами.",
}
AAVE_DATE = {
    "zh": "2026年9月7日",
    "en": "7 Sep 2026",
    "ja": "2026年9月7日",
    "ko": "2026년 9월 7일",
    "fr": "7 sept. 2026",
    "es": "7 sep 2026",
    "ru": "7 сен 2026",
}
UNI_TITLE = {
    "zh": "UNI 研究简报：DEX 费用池很厚，代币仍只分到一薄层",
    "en": "UNI research note: a thick DEX fee pool, a thin slice for the token",
    "ja": "UNIリサーチノート：DEXの手数料は厚いが、トークンが取る分は薄い",
    "ko": "UNI 리서치 노트: DEX 수수료 풀은 두껍고, 토큰 몫은 얇다",
    "fr": "Note UNI : un gros pot de frais DEX, une fine part pour le jeton",
    "es": "Nota UNI: un pozo grueso de comisiones DEX, una lonja fina para el token",
    "ru": "Записка по UNI: толстый пул комиссий DEX, тонкий кусок для токена",
}
UNI_SUM = {
    "zh": "现货 DEX 费用与成交仍是第一；近 30 日费用约 1.52 亿美元，协议收入只留下约 8%。6.9/10，谨慎跟踪。",
    "en": "Still first in spot DEX fees and volume. 30-day fees about $152M; protocol keep is about 8%. 6.9/10, cautious watch.",
    "ja": "現物DEXの手数料と出来高は首位。30日手数料約1.52億ドル、プロトコル取り分は約8%。6.9/10、慎重ウォッチ。",
    "ko": "현물 DEX 수수료와 거래대금은 1위. 30일 수수료 약 1.52억 달러, 프로토콜 몫은 약 8%. 6.9/10, 신중 추적.",
    "fr": "Toujours premier en frais et volume DEX spot. Frais 30 jours ~152 M$ ; le protocole garde ~8%. 6.9/10, suivi prudent.",
    "es": "Sigue primero en comisiones y volumen DEX spot. Comisiones 30 días ~152 M$; el protocolo se queda ~8%. 6.9/10, seguimiento cauto.",
    "ru": "По-прежнему первый по комиссиям и обороту спот-DEX. Комиссии за 30 дней ~$152 млн; протоколу ~8%. 6.9/10, осторожное наблюдение.",
}
UNI_DATE = {
    "zh": "2026年9月9日",
    "en": "9 Sep 2026",
    "ja": "2026年9月9日",
    "ko": "2026년 9월 9일",
    "fr": "9 sept. 2026",
    "es": "9 sep 2026",
    "ru": "9 сен 2026",
}
DOGE_TITLE = {
    "zh": "DOGE 研究简报：市值第十二，基本面评分仍进不了跟踪带",
    "en": "DOGE research note: twelfth by cap, still below the watch band on fundamentals",
    "ja": "DOGEリサーチノート：時価総額12位でも、ファンダメンタルはウォッチ帯に入らない",
    "ko": "DOGE 리서치 노트: 시총 12위여도 펀더멘털은 추적 밴드에 못 든다",
    "fr": "Note DOGE : 12e en capitalisation, toujours sous la bande de suivi sur les fondamentaux",
    "es": "Nota DOGE: duodécimo por capitalización, aún bajo la banda de seguimiento en fundamentales",
    "ru": "Записка по DOGE: 12-е место по капитализации, по фундаменталу всё ещё ниже полосы наблюдения",
}
DOGE_SUM = {
    "zh": "流动性与品牌都在，但没有协议收入、没有供应上限。买入评分 4.7/10，回避：可以交易，不能写成价值持仓。",
    "en": "Liquidity and brand are real. There is no protocol revenue and no hard cap. Buy score 4.7/10, avoid: tradable, not a value book.",
    "ja": "流動性とブランドは本物。プロトコル収入もハードキャップもない。4.7/10、回避。取引はできるが価値保有ではない。",
    "ko": "유동성과 브랜드는 실재. 프로토콜 수입과 하드캡은 없다. 4.7/10, 회피. 거래는 가능하고 가치 보유는 아니다.",
    "fr": "Liquidité et marque sont réelles. Pas de revenu protocole, pas de plafond. 4.7/10, éviter : négociable, pas un livre value.",
    "es": "Liquidez y marca son reales. Sin ingreso de protocolo ni tope. 4.7/10, evitar: se negocia, no es un libro value.",
    "ru": "Ликвидность и бренд реальны. Нет дохода протокола и потолка. 4.7/10, избегать: торгуется, не value-книга.",
}
DOGE_DATE = {
    "zh": "2026年9月9日",
    "en": "9 Sep 2026",
    "ja": "2026年9月9日",
    "ko": "2026년 9월 9일",
    "fr": "9 sept. 2026",
    "es": "9 sep 2026",
    "ru": "9 сен 2026",
}

def archive_block(prefix: str) -> str:
    return (
        archive_item(f"{prefix}uni/", "DeFi", "UNI", UNI_DATE, "2026-09-08 21:27 UTC", UNI_TITLE, UNI_SUM, "6.9")
        + archive_item(f"{prefix}doge/", "Meme", "DOGE", DOGE_DATE, "2026-09-08 21:27 UTC", DOGE_TITLE, DOGE_SUM, "4.7")
        + archive_item(f"{prefix}bnb/", "DeFi L1", "BNB", BNB_DATE, "2026-09-08", BNB_TITLE, BNB_SUM, "6.6")
        + archive_item(f"{prefix}aave/", "DeFi", "AAVE", AAVE_DATE, "2026-09-07", AAVE_TITLE, AAVE_SUM, "6.7")
    )


HOME_BODY = f"""
  {bundle("p", {"zh": "DRLabs", "en": "DRLabs", "ja": "DRLabs", "ko": "DRLabs", "fr": "DRLabs", "es": "DRLabs", "ru": "DRLabs"}, cls="muted")}
  {bundle("h1", {"zh": "分布式加密项目研究室", "en": "A distributed crypto research lab", "ja": "分散型暗号プロジェクト研究室", "ko": "분산형 암호화 프로젝트 연구실", "fr": "Laboratoire de recherche crypto distribué", "es": "Laboratorio de investigación cripto distribuido", "ru": "Распределённая лаборатория криптоисследований"})}
  {bundle("p", {"zh": "成员在新加坡、澳大利亚与英国。我们发布 DeFi、GameFi 与 Meme 研究报告。数字写清出处与截止时间。不是投资建议。", "en": "Members in Singapore, Australia and the United Kingdom. We publish research on DeFi, GameFi and memes. Figures carry sources and as-of times. Not investment advice.", "ja": "メンバーはシンガポール、オーストラリア、英国。DeFi、GameFi、ミームのリサーチを公開。数字には出典と基準時点を付けます。投資助言ではありません。", "ko": "구성원은 싱가포르, 호주, 영국. DeFi, GameFi, 밈 리서치를 공개합니다. 숫자는 출처와 기준 시점을 밝힙니다. 투자 자문이 아닙니다.", "fr": "Membres à Singapour, en Australie et au Royaume-Uni. Notes sur DeFi, GameFi et les memes. Les chiffres portent source et date. Pas un conseil d’investissement.", "es": "Miembros en Singapur, Australia y Reino Unido. Publicamos DeFi, GameFi y memes. Las cifras llevan fuente y fecha. No es consejo de inversión.", "ru": "Участники в Сингапуре, Австралии и Великобритании. Публикуем DeFi, GameFi и мемы. Цифры — с источником и датой. Не инвестиционная рекомендация."})}
  {bundle("h2", {"zh": "最新报告", "en": "Latest notes", "ja": "最新ノート", "ko": "최신 노트", "fr": "Dernières notes", "es": "Últimas notas", "ru": "Последние записки"})}
  <div class="archive-list">
  {archive_block("research/")}
  </div>
  <p><a href="research/">{spans({"zh": "全部报告 →", "en": "All notes →", "ja": "すべて →", "ko": "전체 →", "fr": "Tout →", "es": "Todas →", "ru": "Все →"})}</a>
  · <a href="about.html">{spans({"zh": "关于研究室", "en": "About the lab", "ja": "研究室について", "ko": "연구실 소개", "fr": "À propos", "es": "Sobre el laboratorio", "ru": "О лаборатории"})}</a></p>
"""

RESEARCH_BODY = f"""
  {bundle("p", {"zh": "研究报告", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"}, cls="muted")}
  {bundle("h1", {"zh": "出版目录", "en": "Publication index", "ja": "刊行目録", "ko": "출판 목록", "fr": "Catalogue", "es": "Catálogo", "ru": "Каталог публикаций"})}
  {bundle("p", {"zh": "按发布日期倒序。可按主题筛选。摘要公开，正文需登录。", "en": "Newest first. Filter by topic. Abstracts are public; full text needs login.", "ja": "新しい順。テーマで絞り込めます。要約は公開、本文はログイン。", "ko": "최신순. 주제로 걸러 볼 수 있습니다. 요약은 공개, 본문은 로그인.", "fr": "Les plus récentes d’abord. Filtrer par thème. Résumés publics ; texte après connexion.", "es": "Las más nuevas primero. Filtra por tema. Resúmenes públicos; el texto pide login.", "ru": "Сначала новые. Фильтр по теме. Аннотации открыты, текст после входа."}, cls="muted")}
  {filter_bar()}
  <div class="archive-list">
  {archive_block("")}
  </div>
  <p id="filterEmpty" class="muted" hidden>{spans({"zh": "该主题暂无已发布报告。", "en": "No published notes in this topic yet.", "ja": "このテーマの公開レポートはまだありません。", "ko": "이 주제의 공개 리포트가 아직 없습니다.", "fr": "Pas encore de notes dans ce thème.", "es": "Aún no hay notas en este tema.", "ru": "По этой теме записок пока нет."})}</p>
"""

ABOUT_BODY = f"""
  {bundle("h1", {"zh": "关于 DRLabs", "en": "About DRLabs", "ja": "DRLabs について", "ko": "DRLabs 소개", "fr": "À propos de DRLabs", "es": "Acerca de DRLabs", "ru": "О DRLabs"})}
  {bundle("p", {"zh": "DRLabs 是分布式加密项目研究室。我们研究 DeFi、GameFi 与 Meme，把链上项目写成可阅读的报告。对外以研究室名义发表。", "en": "DRLabs is a distributed crypto research lab. We study DeFi, GameFi and memes, and write on-chain projects into reports you can read. Notes are published in the lab’s name.", "ja": "DRLabsは分散型の暗号プロジェクト研究室です。DeFi、GameFi、ミームを扱い、オンチェーンの案件を読めるレポートにします。対外発表は研究室名義です。", "ko": "DRLabs는 분산형 암호화 프로젝트 연구실입니다. DeFi, GameFi, 밈을 다루며 온체인 프로젝트를 읽을 수 있는 리포트로 씁니다. 대외 발표는 연구실 명의입니다.", "fr": "DRLabs est un laboratoire de recherche crypto distribué. Nous étudions DeFi, GameFi et les memes. Les notes sont publiées au nom du laboratoire.", "es": "DRLabs es un laboratorio de investigación cripto distribuido. Estudiamos DeFi, GameFi y memes. Las notas se publican a nombre del laboratorio.", "ru": "DRLabs — распределённая лаборатория криптоисследований. Пишем читаемые записки по DeFi, GameFi и мемам. Публикации — от имени лаборатории."})}
  {bundle("h2", {"zh": "成员", "en": "Members", "ja": "メンバー", "ko": "구성원", "fr": "Membres", "es": "Miembros", "ru": "Участники"})}
  {bundle("p", {"zh": "研究室成员在新加坡、澳大利亚与英国工作。", "en": "Lab members work in Singapore, Australia and the United Kingdom.", "ja": "研究室のメンバーはシンガポール、オーストラリア、英国で働いています。", "ko": "연구실 구성원은 싱가포르, 호주, 영국에서 일합니다.", "fr": "Les membres du laboratoire travaillent à Singapour, en Australie et au Royaume-Uni.", "es": "Los miembros del laboratorio trabajan en Singapur, Australia y el Reino Unido.", "ru": "Участники лаборатории работают в Сингапуре, Австралии и Великобритании."}, cls="muted")}
  <ul class="people-list">
    <li><strong>{spans({"zh": "研究", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"})}</strong> · {spans({"zh": "新加坡", "en": "Singapore", "ja": "シンガポール", "ko": "싱가포르", "fr": "Singapour", "es": "Singapur", "ru": "Сингапур"})}</li>
    <li><strong>{spans({"zh": "研究", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"})}</strong> · {spans({"zh": "澳大利亚", "en": "Australia", "ja": "オーストラリア", "ko": "호주", "fr": "Australie", "es": "Australia", "ru": "Австралия"})}</li>
    <li><strong>{spans({"zh": "研究", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"})}</strong> · {spans({"zh": "英国", "en": "United Kingdom", "ja": "英国", "ko": "영국", "fr": "Royaume-Uni", "es": "Reino Unido", "ru": "Великобритания"})}</li>
  </ul>
  {bundle("h2", {"zh": "研究范围", "en": "Coverage", "ja": "対象", "ko": "범위", "fr": "Couverture", "es": "Cobertura", "ru": "Охват"})}
  <ul class="people-list">
    <li><strong>DeFi</strong> · {spans({"zh": "协议、市场结构与链上费用", "en": "Protocols, market structure and on-chain fees", "ja": "プロトコル、市場構造、オンチェーン手数料", "ko": "프로토콜, 시장 구조, 온체인 수수료", "fr": "Protocoles, structure de marché et frais on-chain", "es": "Protocolos, estructura de mercado y comisiones on-chain", "ru": "Протоколы, структура рынка и ончейн-комиссии"})}</li>
    <li><strong>GameFi</strong> · {spans({"zh": "链上游戏与相关资产", "en": "On-chain games and related assets", "ja": "オンチェーンゲームと関連資産", "ko": "온체인 게임과 관련 자산", "fr": "Jeux on-chain et actifs liés", "es": "Juegos on-chain y activos relacionados", "ru": "Ончейн-игры и связанные активы"})}</li>
    <li><strong>Meme</strong> · {spans({"zh": "高流动性迷因资产", "en": "Highly liquid meme assets", "ja": "流動性の高いミーム資産", "ko": "유동성이 높은 밈 자산", "fr": "Memes très liquides", "es": "Memes de alta liquidez", "ru": "Высоколиквидные мемы"})}</li>
  </ul>
  {bundle("h2", {"zh": "联系", "en": "Contact", "ja": "連絡", "ko": "연락", "fr": "Contact", "es": "Contacto", "ru": "Контакты"})}
  {bundle("p", {"zh": "研究与媒体问询请通过 GitHub 联系研究室。", "en": "For research or media questions, contact the lab on GitHub.", "ja": "研究・取材の問い合わせは GitHub で研究室へ。", "ko": "연구·미디어 문의는 GitHub로 연구실에 연락하세요.", "fr": "Pour la recherche ou la presse, contactez le laboratoire sur GitHub.", "es": "Para investigación o prensa, contacta al laboratorio en GitHub.", "ru": "По вопросам исследований и прессы — лаборатория в GitHub."}, cls="muted")}
  <p><a href="https://github.com/DRLabs-code" rel="noreferrer">DRLabs-code</a> · <a href="rss.xml">RSS</a></p>
  {bundle("h2", {"zh": "语言", "en": "Language", "ja": "言語", "ko": "언어", "fr": "Langue", "es": "Idioma", "ru": "Язык"})}
  {bundle("p", {"zh": "右上角可选择中文、English、日本語、한국어、Français、Español、Русский。正文与导航随语言切换；表格单元格仍保留中英对照。", "en": "Top right: Chinese, English, Japanese, Korean, French, Spanish, Russian. Prose and navigation switch; table cells stay Chinese + English.", "ja": "右上で7言語を選択。本文とナビは切り替わり、表は中英併記のまま。", "ko": "오른쪽 위에서 7개 언어를 고릅니다. 본문과 탐색은 바뀌고, 표는 중·영 대조를 유지합니다.", "fr": "7 langues en haut à droite. Le texte change ; les tableaux restent ZH+EN.", "es": "7 idiomas arriba a la derecha. El texto cambia; las tablas siguen ZH+EN.", "ru": "7 языков справа сверху. Текст переключается; таблицы остаются ZH+EN."})}
  <div id="disclaimer">
  {bundle("h2", {"zh": "免责声明", "en": "Disclaimer", "ja": "免責", "ko": "면책", "fr": "Avertissement", "es": "Aviso legal", "ru": "Отказ от ответственности"})}
  {bundle("p", {"zh": "本站内容基于公开信息整理，仅供一般性信息参考与研究讨论，不构成投资建议、要约或承诺。加密资产波动剧烈，可能导致部分或全部本金损失。读者应独立判断并自行承担决策后果。文中买入评分为主观量化结果，不代表买卖推荐。数据可能存在延迟、口径差异或错误，DRLabs 不保证其完整性与时效性。", "en": "Site content is compiled from public information for general reference and research discussion. It is not investment advice, an offer or a commitment. Crypto is volatile and can cause partial or total loss of principal. Readers should judge independently and own the consequences. Buy scores are subjective quantifications, not trade recommendations. Data may be delayed, differently defined or wrong; DRLabs does not warrant completeness or timeliness.", "ja": "本サイトは公開情報に基づく一般的な参考・研究討議であり、投資助言・募集・約束ではありません。暗号資産は変動が大きく、元本の一部または全部を失う可能性があります。判断と結果は読者自身に帰属します。買いスコアは主観的な定量であり売買推奨ではありません。データは遅延・定義差・誤りの可能性があり、完全性や適時性を保証しません。", "ko": "본 사이트는 공개 정보를 정리한 일반 참고 및 연구 토론이며 투자 자문, 청약, 약속이 아닙니다. 암호화폐는 변동성이 커 원금 일부 또는 전액 손실이 날 수 있습니다. 판단과 결과는 독자 책임입니다. 매수 점수는 주관적 정량이며 매매 추천이 아닙니다. 데이터는 지연·정의 차이·오류가 있을 수 있으며 완전성과 적시를 보장하지 않습니다.", "fr": "Le contenu est compilé à partir d’informations publiques pour référence générale et discussion. Ce n’est pas un conseil d’investissement, une offre ou un engagement. Les cryptoactifs sont volatils et peuvent entraîner une perte partielle ou totale. Les lecteurs jugent et assument. Les scores d’achat sont subjectifs, pas des recommandations. Les données peuvent être tardives, mal définies ou fausses ; aucune garantie d’exhaustivité ni d’actualité.", "es": "El contenido se compila de información pública para referencia general y debate. No es consejo de inversión, oferta ni compromiso. Los criptoactivos son volátiles y pueden causar pérdida parcial o total. El lector decide y asume. Las puntuaciones de compra son subjetivas, no recomendaciones. Los datos pueden ir retrasados, mal definidos o erróneos; no se garantiza integridad ni actualidad.", "ru": "Материалы собраны из открытых источников для справки и обсуждения. Это не инвестиционная рекомендация, оферта или обязательство. Криптоактивы волатильны и могут привести к частичной или полной потере средств. Решения и последствия — на читателе. Баллы покупки субъективны и не являются советом торговать. Данные могут запаздывать, отличаться по методике или содержать ошибки; полнота и актуальность не гарантируются."})}
  </div>
"""

LOGIN_BODY = f"""
<div class="gate card">
  {bundle("h1", {"zh": "登录 / 注册", "en": "Log in / Sign up", "ja": "ログイン / 登録", "ko": "로그인 / 가입", "fr": "Connexion / Inscription", "es": "Entrar / Registrarse", "ru": "Вход / Регистрация"})}
  {bundle("p", {"zh": "使用手机号 + 密码。阅读研报前需登录。我们仅保存手机号与密码哈希，用于阅读权限；不出售数据。", "en": "Use phone number + password. Login is required before full reports. We store only the phone number and a password hash for reading access. We do not sell data.", "ja": "電話番号とパスワード。本文はログイン後。電話番号とパスワードハッシュのみ保存し、閲覧権限に使います。データは販売しません。", "ko": "전화번호와 비밀번호. 전문은 로그인 후. 번호와 비밀번호 해시만 저장하며 열람 권한에 씁니다. 데이터를 팔지 않습니다.", "fr": "Téléphone + mot de passe. Connexion requise pour le texte intégral. Nous stockons le numéro et un hash, pour l’accès lecture. Pas de vente de données.", "es": "Teléfono + contraseña. Hay que entrar para el texto completo. Solo guardamos el número y un hash para el acceso. No vendemos datos.", "ru": "Телефон и пароль. Полный текст — после входа. Храним номер и хеш пароля для доступа. Данные не продаём."}, cls="muted")}
  <div>
    <label>{spans({"zh": "手机号", "en": "Phone", "ja": "電話番号", "ko": "전화번호", "fr": "Téléphone", "es": "Teléfono", "ru": "Телефон"})}</label>
    <input id="phone" type="tel" data-i18n-placeholder="auth.phonePh" autocomplete="username">
    <label>{spans({"zh": "密码", "en": "Password", "ja": "パスワード", "ko": "비밀번호", "fr": "Mot de passe", "es": "Contraseña", "ru": "Пароль"})}</label>
    <input id="password" type="password" data-i18n-placeholder="auth.passwordPh" autocomplete="new-password">
    <p id="msg" class="err"></p>
    <p>
      <button class="btn" type="button" onclick="doLogin()">{spans({"zh": "登录", "en": "Log in", "ja": "ログイン", "ko": "로그인", "fr": "Connexion", "es": "Entrar", "ru": "Войти"})}</button>
      <button class="btn secondary" type="button" onclick="doRegister()">{spans({"zh": "注册", "en": "Sign up", "ja": "登録", "ko": "가입", "fr": "Inscription", "es": "Registrarse", "ru": "Регистрация"})}</button>
    </p>
  </div>
</div>
"""


def article_shell(prefix: str, meta: dict[str, str], article_html: str) -> str:
    login = f"{prefix}login.html"
    return f"""
  <div id="loginNeeded" class="login-needed card" style="display:none">
    <p><strong>{spans({"zh": "登录后阅读完整研报", "en": "Log in to read the full report", "ja": "ログイン後に全文", "ko": "로그인 후 전문", "fr": "Connectez-vous pour le texte intégral", "es": "Entra para leer el informe completo", "ru": "Войдите, чтобы читать полный текст"})}</strong></p>
    <p class="muted">{spans({"zh": "未登录不展示正文，避免只看到图片预览。", "en": "The body is hidden until you log in, so the charts are not shown as a free preview.", "ja": "未ログインでは本文を出さず、図だけ見えないようにします。", "ko": "로그인 전에는 본문을 숨겨 차트만 미리 보이지 않게 합니다.", "fr": "Le corps est masqué tant que vous n’êtes pas connecté, pour ne pas offrir les graphiques en avant-goût.", "es": "El cuerpo se oculta hasta iniciar sesión, para que los gráficos no sean una vista previa gratis.", "ru": "Текст скрыт до входа, чтобы графики не были бесплатным превью."})}</p>
    <p class="muted">{spans({"zh": "注册只需手机号 + 密码（无短信费用）。", "en": "Sign up with phone number + password. No SMS fee.", "ja": "登録は電話番号とパスワードのみ（SMS料金なし）。", "ko": "가입은 전화번호와 비밀번호만 (문자 요금 없음).", "fr": "Inscription : téléphone + mot de passe. Pas de frais SMS.", "es": "Registro con teléfono y contraseña. Sin coste de SMS.", "ru": "Регистрация: телефон и пароль. Без платы за SMS."})}</p>
    <p><a class="btn" href="{login}">{spans({"zh": "去登录 / 注册", "en": "Log in / Sign up", "ja": "ログイン / 登録", "ko": "로그인 / 가입", "fr": "Connexion / Inscription", "es": "Entrar / Registrarse", "ru": "Вход / Регистрация"})}</a></p>
  </div>
  <article id="article" data-locked="1">
  <p class="muted">{spans(meta)}</p>
{article_html}
  </article>
"""


def load_mds(folder: Path) -> dict[str, str]:
    out = {"zh": (folder / "report.md").read_text(encoding="utf-8")}
    for lang in LANGS:
        if lang == "zh":
            continue
        p = folder / f"report.{lang}.md"
        if p.exists():
            out[lang] = p.read_text(encoding="utf-8")
    return out


def write_note(slug: str, titles: dict[str, str], meta: dict[str, str], astro_name: str) -> None:
    mds = load_mds(ROOT / f"research/{slug}")
    html_body = article_from_mds(mds, lambda s, k=slug: rewrite_img(s, k), slug)
    (ROOT / f"research/{slug}/index.html").write_text(
        page(titles, "../../", article_shell("../../", meta, html_body)),
        encoding="utf-8",
    )
    if ASTRO_GEN.parent.exists():
        ASTRO_GEN.mkdir(parents=True, exist_ok=True)
        (ASTRO_GEN / astro_name).write_text(
            article_from_mds(mds, lambda s, n=astro_name: rewrite_img_astro(s, n), f"{slug}-astro"),
            encoding="utf-8",
        )


def main() -> None:
    pages = [
        (ROOT / "index.html", {"zh": "DRLabs — 加密货币研究", "en": "DRLabs — Crypto Research", "ja": "DRLabs — 暗号資産リサーチ", "ko": "DRLabs — 암호화폐 리서치", "fr": "DRLabs — Recherche crypto", "es": "DRLabs — Investigación cripto", "ru": "DRLabs — Криптоисследования"}, "./", HOME_BODY),
        (ROOT / "research/index.html", {"zh": "研究报告 · DRLabs", "en": "Research · DRLabs", "ja": "リサーチ · DRLabs", "ko": "리서치 · DRLabs", "fr": "Recherche · DRLabs", "es": "Investigación · DRLabs", "ru": "Исследования · DRLabs"}, "../", RESEARCH_BODY),
        (ROOT / "about.html", {"zh": "关于 · DRLabs", "en": "About · DRLabs", "ja": "概要 · DRLabs", "ko": "소개 · DRLabs", "fr": "À propos · DRLabs", "es": "Acerca de · DRLabs", "ru": "О нас · DRLabs"}, "./", ABOUT_BODY),
        (ROOT / "login.html", {"zh": "登录/注册 · DRLabs", "en": "Log in / Sign up · DRLabs", "ja": "ログイン · DRLabs", "ko": "로그인 · DRLabs", "fr": "Connexion · DRLabs", "es": "Entrar · DRLabs", "ru": "Вход · DRLabs"}, "./", LOGIN_BODY),
    ]
    for path, titles, prefix, body in pages:
        path.write_text(page(titles, prefix, body), encoding="utf-8")
    for stale in (ROOT / "method.html", ROOT / "desk.html"):
        if stale.exists():
            stale.unlink()

    write_note("aave", {"zh": "Aave 研报 · DRLabs", "en": "Aave report · DRLabs", "ja": "Aave レポート · DRLabs", "ko": "Aave 리포트 · DRLabs", "fr": "Rapport Aave · DRLabs", "es": "Informe Aave · DRLabs", "ru": "Отчёт Aave · DRLabs"}, {"zh": "发布 2026年9月7日 · 数据 2026年9月7日 · AAVE · 6.7 / 10", "en": "Published 7 Sep 2026 · as-of 7 Sep 2026 · AAVE · 6.7 / 10", "ja": "公開 2026年9月7日 · 基準 2026年9月7日 · AAVE · 6.7 / 10", "ko": "게시 2026년 9월 7일 · 기준 2026년 9월 7일 · AAVE · 6.7 / 10", "fr": "Publication 7 sept. 2026 · as-of 7 sept. 2026 · AAVE · 6.7 / 10", "es": "Publicado 7 sep 2026 · as-of 7 sep 2026 · AAVE · 6.7 / 10", "ru": "Публикация 7 сен 2026 · as-of 7 сен 2026 · AAVE · 6.7 / 10"}, "aave-2026-09-07.html")
    write_note("bnb", {"zh": "BNB 研报 · DRLabs", "en": "BNB report · DRLabs", "ja": "BNB レポート · DRLabs", "ko": "BNB 리포트 · DRLabs", "fr": "Rapport BNB · DRLabs", "es": "Informe BNB · DRLabs", "ru": "Отчёт BNB · DRLabs"}, {"zh": "发布 2026年9月8日 · 数据 2026年9月8日 · BNB · 6.6 / 10", "en": "Published 8 Sep 2026 · as-of 8 Sep 2026 · BNB · 6.6 / 10", "ja": "公開 2026年9月8日 · 基準 2026年9月8日 · BNB · 6.6 / 10", "ko": "게시 2026년 9월 8일 · 기준 2026년 9월 8일 · BNB · 6.6 / 10", "fr": "Publication 8 sept. 2026 · as-of 8 sept. 2026 · BNB · 6.6 / 10", "es": "Publicado 8 sep 2026 · as-of 8 sep 2026 · BNB · 6.6 / 10", "ru": "Публикация 8 сен 2026 · as-of 8 сен 2026 · BNB · 6.6 / 10"}, "bnb-2026-09-08.html")
    write_note("uni", {"zh": "UNI 研报 · DRLabs", "en": "UNI report · DRLabs", "ja": "UNI レポート · DRLabs", "ko": "UNI 리포트 · DRLabs", "fr": "Rapport UNI · DRLabs", "es": "Informe UNI · DRLabs", "ru": "Отчёт UNI · DRLabs"}, {"zh": "发布 2026年9月9日 · 数据 2026年9月8日 21:27 UTC · UNI · 6.9 / 10", "en": "Published 9 Sep 2026 · as-of 8 Sep 2026 21:27 UTC · UNI · 6.9 / 10", "ja": "公開 2026年9月9日 · 基準 2026年9月8日 21:27 UTC · UNI · 6.9 / 10", "ko": "게시 2026년 9월 9일 · 기준 2026년 9월 8일 21:27 UTC · UNI · 6.9 / 10", "fr": "Publication 9 sept. 2026 · as-of 8 sept. 2026 21:27 UTC · UNI · 6.9 / 10", "es": "Publicado 9 sep 2026 · as-of 8 sep 2026 21:27 UTC · UNI · 6.9 / 10", "ru": "Публикация 9 сен 2026 · as-of 8 сен 2026 21:27 UTC · UNI · 6.9 / 10"}, "uni-2026-09-09.html")
    write_note("doge", {"zh": "DOGE 研报 · DRLabs", "en": "DOGE report · DRLabs", "ja": "DOGE レポート · DRLabs", "ko": "DOGE 리포트 · DRLabs", "fr": "Rapport DOGE · DRLabs", "es": "Informe DOGE · DRLabs", "ru": "Отчёт DOGE · DRLabs"}, {"zh": "发布 2026年9月9日 · 数据 2026年9月8日 21:27 UTC · DOGE · 4.7 / 10", "en": "Published 9 Sep 2026 · as-of 8 Sep 2026 21:27 UTC · DOGE · 4.7 / 10", "ja": "公開 2026年9月9日 · 基準 2026年9月8日 21:27 UTC · DOGE · 4.7 / 10", "ko": "게시 2026년 9월 9일 · 기준 2026년 9월 8일 21:27 UTC · DOGE · 4.7 / 10", "fr": "Publication 9 sept. 2026 · as-of 8 sept. 2026 21:27 UTC · DOGE · 4.7 / 10", "es": "Publicado 9 sep 2026 · as-of 8 sep 2026 21:27 UTC · DOGE · 4.7 / 10", "ru": "Публикация 9 сен 2026 · as-of 8 сен 2026 21:27 UTC · DOGE · 4.7 / 10"}, "doge-2026-09-09.html")

    (ROOT / "rss.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>DRLabs Research</title>
<link>https://drlabs-code.github.io/drlabs/</link>
<description>DRLabs — distributed crypto research lab. DeFi, GameFi and meme notes.</description>
<item><title>UNI research note</title><link>https://drlabs-code.github.io/drlabs/research/uni/</link><pubDate>Wed, 09 Sep 2026 00:00:00 +0000</pubDate></item>
<item><title>DOGE research note</title><link>https://drlabs-code.github.io/drlabs/research/doge/</link><pubDate>Wed, 09 Sep 2026 00:00:00 +0000</pubDate></item>
<item><title>BNB research note</title><link>https://drlabs-code.github.io/drlabs/research/bnb/</link><pubDate>Tue, 08 Sep 2026 00:00:00 +0000</pubDate></item>
<item><title>Aave research note</title><link>https://drlabs-code.github.io/drlabs/research/aave/</link><pubDate>Mon, 07 Sep 2026 00:00:00 +0000</pubDate></item>
</channel>
</rss>
""",
        encoding="utf-8",
    )
    print("done")


if __name__ == "__main__":
    main()

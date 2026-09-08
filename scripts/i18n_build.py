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
document.documentElement.setAttribute('lang',map[l]||'en');}catch(e){}})();
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
    method = f"{prefix}method.html"
    desk = f"{prefix}desk.html"
    about = f"{prefix}about.html"
    login = f"{prefix}login.html"
    return f"""<header class="nav">
  <a class="brand" href="{home}">DRLabs</a>
  <a href="{home}">{spans({"zh": "首页", "en": "Home", "ja": "ホーム", "ko": "홈", "fr": "Accueil", "es": "Inicio", "ru": "Главная"})}</a>
  <a href="{research}">{spans({"zh": "研究报告", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"})}</a>
  <a href="{method}">{spans({"zh": "方法", "en": "Method", "ja": "方法", "ko": "방법", "fr": "Méthode", "es": "Método", "ru": "Метод"})}</a>
  <a href="{desk}">{spans({"zh": "台历", "en": "Desk", "ja": "台帳", "ko": "데스크", "fr": "Bureau", "es": "Mesa", "ru": "Стол"})}</a>
  <a href="{about}">{spans({"zh": "关于", "en": "About", "ja": "概要", "ko": "소개", "fr": "À propos", "es": "Acerca de", "ru": "О нас"})}</a>
  <span class="spacer"></span>
  {lang_menu()}
  <a class="theme-btn" href="#" onclick="cycleTheme();return false;" id="themeLabel">皮肤:自动</a>
  <span id="authSlot" data-login="{login}"></span>
</header>"""


def footer(prefix: str = "./") -> str:
    return (
        "<footer>\n<p>"
        + spans({
            "zh": "内容仅供研究参考，不构成投资建议。加密资产风险极高，投资请理性。",
            "en": "For research only. Not investment advice. Crypto can result in partial or total loss.",
            "ja": "研究目的のみ。投資助言ではありません。暗号資産は元本の一部または全部を失う可能性があります。",
            "ko": "연구 참고용이며 투자 자문이 아닙니다. 암호화폐는 원금 일부 또는 전액 손실이 날 수 있습니다.",
            "fr": "Recherche uniquement. Pas un conseil d’investissement. Les cryptoactifs peuvent entraîner une perte partielle ou totale.",
            "es": "Solo investigación. No es consejo de inversión. Los criptoactivos pueden causar pérdida parcial o total.",
            "ru": "Только для исследования, не инвестиционная рекомендация. Криптоактивы могут привести к частичной или полной потере средств.",
        })
        + "</p>\n<p class=\"foot-links\">"
        + f'<a href="{prefix}method.html">{spans({"zh": "研究方法", "en": "Methodology", "ja": "方法", "ko": "방법", "fr": "Méthode", "es": "Método", "ru": "Метод"})}</a>'
        + f' · <a href="{prefix}desk.html">{spans({"zh": "研究台历", "en": "Desk log", "ja": "台帳", "ko": "데스크", "fr": "Journal", "es": "Registro", "ru": "Журнал"})}</a>'
        + f' · <a href="{prefix}about.html#disclaimer">{spans({"zh": "免责声明", "en": "Disclaimer", "ja": "免責", "ko": "면책", "fr": "Avertissement", "es": "Aviso", "ru": "Отказ"})}</a>'
        + f' · <a href="{prefix}rss.xml">RSS</a>'
        + "</p>\n</footer>"
    )


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
    "zh": "2026年9月8日 · BNB · L1",
    "en": "8 Sep 2026 · BNB · L1",
    "ja": "2026年9月8日 · BNB · L1",
    "ko": "2026년 9월 8일 · BNB · L1",
    "fr": "8 sept. 2026 · BNB · L1",
    "es": "8 sep 2026 · BNB · L1",
    "ru": "8 сен 2026 · BNB · L1",
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
    "zh": "2026年9月7日 · AAVE · DeFi",
    "en": "7 Sep 2026 · AAVE · DeFi",
    "ja": "2026年9月7日 · AAVE · DeFi",
    "ko": "2026년 9월 7일 · AAVE · DeFi",
    "fr": "7 sept. 2026 · AAVE · DeFi",
    "es": "7 sep 2026 · AAVE · DeFi",
    "ru": "7 сен 2026 · AAVE · DeFi",
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
    "zh": "2026年9月9日 · UNI · DeFi",
    "en": "9 Sep 2026 · UNI · DeFi",
    "ja": "2026年9月9日 · UNI · DeFi",
    "ko": "2026년 9월 9일 · UNI · DeFi",
    "fr": "9 sept. 2026 · UNI · DeFi",
    "es": "9 sep 2026 · UNI · DeFi",
    "ru": "9 сен 2026 · UNI · DeFi",
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
    "zh": "2026年9月9日 · DOGE · Meme",
    "en": "9 Sep 2026 · DOGE · Meme",
    "ja": "2026年9月9日 · DOGE · Meme",
    "ko": "2026년 9월 9일 · DOGE · Meme",
    "fr": "9 sept. 2026 · DOGE · Meme",
    "es": "9 sep 2026 · DOGE · Meme",
    "ru": "9 сен 2026 · DOGE · Meme",
}

HOME_BODY = f"""
  {bundle("p", {"zh": "独立研究台 · 公开数据 · 日更两篇", "en": "Independent desk · public data · two notes a day", "ja": "独立リサーチ · 公開データ · 毎日2本", "ko": "독립 데스크 · 공개 데이터 · 하루 두 편", "fr": "Bureau indépendant · données publiques · deux notes par jour", "es": "Mesa independiente · datos públicos · dos notas al día", "ru": "Независимый стол · открытые данные · две записки в день"}, cls="muted")}
  {bundle("h1", {"zh": "把判断写清楚，把风险说在前面。", "en": "Write the call clearly. Put risk in front of return.", "ja": "判断をはっきり書き、リスクをリターンの前に置く。", "ko": "판단을 분명히 쓰고, 수익보다 위험을 앞에 둔다.", "fr": "Écrire le jugement clairement. Mettre le risque avant le rendement.", "es": "Escribir el juicio con claridad. Poner el riesgo delante del retorno.", "ru": "Писать вывод ясно. Ставить риск раньше доходности."})}
  {bundle("p", {"zh": "DRLabs 用同一套七维框架给代币打分。分数可以低于 5。表格单元格始终中英对照。", "en": "DRLabs scores tokens on one seven-factor frame. Scores can print below 5. Table cells stay Chinese + English.", "ja": "DRLabsは同じ7因子で採点する。5点未満もあり得る。表は中英併記。", "ko": "DRLabs는 같은 7요인으로 채점합니다. 5점 미만도 나옵니다. 표는 중·영 대조.", "fr": "DRLabs note sur un cadre à sept facteurs. Un score peut passer sous 5. Tableaux ZH+EN.", "es": "DRLabs puntúa con un marco de siete factores. La nota puede bajar de 5. Tablas ZH+EN.", "ru": "DRLabs ставит баллы по семи факторам. Балл может быть ниже 5. Таблицы ZH+EN."})}
  <div class="stat-row">
    <div class="stat"><strong>4</strong>{bundle("p", {"zh": "已刊研报", "en": "Published notes", "ja": "公開レポート", "ko": "공개 리포트", "fr": "Notes publiées", "es": "Notas publicadas", "ru": "Записки"}, cls="muted")}</div>
    <div class="stat"><strong>2</strong>{bundle("p", {"zh": "每日更新目标", "en": "Daily target", "ja": "毎日の本数", "ko": "일일 목표", "fr": "Objectif quotidien", "es": "Objetivo diario", "ru": "Цель в день"}, cls="muted")}</div>
    <div class="stat"><strong>4.7–6.9</strong>{bundle("p", {"zh": "现有评分区间", "en": "Score range now", "ja": "現在のスコア帯", "ko": "현재 점수대", "fr": "Fourchette actuelle", "es": "Rango actual", "ru": "Текущий диапазон"}, cls="muted")}</div>
    <div class="stat"><strong>UTC</strong>{bundle("p", {"zh": "快照时区已标注", "en": "Snapshot timezone marked", "ja": "スナップショット時区", "ko": "스냅샷 시구", "fr": "Fuseau du snapshot", "es": "Zona del snapshot", "ru": "Пояс снимка"}, cls="muted")}</div>
  </div>
  {bundle("h2", {"zh": "今日台历", "en": "Today’s desk", "ja": "今日の台帳", "ko": "오늘 데스크", "fr": "Bureau du jour", "es": "Mesa de hoy", "ru": "Стол дня"})}
  <div class="card">
    <span class="badge">6.9 / 10</span>
    <span class="chip">DeFi</span>
    <h2 style="margin:8px 0"><a href="research/uni/">{spans(UNI_TITLE)}</a></h2>
    <p class="muted">{spans(UNI_DATE)}</p>
    {bundle("p", UNI_SUM)}
  </div>
  <div class="card">
    <span class="badge">4.7 / 10</span>
    <span class="chip">Meme</span>
    <h2 style="margin:8px 0"><a href="research/doge/">{spans(DOGE_TITLE)}</a></h2>
    <p class="muted">{spans(DOGE_DATE)}</p>
    {bundle("p", DOGE_SUM)}
  </div>
  {bundle("h2", {"zh": "评分怎么读", "en": "How to read a score", "ja": "スコアの読み方", "ko": "점수 읽는 법", "fr": "Lire un score", "es": "Cómo leer una nota", "ru": "Как читать балл"})}
  <div class="bands">
    <p><span class="badge">≥ 8.0</span> {spans({"zh": "积极跟踪", "en": "Active watch", "ja": "積極ウォッチ", "ko": "적극 추적", "fr": "Suivi actif", "es": "Seguimiento activo", "ru": "Активное наблюдение"})}</p>
    <p><span class="badge">6.5–7.9</span> {spans({"zh": "谨慎跟踪", "en": "Cautious watch", "ja": "慎重ウォッチ", "ko": "신중 추적", "fr": "Suivi prudent", "es": "Seguimiento cauto", "ru": "Осторожное наблюдение"})}</p>
    <p><span class="badge">5.0–6.4</span> {spans({"zh": "观望", "en": "Hold / wait", "ja": "様子見", "ko": "관망", "fr": "Attente", "es": "Espera", "ru": "Выжидание"})}</p>
    <p><span class="badge">&lt; 5.0</span> {spans({"zh": "回避（基本面分，不是立刻下跌预测）", "en": "Avoid (fundamentals, not a crash call)", "ja": "回避（ファンダ点であり暴落予測ではない）", "ko": "회피(펀더멘털 점수, 급락 예측 아님)", "fr": "Éviter (fondamentaux, pas un crash)", "es": "Evitar (fundamentales, no un crash)", "ru": "Избегать (фундамент, не прогноз обвала)"})}</p>
  </div>
  <p><a href="method.html">{spans({"zh": "阅读完整方法 →", "en": "Full methodology →", "ja": "方法の全文 →", "ko": "방법 전문 →", "fr": "Méthode complète →", "es": "Método completo →", "ru": "Полный метод →"})}</a></p>
  {bundle("h2", {"zh": "此前报告", "en": "Earlier notes", "ja": "以前のレポート", "ko": "이전 리포트", "fr": "Notes précédentes", "es": "Notas anteriores", "ru": "Предыдущие записки"})}
  <div class="card">
    <span class="badge">6.6 / 10</span>
    <h2 style="margin:8px 0"><a href="research/bnb/">{spans(BNB_TITLE)}</a></h2>
    <p class="muted">{spans(BNB_DATE)}</p>
    {bundle("p", BNB_SUM)}
  </div>
  <div class="card">
    <span class="badge">6.7 / 10</span>
    <h2 style="margin:8px 0"><a href="research/aave/">{spans(AAVE_TITLE)}</a></h2>
    <p class="muted">{spans(AAVE_DATE)}</p>
    {bundle("p", AAVE_SUM)}
  </div>
  <p><a href="research/">{spans({"zh": "全部研究报告 →", "en": "All research notes →", "ja": "すべてのリサーチ →", "ko": "전체 리서치 →", "fr": "Toutes les notes →", "es": "Todas las notas →", "ru": "Все записки →"})}</a>
  · <a href="desk.html">{spans({"zh": "研究台历", "en": "Desk log", "ja": "台帳", "ko": "데스크", "fr": "Journal", "es": "Registro", "ru": "Журнал"})}</a></p>
"""

RESEARCH_BODY = f"""
  {bundle("h1", {"zh": "研究报告", "en": "Research", "ja": "リサーチ", "ko": "리서치", "fr": "Recherche", "es": "Investigación", "ru": "Исследования"})}
  {bundle("p", {"zh": "按发布日期倒序。摘要公开，正文需登录。同一框架打分，迷因不另开一套标准。", "en": "Newest first. Abstracts are public; full text needs login. One scorecard; memes do not get a second standard.", "ja": "新しい順。要約は公開、本文はログイン。採点表は一つ。ミームに第二基準は作らない。", "ko": "최신순. 요약은 공개, 본문은 로그인. 채점표는 하나. 밈에 두 번째 기준 없음.", "fr": "Les plus récentes d’abord. Résumés publics ; texte après connexion. Un seul barème ; pas de second standard pour les memes.", "es": "Las más nuevas primero. Resúmenes públicos; el texto pide login. Una sola cartilla; los memes no tienen otro estándar.", "ru": "Сначала новые. Аннотации открыты, текст после входа. Одна таблица; мемам второй стандарт не дают."}, cls="muted")}
  <div class="card">
    <span class="badge">6.9 / 10</span>
    <span class="chip">DeFi</span>
    <h2 style="margin:8px 0"><a href="uni/">{spans(UNI_TITLE)}</a></h2>
    <p class="muted">{spans(UNI_DATE)}</p>
    {bundle("p", UNI_SUM)}
  </div>
  <div class="card">
    <span class="badge">4.7 / 10</span>
    <span class="chip">Meme</span>
    <h2 style="margin:8px 0"><a href="doge/">{spans(DOGE_TITLE)}</a></h2>
    <p class="muted">{spans(DOGE_DATE)}</p>
    {bundle("p", DOGE_SUM)}
  </div>
  <div class="card">
    <span class="badge">6.6 / 10</span>
    <span class="chip">L1</span>
    <h2 style="margin:8px 0"><a href="bnb/">{spans(BNB_TITLE)}</a></h2>
    <p class="muted">{spans(BNB_DATE)}</p>
    {bundle("p", BNB_SUM)}
  </div>
  <div class="card">
    <span class="badge">6.7 / 10</span>
    <span class="chip">DeFi</span>
    <h2 style="margin:8px 0"><a href="aave/">{spans(AAVE_TITLE)}</a></h2>
    <p class="muted">{spans(AAVE_DATE)}</p>
    {bundle("p", AAVE_SUM)}
  </div>
"""

ABOUT_BODY = f"""
  {bundle("h1", {"zh": "关于 DRLabs", "en": "About DRLabs", "ja": "DRLabs について", "ko": "DRLabs 소개", "fr": "À propos de DRLabs", "es": "Acerca de DRLabs", "ru": "О DRLabs"})}
  {bundle("p", {"zh": "DRLabs 是一间独立加密研究台。默认覆盖 DeFi、GameFi 与 Meme。每篇报告写清数据时点、来源与买入评分；分数可以低于 5。", "en": "DRLabs is an independent crypto research desk. Default coverage is DeFi, GameFi and memes. Each note states as-of time, sources and a buy score. Scores can print below 5.", "ja": "DRLabsは独立暗号リサーチデスク。既定カバーはDeFi、GameFi、ミーム。各レポートに時点、出典、買いスコアを書く。5点未満もあり得る。", "ko": "DRLabs는 독립 암호화 리서치 데스크입니다. 기본 커버는 DeFi, GameFi, 밈. 각 노트에 시점, 출처, 매수 점수를 씁니다. 5점 미만도 나옵니다.", "fr": "DRLabs est un bureau de recherche crypto indépendant. Couverture par défaut : DeFi, GameFi, memes. Chaque note date le snapshot, cite les sources et donne un score. Un score peut passer sous 5.", "es": "DRLabs es una mesa de investigación cripto independiente. Cobertura por defecto: DeFi, GameFi y memes. Cada nota fecha el snapshot, cita fuentes y da una nota. Puede bajar de 5.", "ru": "DRLabs — независимый криптоисследовательский стол. Покрытие по умолчанию: DeFi, GameFi и мемы. В каждой записке — момент снимка, источники и балл. Балл может быть ниже 5."})}
  {bundle("h2", {"zh": "研究纪律", "en": "Desk rules", "ja": "規律", "ko": "규율", "fr": "Règles", "es": "Reglas", "ru": "Правила"})}
  <ul>
    <li>{spans({"zh": "只用公开数据。数字写出来源与时点，不编造成交、锁仓或解锁。", "en": "Public data only. Every print has a source and a timestamp. No invented volume, TVL or unlocks.", "ja": "公開データのみ。数値には出典と時点。出来高・TVL・解锁は捏造しない。", "ko": "공개 데이터만. 숫자에는 출처와 시점. 거래대금·TVL·언락을 지어내지 않음.", "fr": "Données publiques seulement. Chaque chiffre a une source et une heure. Pas de volume, TVL ou unlock inventés.", "es": "Solo datos públicos. Cada cifra tiene fuente y hora. No se inventan volumen, TVL ni unlocks.", "ru": "Только открытые данные. У каждой цифры источник и время. Без выдуманных оборотов, TVL и анлоков."})}</li>
    <li>{spans({"zh": "同一套七维权重。迷因不另开高分通道。", "en": "One seven-factor weight set. Memes do not get a high-score side door.", "ja": "7因子のウェイトは一つ。ミームに高得点の抜け道は作らない。", "ko": "7요인 가중치는 하나. 밈에 고득점 옆문은 없음.", "fr": "Un seul jeu de poids. Les memes n’ont pas de porte latérale vers un haut score.", "es": "Un solo juego de pesos. Los memes no tienen puerta lateral a una nota alta.", "ru": "Один набор весов. Мемам не дают боковую дверь к высокому баллу."})}</li>
    <li>{spans({"zh": "每个日历日目标两篇代币研报，写在台历上，缺刊会标明。", "en": "Target: two token notes each calendar day, logged on the desk page. Misses are marked.", "ja": "目標は各暦日2本。台帳に残し、欠号は明示。", "ko": "목표: 달력일마다 토큰 노트 두 편. 데스크에 기록하고 결호는 표시.", "fr": "Objectif : deux notes par jour civil, journalisées. Les manques sont marqués.", "es": "Objetivo: dos notas por día civil, registradas. Las faltas se marcan.", "ru": "Цель: две записки в календарный день, в журнале. Пропуски помечаются."})}</li>
    <li>{spans({"zh": "不写持仓建议的仓位大小。评分不是买卖指令。", "en": "No position sizing. A score is not a trade ticket.", "ja": "ポジションサイズは書かない。スコアは発注ではない。", "ko": "포지션 크기는 쓰지 않음. 점수는 주문 표가 아님.", "fr": "Pas de sizing. Un score n’est pas un ticket.", "es": "Sin sizing. Una nota no es un ticket.", "ru": "Без сайзинга. Балл не тикет."})}</li>
  </ul>
  {bundle("p", {"zh": "权重、数据源与利益冲突说明见方法页。", "en": "Weights, sources and conflicts sit on the methodology page.", "ja": "ウェイト、出典、利益相反は方法ページ。", "ko": "가중치, 출처, 이해충돌은 방법 페이지.", "fr": "Poids, sources et conflits : page méthode.", "es": "Pesos, fuentes y conflictos: página de método.", "ru": "Веса, источники и конфликты — на странице метода."})}
  <p><a href="method.html">{spans({"zh": "打开研究方法", "en": "Open methodology", "ja": "方法を開く", "ko": "방법 열기", "fr": "Ouvrir la méthode", "es": "Abrir el método", "ru": "Открыть метод"})}</a></p>
  {bundle("h2", {"zh": "语言", "en": "Language", "ja": "言語", "ko": "언어", "fr": "Langue", "es": "Idioma", "ru": "Язык"})}
  {bundle("p", {"zh": "右上角可选择中文、English、日本語、한국어、Français、Español、Русский。正文与导航随语言切换；表格单元格仍保留中英对照。", "en": "Top right: Chinese, English, Japanese, Korean, French, Spanish, Russian. Prose and navigation switch; table cells stay Chinese + English.", "ja": "右上で7言語を選択。本文とナビは切り替わり、表は中英併記のまま。", "ko": "오른쪽 위에서 7개 언어를 고릅니다. 본문과 탐색은 바뀌고, 표는 중·영 대조를 유지합니다.", "fr": "7 langues en haut à droite. Le texte change ; les tableaux restent ZH+EN.", "es": "7 idiomas arriba a la derecha. El texto cambia; las tablas siguen ZH+EN.", "ru": "7 языков справа сверху. Текст переключается; таблицы остаются ZH+EN."})}
  <div id="disclaimer">
  {bundle("h2", {"zh": "免责声明", "en": "Disclaimer", "ja": "免責", "ko": "면책", "fr": "Avertissement", "es": "Aviso legal", "ru": "Отказ от ответственности"})}
  {bundle("p", {"zh": "本站内容基于公开信息整理，仅供一般性信息参考与研究讨论，不构成投资建议、要约或承诺。加密资产波动剧烈，可能导致部分或全部本金损失。读者应独立判断并自行承担决策后果。文中买入评分为主观量化结果，不代表买卖推荐。数据可能存在延迟、口径差异或错误，DRLabs 不保证其完整性与时效性。", "en": "Site content is compiled from public information for general reference and research discussion. It is not investment advice, an offer or a commitment. Crypto is volatile and can cause partial or total loss of principal. Readers should judge independently and own the consequences. Buy scores are subjective quantifications, not trade recommendations. Data may be delayed, differently defined or wrong; DRLabs does not warrant completeness or timeliness.", "ja": "本サイトは公開情報に基づく一般的な参考・研究討議であり、投資助言・募集・約束ではありません。暗号資産は変動が大きく、元本の一部または全部を失う可能性があります。判断と結果は読者自身に帰属します。買いスコアは主観的な定量であり売買推奨ではありません。データは遅延・定義差・誤りの可能性があり、完全性や適時性を保証しません。", "ko": "본 사이트는 공개 정보를 정리한 일반 참고 및 연구 토론이며 투자 자문, 청약, 약속이 아닙니다. 암호화폐는 변동성이 커 원금 일부 또는 전액 손실이 날 수 있습니다. 판단과 결과는 독자 책임입니다. 매수 점수는 주관적 정량이며 매매 추천이 아닙니다. 데이터는 지연·정의 차이·오류가 있을 수 있으며 완전성과 적시를 보장하지 않습니다.", "fr": "Le contenu est compilé à partir d’informations publiques pour référence générale et discussion. Ce n’est pas un conseil d’investissement, une offre ou un engagement. Les cryptoactifs sont volatils et peuvent entraîner une perte partielle ou totale. Les lecteurs jugent et assument. Les scores d’achat sont subjectifs, pas des recommandations. Les données peuvent être tardives, mal définies ou fausses ; aucune garantie d’exhaustivité ni d’actualité.", "es": "El contenido se compila de información pública para referencia general y debate. No es consejo de inversión, oferta ni compromiso. Los criptoactivos son volátiles y pueden causar pérdida parcial o total. El lector decide y asume. Las puntuaciones de compra son subjetivas, no recomendaciones. Los datos pueden ir retrasados, mal definidos o erróneos; no se garantiza integridad ni actualidad.", "ru": "Материалы собраны из открытых источников для справки и обсуждения. Это не инвестиционная рекомендация, оферта или обязательство. Криптоактивы волатильны и могут привести к частичной или полной потере средств. Решения и последствия — на читателе. Баллы покупки субъективны и не являются советом торговать. Данные могут запаздывать, отличаться по методике или содержать ошибки; полнота и актуальность не гарантируются."})}
  </div>
"""

METHOD_BODY = f"""
  {bundle("h1", {"zh": "研究方法", "en": "Methodology", "ja": "研究方法", "ko": "연구 방법", "fr": "Méthode", "es": "Método", "ru": "Метод"})}
  {bundle("p", {"zh": "框架版本 2026-09。权重固定。单项 0–10，加权后四舍五入到一位小数。表格为中英对照。", "en": "Framework version 2026-09. Weights are fixed. Each factor is 0–10, then weighted and rounded to one decimal. Tables stay Chinese + English.", "ja": "枠バージョン2026-09。ウェイト固定。各項目0–10、加重後に小数1桁。表は中英併記。", "ko": "프레임 버전 2026-09. 가중치 고정. 항목 0–10, 가중 후 소수 첫째 자리. 표는 중·영 대조.", "fr": "Cadre version 2026-09. Poids fixes. Chaque facteur 0–10, pondéré à une décimale. Tableaux ZH+EN.", "es": "Marco versión 2026-09. Pesos fijos. Cada factor 0–10, ponderado a un decimal. Tablas ZH+EN.", "ru": "Рамка версии 2026-09. Веса фиксированы. Каждый фактор 0–10, взвешивание до одного знака. Таблицы ZH+EN."}, cls="muted")}
  <div class="table-wrap"><table>
  <thead><tr>
    <th>维度<br><span class="bi">Factor</span></th>
    <th>权重<br><span class="bi">Weight</span></th>
    <th>观察重点<br><span class="bi">What we watch</span></th>
  </tr></thead>
  <tbody>
    <tr><td>市场地位与流动性<br><span class="bi">Market position &amp; liquidity</span></td><td>20%</td><td>市值位次、成交深度、迁移摩擦<br><span class="bi">Rank, depth, migration friction</span></td></tr>
    <tr><td>收入与费用捕获<br><span class="bi">Revenue &amp; fee capture</span></td><td>15%</td><td>费用规模、协议分成、持有人能否拿到<br><span class="bi">Fee scale, protocol take, holder claim</span></td></tr>
    <tr><td>代币经济与估值<br><span class="bi">Token economics &amp; valuation</span></td><td>15%</td><td>流通占比、解锁、通胀、市值/费用<br><span class="bi">Float, unlocks, inflation, cap / fees</span></td></tr>
    <tr><td>产品与技术演进<br><span class="bi">Product &amp; tech path</span></td><td>15%</td><td>版本路线、安全记录、上线节奏<br><span class="bi">Roadmap, security record, launch pace</span></td></tr>
    <tr><td>竞争格局<br><span class="bi">Competitive landscape</span></td><td>15%</td><td>替代协议、费率与分发<br><span class="bi">Peers, fees and distribution</span></td></tr>
    <tr><td>风险与治理<br><span class="bi">Risk &amp; governance</span></td><td>10%</td><td>预言机、监管、治理集中度<br><span class="bi">Oracles, regulation, governance concentration</span></td></tr>
    <tr><td>增长期权<br><span class="bi">Growth options</span></td><td>10%</td><td>新链、新入口、尚未计价的分发<br><span class="bi">New chains, rails, unpriced distribution</span></td></tr>
  </tbody>
  </table></div>
  {bundle("h2", {"zh": "分数带", "en": "Score bands", "ja": "スコア帯", "ko": "점수대", "fr": "Bandes", "es": "Bandas", "ru": "Полосы"})}
  <ul>
    <li>{spans({"zh": "8.0–10 积极跟踪：质量高，仍要自己做仓位。", "en": "8.0–10 active watch: high quality; you still size the book.", "ja": "8.0–10 積極ウォッチ：質は高いがサイズは自分で。", "ko": "8.0–10 적극 추적: 질은 높고 사이즈는 직접.", "fr": "8.0–10 suivi actif : qualité haute ; le sizing reste à vous.", "es": "8.0–10 seguimiento activo: alta calidad; el sizing es tuyo.", "ru": "8.0–10 активное наблюдение: качество высоко; размер — ваш."})}</li>
    <li>{spans({"zh": "6.5–7.9 谨慎跟踪：值得持续观察，不等于应当加仓。", "en": "6.5–7.9 cautious watch: worth tracking, not a reason to add.", "ja": "6.5–7.9 慎重ウォッチ：追う価値はあるが増加理由ではない。", "ko": "6.5–7.9 신중 추적: 볼 가치는 있고 가산 이유는 아님.", "fr": "6.5–7.9 suivi prudent : à suivre, pas une raison d’ajouter.", "es": "6.5–7.9 seguimiento cauto: merece seguimiento, no es motivo de añadir.", "ru": "6.5–7.9 осторожное наблюдение: стоит вести, не повод докупать."})}</li>
    <li>{spans({"zh": "5.0–6.4 观望：机制未闭合，或估值已经透支反弹。", "en": "5.0–6.4 hold / wait: the mechanism is open, or the bounce is already priced.", "ja": "5.0–6.4 様子見：機構が未完、または反発が織り込み済み。", "ko": "5.0–6.4 관망: 메커니즘이 덜 닫혔거나 반등이 이미 가격에 있음.", "fr": "5.0–6.4 attente : mécanisme ouvert, ou rebond déjà dans le prix.", "es": "5.0–6.4 espera: el mecanismo está abierto, o el rebote ya está en precio.", "ru": "5.0–6.4 выжидание: механизм открыт или отскок уже в цене."})}</li>
    <li>{spans({"zh": "0–4.9 回避：基本面分。不是预测立刻下跌，是研究台不建议把它当基本面持仓。", "en": "0–4.9 avoid: a fundamentals score. Not a crash call. The desk will not book it as a fundamental hold.", "ja": "0–4.9 回避：ファンダ点。暴落予測ではない。ファンダ保有としては扱わない。", "ko": "0–4.9 회피: 펀더멘털 점수. 급락 예측 아님. 펀더멘털 보유로 보지 않음.", "fr": "0–4.9 éviter : score de fondamentaux. Pas un crash. Le desk ne le livre pas comme un hold fondamental.", "es": "0–4.9 evitar: nota de fundamentales. No es un crash. El desk no lo trata como hold fundamental.", "ru": "0–4.9 избегать: фундаментальный балл. Не прогноз обвала. Стол не ведёт это как фундаментальный холд."})}</li>
  </ul>
  {bundle("h2", {"zh": "数据来源", "en": "Sources", "ja": "出典", "ko": "출처", "fr": "Sources", "es": "Fuentes", "ru": "Источники"})}
  <ul>
    <li>CoinGecko — {spans({"zh": "价格、市值、流通量、ATH、成交", "en": "price, cap, supply, ATH, volume", "ja": "価格、時価、供給、ATH、出来高", "ko": "가격, 시총, 공급, ATH, 거래대금", "fr": "prix, cap, offre, ATH, volume", "es": "precio, cap, oferta, ATH, volumen", "ru": "цена, кап, предложение, ATH, оборот"})}</li>
    <li>DefiLlama — TVL, fees, revenue, DEX volume</li>
    <li>{spans({"zh": "协议文档与治理论坛：只引用可复核的公开页", "en": "Protocol docs and governance forums: checkable public pages only", "ja": "プロトコル文書とガバナンス：検証可能な公開ページのみ", "ko": "프로토콜 문서와 거버넌스: 검증 가능한 공개 페이지만", "fr": "Docs protocole et forums : pages publiques vérifiables seulement", "es": "Docs de protocolo y foros: solo páginas públicas comprobables", "ru": "Документы протокола и форумы: только проверяемые публичные страницы"})}</li>
  </ul>
  {bundle("h2", {"zh": "利益冲突", "en": "Conflicts", "ja": "利益相反", "ko": "이해충돌", "fr": "Conflits", "es": "Conflictos", "ru": "Конфликты"})}
  {bundle("p", {"zh": "DRLabs 不接受项目方付费写评。若作者持有所评代币，会在当篇注明。本站目前为研究台默认披露：未就单篇收取发行方费用。", "en": "DRLabs does not take issuer pay-for-coverage. If the author holds the token under review, that note will say so. Default disclosure: no issuer fee on these notes.", "ja": "DRLabsは発行体からの有料カバーを受けない。著者が当該トークンを保有する場合、当該レポートに書く。既定開示：本ノートに発行体手数料なし。", "ko": "DRLabs는 발행사 유료 커버를 받지 않습니다. 저자가 해당 토큰을 보유하면 그 노트에 씁니다. 기본 공시: 이 노트에 발행사 수수료 없음.", "fr": "DRLabs n’accepte pas le pay-for-coverage. Si l’auteur détient le jeton, la note le dit. Divulgation par défaut : pas de frais émetteur sur ces notes.", "es": "DRLabs no acepta cobertura de pago del emisor. Si el autor tiene el token, la nota lo dice. Divulgación por defecto: sin fee de emisor en estas notas.", "ru": "DRLabs не берёт оплату эмитента за покрытие. Если автор держит токен, записка это пишет. Раскрытие по умолчанию: без платы эмитента на этих записках."})}
  {bundle("h2", {"zh": "以后怎么日更", "en": "Daily cadence", "ja": "日次の進め方", "ko": "일간 리듬", "fr": "Cadence quotidienne", "es": "Ritmo diario", "ru": "Дневной ритм"})}
  {bundle("p", {"zh": "每个日历日两篇：优先补齐赛道空白（GameFi 仍在队列），其次跟踪已覆盖标的的数据漂移。新报告用同一 Markdown 块结构写七语，表格只保留中英。", "en": "Two notes each calendar day. First fill coverage gaps (GameFi is still in the queue), then refresh drift on names we already cover. New notes keep the same Markdown block structure across seven languages. Tables stay Chinese + English.", "ja": "各暦日2本。まずカバーの空白（GameFiはキュー）、次に既報のドリフト。新規は同じMarkdown塊で7言語。表は中英。", "ko": "달력일마다 두 편. 먼저 커버 공백(GameFi는 대기), 그다음 기존 종목 드리프트. 새 노트는 같은 마크다운 블록으로 7개 언어. 표는 중·영.", "fr": "Deux notes par jour civil. D’abord les trous de couverture (GameFi encore en file), puis la dérive des noms déjà couverts. Même structure Markdown en 7 langues. Tableaux ZH+EN.", "es": "Dos notas por día civil. Primero huecos de cobertura (GameFi sigue en cola), luego la deriva de nombres ya cubiertos. Misma estructura Markdown en 7 idiomas. Tablas ZH+EN.", "ru": "Две записки в календарный день. Сначала дыры покрытия (GameFi ещё в очереди), затем дрейф уже покрытых имён. Та же структура Markdown на 7 языках. Таблицы ZH+EN."})}
"""

DESK_BODY = f"""
  {bundle("h1", {"zh": "研究台历", "en": "Desk log", "ja": "研究台帳", "ko": "리서치 데스크", "fr": "Journal de bureau", "es": "Registro de mesa", "ru": "Журнал стола"})}
  {bundle("p", {"zh": "公开记录每天写了什么、缺了什么。目标：每个日历日两篇代币研报。", "en": "A public log of what shipped and what slipped. Target: two token notes each calendar day.", "ja": "何を出し、何を欠いたかの公開記録。目標は各暦日2本。", "ko": "무엇을 냈고 무엇을 빠뜨렸는지 공개 기록. 목표: 달력일마다 두 편.", "fr": "Journal public de ce qui est sorti et de ce qui a manqué. Objectif : deux notes par jour civil.", "es": "Registro público de lo publicado y lo que faltó. Objetivo: dos notas por día civil.", "ru": "Открытый журнал того, что вышло и что сорвалось. Цель: две записки в календарный день."}, cls="muted")}
  <div class="card">
    {bundle("h2", {"zh": "2026年9月9日 · 两篇已刊", "en": "9 Sep 2026 · two shipped", "ja": "2026年9月9日 · 2本公開", "ko": "2026년 9월 9일 · 두 편 발행", "fr": "9 sept. 2026 · deux publiées", "es": "9 sep 2026 · dos publicadas", "ru": "9 сен 2026 · две вышли"})}
    <p><span class="chip">DeFi</span> <a href="research/uni/">{spans(UNI_TITLE)}</a> · 6.9</p>
    <p><span class="chip">Meme</span> <a href="research/doge/">{spans(DOGE_TITLE)}</a> · 4.7</p>
    {bundle("p", {"zh": "数据快照 2026-09-08 21:27 UTC。补齐 DEX 龙头与迷因样本，让评分出现 4 分带。", "en": "Snapshot 8 Sep 2026 21:27 UTC. Fills the DEX leader and a meme sample, so the scoreboard can print a 4-handle.", "ja": "スナップショット 2026-09-08 21:27 UTC。DEX盟主とミーム標本を補い、4点台を出せるようにした。", "ko": "스냅샷 2026-09-08 21:27 UTC. DEX 선두와 밈 표본을 채워 4점대가 나오게 함.", "fr": "Snapshot 8 sept. 2026 21:27 UTC. Couvre le leader DEX et un échantillon meme, pour qu’un 4 puisse s’imprimer.", "es": "Snapshot 8 sep 2026 21:27 UTC. Cubre el líder DEX y una muestra meme, para que pueda salir un 4.", "ru": "Снимок 8 сен 2026 21:27 UTC. Закрыли лидера DEX и мем-выборку, чтобы на табло мог выйти 4."}, cls="muted")}
  </div>
  <div class="card">
    {bundle("h2", {"zh": "2026年9月8日 · 一篇已刊", "en": "8 Sep 2026 · one shipped", "ja": "2026年9月8日 · 1本公開", "ko": "2026년 9월 8일 · 한 편 발행", "fr": "8 sept. 2026 · une publiée", "es": "8 sep 2026 · una publicada", "ru": "8 сен 2026 · одна вышла"})}
    <p><span class="chip">L1</span> <a href="research/bnb/">{spans(BNB_TITLE)}</a> · 6.6</p>
    {bundle("p", {"zh": "日更两篇纪律从 9 月 9 日起算。8 日只刊 BNB，记为建台日。", "en": "The two-a-day rule starts 9 Sep. The 8th shipped BNB only and is logged as a setup day.", "ja": "毎日2本の規律は9月9日から。8日はBNBのみで準備日と記録。", "ko": "하루 두 편 규율은 9월 9일부터. 8일은 BNB만 냈고 준비일로 기록.", "fr": "La règle deux-par-jour commence le 9 sept. Le 8 n’a sorti que BNB, jour de mise en place.", "es": "La regla de dos al día empieza el 9 sep. El 8 solo publicó BNB, día de montaje.", "ru": "Правило двух в день с 9 сен. 8-е выпустило только BNB, день настройки."}, cls="muted")}
  </div>
  <div class="card">
    {bundle("h2", {"zh": "2026年9月7日 · 一篇已刊", "en": "7 Sep 2026 · one shipped", "ja": "2026年9月7日 · 1本公開", "ko": "2026년 9월 7일 · 한 편 발행", "fr": "7 sept. 2026 · une publiée", "es": "7 sep 2026 · una publicada", "ru": "7 сен 2026 · одна вышла"})}
    <p><span class="chip">DeFi</span> <a href="research/aave/">{spans(AAVE_TITLE)}</a> · 6.7</p>
  </div>
  {bundle("h2", {"zh": "队列", "en": "Queue", "ja": "キュー", "ko": "대기", "fr": "File", "es": "Cola", "ru": "Очередь"})}
  {bundle("p", {"zh": "下一优先：GameFi（Immutable / Axie 等，用同一框架，预计落在回避或观望）。随后轮换已覆盖标的的数据更新。", "en": "Next priority: GameFi (Immutable / Axie and peers, same frame, likely avoid or hold). Then refresh already-covered names when prints drift.", "ja": "次はGameFi（Immutable / Axieなど、同じ枠、回避か様子見の見込み）。その後は既報の数値ドリフト更新。", "ko": "다음 우선: GameFi(Immutable / Axie 등, 같은 프레임, 회피 또는 관망 가능성). 이후 기존 종목 수치 드리프트 갱신.", "fr": "Priorité suivante : GameFi (Immutable / Axie, même cadre, probablement éviter ou attendre). Puis rafraîchir les noms déjà couverts.", "es": "Siguiente prioridad: GameFi (Immutable / Axie, mismo marco, probablemente evitar o esperar). Luego refrescar nombres ya cubiertos.", "ru": "Дальше: GameFi (Immutable / Axie, та же рамка, скорее избегать или ждать). Затем обновлять уже покрытые имена."})}
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
        (ROOT / "method.html", {"zh": "研究方法 · DRLabs", "en": "Methodology · DRLabs", "ja": "方法 · DRLabs", "ko": "방법 · DRLabs", "fr": "Méthode · DRLabs", "es": "Método · DRLabs", "ru": "Метод · DRLabs"}, "./", METHOD_BODY),
        (ROOT / "desk.html", {"zh": "研究台历 · DRLabs", "en": "Desk log · DRLabs", "ja": "台帳 · DRLabs", "ko": "데스크 · DRLabs", "fr": "Journal · DRLabs", "es": "Registro · DRLabs", "ru": "Журнал · DRLabs"}, "./", DESK_BODY),
        (ROOT / "login.html", {"zh": "登录/注册 · DRLabs", "en": "Log in / Sign up · DRLabs", "ja": "ログイン · DRLabs", "ko": "로그인 · DRLabs", "fr": "Connexion · DRLabs", "es": "Entrar · DRLabs", "ru": "Вход · DRLabs"}, "./", LOGIN_BODY),
    ]
    for path, titles, prefix, body in pages:
        path.write_text(page(titles, prefix, body), encoding="utf-8")

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
<description>Independent crypto research. Two token notes a day.</description>
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

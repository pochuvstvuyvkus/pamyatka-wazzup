"""Builds index.html (site) and pamyatka.docx (for Google Docs) from content.md."""
import html
import re
from pathlib import Path

ROOT = Path(__file__).parent


def parse_sections():
    sections = []
    for chunk in (ROOT / "content.md").read_text(encoding="utf-8").split("=== ")[1:]:
        head, body = chunk.split("\n", 1)
        sid, title = [s.strip() for s in head.split("|", 1)]
        sections.append({"id": sid, "title": title, "body": body.strip()})
    return sections


OL_START = {}


def blocks(md):
    """Split markdown into simple blocks: h1, h2, p, ul, ol, check, table, code, img."""
    lines = md.split("\n")
    i, out = 0, []
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            out.append(("code", "\n".join(lines[i + 1:j])))
            i = j + 1
        elif line.startswith("# "):
            out.append(("h1", line[2:])); i += 1
        elif line.startswith("## "):
            out.append(("h2", line[3:])); i += 1
        elif line.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            out.append(("img", (m.group(1), m.group(2)))); i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append(("table", rows))
        elif line.startswith("- [ ] "):
            items = []
            while i < len(lines) and lines[i].startswith("- [ ] "):
                items.append(lines[i][6:]); i += 1
            out.append(("check", items))
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:]); i += 1
            out.append(("ul", items))
        elif re.match(r"\d+\. ", line):
            start_n = int(re.match(r"(\d+)\. ", line).group(1))
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i])); i += 1
            if start_n != 1:
                OL_START[id(items)] = start_n
            out.append(("ol", items))
        else:
            out.append(("p", line)); i += 1
    return out


ICONS = {
 "start": '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
 "wazzup": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.9A8 8 0 1 1 21 12z"/>',
 "max": '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5v.5"/>',
 "tg": '<path d="M21 4L3 11l6 2 2 6 3-4 5 4z"/><path d="M9 13l7-5"/>',
 "chats": '<path d="M4 5h16v11H8l-4 4z"/><path d="M8 9h8M8 12h5"/>',
 "files": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>',
 "nonumber": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1z"/><path d="M3 3l18 18"/>',
 "spam": '<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>',
 "dupes": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
 "calls": '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6"/>',
 "admin": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
 "howto": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
}


def icon(sid, cls="ico"):
    return f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(sid, ICONS["start"])}</svg>'


PILLS = {"Сам": "self", "Администратор": "admin", "Чат": "chat", "Сам, если оригинал доступен": "self"}


def inline_html(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"«(@[^»]+)»", r"«\1»", t)

    def link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith("#"):
            return f'<a href="{url}">{label}</a>'
        return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'
    return re.sub(r"\[(.+?)\]\((.+?)\)", link, t)


def cell_html(text):
    if text in PILLS:
        return f'<span class="pill {PILLS[text]}">{html.escape(text)}</span>'
    return inline_html(text)


def block_html(kind, val, ctx):
    if kind == "p":
        if re.match(r"\*\*(Пример|Примеры|Частая ошибка)", val):
            m = re.match(r"\*\*(.+?)\*\*\s*(.*)", val)
            return f'<blockquote class="example"><div class="ex-label">{icon("chats","ex-ico")}{inline_html(m.group(1).rstrip("."))}</div><p>{inline_html(m.group(2))}</p></blockquote>'
        if val.startswith("Источник"):
            return f'<p class="src">{inline_html(val)}</p>'
        return f"<p>{inline_html(val)}</p>"
    if kind in ("ul", "ol"):
        items = "".join(f"<li>{inline_html(x)}</li>" for x in val)
        cls = ' class="steps"' if kind == "ol" else ""
        st = OL_START.get(id(val))
        if kind == "ol" and st:
            cls += f' start="{st}" style="counter-reset:s {st - 1}"'
        return f"<{kind}{cls}>{items}</{kind}>"
    if kind == "check":
        items = "".join(f'<li><label><input type="checkbox"><span>{inline_html(x)}</span></label></li>' for x in val)
        return f'<ul class="check">{items}</ul>'
    if kind == "code":
        return f'<div class="tpl"><div class="tpl-head"><span>Шаблон сообщения</span><button class="copy" type="button">Скопировать</button></div><pre>{html.escape(val)}</pre></div>'
    if kind == "img":
        alt, src = val
        return f'<figure><button class="zoom" type="button" data-src="{src}" aria-label="Увеличить"><img src="{src}" alt="{html.escape(alt)}" decoding="async"></button><figcaption>{html.escape(alt)}</figcaption></figure>'
    if kind == "table":
        head = "".join(f"<th>{inline_html(c)}</th>" for c in val[0])
        rows = "".join("<tr>" + "".join(f'<td data-label="{html.escape(val[0][k])}">{cell_html(c)}</td>' for k, c in enumerate(r)) + "</tr>" for r in val[1:])
        return f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    return ""


def h2_kind(title):
    t = title.lower()
    if t.startswith("сделай сам"):
        return "do"
    if t.startswith("пиши в чат") or t.startswith("контакта нет"):
        return "warn"
    if t.startswith("как выглядит"):
        return "look"
    return "plain"


def section_html(sec, sections):
    bl = blocks(sec["body"])
    out, lead, title = [], "", ""
    if bl and bl[0][0] == "h1":
        title = bl[0][1]; bl = bl[1:]
    if bl and bl[0][0] == "p":
        lead = bl[0][1]; bl = bl[1:]
    num = sec["title"].split(".")[0] if sec["id"] != "start" else ""
    out.append(f'<header class="sec-head"><div class="sec-ico">{icon(sec["id"])}</div><div>'
               + (f'<div class="eyebrow">Раздел {num}</div>' if num else '<div class="eyebrow">Памятка менеджера</div>')
               + f'<h1>{inline_html(title)}</h1></div></header>')
    if lead:
        out.append(f'<p class="lead">{inline_html(lead)}</p>')
    if sec["id"] == "start":
        out.append(start_cards(bl, sections))
        return "\n".join(out)
    groups, cur = [], None
    for kind, val in bl:
        if kind == "h2":
            cur = {"title": val, "items": []}; groups.append(cur)
        else:
            if cur is None:
                cur = {"title": None, "items": []}; groups.append(cur)
            cur["items"].append((kind, val))
    for g in groups:
        k = h2_kind(g["title"]) if g["title"] else "plain"
        parts, items, j = [], g["items"], 0
        while j < len(items):
            a, v = items[j]
            if a == "p" and re.fullmatch(r"\*\*(Примеры[^*]*)\*\*", v) and j + 1 < len(items) and items[j + 1][0] == "ul":
                lab = re.fullmatch(r"\*\*(.+?)\*\*", v).group(1).rstrip(".")
                lis = "".join(f"<li>{inline_html(x)}</li>" for x in items[j + 1][1])
                parts.append(f'<blockquote class="example"><div class="ex-label">{icon("chats","ex-ico")}{inline_html(lab)}</div><ul>{lis}</ul></blockquote>')
                j += 2
                continue
            parts.append(block_html(a, v, k)); j += 1
        inner = "\n".join(parts)
        head = ""
        if g["title"]:
            badge = {"do": '<span class="tag self">Сделай сам</span>', "warn": '<span class="tag admin">Когда в чат</span>'}.get(k, "")
            head = f'<h2>{inline_html(g["title"])}{badge}</h2>'
        out.append(f'<div class="block {k}">{head}{inner}</div>')
    return "\n".join(out)


def start_cards(bl, sections):
    titles = {s["id"]: s["title"].split(". ", 1)[-1] for s in sections}
    table = next(v for k, v in bl if k == "table")
    groups = {"self": [], "chat": [], "admin": []}
    for row in table[1:]:
        sit, who, link = row
        sid = re.search(r"\(#(\w+)\)", link).group(1)
        kind = "admin" if who == "Администратор" else "chat" if who == "Чат" else "self"
        note = "" if who in ("Сам", "Чат", "Администратор") else f'<span class="note">{html.escape(who)}</span>'
        groups[kind].append(f'<a class="card {kind}" href="#{sid}"><span class="card-ico">{icon(sid)}</span><span class="card-body"><span class="card-sit">{inline_html(sit)}</span><span class="card-sec">{html.escape(titles[sid])} →</span>{note}</span></a>')
    names = {"self": ("Решаешь сам", "1–2 минуты, без чата"), "chat": ("Нужен коллега", "одно сообщение в чат"), "admin": ("Только администратор", "сразу в чат с отметкой")}
    out = ['<div class="search-hero"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="q2" type="search" placeholder="Что случилось? Например: спам, дубль, тариф, видео" autocomplete="off"></div>']
    for k in ("self", "chat", "admin"):
        if groups[k]:
            out.append(f'<div class="group"><div class="group-head"><span class="dot {k}"></span><b>{names[k][0]}</b><span>{names[k][1]}</span></div><div class="cards">{"".join(groups[k])}</div></div>')
    rest = [(k, v) for k, v in bl if k != "table"]
    gi, cur = [], None
    for kind, val in rest:
        if kind == "h2":
            cur = {"title": val, "items": []}; gi.append(cur)
        elif cur:
            cur["items"].append((kind, val))
    for g in gi:
        out.append(f'<div class="block plain"><h2>{inline_html(g["title"])}</h2>' + "".join(block_html(a, b, "plain") for a, b in g["items"]) + "</div>")
    return "\n".join(out)


def build_site(sections):
    nav = "\n".join(
        f'<a href="{"#" if s["id"] == "start" else "#" + s["id"]}" data-nav="{s["id"]}">{icon(s["id"])}<span>{html.escape(s["title"])}</span></a>' for s in sections)
    body = "\n".join(
        f'<section data-id="{s["id"]}" data-title="{html.escape(s["title"])}">{section_html(s, sections)}</section>' for s in sections)
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    (ROOT / "page.html").write_text(tpl.replace("{{NAV}}", nav).replace("{{BODY}}", body), encoding="utf-8")
    (ROOT / "index.html").write_text(SHELL, encoding="utf-8")


# index.html never changes: it always fetches the latest page.html past the browser cache
SHELL = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow"><title>Памятка менеджера: Wazzup и CRM</title>
<style>body{margin:0;font:16px -apple-system,BlinkMacSystemFont,Arial,sans-serif;background:#f4f6f5;color:#6b7a73;display:grid;place-items:center;height:100vh}</style>
</head><body>Загружаю памятку…
<script>
fetch('page.html?t=' + Date.now(), {cache: 'no-store'}).then(function (r) { return r.text(); }).then(function (h) {
  document.open(); document.write(h); document.close();
}).catch(function () { location.replace('page.html'); });
</script></body></html>
"""


# ---------- DOCX ----------
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor
from PIL import Image

_bm_id = [0]


def add_bookmark(par, name):
    _bm_id[0] += 1
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(_bm_id[0])); start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd"); end.set(qn("w:id"), str(_bm_id[0]))
    par._p.insert(0, start); par._p.append(end)


def add_link(par, text, target, internal):
    link = OxmlElement("w:hyperlink")
    if internal:
        link.set(qn("w:anchor"), target)
    else:
        rid = par.part.relate_to(target, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
        link.set(qn("r:id"), rid)
    r = OxmlElement("w:r"); rpr = OxmlElement("w:rPr")
    col = OxmlElement("w:color"); col.set(qn("w:val"), "1155CC"); rpr.append(col)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rpr.append(u)
    r.append(rpr)
    t = OxmlElement("w:t"); t.text = text; t.set(qn("xml:space"), "preserve"); r.append(t)
    link.append(r); par._p.append(link)


def add_inline(par, text):
    pos = 0
    for m in re.finditer(r"\*\*(.+?)\*\*|\[(.+?)\]\((.+?)\)", text):
        if m.start() > pos:
            par.add_run(text[pos:m.start()])
        if m.group(1):
            par.add_run(m.group(1)).bold = True
        else:
            url = m.group(3)
            add_link(par, m.group(2), "s_" + url[1:] if url.startswith("#") else url, url.startswith("#"))
        pos = m.end()
    if pos < len(text):
        par.add_run(text[pos:])


def build_docx(sections):
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(11)
    sec0 = doc.sections[0]
    sec0.left_margin = sec0.right_margin = Cm(2)
    for n, s in enumerate(sections):
        if n:
            doc.add_page_break()
        for kind, val in blocks(s["body"]):
            if kind == "h1":
                p = doc.add_heading(level=0 if n == 0 else 1)
                p.add_run(val if n == 0 else val)
                add_bookmark(p, "s_" + s["id"])
                if n:
                    back = doc.add_paragraph(); add_link(back, "← К оглавлению", "s_start", True)
            elif kind == "h2":
                doc.add_heading(val, level=2)
            elif kind == "p":
                p = doc.add_paragraph(); add_inline(p, val)
            elif kind == "ol":
                start = OL_START.get(id(val), 1)
                for k, x in enumerate(val):
                    p = doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(0.9)
                    p.paragraph_format.first_line_indent = Cm(-0.6)
                    r = p.add_run(f"{start + k}. "); r.bold = True
                    add_inline(p, x)
            elif kind in ("ul", "check"):
                for x in val:
                    p = doc.add_paragraph(style="List Bullet")
                    if kind == "check":
                        p.add_run("☐ ")
                    add_inline(p, x)
            elif kind == "code":
                p = doc.add_paragraph()
                r = p.add_run(val); r.font.name = "Courier New"; r.font.size = Pt(10)
                shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "F1F3F4")
                p._p.get_or_add_pPr().append(shd)
            elif kind == "img":
                alt, src = val
                w, h = Image.open(ROOT / src).size
                width = Cm(min(16, 16 * w / max(w, 806) if w < 806 else 16))
                if h > w * 1.4:
                    width = Cm(6)
                doc.add_picture(str(ROOT / src), width=width)
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap = doc.add_paragraph(alt); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap.runs[0].italic = True; cap.runs[0].font.size = Pt(9); cap.runs[0].font.color.rgb = RGBColor(0x5F, 0x63, 0x68)
            elif kind == "table":
                t = doc.add_table(rows=len(val), cols=len(val[0])); t.style = "Table Grid"
                for ri, row in enumerate(val):
                    for ci, cell in enumerate(row):
                        c = t.cell(ri, ci); c.text = ""
                        add_inline(c.paragraphs[0], cell)
                        if ri == 0:
                            for r in c.paragraphs[0].runs:
                                r.bold = True
                doc.add_paragraph()
        if n == 0:
            doc.add_heading("Содержание", level=2)
            for s2 in sections[1:]:
                p = doc.add_paragraph(style="List Bullet"); add_link(p, s2["title"], "s_" + s2["id"], True)
    doc.save(ROOT / "Памятка менеджера Wazzup и CRM.docx")


if __name__ == "__main__":
    secs = parse_sections()
    build_site(secs)
    build_docx(secs)
    print("built", len(secs), "sections")

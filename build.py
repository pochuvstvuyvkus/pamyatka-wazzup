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
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i])); i += 1
            out.append(("ol", items))
        else:
            out.append(("p", line)); i += 1
    return out


def inline_html(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)

    def link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith("#"):
            return f'<a href="{url}" data-nav="{url[1:]}">{label}</a>'
        return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'
    return re.sub(r"\[(.+?)\]\((.+?)\)", link, t)


def section_html(sec):
    parts = []
    for kind, val in blocks(sec["body"]):
        if kind == "h1":
            parts.append(f"<h1>{inline_html(val)}</h1>")
        elif kind == "h2":
            parts.append(f"<h2>{inline_html(val)}</h2>")
        elif kind == "p":
            cls = ' class="example"' if val.startswith("**Пример") or val.startswith("**Частая") or val.startswith("**Примеры") else ""
            parts.append(f"<p{cls}>{inline_html(val)}</p>")
        elif kind in ("ul", "ol"):
            items = "".join(f"<li>{inline_html(x)}</li>" for x in val)
            parts.append(f"<{kind}>{items}</{kind}>")
        elif kind == "check":
            items = "".join(f'<li><label><input type="checkbox"> <span>{inline_html(x)}</span></label></li>' for x in val)
            parts.append(f'<ul class="check">{items}</ul>')
        elif kind == "code":
            parts.append(f'<div class="tpl"><pre>{html.escape(val)}</pre><button class="copy" type="button">Скопировать</button></div>')
        elif kind == "img":
            alt, src = val
            parts.append(f'<figure><a href="{src}" target="_blank"><img src="{src}" alt="{html.escape(alt)}" loading="lazy"></a><figcaption>{html.escape(alt)}</figcaption></figure>')
        elif kind == "table":
            head = "".join(f"<th>{inline_html(c)}</th>" for c in val[0])
            rows = "".join("<tr>" + "".join(f'<td data-label="{html.escape(val[0][k])}">{inline_html(c)}</td>' for k, c in enumerate(r)) + "</tr>" for r in val[1:])
            parts.append(f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')
    return "\n".join(parts)


def build_site(sections):
    nav = "\n".join(
        f'<a href="#{s["id"]}" data-nav="{s["id"]}">{html.escape(s["title"])}</a>' for s in sections)
    body = "\n".join(
        f'<section id="{s["id"]}" data-title="{html.escape(s["title"])}">{section_html(s)}</section>' for s in sections)
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    (ROOT / "index.html").write_text(tpl.replace("{{NAV}}", nav).replace("{{BODY}}", body), encoding="utf-8")


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
            elif kind in ("ul", "ol", "check"):
                style = "List Number" if kind == "ol" else "List Bullet"
                for x in val:
                    p = doc.add_paragraph(style=style)
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

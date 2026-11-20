"""
form0.py
Form 0: one fixed page (header, body, footer) for every document.
A form recipe (from the database) only says what changes: title, query,
inputs, info lines, paragraphs, table columns.
build_doc() makes one document dict; generate(doc, fmt) turns it into
HTML (preview), PDF, DOCX, RTF or CSV.
  PDF  = reportlab Platypus (page breaks, repeated table head, page numbers)
  DOCX = python-docx
  RTF  = the DOCX converted by pandoc (no own RTF writer)
"""

import re
import os
import csv
import base64
import tempfile
from html import escape
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

import pypandoc
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (HRFlowable, Image, KeepTogether, Paragraph,
                                SimpleDocTemplate, Spacer, Table)

from db import get_company_logo
from documents import (ACCENT_HEX, DATE_FORMAT, DEFAULT_CURRENCY, DEFAULT_FONT_NAME, GRAY_HEX,
                       LETTER_MARGIN_PT, LOGO_HEIGHT_PT, PDF_FONT, PDF_FONT_BOLD,
                       get_slogan, has_logo, logo_mime, money, register_fonts, today_armenia)

DEFAULT_FOOTER = {"signer": "Authorized signature"}
COLUMN_TYPES = ["text", "date", "money", "number"]
LINE_STYLES = ["rows", "grid", "none"]
TABLE_DEFAULTS = {"header_color": ACCENT_HEX, "header_text_color": "#FFFFFF", "font_size": 9,
                  "zebra": False, "lines": "rows", "row_numbers": False, "totals": []}
FORMATS = ["PDF", "DOCX", "RTF", "CSV"]
MIME = {"PDF": "application/pdf",
        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "RTF": "application/rtf",
        "CSV": "text/csv"}

# ============================================================
# 1. VALUES AND THE DOCUMENT DICT
# ============================================================

class Money(str):
    """An amount already written as text. fill() adds the default currency to it
    unless the template already has one next to it."""

def format_value(value):
    """Format one query value for use in a paragraph."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime(DATE_FORMAT)
    if isinstance(value, (Decimal, float)):
        return Money(money(value))
    return str(value)

def format_cell(value, kind="text"):
    """Format one table cell by column type: text, date, money or number."""
    if value is None:
        return ""
    try:
        if kind == "money":
            return money(value)
        if kind == "number":
            if isinstance(value, Decimal) and value == value.to_integral_value():
                return format(int(value), ",")                  # 3 stays 3, not 3.00
            return format(value, ",") if isinstance(value, int) else money(value)
    except (InvalidOperation, ValueError):
        return str(value)                 # not a number: show it as it is
    return format_value(value)

# A currency written by the template author: code, word or symbol.
CURRENCY = (r"(?:AMD|USD|EUR|RUB|GBP|GEL|CHF|JPY|CNY|AED|KZT|UAH"
            r"|dollars?|euros?|rubles?|drams?|pounds?|lari|դրամ|դր)\b|[֏$€₽]")
CURRENCY_AFTER = re.compile(r"\{\{(\w+)\}\}(\s*(?:\{\{currency\}\}|" + CURRENCY + "))?", re.I)
CURRENCY_BEFORE = re.compile("(?:" + CURRENCY + r")\s*$", re.I)
CURRENCY_ANYWHERE = re.compile(CURRENCY, re.I)

def fill(text, values):
    """Replace {{name}} with values["name"]. Unknown names stay as they are.
    An amount gets the default currency (AMD) unless the author wrote one
    before or after it (AMD, USD, {{currency}}, ...). Writing AMD changes nothing."""
    currency = str(values.get("currency", DEFAULT_CURRENCY))

    def put(m):
        value = values.get(m.group(1))
        if value is None:
            return m.group(0)
        out, rest = str(value), m.group(2)
        if rest:
            return out + rest.replace("{{currency}}", currency)
        if isinstance(value, Money) and not CURRENCY_BEFORE.search(text[:m.start()]):
            return out + " " + currency
        return out
    return CURRENCY_AFTER.sub(put, text)

def unfilled_placeholders(doc):
    """Names of {{placeholders}} still in the document text (nothing filled them)."""
    h = doc["header"]
    texts = [doc["title"], *doc["info_lines"], *doc["paragraphs"], *doc["paragraphs_after"],
             h["company"], h["slogan"], *h["right_lines"], doc["footer"]["signer"]]
    return sorted({name for text in texts for name in re.findall(r"\{\{(\w+)\}\}", text)})

def add_currency(label, currency):
    """'Amount' -> 'Amount (AMD)'. A label that already has a currency stays as it is."""
    if CURRENCY_ANYWHERE.search(label):
        return label
    return label + " (" + currency + ")"

def default_header(company_name):
    """The header every document gets."""
    return {"logo": get_company_logo(company_name) if company_name else b"",
            "company": company_name or "",
            "slogan": get_slogan(company_name) if company_name else "",
            "right_lines": ["Date: {{current_date}}", "Place: Yerevan"]}

HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")

def table_style(form):
    """The table look of a recipe: defaults plus its "table_style". ValueError if something is wrong."""
    style = {**TABLE_DEFAULTS, **(form.get("table_style") or {})}
    for key in ("header_color", "header_text_color"):
        if not HEX_COLOR.fullmatch(str(style[key])):
            raise ValueError("table_style " + key + " must look like #1F4E8C")
    try:
        style["font_size"] = int(style["font_size"])
    except (TypeError, ValueError):
        raise ValueError("table_style font_size must be a number")
    if not 6 <= style["font_size"] <= 14:
        raise ValueError("table_style font_size must be between 6 and 14")
    if style["lines"] not in LINE_STYLES:
        raise ValueError("table_style lines must be one of: " + ", ".join(LINE_STYLES))
    style["totals"] = [str(x) for x in (style["totals"] or [])]
    style["zebra"], style["row_numbers"] = bool(style["zebra"]), bool(style["row_numbers"])
    return style

def total_row(columns, rows, index, fields):
    """Cells of the 'Total' row for the columns named in `fields` (None if there are none)."""
    if not fields:
        return None
    unknown = [x for x in fields if x not in [c["field"] for c in columns]]
    if unknown:
        raise ValueError("Cannot add up column(s) that are not in the table: " + ", ".join(unknown))
    cells = []
    for c in columns:
        if c["field"] not in fields:
            cells.append("")
            continue
        try:
            total = sum((Decimal(str(r[index[c["field"]]])) for r in rows
                         if r[index[c["field"]]] is not None), Decimal(0))
        except InvalidOperation:
            raise ValueError("Cannot add up '" + c["field"] + "': it is not a number")
        whole = c.get("type") == "number" and total == total.to_integral_value()
        cells.append(format(int(total), ",") if whole else money(total))     # counts stay whole numbers
    if "" in cells:
        cells[cells.index("")] = "Total"
    return cells

def build_doc(form, values, col_names, rows, doc_no="DRAFT"):
    """Template + input values + query result -> one document dict.
    Without a table (no columns, or "show_table": false) the first result row becomes {{placeholders}}.
    The recipe may override the header ("header": {...}) and footer ("footer": {...}),
    and set the table look ("table_style": {...})."""
    header = default_header(values.get("company_name", ""))
    header.update(form.get("header", {}))
    style = table_style(form)
    currency = values.get("currency", DEFAULT_CURRENCY)
    shown = form.get("columns", []) if form.get("show_table", True) else []
    columns = [dict(c, label=add_currency(c["label"], currency)) if c.get("type") == "money" else c
               for c in shown]
    index = {name: i for i, name in enumerate(col_names)}
    unknown = [c["field"] for c in columns if c["field"] not in index]
    if unknown:
        raise ValueError("Table column(s) not in the query result: " + ", ".join(unknown)
                         + ". The query returns: " + ", ".join(col_names))
    table = [[format_cell(row[index[c["field"]]], c.get("type", "text")) for c in columns]
             for row in rows] if columns else []
    totals = total_row(columns, rows, index, style["totals"]) if columns else None
    if columns and style["row_numbers"]:
        columns = [{"label": "#", "field": None, "type": "text", "align": "right", "width": 0.4}] + columns
        table = [[str(i + 1)] + cells for i, cells in enumerate(table)]
        totals = [""] + totals if totals else None
    values = dict(values)
    values["count"] = len(table)
    values["current_date"] = today_armenia()
    values["company_name"] = values.get("company_name", "")
    values["slogan"] = get_slogan(values["company_name"]) if values.get("company_name") else ""
    if not columns and rows:
        for name, value in zip(col_names, rows[0]):
            values[name] = format_value(value)
    header["company"] = fill(header["company"], values)
    header["slogan"] = fill(header["slogan"], values)
    header["right_lines"] = [fill(x, values) for x in header["right_lines"]] + ["No: " + doc_no]
    footer = {**DEFAULT_FOOTER, **form.get("footer", {})}
    info = [fill(line, values) for line in form.get("info_lines", [])]
    if values.get("filter_line"):
        info.append(values["filter_line"])
    paragraphs = [fill(p, values) for p in form.get("paragraphs", [])]
    below = []
    if "{{table}}" in paragraphs:
        i = paragraphs.index("{{table}}")
        paragraphs, below = paragraphs[:i], paragraphs[i + 1:]
    return {"header": header, "title": fill(form["title"], values), "info_lines": info,
            "paragraphs": paragraphs, "columns": columns, "table": table, "totals": totals,
            "style": style, "empty_text": form.get("empty_text", "No records."),
            "footer": footer, "paragraphs_after": below}

def shares(columns):
    """Each column's share of the table width (from "width" in the template)."""
    weights = [float(c.get("width", 1)) for c in columns]
    return [w / sum(weights) for w in weights]

# ============================================================
# 2. HTML PREVIEW
# ============================================================

def make_html(doc):
    """The document as an A4-style HTML page (preview only)."""
    h, stl = doc["header"], doc["style"]
    if has_logo(h):
        data = base64.b64encode(h["logo"]).decode()
        mime = logo_mime(h["logo"])
        img = "<img src='data:" + mime + ";base64," + data + "' style='height:" + str(LOGO_HEIGHT_PT) + "pt;'>"
        brand = ("<div style='display:flex;align-items:center;gap:10pt;'>" + img
                 + "<b style='font-size:16pt;'>" + escape(h["company"]) + "</b></div>")
    else:
        brand = "<div style='font-size:20pt;font-weight:bold;color:" + ACCENT_HEX + ";'>" + escape(h["company"]) + "</div>"
    left = "<div>" + brand + "<div style='font-size:10pt;color:" + GRAY_HEX + ";margin-top:6pt;'>" + escape(h["slogan"]) + "</div></div>"
    right = "<div style='text-align:right;font-size:10pt;line-height:14pt;'>" + "<br>".join(escape(x) for x in h["right_lines"]) + "</div>"
    header = "<div style='display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid " + ACCENT_HEX + ";padding-bottom:14pt;'>" + left + right + "</div>"

    info = "<div style='margin:18pt 0 10pt 0;'><div style='font-size:16pt;font-weight:bold;margin-bottom:6pt;'>" + escape(doc["title"]) + "</div>"
    for line in doc["info_lines"]:
        info += "<div style='font-size:10pt;line-height:15pt;'>" + escape(line) + "</div>"
    info += "</div>"

    paragraphs = "".join("<p style='font-size:12pt;margin:0 0 8pt 0;'>" + escape(p) + "</p>"
                         for p in doc["paragraphs"])

    table = ""
    if doc["columns"]:
        size = str(stl["font_size"]) + "pt"
        line = {"rows": "border-bottom:1px solid #ddd;", "grid": "border:1px solid #bbb;", "none": ""}[stl["lines"]]
        table = "<table style='width:100%;border-collapse:collapse;table-layout:fixed;'><tr>"
        for col, share in zip(doc["columns"], shares(doc["columns"])):
            table += ("<th style='background:" + stl["header_color"] + ";color:" + stl["header_text_color"]
                      + ";padding:5pt 6pt;font-size:" + size + ";width:" + str(round(share * 100, 1))
                      + "%;text-align:" + col.get("align", "left") + ";'>" + escape(col["label"]) + "</th>")
        table += "</tr>"
        for i, row in enumerate(doc["table"]):
            table += "<tr style='background:" + ("#F5F7FA" if stl["zebra"] and i % 2 else "transparent") + ";'>"
            for col, cell in zip(doc["columns"], row):
                table += ("<td style='padding:4pt 6pt;font-size:" + size + ";" + line
                          + "word-wrap:break-word;text-align:" + col.get("align", "left") + ";'>" + escape(cell) + "</td>")
            table += "</tr>"
        if doc["totals"]:
            table += "<tr>"
            for col, cell in zip(doc["columns"], doc["totals"]):
                table += ("<td style='padding:4pt 6pt;font-size:" + size + ";font-weight:bold;border-top:2px solid #888;"
                          "text-align:" + col.get("align", "left") + ";'>" + escape(cell) + "</td>")
            table += "</tr>"
        table += "</table>"
        if not doc["table"]:
            table += "<p style='font-size:10pt;color:" + GRAY_HEX + ";'>" + escape(doc["empty_text"]) + "</p>"

    signature = ""
    if doc["footer"]["signer"]:
        signature = ("<div style='align-self:flex-end;width:180pt;border-top:1px solid black;padding-top:4pt;text-align:right;font-size:9pt;color:"
                     + GRAY_HEX + ";margin-top:30pt;'>" + escape(doc["footer"]["signer"]) + "</div>")
    after = "".join("<p style='font-size:12pt;margin:8pt 0 0 0;'>" + escape(p) + "</p>"
                    for p in doc["paragraphs_after"])
    page = ("<div style='background:white;color:black;width:794px;max-width:100%;min-height:1123px;box-sizing:border-box;padding:"
            + str(LETTER_MARGIN_PT) + "px;margin:auto;display:flex;flex-direction:column;box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:"
            + escape(DEFAULT_FONT_NAME) + ",Arial,sans-serif;'>")
    return page + header + info + "<div style='flex:1;'>" + paragraphs + table + after + "</div>" + signature + "</div>"

# ============================================================
# 3. PDF (reportlab Platypus)
# ============================================================

def para(text, size=12, bold=False, color="#000000", align=0, after=8):
    """One text paragraph. align: 0 left, 1 centre, 2 right."""
    style = ParagraphStyle("p", fontName=PDF_FONT_BOLD if bold else PDF_FONT,
                           fontSize=size, leading=size * 1.35, textColor=HexColor(color),
                           alignment=align, spaceAfter=after)
    return Paragraph(escape(str(text)), style)

def pdf_header(h, width):
    """Logo/company name + slogan on the left, date/place/number on the right."""
    if has_logo(h):
        iw, ih = ImageReader(BytesIO(h["logo"])).getSize()
        img = Image(BytesIO(h["logo"]), width=LOGO_HEIGHT_PT * iw / ih, height=LOGO_HEIGHT_PT)
        brand = Table([[img, para(h["company"], 16, True, after=0)]],
                      style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE")], hAlign="LEFT")
    else:
        brand = para(h["company"], 20, True, ACCENT_HEX, after=0)
    left = [brand, Spacer(1, 6), para(h["slogan"], 10, color=GRAY_HEX, after=0)]
    right = [para(line, 10, align=2, after=2) for line in h["right_lines"]]
    return Table([[left, right]], colWidths=[width * 0.65, width * 0.35],
                 style=[("VALIGN", (0, 0), (-1, -1), "TOP")])

def pdf_table(doc, width):
    """Head row (repeats on every page), body rows with wrapping text, optional total row."""
    cols, stl = doc["columns"], doc["style"]
    size = stl["font_size"]
    aligns = [2 if c.get("align") == "right" else 0 for c in cols]
    head = [para(c["label"], size, True, stl["header_text_color"], a, 0) for c, a in zip(cols, aligns)]
    body = [[para(cell, size, align=a, after=0) for cell, a in zip(row, aligns)] for row in doc["table"]]
    total = [[para(cell, size, True, align=a, after=0) for cell, a in zip(doc["totals"], aligns)]] if doc["totals"] else []
    commands = [("BACKGROUND", (0, 0), (-1, 0), HexColor(stl["header_color"])),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if stl["lines"] == "rows":
        commands.append(("LINEBELOW", (0, 1), (-1, -1), 0.5, HexColor("#DDDDDD")))
    elif stl["lines"] == "grid":
        commands.append(("GRID", (0, 0), (-1, -1), 0.5, HexColor("#BBBBBB")))
    if stl["zebra"] and body:
        commands.append(("ROWBACKGROUNDS", (0, 1), (-1, len(body)), [HexColor("#FFFFFF"), HexColor("#F5F7FA")]))
    if total:
        commands.append(("LINEABOVE", (0, -1), (-1, -1), 1.2, HexColor("#888888")))
    return Table([head] + body + total, colWidths=[width * s for s in shares(cols)], repeatRows=1, style=commands)

def page_number(canvas, _doc):
    canvas.setFont(PDF_FONT, 8)
    canvas.setFillColor(HexColor(GRAY_HEX))
    canvas.drawCentredString(A4[0] / 2, 30, "Page " + str(canvas.getPageNumber()))

def make_pdf(doc):
    """The document as an A4 PDF (bytes)."""
    register_fonts()
    m = LETTER_MARGIN_PT
    width = A4[0] - 2 * m
    story = [pdf_header(doc["header"], width),
             HRFlowable(width="100%", thickness=2, color=HexColor(ACCENT_HEX),
                        spaceBefore=10, spaceAfter=18),
             para(doc["title"], 16, True, after=6)]
    story += [para(line, 10, after=3) for line in doc["info_lines"]]
    story += [Spacer(1, 10)] + [para(p) for p in doc["paragraphs"]]
    if doc["columns"]:
        story.append(pdf_table(doc, width))
        if not doc["table"]:
            story.append(para(doc["empty_text"], 10, color=GRAY_HEX))
        story.append(Spacer(1, 16))
    story += [para(p) for p in doc["paragraphs_after"]]
    if doc["footer"]["signer"]:
        story.append(KeepTogether([Spacer(1, 40), para("_" * 28, align=2, after=2),
                                   para(doc["footer"]["signer"], 9, color=GRAY_HEX, align=2)]))
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=m, rightMargin=m,
                      topMargin=m, bottomMargin=m).build(
        story, onFirstPage=page_number, onLaterPages=page_number)
    return buffer.getvalue()

# ============================================================
# 4. DOCX (python-docx) AND RTF (pandoc)
# ============================================================

def add_text(box, text, size=12, bold=False, color=None, right=False):
    """Add one paragraph to the document or to a table cell."""
    p = box.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
    if right:
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    return p

def shade(cell, hex_color):
    """Fill a Word table cell with a color."""
    shading = OxmlElement("w:shd")
    for key, val in (("val", "clear"), ("color", "auto"), ("fill", hex_color.lstrip("#"))):
        shading.set(qn("w:" + key), val)
    cell._tc.get_or_add_tcPr().append(shading)

def line_below(cell):
    """A thin line under a Word table cell (add before shade(): Word wants borders first)."""
    borders = OxmlElement("w:tcBorders")
    bottom = OxmlElement("w:bottom")
    for key, val in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", "DDDDDD")):
        bottom.set(qn("w:" + key), val)
    borders.append(bottom)
    cell._tc.get_or_add_tcPr().append(borders)

def make_docx(doc):
    """The document as a Word file (bytes)."""
    h, stl = doc["header"], doc["style"]
    d = Document()
    section = d.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin = section.right_margin = Pt(LETTER_MARGIN_PT)
    section.top_margin = section.bottom_margin = Pt(LETTER_MARGIN_PT)
    d.styles["Normal"].font.name = DEFAULT_FONT_NAME
    d.styles["Normal"].font.size = Pt(12)

    left, right = d.add_table(rows=1, cols=2).rows[0].cells
    if has_logo(h):
        left.paragraphs[0].add_run().add_picture(BytesIO(h["logo"]), height=Pt(LOGO_HEIGHT_PT))
    add_text(left, h["company"], 16, True, ACCENT_HEX)
    add_text(left, h["slogan"], 10, color=GRAY_HEX)
    for line in h["right_lines"]:
        add_text(right, line, 10, right=True)

    add_text(d, doc["title"], 16, True)
    for line in doc["info_lines"]:
        add_text(d, line, 10)
    for text in doc["paragraphs"]:
        add_text(d, text)

    cols = doc["columns"]
    if cols:
        table = d.add_table(rows=0, cols=len(cols))
        if stl["lines"] == "grid":
            table.style = "Table Grid"
        table.autofit = False
        widths = [Pt((A4[0] - 2 * LETTER_MARGIN_PT) * s) for s in shares(cols)]
        rows_all = [[c["label"] for c in cols]] + doc["table"] + ([doc["totals"]] if doc["totals"] else [])
        for i, row in enumerate(rows_all):
            head, total = i == 0, bool(doc["totals"]) and i == len(rows_all) - 1
            for cell, text, col, w in zip(table.add_row().cells, row, cols, widths):
                cell.width = w
                p = cell.paragraphs[0]
                run = p.add_run(text)
                run.font.size = Pt(stl["font_size"])
                run.bold = head or total
                if col.get("align") == "right":
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                if head:
                    run.font.color.rgb = RGBColor.from_string(stl["header_text_color"].lstrip("#"))
                    shade(cell, stl["header_color"])
                else:
                    if stl["lines"] == "rows":
                        line_below(cell)
                    if stl["zebra"] and not total and i % 2 == 0:
                        shade(cell, "#F5F7FA")
        if not doc["table"]:
            add_text(d, doc["empty_text"], 10, color=GRAY_HEX)
    for text in doc["paragraphs_after"]:
        add_text(d, text)

    if doc["footer"]["signer"]:
        add_text(d, "_" * 28, right=True).paragraph_format.space_before = Pt(40)
        add_text(d, doc["footer"]["signer"], 9, color=GRAY_HEX, right=True)
    buffer = BytesIO()
    d.save(buffer)
    return buffer.getvalue()

def make_rtf(doc):
    """The document as RTF (bytes): the DOCX converted by pandoc."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doc.docx")
        with open(path, "wb") as f:
            f.write(make_docx(doc))
        text = pypandoc.convert_file(path, "rtf", format="docx", extra_args=["--standalone"])
    return text.encode("utf-8")

# ============================================================
# 5. CSV AND generate
# ============================================================

def make_csv(doc):
    """The table as CSV (bytes). utf-8-sig so Excel shows Armenian correctly."""
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow([c["label"] for c in doc["columns"]])
    writer.writerows(doc["table"])
    return out.getvalue().encode("utf-8-sig")

MAKERS = {"HTML": make_html, "PDF": make_pdf, "DOCX": make_docx,
          "RTF": make_rtf, "CSV": make_csv}

def generate(doc, fmt):
    """Make the document: "HTML" (str) or "PDF", "DOCX", "RTF", "CSV" (bytes)."""
    if fmt not in MAKERS:
        raise ValueError("Unknown format: " + str(fmt))
    return MAKERS[fmt](doc)

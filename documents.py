"""
documents.py
Builds customer documents: fills template blocks with values, writes
RTF/PDF files, and converts between RTF and PDF (files made by this app).
Used by app.py and scripts/verify.py.
"""

# ============================================================
# 1. IMPORTS
# ============================================================

import re
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import base64
import os
from html import escape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader, simpleSplit

# ============================================================
# 2. CONSTANTS
# ============================================================
TIMEZONE = "Asia/Yerevan"
DATE_FORMAT = "%d/%m/%Y"

PDF_FONT = "DejaVuSans"
PDF_FONT_BOLD = "DejaVuSans-Bold"
PDF_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PDF_FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

DEFAULT_FONT_NAME = "DejaVu Sans"
DEFAULT_MARGIN_PT = 72
DEFAULT_SIZE_PT = 12

LETTER_MARGIN_PT = 56
LOGO_HEIGHT_PT = 50
ACCENT_HEX = "#1F4E8C"
GRAY_HEX = "#666666"
DEFAULT_SLOGAN = "We are strong together"
SLOGANS = {"Ardshin": "We are strong together",
           "Ameria": "Bank about people",
           "Adidas": "Impossible is nothing",
           "Puma": "Forever Faster"}

RTF_ALIGN_CODES = {"left": "\\ql", "center": "\\qc", "right": "\\qr"}
RTF_ALIGN_NAMES = {"ql": "left", "qc": "center", "qr": "right"}

# Pieces of an RTF file: unicode char, control word, escaped char, brace, plain text
RTF_TOKEN = re.compile(r"\\u(-?\d+)\??|\\([a-z]+)(-?\d+)? ?|\\([\\{}])|[{}]|([^\\{}]+)")

# ============================================================
# 3. VALUES AND TEMPLATE FILLING
# ============================================================

def today_armenia():
    """Return today's date in Yerevan time as dd/mm/yyyy."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.strftime(DATE_FORMAT)

def build_values(first_name, surname, company_name=""):
    """Return the values that fill the {{placeholders}} in a template."""
    return {"first_name": first_name,
            "surname": surname,
            "company_name": company_name,
            "current_date": today_armenia()}

def fill_text(text, values):
    """Replace every {{key}} in one line of text with its value."""
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text

def fill_blocks(template, values):
    """Return a copy of the template blocks with all placeholders filled."""
    filled = []
    for block in template["blocks"]:
        new_block = dict(block)
        new_block["text"] = fill_text(block["text"], values)
        filled.append(new_block)
    return filled

# ============================================================
# 4. RTF WRITER
# ============================================================

def rtf_escape(text):
    """Escape special characters and non-ASCII letters for RTF."""
    result = ""
    for ch in str(text):
        if ch in "\\{}":
            result += "\\" + ch
        elif ord(ch) > 127:
            code = ord(ch)
            if code > 32767:
                code = code - 65536
            result += "\\u" + str(code) + "?"
        else:
            result = result + ch
    return result

def rtf_paragraph(block):
    """Turn one block into one RTF paragraph."""
    result = "\\pard" + RTF_ALIGN_CODES.get(block["align"], "\\ql")
    result += "\\sa" + str(block["space_after"] * 20)
    result += "\\fs" + str(block["size"] * 2) + " "
    if block["bold"]:
        result += "\\b " + rtf_escape(block["text"]) + "\\b0"
    else:
        result += rtf_escape(block["text"])
    result += "\\par"
    return result

def make_rtf(template, blocks):
    """Build a whole RTF document and return it as bytes."""
    margin = str(template["page"]["margin_pt"] * 20)
    rtf = "{\\rtf1\\ansi\\deff0"
    rtf += "{\\fonttbl{\\f0 " + rtf_escape(template["font"]) + ";}}\\f0"
    rtf += "\\paperw11906\\paperh16838"
    rtf += "\\margl" + margin + "\\margr" + margin + "\\margt" + margin + "\\margb" + margin
    for block in blocks:
        rtf += rtf_paragraph(block)
    rtf += "}"
    return rtf.encode("ascii")

# ============================================================
# 5. PDF WRITER
# ============================================================

def register_fonts():
    """Register the DejaVu fonts with reportlab (once)."""
    if PDF_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(PDF_FONT, PDF_FONT_PATH))
        pdfmetrics.registerFont(TTFont(PDF_FONT_BOLD, PDF_FONT_BOLD_PATH))

def make_pdf(template, blocks):
    """Build a whole PDF document and return it as bytes."""
    register_fonts()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = template["page"]["margin_pt"]
    y = height - margin
    for block in blocks:
        size = block["size"]
        if block["bold"]:
            font = PDF_FONT_BOLD
        else:
            font = PDF_FONT
        y = y - size
        if y < margin:
            pdf.showPage()
            y = height - margin - size
        pdf.setFont(font, size)
        if block["align"] == "center":
            pdf.drawCentredString(width / 2, y, block["text"])
        elif block["align"] == "right":
            pdf.drawRightString(width - margin, y, block["text"])
        else:
            pdf.drawString(margin, y, block["text"])
        y = y - block["space_after"]
    pdf.save()
    return buffer.getvalue()

# ============================================================
# 6. RTF READER  (RTF bytes --> template, blocks)
# ============================================================

def rtf_to_blocks(data):
    """Read an RTF made by this app back into (template, blocks)."""
    rtf = data.decode("latin-1")
    start = rtf.find("\\pard")
    if start == -1:
        raise ValueError("No text found. Only RTF files made by this app can be converted.")
    font = re.search(r"\{\\f0 ([^;]*);\}", rtf)
    margin = re.search(r"\\margl(\d+)", rtf)
    template = {"font": font.group(1) if font else DEFAULT_FONT_NAME,
                "page": {"margin_pt": int(margin.group(1)) // 20 if margin else DEFAULT_MARGIN_PT}}
    blocks = []
    align, space, size, bold = "left", 0, DEFAULT_SIZE_PT, False
    text, block_bold = "", False
    for m in RTF_TOKEN.finditer(rtf[start:]):
        unicode_code, word, number, escaped, plain = m.groups()
        if unicode_code is not None:
            code = int(unicode_code)
            if code < 0:
                code += 65536
            text += chr(code)
            block_bold = block_bold or bold
        elif escaped is not None:
            text += escaped
            block_bold = block_bold or bold
        elif plain is not None:
            text += plain
            block_bold = block_bold or bold
        elif word:
            if word == "pard":
                align, space = "left", 0
            elif word in RTF_ALIGN_NAMES:
                align = RTF_ALIGN_NAMES[word]
            elif word == "sa" and number:
                space = int(number) // 20
            elif word == "fs" and number:
                size = int(number) // 2
            elif word == "b":
                bold = number != "0"
            elif word == "par":
                blocks.append({"text": text, "align": align, "size": size,
                               "bold": block_bold, "space_after": space})
                text, block_bold = "", False
    if not blocks:
        raise ValueError("No text found in this RTF.")
    return template, blocks

# ============================================================
# 7. PDF READER  (PDF bytes --> template, blocks), LETTER LAYOUT  (logo + slogan, date, thank-you text, signature)
# ============================================================

def pdf_to_blocks(data):
    """Read a PDF made by this app back into (template, blocks)."""
    lines = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_lines = page.extract_text_lines()
            for i, line in enumerate(page_lines):
                first = next((c for c in line["chars"] if c["text"].strip()), None)
                if first is None:
                    continue
                lines.append({"text": line["text"].strip(),
                              "x0": line["x0"], "x1": line["x1"],
                              "baseline": first["matrix"][5],
                              "size": round(first["size"]),
                              "bold": "bold" in first["fontname"].lower(),
                              "width": page.width,
                              "last_on_page": i == len(page_lines) - 1})
    if not lines:
        raise ValueError("No text found in this PDF.")
    margin = round(min(l["x0"] for l in lines))
    template = {"font": DEFAULT_FONT_NAME, "page": {"margin_pt": margin}}
    blocks = []
    for i, l in enumerate(lines):
        centre = (l["x0"] + l["x1"]) / 2
        if abs(centre - l["width"] / 2) < 3:
            align = "center"
        elif abs(l["x1"] - (l["width"] - margin)) < 3:
            align = "right"
        else:
            align = "left"
        space = 0
        if not l["last_on_page"] and i + 1 < len(lines):
            nxt = lines[i + 1]
            space = max(0, round(l["baseline"] - nxt["baseline"] - nxt["size"]))
        blocks.append({"text": l["text"], "align": align, "size": l["size"],
                       "bold": l["bold"], "space_after": space})
    return template, blocks

def build_letter(first_name, surname, company_name, logo_path):
    """Return everything the letter shows. Change the texts here."""
    who = company_name or "us"
    return {"logo": logo_path,
            "company": company_name,
            "slogan": get_slogan(company_name),
            "right_lines": ["Date: " + today_armenia(), "Place: Yerevan"],
            "title": "Thank you, " + first_name + " " + surname,
            "paragraphs": ["Thank you for working with " + who + ".",
                           "We value your trust and look forward to our continued cooperation."],
            "signer": "Authorized signature"}

def has_logo(letter):
    """True if the letter has a logo file that exists."""
    return bool(letter["logo"]) and os.path.exists(letter["logo"])

def make_letter_html(letter):
    """Return the letter as an A4-style HTML page for the preview."""
    if has_logo(letter):
        with open(letter["logo"], "rb") as f:
            data = base64.b64encode(f.read()).decode()
        if letter["logo"].lower().endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        else:
            mime = "image/png"
        brand = "<img src='data:" + mime + ";base64," + data + "' style='height:" + str(LOGO_HEIGHT_PT) + "pt;'>"
    else:
        brand = "<div style='font-size:20pt;font-weight:bold;color:" + ACCENT_HEX + ";'>" + escape(letter["company"]) + "</div>"
    left = "<div>" + brand + "<div style='font-size:10pt;color:" + GRAY_HEX + ";margin-top:6pt;'>" + escape(letter["slogan"]) + "</div></div>"
    right = "<div style='text-align:right;font-size:10pt;line-height:14pt;'>" + "<br>".join(escape(line) for line in letter["right_lines"]) + "</div>"
    header = "<div style='display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid " + ACCENT_HEX + ";padding-bottom:14pt;'>" + left + right + "</div>"
    body = "<div style='flex:1;display:flex;flex-direction:column;justify-content:center;'>"
    body += "<div style='font-size:18pt;font-weight:bold;margin-bottom:10pt;'>" + escape(letter["title"]) + "</div>"
    for paragraph in letter["paragraphs"]:
        body += "<p style='font-size:12pt;margin:0 0 8pt 0;'>" + escape(paragraph) + "</p>"
    body += "</div>"
    signature = "<div style='align-self:flex-end;width:180pt;border-top:1px solid black;padding-top:4pt;text-align:right;font-size:9pt;color:" + GRAY_HEX + ";'>" + escape(letter["signer"]) + "</div>"
    page = "<div style='background:white;color:black;width:794px;max-width:100%;min-height:1123px;box-sizing:border-box;padding:" + str(LETTER_MARGIN_PT) + "px;margin:auto;display:flex;flex-direction:column;box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:" + escape(DEFAULT_FONT_NAME) + ",Arial,sans-serif;'>"
    return page + header + body + signature + "</div>"

def make_letter_pdf(letter):
    """Build the letter as an A4 PDF and return it as bytes."""
    register_fonts()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    m = LETTER_MARGIN_PT
    top = height - m

    # top left: logo (or company name) and slogan
    if has_logo(letter):
        img = ImageReader(letter["logo"])
        iw, ih = img.getSize()
        pdf.drawImage(img, m, top - LOGO_HEIGHT_PT, LOGO_HEIGHT_PT * iw / ih,
                      LOGO_HEIGHT_PT, mask="auto")
    else:
        pdf.setFillColor(HexColor(ACCENT_HEX))
        pdf.setFont(PDF_FONT_BOLD, 20)
        pdf.drawString(m, top - 30, letter["company"])
    pdf.setFillColor(HexColor(GRAY_HEX))
    pdf.setFont(PDF_FONT, 10)
    pdf.drawString(m, top - LOGO_HEIGHT_PT - 16, letter["slogan"])

    # top right: date and place
    pdf.setFillColor(HexColor("#000000"))
    pdf.setFont(PDF_FONT, 10)
    y = top - 10
    for line in letter["right_lines"]:
        pdf.drawRightString(width - m, y, line)
        y = y - 14

    # colored line under the header
    rule_y = top - LOGO_HEIGHT_PT - 30
    pdf.setStrokeColor(HexColor(ACCENT_HEX))
    pdf.setLineWidth(2)
    pdf.line(m, rule_y, width - m, rule_y)

    # middle: title and text
    text_width = width - 2 * m
    y = height / 2 + 60
    pdf.setFont(PDF_FONT_BOLD, 18)
    for line in simpleSplit(letter["title"], PDF_FONT_BOLD, 18, text_width):
        pdf.drawString(m, y, line)
        y = y - 24
    y = y - 8
    pdf.setFont(PDF_FONT, 12)
    for paragraph in letter["paragraphs"]:
        for line in simpleSplit(paragraph, PDF_FONT, 12, text_width):
            pdf.drawString(m, y, line)
            y = y - 18
        y = y - 8

    # bottom right: signature line
    sig_y = m + 40
    pdf.setStrokeColor(HexColor("#000000"))
    pdf.setLineWidth(1)
    pdf.line(width - m - 180, sig_y, width - m, sig_y)
    pdf.setFillColor(HexColor(GRAY_HEX))
    pdf.setFont(PDF_FONT, 9)
    pdf.drawRightString(width - m, sig_y - 12, letter["signer"])
    pdf.save()
    return buffer.getvalue()

def rtf_logo(path):
    """Return the logo as an RTF picture."""
    img = ImageReader(path)
    iw, ih = img.getSize()
    with open(path, "rb") as f:
        data = f.read()
    if path.lower().endswith((".jpg", ".jpeg")):
        kind = "\\jpegblip"
    else:
        kind = "\\pngblip"
    goal_h = LOGO_HEIGHT_PT * 20
    goal_w = int(goal_h * iw / ih)
    return ("{\\pict" + kind + "\\picw" + str(iw) + "\\pich" + str(ih)
            + "\\picwgoal" + str(goal_w) + "\\pichgoal" + str(goal_h)
            + " " + data.hex() + "}")

def make_letter_rtf(letter):
    """Build the letter as an RTF file and return it as bytes."""
    margin = LETTER_MARGIN_PT * 20
    full = 11906 - 2 * margin
    half = full // 2
    rtf = "{\\rtf1\\ansi\\deff0"
    rtf += "{\\fonttbl{\\f0 " + DEFAULT_FONT_NAME + ";}}"
    rtf += "{\\colortbl;\\red31\\green78\\blue140;\\red102\\green102\\blue102;}\\f0"
    rtf += "\\paperw11906\\paperh16838"
    rtf += "\\margl" + str(margin) + "\\margr" + str(margin) + "\\margt" + str(margin) + "\\margb" + str(margin)

    # header table: left cell logo + slogan, right cell date and place
    if has_logo(letter):
        brand = rtf_logo(letter["logo"])
    else:
        brand = "\\cf1\\b\\fs40 " + rtf_escape(letter["company"]) + "\\b0\\cf0"
    left = brand + "\\line\\cf2\\fs20 " + rtf_escape(letter["slogan"]) + "\\cf0\\fs24"
    right = "\\line ".join(rtf_escape(line) for line in letter["right_lines"])
    rtf += "\\trowd\\trgaph0\\cellx" + str(half) + "\\cellx" + str(full)
    rtf += "\\pard\\intbl " + left + "\\cell"
    rtf += "\\pard\\intbl\\qr\\fs20 " + right + "\\cell\\row"

    # colored line
    rtf += "\\pard\\sb100\\brdrb\\brdrs\\brdrw20\\brdrcf1\\par"

    # middle: title and text
    rtf += "\\pard\\sb3600\\sa300\\fs36\\b " + rtf_escape(letter["title"]) + "\\b0\\par"
    for paragraph in letter["paragraphs"]:
        rtf += "\\pard\\sa200\\fs24 " + rtf_escape(paragraph) + "\\par"

    # bottom right: signature (RTF can't pin to the page bottom, so spacing is approximate)
    rtf += "\\pard\\qr\\sb3600\\fs24 ____________________\\par"
    rtf += "\\pard\\qr\\cf2\\fs18 " + rtf_escape(letter["signer"]) + "\\cf0\\par"
    rtf += "}"
    return rtf.encode("ascii")

# ============================================================
# 8. CONVERTERS
# ============================================================

def rtf_to_pdf(data):
    """Convert RTF bytes to PDF bytes."""
    template, blocks = rtf_to_blocks(data)
    return make_pdf(template, blocks)

def pdf_to_rtf(data):
    """Convert PDF bytes to RTF bytes."""
    template, blocks = pdf_to_blocks(data)
    return make_rtf(template, blocks)
    
# ============================================================
# 9. TRANSACTION STATEMENT  (letterhead + table, no running balance)
# ============================================================

STMT_DATE_X = 6
STMT_TYPE_X = 76
STMT_AMOUNT_RIGHT = 250
STMT_DESC_X = 262
STMT_ROW_PT = 20

def format_date(value):
    """Return a date as dd/mm/yyyy."""
    if hasattr(value, "strftime"):
        return value.strftime(DATE_FORMAT)
    return str(value)

def build_statement(first_name, surname, customer_id, company_name, logo_path,
                    date_from, date_to, rows):
    """Return everything the statement shows. Change the texts here."""
    table = []
    for tx_date, tx_type, amount, description in rows:
        table.append([format_date(tx_date), str(tx_type),
                      format(float(amount), ",.2f"), str(description or "")])
    return {"logo": logo_path,
            "company": company_name,
            "slogan": get_slogan(company_name),
            "right_lines": ["Date: " + today_armenia(), "Place: Yerevan"],
            "title": "Transaction statement",
            "info_lines": ["Customer: " + first_name + " " + surname + " (ID " + str(customer_id) + ")",
                           "Period: " + format_date(date_from) + " - " + format_date(date_to),
                           "Transactions: " + str(len(table))],
            "table": table,
            "signer": "Authorized signature"}

def fit_text(text, font, size, max_width):
    """Cut text with ... so it fits into max_width."""
    if pdfmetrics.stringWidth(text, font, size) <= max_width:
        return text
    while text and pdfmetrics.stringWidth(text + "...", font, size) > max_width:
        text = text[:-1]
    return text + "..."

# ---------- preview (HTML) ----------

def make_statement_html(doc):
    """Return the statement as an A4-style HTML page for the preview."""
    if has_logo(doc):
        with open(doc["logo"], "rb") as f:
            data = base64.b64encode(f.read()).decode()
        if doc["logo"].lower().endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        else:
            mime = "image/png"
        brand = "<img src='data:" + mime + ";base64," + data + "' style='height:" + str(LOGO_HEIGHT_PT) + "pt;'>"
    else:
        brand = "<div style='font-size:20pt;font-weight:bold;color:" + ACCENT_HEX + ";'>" + escape(doc["company"]) + "</div>"
    left = "<div>" + brand + "<div style='font-size:10pt;color:" + GRAY_HEX + ";margin-top:6pt;'>" + escape(doc["slogan"]) + "</div></div>"
    right = "<div style='text-align:right;font-size:10pt;line-height:14pt;'>" + "<br>".join(escape(line) for line in doc["right_lines"]) + "</div>"
    header = "<div style='display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid " + ACCENT_HEX + ";padding-bottom:14pt;'>" + left + right + "</div>"

    info = "<div style='margin:18pt 0 10pt 0;'>"
    info += "<div style='font-size:16pt;font-weight:bold;margin-bottom:6pt;'>" + escape(doc["title"]) + "</div>"
    for line in doc["info_lines"]:
        info += "<div style='font-size:10pt;line-height:15pt;'>" + escape(line) + "</div>"
    info += "</div>"

    th = "style='background:" + ACCENT_HEX + ";color:white;padding:5pt 6pt;font-size:9pt;text-align:"
    table = "<table style='width:100%;border-collapse:collapse;'><tr>"
    table += "<th " + th + "left;'>Date</th><th " + th + "left;'>Type</th>"
    table += "<th " + th + "right;'>Amount</th><th " + th + "left;'>Description</th></tr>"
    td = "style='padding:4pt 6pt;font-size:9pt;border-bottom:1px solid #ddd;text-align:"
    for date_text, tx_type, amount, description in doc["table"]:
        table += "<tr><td " + td + "left;'>" + escape(date_text) + "</td>"
        table += "<td " + td + "left;'>" + escape(tx_type) + "</td>"
        table += "<td " + td + "right;'>" + escape(amount) + "</td>"
        table += "<td " + td + "left;'>" + escape(description) + "</td></tr>"
    table += "</table>"
    if not doc["table"]:
        table += "<p style='font-size:10pt;color:" + GRAY_HEX + ";'>No transactions in this period.</p>"

    signature = "<div style='align-self:flex-end;width:180pt;border-top:1px solid black;padding-top:4pt;text-align:right;font-size:9pt;color:" + GRAY_HEX + ";margin-top:30pt;'>" + escape(doc["signer"]) + "</div>"
    page = "<div style='background:white;color:black;width:794px;max-width:100%;min-height:1123px;box-sizing:border-box;padding:" + str(LETTER_MARGIN_PT) + "px;margin:auto;display:flex;flex-direction:column;box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:" + escape(DEFAULT_FONT_NAME) + ",Arial,sans-serif;'>"
    return page + header + info + "<div style='flex:1;'>" + table + "</div>" + signature + "</div>"

# ---------- PDF ----------

def draw_statement_header(pdf, doc):
    """Draw logo, slogan, date and the colored line. Return the y of the line."""
    width, height = A4
    m = LETTER_MARGIN_PT
    top = height - m
    if has_logo(doc):
        img = ImageReader(doc["logo"])
        iw, ih = img.getSize()
        pdf.drawImage(img, m, top - LOGO_HEIGHT_PT, LOGO_HEIGHT_PT * iw / ih,
                      LOGO_HEIGHT_PT, mask="auto")
    else:
        pdf.setFillColor(HexColor(ACCENT_HEX))
        pdf.setFont(PDF_FONT_BOLD, 20)
        pdf.drawString(m, top - 30, doc["company"])
    pdf.setFillColor(HexColor(GRAY_HEX))
    pdf.setFont(PDF_FONT, 10)
    pdf.drawString(m, top - LOGO_HEIGHT_PT - 16, doc["slogan"])
    pdf.setFillColor(HexColor("#000000"))
    y = top - 10
    for line in doc["right_lines"]:
        pdf.drawRightString(width - m, y, line)
        y = y - 14
    rule_y = top - LOGO_HEIGHT_PT - 30
    pdf.setStrokeColor(HexColor(ACCENT_HEX))
    pdf.setLineWidth(2)
    pdf.line(m, rule_y, width - m, rule_y)
    return rule_y

def draw_statement_head(pdf, y):
    """Draw the colored table head row at y. Return the y below it."""
    width, height = A4
    m = LETTER_MARGIN_PT
    pdf.setFillColor(HexColor(ACCENT_HEX))
    pdf.rect(m, y - STMT_ROW_PT, width - 2 * m, STMT_ROW_PT, stroke=0, fill=1)
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont(PDF_FONT_BOLD, 9)
    base = y - 13
    pdf.drawString(m + STMT_DATE_X, base, "Date")
    pdf.drawString(m + STMT_TYPE_X, base, "Type")
    pdf.drawRightString(m + STMT_AMOUNT_RIGHT, base, "Amount")
    pdf.drawString(m + STMT_DESC_X, base, "Description")
    return y - STMT_ROW_PT

def make_statement_pdf(doc):
    """Build the statement as an A4 PDF and return it as bytes."""
    register_fonts()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    m = LETTER_MARGIN_PT
    desc_width = width - 2 * m - STMT_DESC_X - 6

    y = draw_statement_header(pdf, doc) - 30
    pdf.setFillColor(HexColor("#000000"))
    pdf.setFont(PDF_FONT_BOLD, 16)
    pdf.drawString(m, y, doc["title"])
    y = y - 22
    pdf.setFont(PDF_FONT, 10)
    for line in doc["info_lines"]:
        pdf.drawString(m, y, line)
        y = y - 15
    y = y - 10

    y = draw_statement_head(pdf, y)
    pdf.setFont(PDF_FONT, 9)
    for date_text, tx_type, amount, description in doc["table"]:
        if y < m + 70:
            pdf.showPage()
            y = draw_statement_head(pdf, height - m)
        pdf.setFillColor(HexColor("#000000"))
        pdf.setFont(PDF_FONT, 9)
        base = y - 13
        pdf.drawString(m + STMT_DATE_X, base, date_text)
        pdf.drawString(m + STMT_TYPE_X, base, fit_text(tx_type, PDF_FONT, 9, 70))
        pdf.drawRightString(m + STMT_AMOUNT_RIGHT, base, amount)
        pdf.drawString(m + STMT_DESC_X, base, fit_text(description, PDF_FONT, 9, desc_width))
        pdf.setStrokeColor(HexColor("#DDDDDD"))
        pdf.setLineWidth(0.5)
        pdf.line(m, y - STMT_ROW_PT, width - m, y - STMT_ROW_PT)
        y = y - STMT_ROW_PT
    if not doc["table"]:
        pdf.setFillColor(HexColor(GRAY_HEX))
        pdf.drawString(m + STMT_DATE_X, y - 16, "No transactions in this period.")

    sig_y = m + 40
    pdf.setStrokeColor(HexColor("#000000"))
    pdf.setLineWidth(1)
    pdf.line(width - m - 180, sig_y, width - m, sig_y)
    pdf.setFillColor(HexColor(GRAY_HEX))
    pdf.setFont(PDF_FONT, 9)
    pdf.drawRightString(width - m, sig_y - 12, doc["signer"])
    pdf.save()
    return buffer.getvalue()

# ---------- RTF ----------

def make_statement_rtf(doc):
    """Build the statement as an RTF file and return it as bytes."""
    margin = LETTER_MARGIN_PT * 20
    full = 11906 - 2 * margin
    half = full // 2
    rtf = "{\\rtf1\\ansi\\deff0"
    rtf += "{\\fonttbl{\\f0 " + DEFAULT_FONT_NAME + ";}}"
    rtf += "{\\colortbl;\\red31\\green78\\blue140;\\red102\\green102\\blue102;\\red255\\green255\\blue255;}\\f0"
    rtf += "\\paperw11906\\paperh16838"
    rtf += "\\margl" + str(margin) + "\\margr" + str(margin) + "\\margt" + str(margin) + "\\margb" + str(margin)

    # header: logo + slogan left, date and place right
    if has_logo(doc):
        brand = rtf_logo(doc["logo"])
    else:
        brand = "\\cf1\\b\\fs40 " + rtf_escape(doc["company"]) + "\\b0\\cf0"
    left = brand + "\\line\\cf2\\fs20 " + rtf_escape(doc["slogan"]) + "\\cf0\\fs24"
    right = "\\line ".join(rtf_escape(line) for line in doc["right_lines"])
    rtf += "\\trowd\\trgaph0\\cellx" + str(half) + "\\cellx" + str(full)
    rtf += "\\pard\\intbl " + left + "\\cell"
    rtf += "\\pard\\intbl\\qr\\fs20 " + right + "\\cell\\row"
    rtf += "\\pard\\sb100\\brdrb\\brdrs\\brdrw20\\brdrcf1\\par"

    # title and info
    rtf += "\\pard\\sb300\\sa120\\fs32\\b " + rtf_escape(doc["title"]) + "\\b0\\par"
    for line in doc["info_lines"]:
        rtf += "\\pard\\sa40\\fs20 " + rtf_escape(line) + "\\par"
    rtf += "\\pard\\sa120\\par"

    # table
    c1 = 1300
    c2 = c1 + 1500
    c3 = c2 + 1700
    c4 = full
    edges = [c1, c2, c3, c4]
    head = "\\trowd\\trgaph80"
    for edge in edges:
        head += "\\clcbpat1\\cellx" + str(edge)
    rtf += head
    rtf += "\\pard\\intbl\\cf3\\b\\fs18 Date\\cell"
    rtf += "\\pard\\intbl\\cf3\\b\\fs18 Type\\cell"
    rtf += "\\pard\\intbl\\qr\\cf3\\b\\fs18 Amount\\cell"
    rtf += "\\pard\\intbl\\cf3\\b\\fs18 Description\\cell\\row"
    for date_text, tx_type, amount, description in doc["table"]:
        row = "\\trowd\\trgaph80"
        for edge in edges:
            row += "\\clbrdrb\\brdrs\\brdrw5\\cellx" + str(edge)
        row += "\\pard\\intbl\\cf0\\b0\\fs18 " + rtf_escape(date_text) + "\\cell"
        row += "\\pard\\intbl\\fs18 " + rtf_escape(tx_type) + "\\cell"
        row += "\\pard\\intbl\\qr\\fs18 " + rtf_escape(amount) + "\\cell"
        row += "\\pard\\intbl\\fs18 " + rtf_escape(description) + "\\cell\\row"
        rtf += row
    if not doc["table"]:
        rtf += "\\pard\\sb200\\cf2\\fs20 No transactions in this period.\\cf0\\par"

    # signature
    rtf += "\\pard\\qr\\sb1200\\cf0\\b0\\fs24 ____________________\\par"
    rtf += "\\pard\\qr\\cf2\\fs18 " + rtf_escape(doc["signer"]) + "\\cf0\\par"
    rtf += "}"
    return rtf.encode("ascii")

def get_slogan(company_name):
    """Return the slogan of a company (matched by name prefix, any case)."""
    name = str(company_name).lower()
    for prefix, slogan in SLOGANS.items():
        if name.startswith(prefix.lower()):
            return slogan
    return DEFAULT_SLOGAN
    
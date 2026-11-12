from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pdfplumber

#Date
def today_armenia():
    now = datetime.now(ZoneInfo("Asia/Yerevan"))
    return now.strftime("%d/%m/%Y")

#Files Exactly One Line Of The Info
def fill_text(text,values):
    for key,value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text

#Loop For Fill_text
def fill_blocks(template,values):
    filled=[]
    for block in template["blocks"]:
        new_block = dict(block)
        new_block["text"] = fill_text(block["text"], values)
        filled.append(new_block)
    return filled

#Value Building
def build_values(first_name, surname):
    return {"first_name":first_name,
            "surname":surname,
            "current_date":today_armenia()}

#RTF
def rtf_escape(text):
    result=""
    for ch in str(text):
        if ch in "\\{}":
            result += "\\" + ch
        elif ord(ch)>127:
            code = ord(ch)
            if code > 32767:
                code = code - 65536
            result += "\\u" + str(code) + "?"
        else:
            result = result + ch
    return result

def rtf_paragraph(block):
    aligns = {"left":"\\ql","center":"\\qc","right":"\\qr"}
    result = "\\pard" + aligns.get(block["align"], "\\ql")
    result += "\\sa" + str(block["space_after"]*20)
    result += "\\fs" + str(block["size"]*2) + " "
    if block["bold"]:
        result += "\\b " + rtf_escape(block["text"]) + "\\b0"
    else:
        result += rtf_escape(block["text"])
    result += "\\par"
    return result

def make_rtf(template, blocks):
    margin = str(template["page"]["margin_pt"] * 20)
    rtf = "{\\rtf1\\ansi\\deff0"
    rtf += "{\\fonttbl{\\f0 " + rtf_escape(template["font"]) + ";}}\\f0"
    rtf += "\\paperw11906\\paperh16838"
    rtf += "\\margl" + margin + "\\margr" + margin + "\\margt" + margin + "\\margb" + margin
    for block in blocks:
        rtf += rtf_paragraph(block)
    rtf += "}"
    return rtf.encode("ascii")

#PDF
def register_fonts():
    if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

def make_pdf(template, blocks):
    register_fonts()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = template["page"]["margin_pt"]
    y = height - margin
    for block in blocks:
        size = block["size"]
        if block["bold"]:
            font = "DejaVuSans-Bold"
        else:
            font = "DejaVuSans"
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

#Pieces Of An RTF File
RTF_TOKEN = re.compile(r"\\u(-?\d+)\??|\\([a-z]+)(-?\d+)? ?|\\([\\{}])|[{}]|([^\\{}]+)")

#RTF Bytes --> (Template, Blocks)
def rtf_to_blocks(data):
    rtf = data.decode("latin-1")
    start = rtf.find("\\pard")
    if start == -1:
        raise ValueError("No text found. Only RTF files made by this app can be converted.")
    font = re.search(r"\{\\f0 ([^;]*);\}", rtf)
    margin = re.search(r"\\margl(\d+)", rtf)
    template = {"font": font.group(1) if font else "DejaVu Sans",
                "page": {"margin_pt": int(margin.group(1)) // 20 if margin else 72}}
    aligns = {"ql": "left", "qc": "center", "qr": "right"}
    blocks = []
    align, space, size, bold = "left", 0, 12, False
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
            elif word in aligns:
                align = aligns[word]
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

#PDF Bytes --> (Template, Blocks)
def pdf_to_blocks(data):
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
    template = {"font": "DejaVu Sans", "page": {"margin_pt": margin}}
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

def rtf_to_pdf(data):
    template, blocks = rtf_to_blocks(data)
    return make_pdf(template, blocks)

def pdf_to_rtf(data):
    template, blocks = pdf_to_blocks(data)
    return make_rtf(template, blocks)
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .common import ACCENT_HEX, GRAY_HEX, LETTER_MARGIN_PT, LOGO_HEIGHT_PT

PDF_FONT = "DejaVuSans"
PDF_FONT_BOLD = "DejaVuSans-Bold"
PDF_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PDF_FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


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
        font = PDF_FONT_BOLD if block["bold"] else PDF_FONT
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


def make_letter_pdf(letter):
    """Build the letter as an A4 PDF and return it as bytes."""
    register_fonts()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    m = LETTER_MARGIN_PT
    top = height - m

    if letter["logo"] and letter["logo"].strip() and __import__("os").path.exists(letter["logo"]):
        img = ImageReader(letter["logo"])
        iw, ih = img.getSize()
        pdf.drawImage(img, m, top - LOGO_HEIGHT_PT, LOGO_HEIGHT_PT * iw / ih, LOGO_HEIGHT_PT, mask="auto")
    else:
        pdf.setFillColor(HexColor(ACCENT_HEX))
        pdf.setFont(PDF_FONT_BOLD, 20)
        pdf.drawString(m, top - 30, letter["company"])
    pdf.setFillColor(HexColor(GRAY_HEX))
    pdf.setFont(PDF_FONT, 10)
    pdf.drawString(m, top - LOGO_HEIGHT_PT - 16, letter["slogan"])

    pdf.setFillColor(HexColor("#000000"))
    pdf.setFont(PDF_FONT, 10)
    y = top - 10
    for line in letter["right_lines"]:
        pdf.drawRightString(width - m, y, line)
        y = y - 14

    rule_y = top - LOGO_HEIGHT_PT - 30
    pdf.setStrokeColor(HexColor(ACCENT_HEX))
    pdf.setLineWidth(2)
    pdf.line(m, rule_y, width - m, rule_y)

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

    sig_y = m + 40
    pdf.setStrokeColor(HexColor("#000000"))
    pdf.setLineWidth(1)
    pdf.line(width - m - 180, sig_y, width - m, sig_y)
    pdf.setFillColor(HexColor(GRAY_HEX))
    pdf.setFont(PDF_FONT, 9)
    pdf.drawRightString(width - m, sig_y - 12, letter["signer"])
    pdf.save()
    return buffer.getvalue()

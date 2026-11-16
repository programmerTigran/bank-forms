import base64
import os
from html import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from .common import ACCENT_HEX, GRAY_HEX, LETTER_MARGIN_PT, LOGO_HEIGHT_PT, SLOGANS, DEFAULT_SLOGAN, today_armenia
from .pdf import PDF_FONT, PDF_FONT_BOLD, register_fonts
from .rtf import rtf_escape


def build_letter(first_name, surname, company_name, logo_path):
    """Return everything the letter shows. Change the texts here."""
    who = company_name or "us"
    return {
        "logo": logo_path,
        "company": company_name,
        "slogan": get_slogan(company_name),
        "right_lines": ["Date: " + today_armenia(), "Place: Yerevan"],
        "title": "Thank you, " + first_name + " " + surname,
        "paragraphs": [
            "Thank you for working with " + who + ".",
            "We value your trust and look forward to our continued cooperation.",
        ],
        "signer": "Authorized signature",
    }


def get_slogan(company_name):
    """Return the slogan of a company (matched by name prefix, any case)."""
    name = str(company_name).lower()
    for prefix, slogan in SLOGANS.items():
        if name.startswith(prefix.lower()):
            return slogan
    return DEFAULT_SLOGAN


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
    page = "<div style='background:white;color:black;width:794px;max-width:100%;min-height:1123px;box-sizing:border-box;padding:" + str(LETTER_MARGIN_PT) + "px;margin:auto;display:flex;flex-direction:column;'>"
    return page + header + body + signature + "</div>"


def rtf_logo(path):
    """Return the logo as an RTF picture."""
    from reportlab.lib.utils import ImageReader
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
    return ("{\\pict" + kind + "\\picw" + str(iw) + "\\pich" + str(ih) + "\\picwgoal" + str(goal_w) + "\\pichgoal" + str(goal_h) + " " + data.hex() + "}")


def make_letter_rtf(letter):
    """Build the letter as an RTF file and return it as bytes."""
    margin = LETTER_MARGIN_PT * 20
    full = 11906 - 2 * margin
    half = full // 2
    rtf = "{\\rtf1\\ansi\\deff0"
    rtf += "{\\fonttbl{\\f0 " + "DejaVu Sans" + ";}}"
    rtf += "{\\colortbl;\\red31\\green78\\blue140;\\red102\\green102\\blue102;}\\f0"
    rtf += "\\paperw11906\\paperh16838"
    rtf += "\\margl" + str(margin) + "\\margr" + str(margin) + "\\margt" + str(margin) + "\\margb" + str(margin)

    if has_logo(letter):
        brand = rtf_logo(letter["logo"])
    else:
        brand = "\\cf1\\b\\fs40 " + rtf_escape(letter["company"]) + "\\b0\\cf0"
    left = brand + "\\line\\cf2\\fs20 " + rtf_escape(letter["slogan"]) + "\\cf0\\fs24"
    right = "\\line ".join(rtf_escape(line) for line in letter["right_lines"])
    rtf += "\\trowd\\trgaph0\\cellx" + str(half) + "\\cellx" + str(full)
    rtf += "\\pard\\intbl " + left + "\\cell"
    rtf += "\\pard\\intbl\\qr\\fs20 " + right + "\\cell\\row"
    rtf += "\\pard\\sb100\\brdrb\\brdrs\\brdrw20\\brdrcf1\\par"
    rtf += "\\pard\\sb3600\\sa300\\fs36\\b " + rtf_escape(letter["title"]) + "\\b0\\par"
    for paragraph in letter["paragraphs"]:
        rtf += "\\pard\\sa200\\fs24 " + rtf_escape(paragraph) + "\\par"
    rtf += "\\pard\\qr\\sb3600\\fs24 ____________________\\par"
    rtf += "\\pard\\qr\\cf2\\fs18 " + rtf_escape(letter["signer"]) + "\\cf0\\par"
    rtf += "}"
    return rtf.encode("ascii")

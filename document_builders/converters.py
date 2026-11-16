import re

from .common import DEFAULT_FONT_NAME, DEFAULT_MARGIN_PT, DEFAULT_SIZE_PT, LETTER_MARGIN_PT, LOGO_HEIGHT_PT
from .common import ACCENT_HEX, GRAY_HEX

RTF_ALIGN_CODES = {"left": "\\ql", "center": "\\qc", "right": "\\qr"}
RTF_ALIGN_NAMES = {"ql": "left", "qc": "center", "qr": "right"}
RTF_TOKEN = re.compile(r"\\u(-?\d+)\??|\\([a-z]+)(-?\d+)? ?|\\([\\{}])|[{}]|([^\\{}]+)")


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


def rtf_to_blocks(data):
    """Read an RTF made by this app back into (template, blocks)."""
    rtf = data.decode("latin-1")
    start = rtf.find("\\pard")
    if start == -1:
        raise ValueError("No text found. Only RTF files made by this app can be converted.")
    font = re.search(r"\{\\f0 ([^;]*);\}", rtf)
    margin = re.search(r"\\margl(\d+)", rtf)
    template = {
        "font": font.group(1) if font else DEFAULT_FONT_NAME,
        "page": {"margin_pt": int(margin.group(1)) // 20 if margin else DEFAULT_MARGIN_PT},
    }
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
                blocks.append({"text": text, "align": align, "size": size, "bold": block_bold, "space_after": space})
                text, block_bold = "", False
    if not blocks:
        raise ValueError("No text found in this RTF.")
    return template, blocks

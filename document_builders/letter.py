import pdfplumber
from io import BytesIO

from .pdf import make_pdf
from .rtf import make_rtf, rtf_to_blocks


def rtf_to_pdf(data):
    """Convert RTF bytes to PDF bytes."""
    template, blocks = rtf_to_blocks(data)
    return make_pdf(template, blocks)


def pdf_to_rtf(data):
    """Convert PDF bytes to RTF bytes."""
    template, blocks = pdf_to_blocks(data)
    return make_rtf(template, blocks)


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
                lines.append({
                    "text": line["text"].strip(),
                    "x0": line["x0"],
                    "x1": line["x1"],
                    "baseline": first["matrix"][5],
                    "size": round(first["size"]),
                    "bold": "bold" in first["fontname"].lower(),
                    "width": page.width,
                    "last_on_page": i == len(page_lines) - 1,
                })
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
        blocks.append({"text": l["text"], "align": align, "size": l["size"], "bold": l["bold"], "space_after": space})
    return template, blocks

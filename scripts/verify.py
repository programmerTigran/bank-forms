"""
scripts/verify.py
Checks that every customer's RTF and PDF contain the filled-in values.
Run from the project root (venv active): python -m scripts.verify
"""

# ============================================================
# 1. IMPORTS
# ============================================================
import re
from io import BytesIO

from pypdf import PdfReader

from db import get_customer, get_customer_ids, load_template
from documents import build_values, fill_blocks, make_rtf, make_pdf


# ============================================================
# 2. CONSTANTS
# ============================================================
TEMPLATE_NAME = "customer_details"
REQUIRED_KEYS = ("first_name", "surname", "current_date")


# ============================================================
# 3. HELPERS
# ============================================================
def rtf_to_text(rtf_bytes):
    """Decode RTF bytes to plain text (turns \\uNNN? escapes into characters)."""
    text = rtf_bytes.decode("ascii")
    return re.sub(r"\\u(\d+)\?", lambda m: chr(int(m.group(1))), text)


def pdf_to_text(pdf_bytes):
    """Extract the text of the first PDF page."""
    reader = PdfReader(BytesIO(pdf_bytes))
    return reader.pages[0].extract_text()


def find_missing(text, values):
    """Return the required keys whose value is not found in the text."""
    return [key for key in REQUIRED_KEYS if values[key] not in text]


# ============================================================
# 4. CORE LOGIC
# ============================================================
def run_checks():
    """Check every customer in RTF and PDF. Returns (failures, total)."""
    template = load_template(TEMPLATE_NAME)
    failures = 0
    total = 0

    for customer_id in get_customer_ids():
        first_name, surname = get_customer(customer_id)
        values = build_values(first_name, surname)
        blocks = fill_blocks(template, values)
        texts = {
            "RTF": rtf_to_text(make_rtf(template, blocks)),
            "PDF": pdf_to_text(make_pdf(template, blocks)),
        }
        for fmt, text in texts.items():
            total += 1
            missing = find_missing(text, values)
            if missing:
                failures += 1
                print("FAIL", customer_id, fmt, "missing:", missing)
            else:
                print("OK  ", customer_id, fmt)

    return failures, total


# ============================================================
# 5. MAIN
# ============================================================
def main():
    failures, total = run_checks()
    if failures == 0:
        print("All", total, "checks passed.")
    else:
        print(failures, "of", total, "checks failed.")


if __name__ == "__main__":
    main()
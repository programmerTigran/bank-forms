import re
from io import BytesIO
from pypdf import PdfReader
from db import get_customer, load_template
from documents import build_values, fill_blocks, make_rtf, make_pdf

def rtf_to_text(rtf_bytes):  
    text = rtf_bytes.decode("ascii")
    return re.sub(r"\\u(\d+)\?", lambda m: chr(int(m.group(1))), text)

def pdf_to_text(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    return reader.pages[0].extract_text()

def find_missing(text, values):
    missing = []
    for key in ("first_name", "surname", "current_date"):
        if values[key] not in text:
            missing.append(key)
    return missing

template = load_template("customer_details")
failures = 0

for customer_id in range(1, 11):
    first_name, surname = get_customer(customer_id)
    values = build_values(first_name, surname)
    blocks = fill_blocks(template, values)
    texts = {
        "RTF": rtf_to_text(make_rtf(template, blocks)),
        "PDF": pdf_to_text(make_pdf(template, blocks)),
    }
    for fmt, text in texts.items():
        missing = find_missing(text, values)
        if missing:
            failures += 1
            print("FAIL", customer_id, fmt, "missing:", missing)
        else:
            print("OK  ", customer_id, fmt)

if failures == 0:
    print("All 20 checks passed.")
else:
    print(failures, "checks failed.")
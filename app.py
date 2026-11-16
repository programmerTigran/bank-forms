"""
app.py
Streamlit page: pick a customer and a template, preview the filled
document, download it as RTF/PDF, or convert an uploaded RTF/PDF.
Run: streamlit run app.py
"""

# ============================================================
# 1. IMPORTS
# ============================================================

from html import escape
import streamlit as st
from db import search_customers, get_template_names, get_customer, load_template, get_company_logo
from documents import (build_values, fill_blocks, make_rtf, make_pdf, rtf_to_pdf, pdf_to_rtf,
                       build_letter, make_letter_html, make_letter_rtf, make_letter_pdf)

# ============================================================
# 2. CONSTANTS
# ============================================================

PAGE_TITLE = "Bank forms"
PAGE_ICON = "📄"
FORMATS = ["RTF", "PDF"]
MIME_RTF = "application/rtf"
MIME_PDF = "application/pdf"
ALL_CUSTOMERS_LIMIT = 500
LETTER_TEMPLATE = "customer_details"

# ============================================================
# 3. HELPERS
# ============================================================

def show_preview(template, blocks):
    """Show the filled document as a white page."""
    margin = template["page"]["margin_pt"]
    html = "<div style='background:white;color:black;padding:" + str(margin) + "px;min-height:500px;max-width:794px;margin:auto;box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:" + escape(str(template["font"])) + ",Arial,sans-serif;'>"
    for block in blocks:
        if block["bold"]:
            weight = "bold"
        else:
            weight = "normal"
        html += "<p style='text-align:" + block["align"] + ";font-size:" + str(block["size"]) + "pt;font-weight:" + weight + ";margin:0 0 " + str(block["space_after"]) + "pt 0;'>" + escape(str(block["text"])) + "</p>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def download_button(label, data, file_name, mime):
    """Full-width download button."""
    st.download_button(label=label, data=data, file_name=file_name, mime=mime, width="stretch")

# ============================================================
# 4. PAGE SECTIONS
# ============================================================

def pick_customer():
    """One dropdown with all customers (type to filter).
    Returns (first_name, surname, company_name), or ("", "", "") if none."""
    try:
        customers = search_customers("", limit=ALL_CUSTOMERS_LIMIT)
    except Exception as e:
        st.error("Database error: " + str(e))
        return "", "", ""

    if not customers:
        st.warning("No customers found")
        return "", "", ""

    choice = st.selectbox(
        "Customer (type id or name)",
        customers,
        format_func=lambda r: str(r[0]) + " – " + r[1] + " " + r[2],
    )
    return get_customer(choice[0])

def pick_template():
    """Template dropdown. Returns the template name, or None if none."""
    try:
        names = get_template_names()
        if not names:
            st.warning("No templates in the database.")
            return None
        return st.selectbox("Template", names)
    except Exception as e:
        st.error("Database error: " + str(e))
        return None

def show_letter(first_name, surname, company_name, fmt):
    """Preview the letter layout and offer it for download."""
    letter = build_letter(first_name, surname, company_name, get_company_logo(company_name))
    st.markdown(make_letter_html(letter), unsafe_allow_html=True)
    if fmt == "RTF":
        download_button("Download RTF", make_letter_rtf(letter), "customer.rtf", MIME_RTF)
    else:
        download_button("Download PDF", make_letter_pdf(letter), "customer.pdf", MIME_PDF)

def show_document(template_name, first_name, surname, company_name, fmt):
    """Preview the filled document and offer it for download."""
    try:
        if template_name == LETTER_TEMPLATE:
            show_letter(first_name, surname, company_name, fmt)
            return
        template = load_template(template_name)
        blocks = fill_blocks(template, build_values(first_name, surname, company_name))
        show_preview(template, blocks)
        if fmt == "RTF":
            download_button("Download RTF", make_rtf(template, blocks), "customer.rtf", MIME_RTF)
        else:
            download_button("Download PDF", make_pdf(template, blocks), "customer.pdf", MIME_PDF)
    except Exception as e:
        st.error("Could not make the document: " + str(e))

def show_converter():
    """Upload an RTF/PDF made by this app and convert it to the other format."""
    st.divider()
    st.subheader("Convert a file")
    uploaded = st.file_uploader("Upload an RTF or PDF made by this app", type=["rtf", "pdf"])
    if not uploaded:
        return
    try:
        file_data = uploaded.getvalue()
        if uploaded.name.lower().endswith(".pdf"):
            download_button("Download as RTF", pdf_to_rtf(file_data), "converted.rtf", MIME_RTF)
        else:
            download_button("Download as PDF", rtf_to_pdf(file_data), "converted.pdf", MIME_PDF)
    except Exception as e:
        st.error("Could not convert: " + str(e))

# ============================================================
# 5. MAIN
# ============================================================

def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)
    st.title("Bank customer form")

    first_name, surname, company_name = pick_customer()
    template_name = pick_template()
    fmt = st.radio("Format", FORMATS, horizontal=True)

    if first_name and surname and template_name:
        show_document(template_name, first_name, surname, company_name, fmt)
    else:
        st.info("Pick a customer.")

    show_converter()

main()

from html import escape
import streamlit as st
from db import get_customer_ids, get_template_names, get_customer, load_template
from documents import build_values, fill_blocks, make_rtf, make_pdf, rtf_to_pdf, pdf_to_rtf

#Preview (Show Us Information About Selected Customer)
def show_preview(template, blocks):
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

#Page(The Visual)
st.set_page_config(page_title="Bank forms", page_icon="📄")
st.title("Bank customer form")

first_name = ""
surname = ""

try:
    ids = get_customer_ids()
    if not ids:
        st.warning("No customers in the database.")
    else:
        customer_id = st.selectbox("Customer id", ids)
        first_name, surname = get_customer(customer_id)
except Exception as e:
    st.error("Database error: " + str(e))

#Template Choice(One Of The Templates Is For The Customer(Print))
template_name = None
try:
    template_names = get_template_names()
    if not template_names:
        st.warning("No templates in the database.")
    else:
        template_name = st.selectbox("Template", template_names)
except Exception as e:
    st.error("Database error: " + str(e))

fmt = st.radio("Format", ["RTF", "PDF"], horizontal=True)

if first_name and surname and template_name:
    try:
        template = load_template(template_name)
        blocks = fill_blocks(template, build_values(first_name, surname))
        show_preview(template, blocks)
        if fmt == "RTF":
            st.download_button(
                label="Download RTF",
                data=make_rtf(template, blocks),
                file_name="customer.rtf",
                mime="application/rtf",
                width="stretch",
            )
        else:
            st.download_button(
                label="Download PDF",
                data=make_pdf(template, blocks),
                file_name="customer.pdf",
                mime="application/pdf",
                width="stretch",
            )
    except Exception as e:
        st.error("Could not make the document: " + str(e))
else:
    st.info("Pick a customer.")

#Convertation From RTF/PDF to PDF/RTF
st.divider()
st.subheader("Convert a file")
uploaded = st.file_uploader("Upload an RTF or PDF made by this app", type=["rtf", "pdf"])
if uploaded:
    try:
        file_data = uploaded.getvalue()
        if uploaded.name.lower().endswith(".pdf"):
            st.download_button(
                label="Download as RTF",
                data=pdf_to_rtf(file_data),
                file_name="converted.rtf",
                mime="application/rtf",
                width="stretch",
            )
        else:
            st.download_button(
                label="Download as PDF",
                data=rtf_to_pdf(file_data),
                file_name="converted.pdf",
                mime="application/pdf",
                width="stretch",
            )
    except Exception as e:
        st.error("Could not convert: " + str(e))
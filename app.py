from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from html import escape
import json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import psycopg
import streamlit as st

#All Customer IDs For The Dropdown
def get_customer_ids():
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT customer_id " \
                    "FROM customers " \
                    "ORDER BY customer_id")
        return [row[0] for row in cur.fetchall()]

#All Template Names For The Dropdown
def get_template_names():
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT DISTINCT name " \
                    "FROM document_templates " \
                    "ORDER BY name")
        return [row[0] for row in cur.fetchall()]

#Call The Customer By Their ID
def get_customer(customer_id):
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT first_name,surname " \
                    "FROM customers " \
                    "WHERE customer_id=%s",
                    (customer_id,))
        row = cur.fetchone()
        return row

#Save A New Customer
def add_customer(first_name, surname):
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT 1 FROM customers " \
                    "WHERE LOWER(first_name)=LOWER(%s) AND LOWER(surname)=LOWER(%s)",
                    (first_name,surname))
        if cur.fetchone():
            raise ValueError("This customer already exists")
        cur.execute("INSERT INTO customers (customer_id,first_name,surname) " \
                    "SELECT COALESCE(MAX(customer_id),0)+1, %s, %s " \
                    "FROM customers " \
                    "RETURNING customer_id",
                    (first_name,surname))
        new_id=cur.fetchone()[0]
        conn.commit()
    with open("customers.csv","a",newline="",encoding="utf-8") as f:
        csv.writer(f).writerow([new_id,first_name,surname])
    return new_id

#Date
def today_armenia():
    now = datetime.now(ZoneInfo("Asia/Yerevan"))
    return now.strftime("%d/%m/%Y")

#Fetches Newest Form
def load_template(name):
    with psycopg.connect() as conn:
        cur=conn.cursor()
        cur.execute("SELECT definition " \
                    "FROM document_templates " \
                    "WHERE name=%s " \
                    "ORDER BY version DESC " \
                    "LIMIT 1 ",
                    (name,))
        row=cur.fetchone()
        if row is None:
            raise ValueError("Template " + name + " not found")
        definition=row[0]
        if isinstance(definition,str):
            definition=json.loads(definition)
        return definition

#Files One Line Of The Info
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

#Value Building (now takes the names directly, so it works for manual entry too)
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
        #New page when the text would go under the bottom margin
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

#Preview (looks like a white paper page)
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

source = st.radio("Customer", ["Existing customer", "Enter manually"], horizontal=True)

first_name = ""
surname = ""

if source == "Existing customer":
    try:
        ids = get_customer_ids()
        if not ids:
            st.warning("No customers in the database.")
        else:
            customer_id = st.selectbox("Customer id", ids)
            first_name, surname = get_customer(customer_id)
    except Exception as e:
        st.error("Database error: " + str(e))
else:
    first_name = st.text_input("First name")
    surname = st.text_input("Surname")
    if st.button("Save customer to database"):
        if first_name.strip() and surname.strip():
            try:
                new_id = add_customer(first_name.strip(), surname.strip())
                st.success("Saved. Customer id: " + str(new_id))
            except Exception as e:
                st.error("Could not save: " + str(e))
        else:
            st.warning("Type a first name and surname first.")

#Template Choice
template_name = None
try:
    template_names = get_template_names()
    if not template_names:
        st.warning("No templates in the database.")
    else:
        template_name = st.selectbox("Template", template_names)
except Exception as e:
    st.error("Database error: " + str(e))

if source == "Existing customer":
    formats = ["RTF", "PDF"]
else:
    formats = ["RTF"]
fmt = st.radio("Format", formats, horizontal=True)

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
    st.info("Pick a customer or type a first name and surname.")
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import psycopg
import streamlit as st

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
        return row[0]

#Files One Line Of The Info
def fill_text(text,values):
    for key,value in values.items():
        text = text.replace("{{" + key + "}}", value)
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
def build_values(customer_id):
    first_name, surname = get_customer(customer_id)
    return {"first_name":first_name,
            "surname":surname,
            "current_date":today_armenia()}

#RTF
def rtf_escape(text):
    result=""
    for ch in text:
        if ch in ("\\{}"):
            result += "\\" + ch
        elif ord(ch)>127:
            result += "\\u" + str(ord(ch)) + "?"
        else:
            result = result + ch
    return result

def rtf_paragraph(block):
    aligns = {"left":"\\ql","center":"\\qc","right":"\\qr"}
    result = "\\pard" + aligns[block["align"]]
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
    rtf += "{\\fonttbl{\\f0 " + template["font"] + ";}}"
    rtf += "\\paperw11906\\paperh16838"
    rtf += "\\margl" + margin + "\\margr" + margin + "\\margt" + margin + "\\margb" + margin
    for block in blocks:
        rtf += rtf_paragraph(block)
    rtf += "}"
    return rtf.encode("ascii")

#PDF
def register_fonts():
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
            pdf.setFont("DejaVuSans-Bold", size)
        else:
            pdf.setFont("DejaVuSans", size)
        y = y - size
        if block["align"] == "center":
            pdf.drawCentredString(width / 2, y, block["text"])
        elif block["align"] == "right":
            pdf.drawRightString(width - margin, y, block["text"])
        else:
            pdf.drawString(margin, y, block["text"])
        y = y - block["space_after"]
    pdf.save()
    return buffer.getvalue()


#Page(The Visual)
st.title("Bank customer form")
customer_id = st.selectbox("Customer id", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
fmt = st.radio("Format", ["RTF", "PDF"])
st.write("Selected format:", fmt)

template = load_template("customer_details")
blocks = fill_blocks(template, build_values(customer_id))

for block in blocks:
    st.write(block["text"])

if fmt == "RTF":
    st.download_button(
        label="Download RTF",
        data=make_rtf(template, blocks),
        file_name="customer.rtf",
        mime="application/rtf",
    )
else:
    st.download_button(
        label="Download PDF",
        data=make_pdf(template, blocks),
        file_name="customer.pdf",
        mime="application/pdf",
    )
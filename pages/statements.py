"""
pages/statement.py
Transaction statement: pick a customer (type in the dropdown to filter), a date
range and optional filters (type, min/max amount, text), preview the statement,
download it as RTF/PDF.
"""

# ============================================================
# 1. IMPORTS
# ============================================================

from datetime import date, timedelta
import streamlit as st
from db import search_customers, get_customer, get_company_logo, get_transactions_between
from documents import (build_statement, make_statement_html,
                       make_statement_pdf, make_statement_rtf)

# ============================================================
# 2. CONSTANTS
# ============================================================

MIME_RTF = "application/rtf"
MIME_PDF = "application/pdf"
ALL_LIMIT = 500
TX_TYPE_OPTIONS = ["deposit", "withdrawal", "transfer", "payment"]

# ============================================================
# 3. PAGE SECTIONS
# ============================================================

def pick_customer():
    """One dropdown with every customer. Type in it to filter by id or name."""
    results = search_customers("", limit=ALL_LIMIT)
    if not results:
        st.warning("No customers found")
        return None
    choice = st.selectbox(
        "Select customer (type to filter by id or name)",
        results,
        format_func=lambda r: str(r[0]) + " – " + r[1] + " " + r[2],
    )
    return choice[0]

def pick_dates():
    """Two date boxes. Returns (date_from, date_to)."""
    col_from, col_to = st.columns(2)
    date_from = col_from.date_input("From", value=date.today() - timedelta(days=365),
                                    format="DD/MM/YYYY")
    date_to = col_to.date_input("To", value=date.today(), format="DD/MM/YYYY")
    return date_from, date_to

def pick_filters():
    """Optional filters. Returns a dict; empty / 0 means 'no filter'."""
    with st.expander("Filters (optional)"):
        tx_types = st.multiselect("Type", TX_TYPE_OPTIONS)
        col_min, col_max = st.columns(2)
        min_amount = col_min.number_input("Amount from (0 = no limit)", min_value=0.0,
                                          step=10000.0, format="%.2f")
        max_amount = col_max.number_input("Amount up to (0 = no limit)", min_value=0.0,
                                          step=10000.0, format="%.2f")
        search = st.text_input("Text in description or id")
    filters = {"tx_types": tx_types, "search": search.strip()}
    filters["min_amount"] = min_amount if min_amount > 0 else None
    filters["max_amount"] = max_amount if max_amount > 0 else None
    return filters

def describe_filters(filters):
    """Return one line that lists the active filters, or "" if none."""
    parts = []
    if filters["tx_types"]:
        parts.append("type " + ", ".join(filters["tx_types"]))
    if filters["min_amount"] is not None:
        parts.append("amount from " + format(filters["min_amount"], ",.2f"))
    if filters["max_amount"] is not None:
        parts.append("amount up to " + format(filters["max_amount"], ",.2f"))
    if filters["search"]:
        parts.append("text \"" + filters["search"] + "\"")
    if not parts:
        return ""
    return "Filters: " + "; ".join(parts)

def show_statement(customer_id, date_from, date_to, fmt, filters):
    """Preview the statement and offer it for download."""
    first_name, surname, company_name = get_customer(customer_id)
    rows = get_transactions_between(customer_id, date_from, date_to,
                                    filters["tx_types"], filters["min_amount"],
                                    filters["max_amount"], filters["search"])
    doc = build_statement(first_name, surname, customer_id, company_name,
                          get_company_logo(company_name), date_from, date_to, rows)
    filter_line = describe_filters(filters)
    if filter_line:
        doc["info_lines"].append(filter_line)
    st.markdown(make_statement_html(doc), unsafe_allow_html=True)
    if fmt == "RTF":
        st.download_button("Download RTF", make_statement_rtf(doc), "statement.rtf",
                           MIME_RTF, width="stretch")
    else:
        st.download_button("Download PDF", make_statement_pdf(doc), "statement.pdf",
                           MIME_PDF, width="stretch")

# ============================================================
# 4. MAIN
# ============================================================

def main():
    st.set_page_config(page_title="Statement", page_icon="🧾")
    st.title("Transaction statement")
    try:
        customer_id = pick_customer()
        date_from, date_to = pick_dates()
        filters = pick_filters()
        fmt = st.radio("Format", ["PDF", "RTF"], horizontal=True)
        if customer_id is None:
            return
        if date_from > date_to:
            st.warning("'From' must be before 'To'.")
            return
        show_statement(customer_id, date_from, date_to, fmt, filters)
    except Exception as e:
        st.error("Could not make the statement: " + str(e))

main()

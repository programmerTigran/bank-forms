"""
pages/companies.py
Companies page: each company has two tabs.
Total = company totals (click the amount for Debit/Credit), Per customer =
customers (search, 3 shown by default) with a button that opens their
transaction history (search, 8 shown by default).
"""

# ============================================================
# 1. IMPORTS
# ============================================================

import os
import streamlit as st
from db import (get_company_summary, get_company_customers, get_company_customer_count,
                search_customer_transactions, count_customer_transactions,
                get_company_direction_totals, get_company_type_totals)
import pandas as pd
from documents import get_slogan

# ============================================================
# 2. CONSTANTS
# ============================================================

CUSTOMER_LIMIT = 3
CUSTOMER_ALL_LIMIT = 500
TX_LIMIT = 8
TX_ALL_LIMIT = 500

# ============================================================
# 3. POPUPS
# ============================================================

@st.dialog("Transaction history", width="large")
def show_transactions(customer_id, name):
    """Popup: search box + transaction table for one customer."""
    st.subheader(str(customer_id) + ". " + name)
    search = st.text_input("Search (id, type, amount, date or description)")
    show_all = st.checkbox("Show whole table")
    first_only = not show_all and not search.strip()
    limit = TX_ALL_LIMIT if show_all else TX_LIMIT

    rows = search_customer_transactions(customer_id, search, limit, first_only)
    if not rows:
        st.info("No transactions found.")
        return
    table = []
    for tx_id, tx_date, tx_type, amount, description in rows:
        table.append({"ID": tx_id,
                      "Date": tx_date,
                      "Type": tx_type,
                      "Amount": float(amount),
                      "Description": description})
    df = pd.DataFrame(table)
    st.dataframe(
        df.style.format({"Amount": "{:,.2f}"}),
        hide_index=True,
        width="stretch",
        column_config={
            "ID": st.column_config.TextColumn(width="small"),
            "Date": st.column_config.TextColumn(width="small"),
            "Type": st.column_config.TextColumn(width="small"),
            "Amount": st.column_config.TextColumn(width="medium"),
            "Description": st.column_config.TextColumn(width="large"),
        },
    )
    total = count_customer_transactions(customer_id, search)
    if first_only:
        st.caption("Showing the first transaction of each type (ids ending in .1): "
                   + str(len(rows)) + " of " + str(total) + ". "
                   "Tick 'Show whole table' or type in the search to see more.")
    else:
        st.caption("Showing " + str(len(rows)) + " of " + str(total) + " transactions")
    """Popup: search box + transaction table for one customer."""
    st.subheader(str(customer_id) + ". " + name)
        search = st.text_input("Search (id, type, amount, date or description)", key="txs_" + str(customer_id))
    show_all = st.checkbox("Show whole table", key="txa_" + str(customer_id))
    limit = TX_ALL_LIMIT if show_all else TX_LIMIT

    rows = search_customer_transactions(customer_id, search, limit)
    if not rows:
        st.info("No transactions found.")
        return
    table = []
    for tx_id, tx_date, tx_type, amount, description in rows:
        table.append({"ID": tx_id,
                      "Date": tx_date,
                      "Type": tx_type,
                      "Amount": float(amount),
                      "Description": description})
    df = pd.DataFrame(table)
    st.dataframe(
        df.style.format({"Amount": "{:,.2f}"}),
        hide_index=True,
        width="stretch",
        column_config={
            "ID": st.column_config.TextColumn(width="small"),
            "Date": st.column_config.TextColumn(width="small"),
            "Type": st.column_config.TextColumn(width="small"),
            "Amount": st.column_config.TextColumn(width="medium"),
            "Description": st.column_config.TextColumn(width="large"),
        },
    )
    total = count_customer_transactions(customer_id, search)
    st.caption("Showing " + str(len(rows)) + " of " + str(total) + " transactions")

def set_view(view):
    """Switch the amount popup between the summary and a Debit/Credit breakdown."""
    st.session_state["amt_view"] = view

@st.dialog("Total amount", width="large")
def show_amounts(company_id, name):
    """Popup: Debit/Credit totals, click one to see its totals per type."""
    st.subheader(name)
    view = st.session_state.get("amt_view", "summary")

    if view == "summary":
        rows = get_company_direction_totals(company_id)
        if not rows:
            st.info("No transactions found.")
            return
        for direction, n, total in rows:
            label = direction + "s: " + format(total, ",.2f") + "  (" + str(n) + " transactions)"
            st.button(label, key="dir_" + direction, on_click=set_view,
                      args=(direction,), width="stretch")
        return

    st.button("← Back", key="amt_back", on_click=set_view, args=("summary",))
    st.markdown("**" + view + "s by type**")
    rows = get_company_type_totals(company_id, view)
    table = []
    for tx_type, n, total in rows:
        table.append({"Type": tx_type,
                      "Transactions": n,
                      "Total": format(total, ",.2f")})
    st.dataframe(table, hide_index=True, width="stretch")
    st.info("These are totals only. To see specific amounts, go back, open the "
            "Per customer tab and open the transactions of the customer you need.")

# ============================================================
# 4. PAGE SECTIONS
# ============================================================

def show_customer_row(company_id, customer_id, first_name, surname, n, total):
    """One customer row: id, name, total, and the transactions button."""
    col_id, col_name, col_total, col_button = st.columns([1, 3, 2, 2])
    col_id.write(customer_id)
    col_name.write(first_name + " " + surname)
    col_total.write(format(total, ",.2f"))
    key = "tx_" + str(company_id) + "_" + str(customer_id)
    if col_button.button(str(n) + " transactions", key=key, width="stretch"):
        show_transactions(customer_id, first_name + " " + surname)

def show_customers(company_id):
    """Search box, customer rows (3 by default), optional whole table."""
    term = st.text_input("Search customer (id or name)", key="search_" + str(company_id))
    show_all = st.checkbox("Show whole table", key="all_" + str(company_id))
    limit = CUSTOMER_ALL_LIMIT if show_all else CUSTOMER_LIMIT

    rows = get_company_customers(company_id, term, limit, 0)
    if not rows:
        st.info("No customers found.")
        return
    head_id, head_name, head_total, head_button = st.columns([1, 3, 2, 2])
    head_id.caption("ID")
    head_name.caption("Name")
    head_total.caption("Total")
    head_button.caption("History")
    for customer_id, first_name, surname, n, total in rows:
        show_customer_row(company_id, customer_id, first_name, surname, n, total)
    count = get_company_customer_count(company_id, term)
    st.caption("Showing " + str(len(rows)) + " of " + str(count) + " customers.")

def show_company(company_id, name, logo, customer_count, tx_count, tx_total):
    """Logo, name and slogan, then the Total tab and the Per customer tab."""
    col_logo, col_name = st.columns([1, 5])
    with col_logo:
        if logo and os.path.exists(logo):
            st.image(logo, width=80)
    with col_name:
        st.subheader(name)
        st.caption(get_slogan(name))

    tab_total, tab_customers = st.tabs(["Total", "Per customer"])

    with tab_total:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Customers", customer_count)
        col_b.metric("Transactions", tx_count)
        col_c.caption("Total amount (click)")
        if col_c.button(format(tx_total, ",.2f"), key="amt_" + str(company_id), width="stretch"):
            st.session_state["amt_view"] = "summary"
            show_amounts(company_id, name)

    with tab_customers:
        show_customers(company_id)

# ============================================================
# 5. MAIN
# ============================================================

def main():
    st.set_page_config(page_title="Companies", page_icon="🏢")
    st.title("Companies")
    try:
        for row in get_company_summary():
            show_company(*row)
    except Exception as e:
        st.error("Database error: " + str(e))

main()

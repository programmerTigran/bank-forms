"""
pages/companies.py
Company dashboard with totals, customer search, and transaction history.
"""

import os

import pandas as pd
import streamlit as st

from db import (
    count_customer_transactions,
    get_company_customer_count,
    get_company_customers,
    get_company_direction_totals,
    get_company_summary,
    get_company_type_totals,
    search_customer_transactions,
)
from documents import get_slogan

CUSTOMER_LIMIT = 3
CUSTOMER_ALL_LIMIT = 500
TX_LIMIT = 8
TX_ALL_LIMIT = 500


@st.dialog("Transaction history", width="large")
def show_transactions(customer_id, name):
    st.subheader(str(customer_id) + ". " + name)
    search = st.text_input("Search (id, type, amount, date or description)", key="txs_" + str(customer_id))
    show_all = st.checkbox("Show whole table", key="txa_" + str(customer_id))
    first_only = not show_all and not search.strip()
    limit = TX_ALL_LIMIT if show_all else TX_LIMIT
    rows = search_customer_transactions(customer_id, search, limit, first_only)
    if not rows:
        st.info("No transactions found.")
        return

    table = [
        {"ID": tx_id, "Date": tx_date, "Type": tx_type, "Amount": float(amount), "Description": description}
        for tx_id, tx_date, tx_type, amount, description in rows
    ]
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
    total = count_customer_transactions(customer_id, search, first_only)
    if first_only:
        st.caption(
            f"Showing the first transaction of each type (ids ending in .1): {len(rows)} of {total}. "
            "Tick 'Show whole table' or type in the search to see more."
        )
    else:
        st.caption(f"Showing {len(rows)} of {total} transactions")


def set_view(view):
    st.session_state["amt_view"] = view


@st.dialog("Total amount", width="large")
def show_amounts(company_id, name):
    st.subheader(name)
    view = st.session_state.get("amt_view", "summary")
    if view == "summary":
        rows = get_company_direction_totals(company_id)
        if not rows:
            st.info("No transactions found.")
            return
        for direction, count, total in rows:
            label = f"{direction}s: {total:,.2f} ({count} transactions)"
            st.button(label, key="dir_" + direction, on_click=set_view, args=(direction,), width="stretch")
        return

    st.button("← Back", key="amt_back", on_click=set_view, args=("summary",))
    st.markdown("**" + view + "s by type**")
    table = [
        {"Type": tx_type, "Transactions": count, "Total": format(total, ",.2f")}
        for tx_type, count, total in get_company_type_totals(company_id, view)
    ]
    st.dataframe(table, hide_index=True, width="stretch")
    st.info("These are totals only. Open a customer's transaction history to see individual entries.")


def show_customer_row(company_id, customer_id, first_name, surname, count, total):
    col_id, col_name, col_total, col_button = st.columns([1, 3, 2, 2])
    col_id.write(customer_id)
    col_name.write(first_name + " " + surname)
    col_total.write(format(total, ",.2f"))
    key = f"tx_{company_id}_{customer_id}"
    if col_button.button(str(count) + " transactions", key=key, width="stretch"):
        show_transactions(customer_id, first_name + " " + surname)


def show_customers(company_id):
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
    for row in rows:
        show_customer_row(company_id, *row)
    count = get_company_customer_count(company_id, term)
    st.caption(f"Showing {len(rows)} of {count} customers.")


def show_company(company_id, name, logo, customer_count, tx_count, tx_total):
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


def main():
    st.set_page_config(page_title="Companies", page_icon="🏢")
    st.title("Companies")
    try:
        for row in get_company_summary():
            show_company(*row)
    except Exception as exc:
        st.error("Database error: " + str(exc))


main()

"""
pages/companies.py
Companies page: each company has two tabs.
Total = company totals (click the amount for Debit/Credit), Per customer =
customers (search, real paging) with a button that opens their transaction
history (search, 8 shown by default). Opening a history is written to the audit log.
"""

# ============================================================
# 1. IMPORTS
# ============================================================

from math import ceil
import streamlit as st
from db import (get_company_summary, get_company_customers, get_company_customer_count,
                search_customer_transactions, count_customer_transactions,
                get_company_direction_totals, get_company_type_totals, get_company_logo_by_id,
                log_audit)
from documents import DATE_FORMAT, DEFAULT_CURRENCY, get_slogan, money, money_cur
from ui import require_login, current_user, show_error

# ============================================================
# 2. CONSTANTS AND CACHE
# ============================================================

COMPANY_LIMIT = 5          # companies shown before 'Show all'
PAGE_SIZES = [3, 10, 50, "All"]
TX_LIMIT = 8
TX_ALL_LIMIT = 500
CACHE_SECONDS = 60

@st.cache_data(ttl=CACHE_SECONDS)
def cached_summary():
    return get_company_summary()

@st.cache_data(ttl=CACHE_SECONDS)
def cached_logo(company_id):
    return get_company_logo_by_id(company_id)

@st.cache_data(ttl=CACHE_SECONDS)
def cached_customers(company_id, term, limit, offset):
    return get_company_customers(company_id, term, limit, offset)

@st.cache_data(ttl=CACHE_SECONDS)
def cached_customer_count(company_id, term):
    return get_company_customer_count(company_id, term)

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
    table = [{"ID": tx_id,
              "Date": tx_date.strftime(DATE_FORMAT),
              "Type": tx_type,
              "Amount (" + DEFAULT_CURRENCY + ")": money(amount),
              "Description": description}
             for tx_id, tx_date, tx_type, amount, description in rows]
    st.dataframe(table, hide_index=True, width="stretch")
    total = count_customer_transactions(customer_id, search)
    if first_only:
        st.caption("Showing the first transaction of each type (ids ending in .1): "
                   + str(len(rows)) + " of " + str(total) + ". "
                   "Tick 'Show whole table' or type in the search to see more.")
    else:
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
            label = direction + "s: " + money_cur(total) + "  (" + str(n) + " transactions)"
            st.button(label, key="dir_" + direction, on_click=set_view,
                      args=(direction,), width="stretch")
        return

    st.button("← Back", key="amt_back", on_click=set_view, args=("summary",))
    st.markdown("**" + view + "s by type**")
    rows = get_company_type_totals(company_id, view)
    table = [{"Type": tx_type, "Transactions": n, "Total (" + DEFAULT_CURRENCY + ")": money(total)}
             for tx_type, n, total in rows]
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
    col_total.write(money_cur(total))
    key = "tx_" + str(company_id) + "_" + str(customer_id)
    if col_button.button(str(n) + " transactions", key=key, width="stretch"):
        log_audit(current_user()["name"], "view_transactions", customer_id, "")
        show_transactions(customer_id, first_name + " " + surname)

def show_customers(company_id):
    """Search box, page size, page number, customer rows."""
    key = str(company_id)
    col_term, col_size = st.columns([3, 1])
    term = col_term.text_input("Search customer (id or name)", key="search_" + key).strip()
    size = col_size.selectbox("Rows", PAGE_SIZES, key="size_" + key)

    count = cached_customer_count(company_id, term)
    if count == 0:
        st.info("No customers found.")
        return
    if size == PAGE_SIZES[-1]:
        size = count
    pages = ceil(count / size)
    page = 1
    if pages > 1:
        # term and size are in the key, so changing them resets the page to 1
        page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1,
                               key="page_" + key + "_" + term + "_" + str(size))
    rows = cached_customers(company_id, term, size, (page - 1) * size)

    head_id, head_name, head_total, head_button = st.columns([1, 3, 2, 2])
    head_id.caption("ID")
    head_name.caption("Name")
    head_total.caption("Total")
    head_button.caption("History")
    for customer_id, first_name, surname, n, total in rows:
        show_customer_row(company_id, customer_id, first_name, surname, n, total)
    st.caption("Page " + str(page) + " of " + str(pages) + " (" + str(count) + " customers)")

def show_company(company_id, name, logo, customer_count, tx_count, tx_total):
    """Logo, name and slogan, then the Total tab and the Per customer tab."""
    col_logo, col_name = st.columns([1, 5])
    with col_logo:
        picture = cached_logo(company_id)
        if picture:
            st.image(picture, width=80)
    with col_name:
        st.subheader(name)
        st.caption(get_slogan(name))

    tab_total, tab_customers = st.tabs(["Total", "Per customer"])

    with tab_total:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Customers", customer_count)
        col_b.metric("Transactions", tx_count)
        col_c.caption("Total amount (click)")
        if col_c.button(money_cur(tx_total), key="amt_" + str(company_id), width="stretch"):
            st.session_state["amt_view"] = "summary"
            show_amounts(company_id, name)

    with tab_customers:
        show_customers(company_id)

# ============================================================
# 5. MAIN
# ============================================================

def toggle_all_companies():
    st.session_state["all_companies"] = not st.session_state.get("all_companies", False)

def main():
    st.set_page_config(page_title="Companies", page_icon="🏢")
    require_login()
    st.title("Companies")
    try:
        rows = cached_summary()
        term = st.text_input("Search company", key="company_search").strip().lower()
        if term:
            rows = [r for r in rows if term in r[1].lower()]   # r[1] = company name
        if not rows:
            st.info("No companies found.")
            return
        show_all = st.session_state.get("all_companies", False)
        for row in (rows if show_all else rows[:COMPANY_LIMIT]):
            show_company(*row)
        if len(rows) > COMPANY_LIMIT:
            label = "Show fewer" if show_all else "Show all " + str(len(rows)) + " companies"
            st.button(label, key="toggle_companies", on_click=toggle_all_companies)
    except Exception as e:
        show_error("Could not load companies.", e)

main()

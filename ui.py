"""
ui.py
Small Streamlit helpers shared by app.py and pages/ (not the screen itself):
login, current user, and errors that are logged but not shown in detail.
"""

import logging
import pandas as pd
import streamlit as st
from auth import check_password
from db import get_user, search_custom_tables
from form0 import COLUMN_TYPES, LINE_STYLES, TABLE_DEFAULTS
from service import get_table

log = logging.getLogger("bank_forms")

LOGIN_ON = False   # False = no login screen, you are "dev" (admin). Set True to turn the login back on.

def show_error(text, e):
    """Log the real error, show the user only a generic message."""
    log.error(text, exc_info=e)
    st.error(text + " Please try again or contact support.")
    if not LOGIN_ON:         # development mode: show the real reason too (never when login is on)
        st.caption("Details (development mode): " + type(e).__name__ + ": " + str(e)[:300])

def current_user():
    """{'name': ..., 'role': ...} of the logged-in user."""
    return st.session_state["user"]

def login_box():
    st.title("Login")
    username = st.text_input("Username").strip()
    password = st.text_input("Password", type="password")
    if st.button("Log in"):
        try:
            user = get_user(username)
        except Exception as e:
            show_error("Could not log in.", e)
            return
        if user and check_password(password, user[2]):
            st.session_state["user"] = {"name": user[1], "role": user[3]}
            st.rerun()
        else:
            st.error("Wrong username or password.")

def require_login():
    """Stop the page until someone is logged in. Returns the user."""
    if not LOGIN_ON:
        return st.session_state.setdefault("user", {"name": "dev", "role": "admin"})
    if "user" not in st.session_state:
        login_box()
        st.stop()
    user = st.session_state["user"]
    with st.sidebar:
        st.caption(user["name"] + " (" + user["role"] + ")")
        if st.button("Log out"):
            st.session_state.clear()
            st.rerun()
    return user


def table_fields(form, tag):
    """The 'Table' boxes of the form editor. Returns what the user chose:
    {"show_table", "rows" (column editor rows), "table_style"}."""
    look = {**TABLE_DEFAULTS, **(form.get("table_style") or {})}
    st.markdown("**Table** – the list of rows in the document")
    show = st.checkbox("Show the table", value=form.get("show_table", bool(form.get("columns"))),
                       key="t_show_" + tag)
    sources = {"": "The form's own query"}
    for row in search_custom_tables("", 200):
        sources[row[1]] = row[2] + " (" + row[1] + ")"
    current = form.get("source_table") or ""
    sources.setdefault(current, current + " (not found)")
    keys = list(sources)
    source = st.selectbox("Where the rows come from", keys, index=keys.index(current),
                          format_func=lambda k: sources[k], key="t_source_" + tag,
                          help="A table made on the Tables page can be the data of this form. "
                               "Then the form needs no customer: set inputs to [] in the JSON.")
    c1, c2, c3 = st.columns(3)
    header_color = c1.color_picker("Heading color", value=look["header_color"], key="t_color_" + tag)
    font_size = c2.number_input("Text size", min_value=6, max_value=14, value=int(look["font_size"]),
                                key="t_size_" + tag)
    lines = c3.selectbox("Lines", LINE_STYLES, index=LINE_STYLES.index(look["lines"]), key="t_lines_" + tag)
    zebra = c1.checkbox("Striped rows", value=bool(look["zebra"]), key="t_zebra_" + tag)
    numbers = c2.checkbox("Row numbers", value=bool(look["row_numbers"]), key="t_numbers_" + tag)
    totals = c3.text_input("Add up columns (field names, comma separated)",
                           value=", ".join(look["totals"]), key="t_totals_" + tag)
    columns_in = form.get("columns", [])
    if source and (source != current or not columns_in):     # start from the table's own columns
        try:
            columns_in = [{"field": c["name"], "label": c["label"], "type": c["type"],
                           "align": "right" if c["type"] in ("number", "money") else "left", "width": 1}
                          for c in get_table(source)["columns"]]
        except ValueError:
            columns_in = []
    start = pd.DataFrame([{"field": c.get("field", ""), "label": c.get("label", ""),
                           "type": c.get("type", "text"), "align": c.get("align", "left"),
                           "width": c.get("width", 1)} for c in columns_in],
                         columns=["field", "label", "type", "align", "width"])
    edited = st.data_editor(
        start, num_rows="dynamic", hide_index=True, width="stretch", key="t_cols_" + tag + "_" + source,
        column_config={"field": st.column_config.TextColumn("Field (column of the query)"),
                       "label": st.column_config.TextColumn("Heading in the document"),
                       "type": st.column_config.SelectboxColumn("Type", options=COLUMN_TYPES),
                       "align": st.column_config.SelectboxColumn("Align", options=["left", "right"]),
                       "width": st.column_config.NumberColumn("Width", min_value=0.1, max_value=10, step=0.5)})
    st.caption("Add a row for each column. 'Field' must be a column the form's query returns. "
               "Types: text, date, money (adds the currency), number.")
    return {"show_table": show, "rows": edited.to_dict("records"), "source_table": source or None,
            "table_style": {"header_color": header_color, "header_text_color": look["header_text_color"],
                            "font_size": int(font_size), "lines": lines, "zebra": zebra,
                            "row_numbers": numbers,
                            "totals": [x.strip() for x in totals.split(",") if x.strip()]}}


# What can be written as {{name}} in a form's text, by the inputs the form has.
FIELD_HELP = {
    "always": [("Number of table rows", "count"), ("Today's date", "current_date"),
               ("Currency (AMD)", "currency"), ("The company's slogan", "slogan"),
               ("Where the table goes (alone on its own line)", "table")],
    "customer": [("Customer number", "customer_id"), ("First name", "first_name"), ("Surname", "surname"),
                 ("Company", "company_name"), ("Phone", "phone"), ("Email", "email"),
                 ("Passport number", "passport_no"), ("Birth date", "birth_date"), ("Address", "address")],
    "dates": [("Start of the period", "date_from"), ("End of the period", "date_to")],
    "date": [("Date of the certificate", "as_of")],
    "transaction": [("Transaction id", "tx_id"), ("Transaction date", "tx_date"), ("Type", "tx_type"),
                    ("Debit or Credit", "direction"), ("Amount", "amount"), ("Description", "description")],
}

def fields_help(form):
    """A list of the {{fields}} that can be written in the text of this form (by its inputs)."""
    with st.expander("Fields you can write in the text"):
        rows = FIELD_HELP["always"] + [r for i in form.get("inputs", []) for r in FIELD_HELP.get(i, [])]
        st.markdown("| What it shows | Write this |\n|---|---|\n"
                    + "\n".join("| " + what + " | `{{" + name + "}}` |" for what, name in rows))
        st.caption("Any column of the form's query works too (for example {{balance}}) when the form has "
                   "no table. A name that nothing fills shows as \"Not filled\" and blocks issuing.")

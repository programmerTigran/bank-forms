"""
app.py
Forms page (entry point): log in, pick a form and a version, fill its inputs,
preview it, issue it (gets a number, all formats saved in the DB) and
download it. A second tab searches issued documents and re-downloads them.
Roles: clerk = make and issue documents; admin = also create/edit forms.
Run: streamlit run app.py
"""

# ============================================================
# 1. IMPORTS
# ============================================================

import json
import streamlit as st
from zoneinfo import ZoneInfo
from datetime import date, timedelta
from streamlit_searchbox import st_searchbox
from form_store import (find_forms, form_exists, load_form, save_form, list_versions,
                        build_definition, KINDS, COLUMN_OPTIONS)
from db import search_customers, search_customer_transactions, issue_document, log_audit, search_issued, get_issued_files
from documents import DATE_FORMAT, TIMEZONE, money_cur
from form0 import build_doc, generate, default_header, unfilled_placeholders, MIME, DEFAULT_FOOTER
from service import (MAX_TABLE_ROWS, columns_from_rows, fetch_rows, TX_TYPES, as_of_inputs, available_formats, customer_inputs,
                     date_range_inputs, filter_inputs, make_files, save_new_form_version,
                     transaction_inputs)
from armenian_encoding import fonitech_to_unicode
from ui import require_login, current_user, show_error, table_fields, fields_help

# ============================================================
# 2. CONSTANTS
# ============================================================


# ============================================================
# 3. INPUTS (each returns (values, params))
#    values = texts for {{placeholders}} in the template
#    params = parameters for the SQL query
# ============================================================

def customer_label(r):
    return str(r[0]) + " – " + r[1] + " " + r[2]

def search_customer_labels(term):
    term = term.strip()
    return [customer_label(r) for r in search_customers(term, limit=20 if term else 3)]

def input_customer():
    """One box: 3 customers by default, typing searches the database."""
    choice = st_searchbox(search_customer_labels, label="Customer",
                          placeholder="Type id or name",
                          default_options=search_customer_labels(""),
                          key="customer_box")
    if st.checkbox("Show all customers"):
        all_rows = search_customers("", limit=5000)
        st.dataframe([{"ID": r[0], "Name": r[1] + " " + r[2]} for r in all_rows],
                     hide_index=True, width="stretch")
    if not choice:
        st.info("Pick a customer.")
        return None
    st.caption("Selected: " + choice)
    customer_id = int(choice.split(" – ")[0])
    st.session_state["tx_customer_id"] = customer_id
    return customer_inputs(customer_id)

def input_dates():
    """Two date boxes."""
    col_from, col_to = st.columns(2)
    date_from = col_from.date_input("From", value=date.today() - timedelta(days=365),
                                    format="DD/MM/YYYY")
    date_to = col_to.date_input("To", value=date.today(), format="DD/MM/YYYY")
    if date_from > date_to:
        st.warning("'From' must be before 'To'.")
        return None
    return date_range_inputs(date_from, date_to)

def input_date():
    """One date box (certificates): {{as_of}} in text, as_of in SQL."""
    as_of = st.date_input("Date", value=date.today(), format="DD/MM/YYYY", key="as_of")
    return as_of_inputs(as_of)

def input_filters():
    """Optional transaction filters."""
    with st.expander("Filters (optional)"):
        tx_types = st.multiselect("Type", TX_TYPES)
        col_min, col_max = st.columns(2)
        min_amount = col_min.number_input("Amount from (0 = no limit)", min_value=0.0,
                                          step=10000.0, format="%.2f")
        max_amount = col_max.number_input("Amount up to (0 = no limit)", min_value=0.0,
                                          step=10000.0, format="%.2f")
        search = st.text_input("Text in description or id").strip()
    return filter_inputs(tx_types, min_amount, max_amount, search)

def input_transaction():
    """Pick one transaction of the chosen customer (the customer input must come first)."""
    customer_id = st.session_state.get("tx_customer_id")
    if customer_id is None:
        st.info("Pick a customer.")
        return None
    rows = search_customer_transactions(customer_id, "", limit=200)
    if not rows:
        st.warning("This customer has no transactions.")
        return None
    labels = {str(r[0]) + " | " + r[1].strftime(DATE_FORMAT) + " | " + r[2]
              + " | " + money_cur(r[3]): r[0] for r in rows}
    choice = st.selectbox("Transaction", list(labels), key="tx_box_" + str(customer_id))
    tx_id = labels[choice]
    return transaction_inputs(tx_id)

INPUTS = {"customer": input_customer,
          "dates": input_dates,
          "date": input_date,
          "filters": input_filters,
          "transaction": input_transaction}

# ============================================================
# 4. FORM ADMIN (admin only)
# ============================================================

@st.dialog("New form")
def new_form_dialog(name):
    kind = st.selectbox("What should it contain?", KINDS)
    title = st.text_input("Title", value=name.replace("_", " ").capitalize())
    cols = []
    extra = ""
    if kind == "Account statement":
        cols = st.multiselect("Table columns", list(COLUMN_OPTIONS),
                              default=list(COLUMN_OPTIONS))
        extra = st.text_area("Extra text (one paragraph per line. {{table}} alone on a line = table position. Also {{phone}} {{email}} {{address}})")
    if st.button("Save form"):
        if not title.strip():
            st.error("Title is required")
        elif kind == "Account statement" and not cols:
            st.error("Pick at least one column")
        else:
            save_form(name, build_definition(kind, title.strip(), extra, cols))
            log_audit(current_user()["name"], "create_form", None, name)
            st.session_state["created"] = name
            st.session_state["clear_name"] = True
            st.rerun()

def create_form_section():
    """Type a new form name; opens the popup."""
    if st.session_state.pop("clear_name", False):
        st.session_state["new_name"] = ""
    done = st.session_state.pop("created", None)
    typed = st.text_input("Or type a new form name (a-z, 0-9, _)", key="new_name").strip()
    if done:
        st.success("Form '" + done + "' created successfully.")
    if typed and not form_exists(typed):
        if typed.replace("_", "").isalnum() and typed.islower():
            if st.button("Create form '" + typed + "'"):
                new_form_dialog(typed)
        else:
            st.warning("Name: only a-z, 0-9 and _")
    elif typed:
        st.warning("A form named '" + typed + "' already exists.")

def edit_section(user, name, version, form):
    """Header boxes (top), recipe JSON (middle), footer box (bottom).
    Saving adds a new version; old versions stay."""
    msg = st.session_state.pop("saved_msg", None)
    if msg:
        st.success(msg)
    with st.expander("Edit this form"):
        tag = name + "_" + str(version)
        head = form.get("header", {})
        foot = {**DEFAULT_FOOTER, **form.get("footer", {})}

        st.markdown("**Header** – top of the document")
        left, right = st.columns(2)
        company = left.text_input("Company name ({{company_name}} = the customer's company)",
                                  value=head.get("company", "{{company_name}}"),
                                  key="h_company_" + tag)
        slogan = left.text_input("Slogan ({{slogan}} = the company's own slogan)",
                                 value=head.get("slogan", "{{slogan}}"),
                                 key="h_slogan_" + tag)
        lines = right.text_area("Right side, one line per row ({{current_date}} = today)",
                                value="\n".join(head.get("right_lines", default_header("")["right_lines"])),
                                height=120, key="h_lines_" + tag)

        tbl = table_fields(form, tag)
        fields_help(form)

        body = {k: v for k, v in form.items()
                if k not in ("header", "footer", "columns", "show_table", "table_style", "source_table")}
        text = st.text_area("Form recipe (JSON)", key="edit_" + tag, height=300,
                            value=json.dumps(body, indent=2, ensure_ascii=False))

        st.markdown("**Footer** – bottom of the document")
        signer = st.text_input("Signature text (empty = no signature line)",
                               value=foot["signer"], key="f_signer_" + tag)

        if not st.button("Save as new version"):
            return
        try:
            new_def = json.loads(text)
        except ValueError as e:
            st.error("Not valid JSON: " + str(e))
            return
        new_def["header"] = {"company": company.strip(), "slogan": slogan.strip(),
                             "right_lines": [x for x in lines.splitlines() if x.strip()]}
        new_def["footer"] = {"signer": signer.strip()}
        new_def["show_table"] = tbl["show_table"]
        new_def["table_style"] = tbl["table_style"]
        if tbl["source_table"]:
            new_def["source_table"] = tbl["source_table"]
            new_def["query"] = "custom_rows_get"         # not used while a table is the source
        try:
            columns = columns_from_rows(tbl["rows"])
            if columns or "columns" in form:
                new_def["columns"] = columns
            new_version = save_new_form_version(name, new_def, user["name"])
        except ValueError as e:
            st.error(str(e))
            return
        st.session_state["saved_msg"] = "Saved " + name + " as version " + str(new_version)
        st.rerun()

# ============================================================
# 5. MAKE DOCUMENT TAB
# ============================================================

def make_page(user):
    try:
        is_admin = user["role"] == "admin"
        if is_admin:
            create_form_section()
        name = st_searchbox(lambda t: find_forms(t.strip(), 10), label="Document",
                            placeholder="Type a form name",
                            default_options=find_forms("", 10), key="form_box")
        if st.checkbox("Show all forms"):
            all_names = find_forms("", 5000)
            st.dataframe([{"Form": n} for n in all_names], hide_index=True, width="stretch")
            st.caption(str(len(all_names)) + " forms")
        if not name:
            st.info("Pick a form.")
            return
        versions = list_versions(name)
        version = st.selectbox("Version", versions,
                               format_func=lambda v: "v" + str(v) + (" (newest)" if v == versions[0] else ""),
                               key="ver_" + name + "_" + str(len(versions)))
        form = load_form(name, version)
        if is_admin:
            edit_section(user, name, version, form)

        values = {}
        params = {}
        for input_name in form["inputs"]:
            result = INPUTS[input_name]()
            if result is None:
                return
            values.update(result[0])
            params.update(result[1])

        formats = available_formats(form)
        fmt = st.radio("Format", formats, horizontal=True)

        col_names, rows = fetch_rows(form, params)
        if len(rows) > MAX_TABLE_ROWS:
            st.warning("Too many rows (" + str(len(rows)) + ", the limit is " + str(MAX_TABLE_ROWS)
                       + "). Narrow the period or add filters.")
            return
        key = name + "|" + str(version) + "|" + str(sorted(params.items(), key=str))
        issued = st.session_state.get("issued")
        doc_no = issued["no"] if issued and issued["key"] == key else None
        doc = build_doc(form, values, col_names, rows, doc_no or "DRAFT")
        st.markdown(generate(doc, "HTML"), unsafe_allow_html=True)
        missing = unfilled_placeholders(doc)
        if missing:
            st.warning("Not filled: " + ", ".join("{{" + m + "}}" for m in missing)
                       + ". The form's query must return a column with that name. "
                       "Fix the form before issuing.")
            return
        if doc_no is None:
            if st.button("Issue document (gets a number)"):
                new_no = issue_document(
                    name, version, params,
                    lambda no: make_files(form, values, col_names, rows, no, formats),
                    user["name"])
                st.session_state["issued"] = {"key": key, "no": new_no}
                st.rerun()
        else:
            st.success("Issued: " + doc_no)
            st.download_button("Download " + fmt, generate(doc, fmt),
                               name + "_" + doc_no + "." + fmt.lower(), MIME[fmt],
                               width="stretch", on_click=log_audit,
                               args=(user["name"], "download", params.get("customer_id"),
                                     doc_no + " " + fmt))
    except ValueError as e:        # a mistake in the form: say what it is
        st.warning(str(e))
    except Exception as e:
        show_error("Could not make the document.", e)

# ============================================================
# 6. ISSUED DOCUMENTS TAB
# ============================================================

def issued_page(user):
    """Search issued documents and download the saved files."""
    term = st.text_input("Search (number, form name or customer id)",
                         key="issued_term").strip()
    rows = search_issued(term)
    if not rows:
        st.info("Nothing found.")
        return
    local = ZoneInfo(TIMEZONE)
    st.dataframe([{"Number": r[0], "Form": r[1], "Version": r[2], "Customer": r[3],
                   "Issued": r[4].astimezone(local).strftime("%d/%m/%Y %H:%M"),
                   "By": r[5]}
                  for r in rows], hide_index=True, width="stretch")
    st.caption("Showing the newest " + str(len(rows)) + ". Type to narrow down.")
    chosen = st.selectbox("Document", [r[0] for r in rows])
    files = get_issued_files(chosen)
    if not files:
        st.warning("No saved files for this number.")
        return
    buttons = st.columns(len(files))
    for col, (fmt, data) in zip(buttons, files.items()):
        col.download_button("Download " + fmt, data, chosen + "." + fmt.lower(),
                            MIME[fmt], width="stretch", key="dl_" + chosen + "_" + fmt,
                            on_click=log_audit,
                            args=(user["name"], "download", None, chosen + " " + fmt))

# ============================================================
# 7. MAIN
# ============================================================

def main():
    st.set_page_config(page_title="Forms", page_icon="📄")
    user = require_login()
    st.title("Forms")
    tab_make, tab_issued = st.tabs(["Make document", "Issued documents"])
    with tab_make:
        make_page(user)
    with tab_issued:
        try:
            issued_page(user)
        except Exception as e:
            show_error("Could not load issued documents.", e)

main()

"""
pages/tables.py
Tables page: anyone logged in can add a table of their own (any columns), add rows by hand, from a CSV
or from an RTF file (old Armenian fonts are converted), and search the list. Everything is stored in the database (custom_tables and
custom_rows), so others can use it later, also as the data of a form.
The list shows 3 tables; a button shows all. Opening a table shows its rows (paged).
"""

# ============================================================
# 1. IMPORTS AND CONSTANTS
# ============================================================

from math import ceil

import pandas as pd
import streamlit as st

from db import count_custom_rows, count_custom_tables, search_custom_tables
from documents import DATE_FORMAT
from form0 import format_cell
from rtf_import import apply_plan, decide, default_name, hits, known_names, read_rtf
from service import (CUSTOM_TYPES, add_rows, create_table, delete_table, get_table,
                     import_csv, table_rows)
from ui import require_login, show_error

TABLE_LIMIT = 3            # tables shown before "Show all"
TABLE_ALL_LIMIT = 200
ROWS_PER_PAGE = 20
PREVIEW_ROWS = 20
RTF_KINDS = {"table": "Table (many rows)", "row": "One row", "form": "Form (letter / certificate)"}

# ============================================================
# 2. SMALL HELPERS
# ============================================================

def gen():
    """A counter in the box keys: after a save the boxes get new keys, so they start empty."""
    return str(st.session_state.get("gen", 0))

def bump():
    st.session_state["gen"] = st.session_state.get("gen", 0) + 1

def done(message):
    """Remember a message, empty the boxes, redraw the page."""
    st.session_state["table_msg"] = message
    bump()
    st.rerun()

# ============================================================
# 3. NEW TABLE, LIST, ONE TABLE
# ============================================================

def show_new_table(user):
    with st.expander("New table"):
        g = gen()
        name = st.text_input("Name (a-z, 0-9, _)", key="nt_name_" + g)
        title = st.text_input("Title", key="nt_title_" + g)
        description = st.text_area("What is it for?", height=80, key="nt_desc_" + g)
        st.caption("Columns: a name (a-z, 0-9, _), the heading people see, and the type.")
        start = pd.DataFrame([{"name": "", "label": "", "type": "text"}], columns=["name", "label", "type"])
        columns = st.data_editor(
            start, num_rows="dynamic", hide_index=True, width="stretch", key="nt_cols_" + g,
            column_config={"name": st.column_config.TextColumn("Column name"),
                           "label": st.column_config.TextColumn("Heading"),
                           "type": st.column_config.SelectboxColumn("Type", options=CUSTOM_TYPES)})
        if st.button("Create table", key="nt_go_" + g):
            try:
                create_table(name, title, description, columns.to_dict("records"), user["name"])
            except ValueError as e:
                st.error(str(e))
                return
            st.session_state["open_table"] = name.strip().lower()
            done("Table created. Add rows below.")

# ============================================================
# 3b. IMPORT AN RTF FILE (old Armenian fonts become Unicode; the page decides what the file is)
# ============================================================

@st.cache_data(show_spinner=False, max_entries=5)
def read_cached(data):
    """Reading runs pandoc, so do it once per file, not on every redraw."""
    return read_rtf(data)

def unique(headings):
    """Headings for the preview: empty or repeated ones get a number."""
    seen, result = set(), []
    for i, h in enumerate(headings, start=1):
        label = h if h and h not in seen else (h or "column") + " " + str(i)
        seen.add(label)
        result.append(label)
    return result

def show_rtf_import(user):
    table = None
    if st.session_state.get("open_table"):
        try:
            table = get_table(st.session_state["open_table"])
        except ValueError:
            table = None
    with st.expander("📄 Import Word / RTF Document or Table"):
        g = gen()
        st.caption("Upload an RTF or Word document. Armenian text is automatically converted to Unicode. "
                   "The file is automatically recognized as a reusable form template or a data table."
                   + (" Currently viewing table: '" + table["name"] + "'." if table else ""))
        upload = st.file_uploader("Choose RTF file", type="rtf", key="rtf_file_" + g,
                                  help="Drag and drop any .rtf file from Word or banking software")
        if upload is None:
            return
        try:
            paragraphs, tables = read_cached(upload.getvalue())
            found = decide(paragraphs, tables, table)
        except ValueError as e:
            st.error(str(e))
            return
        options = found["options"]
        kinds = list(options)
        key = g + "_" + upload.name + "_" + str(upload.size)
        kind = st.radio("Document Type:", kinds, index=kinds.index(found["kind"]), horizontal=True,
                        format_func=RTF_KINDS.get, key="rtf_kind_" + key)
        plan = options[kind]

        if kind == "form":
            st.subheader(plan["title"] or "Untitled Document")
            if plan.get("placeholders"):
                st.markdown("**Fillable fields detected:** " + " ".join("`{{" + p + "}}`" for p in plan["placeholders"]))
            with st.container(border=True):
                for text in plan["paragraphs"][:PREVIEW_ROWS]:
                    st.write(text)
                if len(plan["paragraphs"]) > PREVIEW_ROWS:
                    st.caption("... and " + str(len(plan["paragraphs"]) - PREVIEW_ROWS) + " more paragraphs")
            adds = False
        else:
            st.dataframe(pd.DataFrame(plan["rows"][:PREVIEW_ROWS], columns=unique(plan["headings"])),
                         hide_index=True, width="stretch")
            st.caption(str(len(plan["rows"])) + " row(s), " + str(len(plan["headings"])) + " column(s)")
            adds = bool(table) and hits(plan["headings"], known_names(table)) * 2 >= len(plan["headings"])

        name = ""
        if adds:
            st.info("The rows will automatically be added to the open table '" + table["name"] + "'.")
        else:
            label = "Document Title" if kind == "form" else "Table Name"
            suggested = plan.get("title") or default_name(upload.name).replace("_", " ").title()
            user_title = st.text_input(label, value=suggested, key="rtf_name_" + key + kind,
                                       help="Give this document a recognizable name")
            name = default_name(user_title)

        save_label = "💾 Save Reusable Template" if kind == "form" else ("➕ Add Rows to Table" if adds else "💾 Create Table")
        if st.button(save_label, type="primary", key="rtf_go_" + key + kind):
            try:
                message = apply_plan(kind, plan, table, name, user["name"],
                                     upload.name, upload.getvalue())
            except ValueError as e:
                st.error(str(e))
                return
            if kind != "form" and not adds:
                st.session_state["open_table"] = name
            done(message)

def toggle_all():
    st.session_state["all_tables"] = not st.session_state.get("all_tables", False)

def show_list():
    term = st.text_input("Search tables (name, title or description)", key="table_search").strip()
    show_all = st.session_state.get("all_tables", False)
    rows = search_custom_tables(term, TABLE_ALL_LIMIT if show_all else TABLE_LIMIT)
    total = count_custom_tables(term)
    if not rows:
        st.info("No tables found." if term else "No tables yet. Create the first one above.")
        return
    for table_id, name, title, description, n_cols, n_rows, created_by, _created_at in rows:
        c_title, c_info, c_open = st.columns([4, 3, 1])
        c_title.markdown("**" + title + "**  \n`" + name + "`")
        if description:
            c_title.caption(description)
        c_info.caption(str(n_cols) + " columns, " + str(n_rows) + " rows  \nby " + created_by)
        if c_open.button("Open", key="open_" + str(table_id)):
            st.session_state["open_table"] = name
    if total > TABLE_LIMIT:
        st.button("Show fewer" if show_all else "Show all " + str(total) + " tables",
                  key="toggle_tables", on_click=toggle_all)
    if show_all and total > TABLE_ALL_LIMIT:
        st.caption("Showing the first " + str(TABLE_ALL_LIMIT) + ". Use the search for the rest.")

def show_table(user, name):
    try:
        table = get_table(name)
    except ValueError as e:
        st.warning(str(e))
        return
    columns = table["columns"]
    st.divider()
    st.subheader(table["title"])
    if table["description"]:
        st.caption(table["description"])
    tab_rows, tab_add, tab_csv, tab_info = st.tabs(["Rows", "Add rows", "Import CSV", "Info"])

    with tab_rows:
        total = count_custom_rows(table["table_id"])
        if total == 0:
            st.info("No rows yet. Use 'Add rows' or 'Import CSV'.")
        else:
            page = 1
            pages = ceil(total / ROWS_PER_PAGE)
            if pages > 1:
                page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1, key="rp_" + name)
            _names, rows = table_rows(table, ROWS_PER_PAGE, (page - 1) * ROWS_PER_PAGE)
            st.dataframe(pd.DataFrame([[format_cell(v, c["type"]) for v, c in zip(row, columns)] for row in rows],
                                      columns=[c["label"] for c in columns]),
                         hide_index=True, width="stretch")
            st.caption(str(total) + " rows")

    with tab_add:
        g = gen()
        st.caption("Numbers like 1500.50, dates like 2026-11-20 or 20/11/2026. Empty rows are skipped.")
        start = pd.DataFrame([{c["name"]: "" for c in columns}], columns=[c["name"] for c in columns])
        edited = st.data_editor(
            start, num_rows="dynamic", hide_index=True, width="stretch", key="add_" + name + "_" + g,
            column_config={c["name"]: st.column_config.TextColumn(c["label"] + " (" + c["type"] + ")")
                           for c in columns})
        if st.button("Add rows", key="add_go_" + name + "_" + g):
            try:
                n = add_rows(table, edited.to_dict("records"), user["name"])
            except ValueError as e:
                st.error(str(e))
            else:
                done(str(n) + " row(s) added.")

    with tab_csv:
        g = gen()
        st.caption("The first line must have the column names: " + ", ".join(c["name"] for c in columns))
        upload = st.file_uploader("CSV file", type="csv", key="csv_" + name + "_" + g)
        if upload is not None and st.button("Import", key="csv_go_" + name + "_" + g):
            try:
                n = import_csv(table, upload.getvalue().decode("utf-8-sig"), user["name"])
            except UnicodeDecodeError:
                st.error("Save the CSV as UTF-8 and try again.")
            except ValueError as e:
                st.error(str(e))
            else:
                done(str(n) + " row(s) imported.")

    with tab_info:
        st.dataframe(pd.DataFrame(columns), hide_index=True, width="stretch")
        st.caption("Created by " + table["created_by"] + " on " + table["created_at"].strftime(DATE_FORMAT))
        st.caption("To use it in a form: Forms page, Edit this form, Table, 'Where the rows come from'.")
        if user["role"] == "admin" and st.checkbox("Yes, delete this table and all its rows", key="del_ok_" + name):
            if st.button("Delete table", key="del_" + name):
                try:
                    delete_table(table, user["name"])
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.session_state.pop("open_table", None)
                    done("Table deleted.")

# ============================================================
# 4. MAIN
# ============================================================

def main():
    st.set_page_config(page_title="Tables", page_icon="🗂️")
    user = require_login()
    st.title("Tables")
    message = st.session_state.pop("table_msg", None)
    if message:
        st.success(message)
    try:
        show_new_table(user)
        show_rtf_import(user)
        show_list()
        if st.session_state.get("open_table"):
            show_table(user, st.session_state["open_table"])
    except Exception as e:
        show_error("Could not load the tables.", e)

main()

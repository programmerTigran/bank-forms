"""
service.py
The app's logic without any screen. Raw input (ids, dates, filters) becomes
document values + SQL params; documents are built and issued; forms are saved.
Used by api.py (the REST API) and app.py (the Streamlit screen).
"""

# ============================================================
# 1. IMPORTS AND CONSTANTS
# ============================================================

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from db import (_like, add_custom_rows, create_custom_table, delete_custom_table, get_custom_rows,
                forms_using_table, get_custom_table, get_customer, issue_document, log_audit, run_query,
                transaction_belongs)
from documents import DATE_FORMAT, DEFAULT_CURRENCY, money_cur
from form0 import (COLUMN_TYPES, FORMATS, build_doc, format_value, generate, table_style,
                   unfilled_placeholders)
from form_store import list_versions, load_form, save_form

SQL_DIR = Path(__file__).parent / "sql" / "queries"     # only files in here can be a form's query
MAX_TABLE_ROWS = 5000                                    # bigger documents: narrow the period or filters
NAME_RE = re.compile(r"[a-z0-9_]+")
TX_TYPES = ["deposit", "withdrawal", "transfer", "payment"]
CUSTOM_TYPES = ["text", "number", "money", "date"]
MAX_CUSTOM_COLUMNS = 40
MAX_IMPORT_ROWS = 5000

# ============================================================
# 2. INPUTS: raw values -> (values for {{placeholders}}, params for SQL)
# ============================================================

def to_date(value):
    """'2026-11-18' (or a date) -> date."""
    return value if isinstance(value, date) else date.fromisoformat(str(value))

def amount_or_none(value):
    """None, 0 or '' -> None (no limit); anything else -> an exact Decimal."""
    if value in (None, "", 0):
        return None
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Amount must be a number: " + str(value))
    return amount if amount > 0 else None

def customer_inputs(customer_id):
    row = get_customer(customer_id)
    if row is None:
        raise ValueError("Customer " + str(customer_id) + " not found")
    first_name, surname, company_name = row
    values = {"customer_id": customer_id, "first_name": first_name, "surname": surname,
              "company_name": company_name or "", "currency": DEFAULT_CURRENCY}
    cols, found = run_query("customer_full", {"customer_id": customer_id})
    if found:
        for col, val in zip(cols, found[0]):
            values.setdefault(col, format_value(val))
    return values, {"customer_id": customer_id}

def date_range_inputs(date_from, date_to):
    if date_from > date_to:
        raise ValueError("'From' must be before 'To'.")
    values = {"date_from": date_from.strftime(DATE_FORMAT),
              "date_to": date_to.strftime(DATE_FORMAT)}
    return values, {"date_from": date_from, "date_to": date_to}

def as_of_inputs(as_of):
    return {"as_of": as_of.strftime(DATE_FORMAT)}, {"as_of": as_of}

def filter_inputs(tx_types=None, min_amount=None, max_amount=None, search=""):
    tx_types = list(tx_types or [])
    bad = [t for t in tx_types if t not in TX_TYPES]
    if bad:
        raise ValueError("Unknown type: " + ", ".join(bad))
    min_amount, max_amount = amount_or_none(min_amount), amount_or_none(max_amount)
    search = (search or "").strip()
    parts = []
    if tx_types:
        parts.append("type " + ", ".join(tx_types))
    if min_amount is not None:
        parts.append("amount from " + money_cur(min_amount))
    if max_amount is not None:
        parts.append("amount up to " + money_cur(max_amount))
    if search:
        parts.append("text \"" + search + "\"")
    params = {"tx_types": tx_types or None, "min_amount": min_amount,
              "max_amount": max_amount, "pattern": _like(search) if search else None}
    return {"filter_line": "Filters: " + "; ".join(parts) if parts else ""}, params

def transaction_inputs(tx_id, customer_id=None):
    """With a customer id given, the transaction must belong to that customer."""
    tx_id = str(tx_id)
    if customer_id is not None and not transaction_belongs(tx_id, int(customer_id)):
        raise ValueError("Transaction " + tx_id + " does not belong to this customer")
    return {"tx_id": tx_id}, {"tx_id": tx_id}

INPUT_BUILDERS = {
    "customer": lambda d: customer_inputs(int(d["customer_id"])),
    "dates": lambda d: date_range_inputs(to_date(d["date_from"]), to_date(d["date_to"])),
    "date": lambda d: as_of_inputs(to_date(d["as_of"])),
    "filters": lambda d: filter_inputs(d.get("tx_types"), d.get("min_amount"),
                                       d.get("max_amount"), d.get("search", "")),
    "transaction": lambda d: transaction_inputs(d["tx_id"], d.get("customer_id")),
}

def resolve_inputs(form, data):
    """Run every input the form asks for, on a plain dict (what the API receives)."""
    values, params = {}, {}
    for name in form["inputs"]:
        try:
            v, p = INPUT_BUILDERS[name](data)
        except KeyError as e:
            raise ValueError("Missing input: " + str(e.args[0]))
        values.update(v)
        params.update(p)
    return values, params

# ============================================================
# 3. DOCUMENTS
# ============================================================

def available_formats(form):
    """CSV only makes sense for forms with a table."""
    has_table = form.get("columns") and form.get("show_table", True)
    return FORMATS if has_table else [f for f in FORMATS if f != "CSV"]

def make_files(form, values, col_names, rows, doc_no, formats):
    """All files of one issued document, with its real number."""
    doc = build_doc(form, values, col_names, rows, doc_no)
    return {f: generate(doc, f) for f in formats}

def issue(form_name, version, data, username):
    """Resolve inputs, run the form's query, issue the document. Returns (doc_no, formats)."""
    versions = list_versions(form_name)
    if not versions:
        raise ValueError("Form " + form_name + " not found")
    if version is None:
        version = versions[0]
    elif version not in versions:
        raise ValueError("Form " + form_name + " has no version " + str(version))
    form = load_form(form_name, version)
    values, params = resolve_inputs(form, data)
    col_names, rows = fetch_rows(form, params)
    if len(rows) > MAX_TABLE_ROWS:
        raise ValueError("Too many rows (" + str(len(rows)) + ", the limit is "
                         + str(MAX_TABLE_ROWS) + "). Narrow the period or add filters.")
    missing = unfilled_placeholders(build_doc(form, values, col_names, rows))
    if missing:
        raise ValueError("Not filled: " + ", ".join("{{" + m + "}}" for m in missing)
                         + ". The form's query must return a column with that name.")
    formats = available_formats(form)
    doc_no = issue_document(form_name, version, params,
                            lambda no: make_files(form, values, col_names, rows, no, formats),
                            username)
    return doc_no, formats

# ============================================================
# 4. FORMS
# ============================================================

def _clean(value):
    """A pandas empty cell (NaN) or None -> None."""
    return None if value is None or (isinstance(value, float) and value != value) else value

def columns_from_rows(rows):
    """Rows of the column editor [{field, label, type, align, width}] -> the recipe's "columns".
    Rows without a field are dropped; missing parts get defaults."""
    columns = []
    for row in rows:
        field = str(_clean(row.get("field")) or "").strip()
        if not field:
            continue
        kind = _clean(row.get("type")) or "text"
        align = _clean(row.get("align")) or "left"
        if kind not in COLUMN_TYPES:
            raise ValueError("Column type must be one of: " + ", ".join(COLUMN_TYPES))
        if align not in ("left", "right"):
            raise ValueError("Column align must be left or right")
        columns.append({"field": field, "label": str(_clean(row.get("label")) or field).strip(),
                        "type": kind, "align": align, "width": float(_clean(row.get("width")) or 1)})
    return columns

def validate_definition(definition):
    """Raise ValueError if a form recipe is not usable."""
    missing = [k for k in ("title", "inputs", "query") if k not in definition]
    if missing:
        raise ValueError("Missing: " + ", ".join(missing))
    bad = [i for i in definition["inputs"] if i not in INPUT_BUILDERS]
    if bad:
        raise ValueError("Unknown input: " + ", ".join(bad))
    for c in definition.get("columns", []):
        if not isinstance(c, dict) or not c.get("field") or not c.get("label"):
            raise ValueError("Every column needs a field and a label")
        if c.get("type", "text") not in COLUMN_TYPES or c.get("align", "left") not in ("left", "right"):
            raise ValueError("Column '" + str(c["field"]) + "': type must be one of "
                             + ", ".join(COLUMN_TYPES) + " and align left or right")
    table_style(definition)
    source = definition.get("source_table")
    if source and get_custom_table(str(source)) is None:
        raise ValueError("No table named '" + str(source) + "' (see the Tables page)")
    query = str(definition["query"])
    # only plain names: no "../" tricks to reach other files
    if not NAME_RE.fullmatch(query) or not (SQL_DIR / (query + ".sql")).exists():
        raise ValueError("No sql file for query '" + query + "'")

def save_new_form_version(name, definition, username):
    """Validate, save as the next version, write the audit row. Returns the version."""
    if not NAME_RE.fullmatch(name):
        raise ValueError("Form name: only a-z, 0-9 and _")
    validate_definition(definition)
    version = save_form(name, definition)
    log_audit(username, "edit_form", None, name + " v" + str(version))
    return version


# ============================================================
# 5. CUSTOM TABLES (made by users on the Tables page, stored in the database)
# ============================================================

def custom_columns(rows):
    """Rows of the column editor [{name, label, type}] -> clean columns. ValueError if wrong."""
    columns, seen = [], set()
    for row in rows:
        name = str(_clean(row.get("name")) or "").strip().lower()
        if not name:
            continue
        if not NAME_RE.fullmatch(name):
            raise ValueError("Column name '" + name + "': only a-z, 0-9 and _")
        if name in seen:
            raise ValueError("Column name '" + name + "' is used twice")
        kind = _clean(row.get("type")) or "text"
        if kind not in CUSTOM_TYPES:
            raise ValueError("Column type must be one of: " + ", ".join(CUSTOM_TYPES))
        columns.append({"name": name, "label": str(_clean(row.get("label")) or name).strip(), "type": kind})
        seen.add(name)
    if not columns:
        raise ValueError("Add at least one column")
    if len(columns) > MAX_CUSTOM_COLUMNS:
        raise ValueError("At most " + str(MAX_CUSTOM_COLUMNS) + " columns")
    return columns

def create_table(name, title, description, column_rows, username):
    """Check and save a new table. Returns its table_id."""
    name = name.strip().lower()
    if not NAME_RE.fullmatch(name):
        raise ValueError("Table name: only a-z, 0-9 and _")
    table_id = create_custom_table(name, title.strip() or name, description.strip(),
                                   custom_columns(column_rows), username)
    log_audit(username, "create_table", None, name)
    return table_id

def get_table(name):
    """One table definition as a dict. ValueError if there is none."""
    row = get_custom_table(name)
    if row is None:
        raise ValueError("No table named '" + str(name) + "'")
    return {"table_id": row[0], "name": row[1], "title": row[2], "description": row[3],
            "columns": row[4], "created_by": row[5], "created_at": row[6]}

def cell_value(value, kind):
    """One cell -> what is stored (text). Empty -> None. ValueError if it does not fit the type."""
    value = _clean(value)
    if value is None or str(value).strip() == "":
        return None
    if kind in ("number", "money"):
        try:
            number = Decimal(str(value).strip().replace(",", ""))
        except InvalidOperation:
            raise ValueError("'" + str(value) + "' is not a number")
        if not number.is_finite() or abs(number) >= Decimal("1e18"):
            raise ValueError("'" + str(value) + "' is not a usable number")
        return str(number)
    if kind == "date":
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(value).strip(), pattern).date().isoformat()
            except ValueError:
                pass
        raise ValueError("'" + str(value) + "' is not a date (use 2026-11-20 or 20/11/2026)")
    return str(value).strip()[:2000]

def clean_rows(columns, rows):
    """Rows as dicts {column name: value} -> rows ready to store. Empty rows are dropped."""
    result = []
    for n, row in enumerate(rows, start=1):
        clean = {}
        for c in columns:
            try:
                clean[c["name"]] = cell_value(row.get(c["name"]), c["type"])
            except ValueError as e:
                raise ValueError("Row " + str(n) + ", column " + c["name"] + ": " + str(e))
        if any(v is not None for v in clean.values()):
            result.append(clean)
    return result

def add_rows(table, rows, username):
    """Check and save rows (all or nothing). Returns how many were saved."""
    clean = clean_rows(table["columns"], rows)
    if not clean:
        raise ValueError("Nothing to add")
    add_custom_rows(table["table_id"], clean, username)
    log_audit(username, "add_rows", None, table["name"] + " +" + str(len(clean)))
    return len(clean)

def import_csv(table, text, username):
    """Rows from CSV text; the first line must contain the column names of the table."""
    reader = csv.DictReader(io.StringIO(text))
    names = [c["name"] for c in table["columns"]]
    missing = [n for n in names if n not in (reader.fieldnames or [])]
    if missing:
        raise ValueError("The first line of the CSV must have these column names: "
                         + ", ".join(names) + " (missing: " + ", ".join(missing) + ")")
    rows = []
    for row in reader:
        rows.append(row)
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError("More than " + str(MAX_IMPORT_ROWS) + " rows: split the file")
    return add_rows(table, rows, username)

def delete_table(table, username):
    used = forms_using_table(table["name"])
    if used:
        raise ValueError("Cannot delete: these forms use it: " + ", ".join(used))
    delete_custom_table(table["table_id"])
    log_audit(username, "delete_table", None, table["name"])

def typed(value, kind):
    """A stored value -> a Python value (Decimal, date, text)."""
    if value is None:
        return None
    if kind in ("number", "money"):
        return Decimal(value)
    if kind == "date":
        return date.fromisoformat(value)
    return value

def table_rows(table, limit, offset=0):
    """(column names, rows) of a custom table, with real numbers and dates."""
    columns = table["columns"]
    raw = get_custom_rows(table["table_id"], limit, offset)
    return ([c["name"] for c in columns],
            [tuple(typed(data.get(c["name"]), c["type"]) for c in columns) for _id, data in raw])

def fetch_rows(form, params):
    """The rows of a form: from its custom table ("source_table") or from its query."""
    if form.get("source_table"):
        return table_rows(get_table(form["source_table"]), MAX_TABLE_ROWS + 1)
    return run_query(form["query"], params)

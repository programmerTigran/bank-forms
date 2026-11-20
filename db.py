"""
db.py
Database layer for bank-forms. SQL lives in sql/*.sql (loaded by name
through queries.py); this file only runs the queries.
Used by app.py, ui.py, pages/ and scripts/.
"""

# ============================================================
# 1. IMPORTS
# ============================================================

import atexit
import json
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

from queries import load

load_dotenv()

# ============================================================
# 2. CONNECTIONS AND HELPERS
# ============================================================

# Debit/Credit rule: deposit = Credit, everything else = Debit.
DIRECTION_SQL = "CASE WHEN t.tx_type = 'deposit' THEN 'Credit' ELSE 'Debit' END"

_pool = None

def new_connection():
    """A plain connection (SQLAlchemy has its own pool and uses this)."""
    return psycopg.connect()

def close_pool():
    """Close the connection pool cleanly (also runs by itself when the program ends)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None

atexit.register(close_pool)

def get_connection():
    """Borrow a connection from the pool: `with get_connection() as conn`.
    Commits at the end of the block, rolls back on an error."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool("", min_size=1, max_size=5, open=True,
                               kwargs={"options": "-c statement_timeout=30000"})   # a query may run 30 s at most
    return _pool.connection()

def _fetchall(sql, params=None):
    with get_connection() as conn:
        return conn.execute(sql, params or {}).fetchall()

def _fetchone(sql, params=None):
    with get_connection() as conn:
        return conn.execute(sql, params or {}).fetchone()

def _like(text):
    """Return a %text% pattern for ILIKE."""
    return "%" + text + "%"

def run_query(name, params):
    """Run sql/<name>.sql. Returns (column_names, rows)."""
    with get_connection() as conn:
        cur = conn.execute(load(name), params)
        return [d.name for d in cur.description], cur.fetchall()

# ============================================================
# 3. USERS AND AUDIT
# ============================================================

def get_user(username):
    """Return (user_id, username, password_hash, role) or None."""
    return _fetchone(load("user_get"), {"username": username})

def add_user(username, password_hash, role):
    with get_connection() as conn:
        conn.execute(load("user_insert"), {"username": username,
                                           "password_hash": password_hash, "role": role})

def log_audit(username, action, customer_id=None, detail=""):
    """Write one audit row: who did what, to which customer."""
    with get_connection() as conn:
        conn.execute(load("audit_insert"), {"username": username, "action": action,
                                            "customer_id": customer_id, "detail": detail})

# ============================================================
# 4. CUSTOMERS
# ============================================================

def get_customer(customer_id):
    """Return (first_name, surname, company_name) for one customer."""
    return _fetchone(load("customer_get"), {"customer_id": customer_id})

def search_customers(term="", limit=3):
    """Return (customer_id, first_name, surname), matched by id or name."""
    term = term.strip()
    return _fetchall(load("customers_search"),
                     {"term": term, "pattern": _like(term), "limit": limit})

# ============================================================
# 5. COMPANIES
# ============================================================

def get_company_logo(company_name):
    """Return the logo image (bytes) of a company, or b"" if none."""
    row = _fetchone(load("company_logo_data"), {"name": company_name})
    return bytes(row[0]) if row and row[0] else b""

def get_company_logo_by_id(company_id):
    """Same, found by company id (used by the Companies page)."""
    row = _fetchone(load("company_logo_by_id"), {"company_id": company_id})
    return bytes(row[0]) if row and row[0] else b""

def set_company_logo(company_id, data):
    """Save a logo image. Only PNG or JPEG, at most 2 MB."""
    if not (data[:4] == b"\x89PNG" or data[:3] == b"\xff\xd8\xff"):
        raise ValueError("Logo must be a PNG or JPEG image")
    if len(data) > 2_000_000:
        raise ValueError("Logo is bigger than 2 MB")
    with get_connection() as conn:
        conn.execute(load("company_logo_set"), {"data": data, "company_id": company_id})

def get_company_summary():
    """Return (company_id, name, logo, customer_count, tx_count, tx_total) per company."""
    return _fetchall(load("company_summary"))

def get_company_customers(company_id, term="", limit=3, offset=0):
    """Return one page of (customer_id, first_name, surname, tx_count, tx_total)."""
    term = term.strip()
    return _fetchall(load("company_customers"),
                     {"company_id": company_id, "term": term, "pattern": _like(term),
                      "limit": limit, "offset": offset})

def get_company_customer_count(company_id, term=""):
    """Return how many customers of one company match the search."""
    term = term.strip()
    return _fetchone(load("company_customer_count"),
                     {"company_id": company_id, "term": term, "pattern": _like(term)})[0]

def get_company_direction_totals(company_id):
    """Return (direction, tx_count, total) for one company: Debit and Credit."""
    return _fetchall(load("company_direction_totals", direction=DIRECTION_SQL),
                     {"company_id": company_id})

def get_company_type_totals(company_id, direction):
    """Return (tx_type, tx_count, total) for one company, only Debit or only Credit."""
    return _fetchall(load("company_type_totals", direction=DIRECTION_SQL),
                     {"company_id": company_id, "direction": direction})

# ============================================================
# 6. TRANSACTIONS
# ============================================================

def search_customer_transactions(customer_id, search="", limit=8, first_only=False):
    """Return (tx_id, tx_date, tx_type, amount, description), newest first.
    first_only=True keeps only the ids ending in .1 (first of each type)."""
    return _fetchall(load("tx_search"),
                     {"customer_id": customer_id, "pattern": _like(search),
                      "first_only": first_only, "limit": limit})

def count_customer_transactions(customer_id, search="", first_only=False):
    """Return how many transactions of one customer match the search."""
    return _fetchone(load("tx_count"),
                     {"customer_id": customer_id, "pattern": _like(search),
                      "first_only": first_only})[0]

def get_transactions_between(customer_id, date_from, date_to, tx_types=None,
                             min_amount=None, max_amount=None, search=""):
    """Return (tx_date, tx_type, amount, description) between two dates, oldest first."""
    search = search.strip()
    return _fetchall(load("tx_between"),
                     {"customer_id": customer_id, "date_from": date_from, "date_to": date_to,
                      "tx_types": list(tx_types) if tx_types else None,
                      "min_amount": min_amount, "max_amount": max_amount,
                      "pattern": _like(search) if search else None})

# ============================================================
# 7. ISSUED DOCUMENTS
# ============================================================

def issue_document(form_name, form_version, params, make_files, username):
    """Number + files + log + audit in ONE transaction: if anything fails,
    nothing is saved and the number is given back (no gaps).
    make_files(doc_no) must return {"PDF": bytes, ...}."""
    with get_connection() as conn:
        doc_no = conn.execute(load("doc_no_next")).fetchone()[0]
        files = make_files(doc_no)
        conn.execute(load("doc_log_insert"),
                     {"doc_no": doc_no, "form_name": form_name, "form_version": form_version,
                      "customer_id": params.get("customer_id"),
                      "params": json.dumps(params, default=str), "issued_by": username})
        for fmt, data in files.items():
            conn.execute(load("doc_file_insert"), {"doc_no": doc_no, "fmt": fmt, "data": data})
        conn.execute(load("audit_insert"),
                     {"username": username, "action": "issue", "customer_id": params.get("customer_id"),
                      "detail": doc_no})
    return doc_no

def search_issued(term="", limit=50):
    """Return (doc_no, form_name, form_version, customer_id, created_at, issued_by), newest first."""
    term = term.strip()
    return _fetchall(load("issued_search"),
                     {"term": term, "pattern": _like(term), "limit": limit})

def get_issued_files(doc_no):
    """Return {"PDF": bytes, ...} for one document (empty if none saved)."""
    rows = _fetchall(load("doc_files_get"), {"doc_no": doc_no})
    return {r[0]: bytes(r[1]) for r in rows}

# ============================================================
# 8. FORMS AND TRANSACTION CHECKS
# ============================================================

def transaction_belongs(tx_id, customer_id):
    """True if this transaction belongs to this customer."""
    return _fetchone(load("tx_belongs"), {"tx_id": tx_id, "customer_id": customer_id}) is not None

def create_form_version(name, definition):
    """Add a new version of a form through the database function. Returns the version number."""
    try:
        return _fetchone(load("form_create"),
                         {"name": name, "definition": json.dumps(definition, ensure_ascii=False)})[0]
    except psycopg.errors.RaiseException as e:   # the function's own messages
        raise ValueError(e.diag.message_primary)

# ============================================================
# 9. CUSTOM TABLES (tables that users create on the Tables page)
# ============================================================

def create_custom_table(name, title, description, columns, username):
    """Save a new table definition. Returns its table_id. ValueError if the name is taken."""
    try:
        return _fetchone(load("custom_table_create"),
                         {"name": name, "title": title, "description": description,
                          "columns": json.dumps(columns, ensure_ascii=False),
                          "username": username})[0]
    except psycopg.errors.UniqueViolation:
        raise ValueError("A table named '" + name + "' already exists")

def search_custom_tables(term="", limit=3):
    """Return (table_id, name, title, description, column_count, row_count, created_by, created_at)."""
    term = term.strip()
    return _fetchall(load("custom_tables_search"),
                     {"term": term, "pattern": _like(term), "limit": limit})

def count_custom_tables(term=""):
    term = term.strip()
    return _fetchone(load("custom_tables_count"), {"term": term, "pattern": _like(term)})[0]

def get_custom_table(name):
    """Return (table_id, name, title, description, columns, created_by, created_at) or None."""
    return _fetchone(load("custom_table_get"), {"name": name})

def add_custom_rows(table_id, rows, username):
    """Save rows (dicts, already checked) in one transaction."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(load("custom_rows_add"),
                            [{"table_id": table_id, "data": json.dumps(r, ensure_ascii=False),
                              "username": username} for r in rows])

def get_custom_rows(table_id, limit=20, offset=0):
    """Return (row_id, data dict), oldest first."""
    return _fetchall(load("custom_rows_get"),
                     {"table_id": table_id, "limit": limit, "offset": offset})

def count_custom_rows(table_id):
    return _fetchone(load("custom_rows_count"), {"table_id": table_id})[0]

def forms_using_table(name):
    """Names of the forms that use this custom table as their data."""
    return [row[0] for row in _fetchall(load("custom_table_forms"), {"name": name})]

def delete_custom_table(table_id):
    """Delete a table and (by the database link) all its rows."""
    with get_connection() as conn:
        conn.execute(load("custom_table_delete"), {"table_id": table_id})

"""
db.py
Database layer for bank-forms. SQL lives in sql/*.sql (loaded by name
through queries.py); this file only runs the queries.
Used by app.py, documents.py, pages/ and scripts/.
"""

import json
import psycopg
from dotenv import load_dotenv

from queries import load

load_dotenv()

DIRECTION_SQL = "CASE WHEN t.tx_type = 'deposit' THEN 'Credit' ELSE 'Debit' END"


def get_connection():
    """Open a connection to bank_forms (settings come from PG* env vars)."""
    return psycopg.connect()


def _fetchall(sql, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            return cur.fetchall()


def _fetchone(sql, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            return cur.fetchone()


def _like(text):
    """Return a %text% pattern for ILIKE."""
    return "%" + text + "%"


def get_customer_ids():
    """Return all customer ids ordered by id."""
    rows = _fetchall("SELECT customer_id FROM customers ORDER BY customer_id")
    return [row[0] for row in rows]


def get_customer(customer_id):
    """Return (first_name, surname, company_name) for one customer."""
    return _fetchone(load("customer_get"), {"customer_id": customer_id})


def search_customers(term="", limit=3):
    """Return (customer_id, first_name, surname), matched by id or name."""
    term = term.strip()
    return _fetchall(
        load("customers_search"),
        {"term": term, "pattern": _like(term), "limit": limit},
    )


def get_template_names():
    """Return all template names for the dropdown."""
    return [row[0] for row in _fetchall(load("template_names"))]


def load_template(name):
    """Return the newest version of a template as a dict."""
    row = _fetchone(load("template_load"), {"name": name})
    if row is None:
        raise ValueError("Template " + name + " not found")
    definition = row[0]
    if isinstance(definition, str):
        definition = json.loads(definition)
    return definition


def get_company_logo(company_name):
    """Return the logo file path of a company, or "" if none."""
    row = _fetchone(load("company_logo"), {"name": company_name})
    if row is None or row[0] is None:
        return ""
    return row[0]


def get_company_summary():
    """Return (company_id, name, logo, customer_count, tx_count, tx_total) per company."""
    return _fetchall(load("company_summary"))


def get_company_customers(company_id, term="", limit=3, offset=0):
    """Return one page of (customer_id, first_name, surname, tx_count, tx_total)."""
    term = term.strip()
    return _fetchall(
        load("company_customers"),
        {
            "company_id": company_id,
            "term": term,
            "pattern": _like(term),
            "limit": limit,
            "offset": offset,
        },
    )


def get_company_customer_count(company_id, term=""):
    """Return how many customers of one company match the search."""
    term = term.strip()
    return _fetchone(
        load("company_customer_count"),
        {"company_id": company_id, "term": term, "pattern": _like(term)},
    )[0]


def get_company_direction_totals(company_id):
    """Return (direction, tx_count, total) for one company: Debit and Credit."""
    return _fetchall(load("company_direction_totals", direction=DIRECTION_SQL), {"company_id": company_id})


def get_company_type_totals(company_id, direction):
    """Return (tx_type, tx_count, total) for one company, only Debit or only Credit."""
    return _fetchall(load("company_type_totals", direction=DIRECTION_SQL), {"company_id": company_id, "direction": direction})


def search_customer_transactions(customer_id, search="", limit=8, first_only=False):
    """Return (tx_id, tx_date, tx_type, amount, description), newest first.
    first_only=True keeps only the ids ending in .1 (first of each type)."""
    return _fetchall(
        load("tx_search"),
        {"customer_id": customer_id, "pattern": _like(search), "first_only": first_only, "limit": limit},
    )


def count_customer_transactions(customer_id, search="", first_only=False):
    """Return how many transactions of one customer match the search."""
    return _fetchone(
        load("tx_count"),
        {"customer_id": customer_id, "pattern": _like(search), "first_only": first_only},
    )[0]


def get_transactions_between(customer_id, date_from, date_to, tx_types=None, min_amount=None, max_amount=None, search=""):
    """Return (tx_date, tx_type, amount, description) between two dates, oldest first.
    Optional filters: tx_types (list), min_amount, max_amount, search (description or id)."""
    search = search.strip()
    return _fetchall(
        load("tx_between"),
        {
            "customer_id": customer_id,
            "date_from": date_from,
            "date_to": date_to,
            "tx_types": list(tx_types) if tx_types else None,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "pattern": _like(search) if search else None,
        },
    )

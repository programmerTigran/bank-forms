"""Database access layer. SQL statements live in sql/*.sql."""

import json

import psycopg
from dotenv import load_dotenv

from queries import load

load_dotenv()

DIRECTION_SQL = "CASE WHEN t.tx_type = 'deposit' THEN 'Credit' ELSE 'Debit' END"


def get_connection():
    """Open a PostgreSQL connection using PG* environment variables."""
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
    return "%" + text + "%"


def get_customer_ids():
    """Return all customer ids in database order."""
    return [row[0] for row in _fetchall(load("customer_ids"))]


def get_customer(customer_id):
    """Return (first_name, surname, company_name) for one customer."""
    return _fetchone(load("customer_get"), {"customer_id": customer_id})


def search_customers(term="", limit=3):
    term = term.strip()
    return _fetchall(load("customers_search"), {"term": term, "pattern": _like(term), "limit": limit})


def get_template_names():
    return [row[0] for row in _fetchall(load("template_names"))]


def load_template(name):
    row = _fetchone(load("template_load"), {"name": name})
    if row is None:
        raise ValueError("Template " + name + " not found")
    definition = row[0]
    return json.loads(definition) if isinstance(definition, str) else definition


def get_company_logo(company_name):
    row = _fetchone(load("company_logo"), {"name": company_name})
    return "" if row is None or row[0] is None else row[0]


def get_company_summary():
    return _fetchall(load("company_summary"))


def get_company_customers(company_id, term="", limit=3, offset=0):
    term = term.strip()
    return _fetchall(load("company_customers"), {
        "company_id": company_id, "term": term, "pattern": _like(term),
        "limit": limit, "offset": offset,
    })


def get_company_customer_count(company_id, term=""):
    term = term.strip()
    row = _fetchone(load("company_customer_count"), {
        "company_id": company_id, "term": term, "pattern": _like(term),
    })
    return row[0]


def get_company_direction_totals(company_id):
    return _fetchall(load("company_direction_totals", direction=DIRECTION_SQL), {"company_id": company_id})


def get_company_type_totals(company_id, direction):
    return _fetchall(load("company_type_totals", direction=DIRECTION_SQL), {
        "company_id": company_id, "direction": direction,
    })


def search_customer_transactions(customer_id, search="", limit=8, first_only=False):
    return _fetchall(load("tx_search"), {
        "customer_id": customer_id, "pattern": _like(search),
        "first_only": first_only, "limit": limit,
    })


def count_customer_transactions(customer_id, search="", first_only=False):
    return _fetchone(load("tx_count"), {
        "customer_id": customer_id, "pattern": _like(search), "first_only": first_only,
    })[0]


def get_transactions_between(customer_id, date_from, date_to, tx_types=None,
                             min_amount=None, max_amount=None, search=""):
    search = search.strip()
    return _fetchall(load("tx_between"), {
        "customer_id": customer_id, "date_from": date_from, "date_to": date_to,
        "tx_types": list(tx_types) if tx_types else None,
        "min_amount": min_amount, "max_amount": max_amount,
        "pattern": _like(search) if search else None,
    })

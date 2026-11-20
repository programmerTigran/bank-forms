"""
scripts/seed_demo.py
Replaces customers with 24 fixed ones (6 per company) and recreates transactions
(20 per customer: 10 in each of the last 2 months). Same result on every run.
Transaction id = type letter + customer id + "." + running number of that type
(P1.1 = first payment of customer 1).
Run from the project root (venv active), after python scripts/migrate.py:
    python -m scripts.seed_demo
"""

import random
from datetime import date, timedelta

from db import get_connection

SEED = 42
END_DATE = date(2026, 11, 13)      # last day of the transaction period
MONTHS, TX_PER_MONTH, PER_COMPANY = 2, 10, 6
COMPANIES = ["ardshin", "ameria", "adidas", "puma"]   # name prefixes, in order

CUSTOMERS = [
    ("Աննա", "Հակոբյան"), ("Արամ", "Սարգսյան"), ("Մարիամ", "Գրիգորյան"),
    ("Դավիթ", "Մելքոնյան"), ("Նարե", "Ավետիսյան"), ("Լուսինե", "Ղազարյան"),
    ("Գոռ", "Մկրտչյան"), ("Սոֆյա", "Հարությունյան"), ("Հասմիկ", "Պետրոսյան"),
    ("Վահե", "Բաղդասարյան"), ("Անահիտ", "Ավագյան"), ("Արման", "Խաչատրյան"),
    ("Կարինե", "Ասատրյան"), ("Հայկ", "Վարդանյան"), ("Գայանե", "Գևորգյան"),
    ("Սարգիս", "Առաքելյան"), ("Լիլիթ", "Դավթյան"), ("Արթուր", "Հովհաննիսյան"),
    ("Մարինե", "Սիմոնյան"), ("Նարեկ", "Մարտիրոսյան"), ("Տաթև", "Անտոնյան"),
    ("Էդգար", "Ներսիսյան"), ("Գոհար", "Ստեփանյան"), ("Սամվել", "Մանուկյան"),
]

# type: (first letter of the transaction id, descriptions)
TX_TYPES = {
    "deposit": ("D", ["Salary", "Cash deposit", "Bonus"]),
    "withdrawal": ("W", ["ATM withdrawal", "Cash withdrawal"]),
    "transfer": ("T", ["Transfer to family", "Rent", "Transfer to friend"]),
    "payment": ("P", ["Utilities", "Groceries", "Online shop", "Phone bill"]),
}

def build_transactions(customer_id, rng):
    """Rows (tx_id, customer_id, tx_date, tx_type, amount, description), oldest first."""
    items = []
    for month in range(MONTHS):
        for _ in range(TX_PER_MONTH):
            tx_date = END_DATE - timedelta(days=month * 30 + rng.randint(0, 29))
            tx_type = rng.choice(list(TX_TYPES))
            description = rng.choice(TX_TYPES[tx_type][1])
            items.append((tx_date, tx_type, rng.randrange(5000, 500001, 100), description))
    counters, rows = {}, []
    for tx_date, tx_type, amount, description in sorted(items):
        counters[tx_type] = counters.get(tx_type, 0) + 1
        tx_id = TX_TYPES[tx_type][0] + str(customer_id) + "." + str(counters[tx_type])
        rows.append((tx_id, customer_id, tx_date, tx_type, amount, description))
    return rows

def main():
    rng = random.Random(SEED)
    with get_connection() as conn:
        cur = conn.cursor()
        # the tables come from migrations (python scripts/migrate.py); this file is data only
        cur.execute("DELETE FROM transactions")
        cur.execute("DELETE FROM document_files")   # issued documents point to customers
        cur.execute("DELETE FROM document_log")
        cur.execute("DELETE FROM customers")

        company_ids = []
        for prefix in COMPANIES:
            cur.execute("SELECT company_id FROM companies WHERE lower(name) LIKE %s "
                        "ORDER BY company_id LIMIT 1", (prefix + "%",))
            row = cur.fetchone()
            if row is None:
                raise ValueError("Company not found: " + prefix)
            company_ids.append(row[0])

        for i, (first_name, surname) in enumerate(CUSTOMERS, start=1):
            cur.execute("INSERT INTO customers (customer_id, first_name, surname, company_id) "
                        "VALUES (%s, %s, %s, %s)",
                        (i, first_name, surname, company_ids[(i - 1) // PER_COMPANY]))
            cur.executemany("INSERT INTO transactions "
                            "(tx_id, customer_id, tx_date, tx_type, amount, description) "
                            "VALUES (%s, %s, %s, %s, %s, %s)",
                            build_transactions(i, rng))

    print("Done:", len(CUSTOMERS), "customers,", len(CUSTOMERS) * MONTHS * TX_PER_MONTH, "transactions")

if __name__ == "__main__":
    main()

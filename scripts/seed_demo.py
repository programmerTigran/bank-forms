"""
scripts/seed_demo.py
Replaces customers with 24 fixed ones (6 per company) and recreates transactions
(20 per customer: 10 in each of the last 2 months). Same result on every run.
Transaction ids: type letter + customer id + "." + running number of that type
(P1.1 = first payment of customer 1).
Run from the project root (venv active): python -m scripts.seed_demo
"""

# ============================================================
# 1. IMPORTS
# ============================================================

import random
from datetime import date, timedelta

from db import get_connection

# ============================================================
# 2. SETTINGS (change these)
# ============================================================

SEED = 42
END_DATE = date(2026, 11, 13)      # last day of the transaction period
MONTHS = 2
TX_PER_MONTH = 10
PER_COMPANY = 6
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

TX_TYPES = {
    "deposit": ["Salary", "Cash deposit", "Bonus"],
    "withdrawal": ["ATM withdrawal", "Cash withdrawal"],
    "transfer": ["Transfer to family", "Rent", "Transfer to friend"],
    "payment": ["Utilities", "Groceries", "Online shop", "Phone bill"],
}

# First letter of each transaction id (must be different for every type)
TYPE_LETTERS = {"deposit": "D", "withdrawal": "W", "transfer": "T", "payment": "P"}

# ============================================================
# 3. HELPERS
# ============================================================

def get_company_ids(cur):
    """Return company_ids in the order of COMPANIES (matched by name prefix)."""
    cur.execute("SELECT company_id, name FROM companies")
    rows = cur.fetchall()
    ids = []
    for prefix in COMPANIES:
        match = [cid for cid, name in rows if name.lower().startswith(prefix)]
        if not match:
            raise ValueError("Company not found: " + prefix)
        ids.append(match[0])
    return ids

def build_transactions(customer_id, rng):
    """Return rows (tx_id, customer_id, tx_date, tx_type, amount, description)."""
    items = []
    for month in range(MONTHS):
        for _ in range(TX_PER_MONTH):
            tx_date = END_DATE - timedelta(days=month * 30 + rng.randint(0, 29))
            tx_type = rng.choice(list(TX_TYPES))
            description = rng.choice(TX_TYPES[tx_type])
            amount = rng.randrange(5000, 500001, 100)
            items.append((tx_date, tx_type, amount, description))
    items.sort()   # oldest first, so P1.1 is the oldest payment of customer 1
    counters = {}
    rows = []
    for tx_date, tx_type, amount, description in items:
        counters[tx_type] = counters.get(tx_type, 0) + 1
        tx_id = TYPE_LETTERS[tx_type] + str(customer_id) + "." + str(counters[tx_type])
        rows.append((tx_id, customer_id, tx_date, tx_type, amount, description))
    return rows

# ============================================================
# 4. MAIN
# ============================================================

def main():
    rng = random.Random(SEED)
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("DROP TABLE IF EXISTS transactions")
        cur.execute("DELETE FROM customers")
        company_ids = get_company_ids(cur)

        cur.execute(
            "CREATE TABLE transactions ("
            "  tx_id       TEXT PRIMARY KEY,"
            "  customer_id INTEGER NOT NULL REFERENCES customers(customer_id),"
            "  tx_date     DATE NOT NULL,"
            "  tx_type     TEXT NOT NULL,"
            "  amount      NUMERIC(12, 2) NOT NULL,"
            "  description TEXT"
            ")"
        )
        cur.execute("CREATE INDEX idx_transactions_customer ON transactions (customer_id, tx_date)")

        for i, (first_name, surname) in enumerate(CUSTOMERS, start=1):
            company_id = company_ids[(i - 1) // PER_COMPANY]
            cur.execute(
                "INSERT INTO customers (customer_id, first_name, surname, company_id) "
                "VALUES (%s, %s, %s, %s)",
                (i, first_name, surname, company_id),
            )
            cur.executemany(
                "INSERT INTO transactions "
                "(tx_id, customer_id, tx_date, tx_type, amount, description) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                build_transactions(i, rng),
            )

    print("Done:", len(CUSTOMERS), "customers,", len(CUSTOMERS) * MONTHS * TX_PER_MONTH, "transactions")

if __name__ == "__main__":
    main()
    
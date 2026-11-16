    """
    scripts/sync_csv.py
    Exports the customers table from the database to data/customers.csv.
    Run from the project root (venv active): python scripts/sync_csv.py
    """

    # ============================================================
    # 1. IMPORTS
    # ============================================================
    import csv
    import psycopg


    # ============================================================
    # 2. CONSTANTS
    # ============================================================
    CSV_PATH = "data/customers.csv"
    HEADER = ["customer_id", "first_name", "surname"]


    # ============================================================
    # 3. CORE LOGIC
    # ============================================================
    def fetch_customers():
        """Return all customers as (customer_id, first_name, surname) rows."""
        with psycopg.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT customer_id, first_name, surname FROM customers ORDER BY customer_id")
            return cur.fetchall()


    def write_csv(rows):
        """Write the header and rows to CSV_PATH."""
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)


    # ============================================================
    # 4. MAIN
    # ============================================================
    def main():
        write_csv(fetch_customers())


    if __name__ == "__main__":
        main()
import csv
import psycopg

with psycopg.connect() as conn:
    cur = conn.cursor()
    cur.execute("SELECT customer_id,first_name,surname FROM customers ORDER BY customer_id")
    rows = cur.fetchall()

with open("data/customers.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["customer_id", "first_name", "surname"])
    w.writerows(rows)
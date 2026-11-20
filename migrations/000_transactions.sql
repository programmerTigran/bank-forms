-- 000: the transactions table in its final shape (date last, big money, link to customers).
-- On a database that already has the table this does nothing.
-- A brand-new database needs sql/setup.sql first (it creates companies and customers).
CREATE TABLE IF NOT EXISTS transactions (
    tx_id       TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
    tx_type     TEXT NOT NULL,
    amount      NUMERIC(20, 2) NOT NULL,
    description TEXT,
    tx_date     DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions (customer_id, tx_date);

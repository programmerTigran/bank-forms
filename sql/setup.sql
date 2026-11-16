CREATE TABLE companies (
    company_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    logo TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    surname TEXT NOT NULL,
    company_id INTEGER REFERENCES companies(company_id)
);

CREATE TABLE transactions (
    tx_id TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    tx_date DATE NOT NULL,
    tx_type TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    description TEXT
);
CREATE INDEX idx_transactions_customer_date ON transactions (customer_id, tx_date);

CREATE TABLE document_templates (
    name TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    definition JSONB NOT NULL,
    PRIMARY KEY (name, version)
);

INSERT INTO companies (company_id, name, sort_order) VALUES
    (1, 'Ardshin', 1),
    (2, 'Ameria', 2),
    (3, 'Adidas', 3),
    (4, 'Puma', 4);

INSERT INTO customers (customer_id, first_name, surname, company_id) VALUES
    (1, 'Աննա', 'Հակոբյան', 1),
    (2, 'Արամ', 'Սարգսյան', 1),
    (3, 'Մարիամ', 'Գրիգորյան', 2),
    (4, 'Դավիթ', 'Մելքոնյան', 2),
    (5, 'Նարե', 'Ավետիսյան', 3),
    (6, 'Լուսինե', 'Ղազարյան', 3),
    (7, 'Գոռ', 'Մկրտչյան', 4),
    (8, 'Սոֆյա', 'Հարությունյան', 4),
    (9, 'Հասմիկ', 'Պետրոսյան', 1),
    (10, 'Վահե', 'Բաղդասարյան', 2);

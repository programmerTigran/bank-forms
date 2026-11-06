CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    surname     TEXT NOT NULL
);

INSERT INTO customers (customer_id, first_name, surname) VALUES
    (1, 'Աննա', 'Հակոբյան'),
    (2, 'Արամ', 'Սարգսյան'),
    (3, 'Մարիամ', 'Գրիգորյան'),
    (4, 'Դավիթ', 'Մելքոնյան'),
    (5, 'Նարե', 'Ավետիսյան'),
    (6, 'Լուսինե', 'Ղազարյան'),
    (7, 'Գոռ', 'Մկրտչյան'),
    (8, 'Սոֆյա', 'Հարությունյան'),
    (9, 'Հասմիկ', 'Պետրոսյան'),
    (10, 'Վահե', 'Բաղդասարյան');

CREATE TABLE document_templates (
    name       TEXT NOT NULL,
    version    INTEGER NOT NULL,
    definition JSONB NOT NULL,
    PRIMARY KEY (name, version)
);

INSERT INTO document_templates (name, version, definition) VALUES (
    'customer_details', 1,
    '{
      "page": {"size": "A4", "margin_pt": 72},
      "font": "DejaVu Sans",
      "blocks": [
        {"text": "CUSTOMER DETAILS", "size": 16, "bold": true, "align": "center", "space_after": 24},
        {"text": "Customer name: {{first_name}}", "size": 12, "bold": false, "align": "left", "space_after": 8},
        {"text": "Customer surname: {{surname}}", "size": 12, "bold": false, "align": "left", "space_after": 8},
        {"text": "Date: {{current_date}}", "size": 12, "bold": false, "align": "left", "space_after": 0}
      ]
    }'::jsonb
);
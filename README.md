# bank-forms

Streamlit app and REST API that make bank documents (account statements, balance
certificates, letters, receipts) as PDF, DOCX, RTF or CSV. Every document uses ONE fixed
layout (header + body + footer, "form0"). A form only describes the body, and forms are
stored in the database with versions, so new forms need no code. All data is synthetic.

## Stack

- **Streamlit** (screens) and **FastAPI** (REST API), both on top of one logic layer, `service.py`.
- **PostgreSQL 17** through `psycopg` with a connection pool. SQLAlchemy only reads the forms.
  All queries are parameterized, and every query is a file in `sql/queries/`.
- **reportlab** (PDF), **python-docx** (DOCX), **pandoc** via `pypandoc_binary` (RTF is made
  from the DOCX), CSV written by hand.
- Database settings come from environment variables (`.env`), never from the code.
- I run PostgreSQL in Docker (`docker start sales_lab_db`). pgAdmin is only for looking at the
  data; no SQL has to be run by hand.

## Setup (existing database)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # fill in PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
python scripts/migrate.py         # database changes (see "Changing the database")
python scripts/load_logos.py      # company logos into the database
python -m scripts.seed_demo       # demo customers + transactions (DELETES the old ones and all issued documents)
python -m scripts.seed_forms      # the two starter forms (account_statement, balance_certificate)
python scripts/seed_users.py admin admin     # asks for a password (min. 8 characters)
python scripts/seed_users.py clerk clerk
```

Known gap: `sql/setup.sql` only creates `customers` and `document_templates`. The other base
tables (`companies`, `customers_v2`, `document_log`, `document_files`) were created by hand,
so a database built from scratch is not scripted yet. The migrations upgrade an existing one.

## Run

```bash
streamlit run app.py --server.port 8501 --server.headless true
uvicorn api:app --reload          # API docs and try-it page: http://localhost:8000/docs
```

## Login and roles

- `LOGIN_ON` at the top of `ui.py`: `False` = no login screen, you act as `dev` (admin);
  `True` = login required.
- `clerk` makes and issues documents. `admin` can also create and edit forms.
- The API always needs a login (HTTP Basic, a user from the `users` table).

## Pages

- **app** (`app.py`): search or pick a form, pick a customer, fill the inputs, preview, issue
  (gets a number like `BF-2026-000001`), download. Second tab: issued documents. Admins can type
  a new name to create a form, and change header, recipe and footer in "Edit this form".
- **tables** (`pages/tables.py`): anyone can add a table of their own (any columns), add rows by hand or
  from a CSV, and search the list (3 shown, button for all). Stored in the database, so others can use it
  later, also as the data of a form ("Edit this form" -> Table -> Where the rows come from).
- **companies** (`pages/companies.py`): companies with logo and totals (5 shown, button for all),
  their customers (paged) and transactions.

## Where things live

| What | Where |
|---|---|
| Forms (recipes, all versions) | table `document_templates` (name, version, definition JSONB) |
| Issued documents | `document_log` (number, who, when) and `document_files` (the PDF/DOCX/RTF/CSV files) |
| Customers, companies, transactions | `customers`, `customers_v2` (phone, email, passport, birth date, address), `companies` (with `logo_data`), `transactions` |
| Tables made by users | `custom_tables` (definition) and `custom_rows` (the rows, JSON) |
| Users and history | `users` (password hashes), `audit_log`, `doc_counter`, `schema_migrations` |
| Data queries | files in `sql/queries/*.sql` (`sql/setup.sql` and `sql/seed_forms.sql` are one-time scripts, not queries) |
| Logic without a screen | `service.py` |
| Fixed layout and file makers | `form0.py`, `documents.py` |
| Reading and saving forms | `form_store.py`, `models.py`; saving uses the database function `create_form_version` |
| Database changes | `migrations/` |

Saving a form never overwrites: it adds a new version. The newest version is the one used.

## How a form is made (flow)

1. The user picks a form; the newest version (a JSON recipe) is loaded.
2. The recipe's inputs (customer, dates, date, filters, transaction) give texts for the
   `{{placeholders}}` and parameters for the SQL (`service.py`).
3. The recipe's query runs `sql/queries/<query>.sql`.
4. `build_doc` fills the text and the table; `generate` makes HTML, PDF, DOCX, RTF or CSV.
5. A form with a `{{placeholder}}` that nothing filled cannot be issued.

Recipe fields: `title`, `inputs`, `query`, `info_lines`, `paragraphs`, `columns`, `empty_text`,
and optional `header` / `footer` (company, slogan, right-side lines, signature),
`show_table` (false = no table) and `table_style` (heading color, text size, lines, striped rows,
row numbers, columns to add up). Column types: text, date, money, number.

## What is dynamic and what needs code

- **No code:** titles, text, table columns, header and footer, choice of query and inputs,
  new versions, any number of forms.
- **Needs code:** a new query (new file in `sql/queries/`), a new input (`INPUT_BUILDERS` in
  `service.py` plus a widget in `app.py`), a new form kind in the popup (`KINDS` and
  `build_definition` in `form_store.py`), a change of the layout (`form0.py`).

## Adding things

- **New form:** type a name on the page, answer the popup.
- **Change a form:** "Edit this form" (admin), then "Save as new version".
- **New data for a form:** add `sql/queries/<name>.sql` and use that name as the form's query. Its
  columns can be used as `{{column}}` in forms without a table.
- **New column or table:** add the next file in `migrations/`, see below.

## Changing the database

Add the next file in `migrations/` (for example `007_city.sql`) and run
`python scripts/migrate.py`. Each file runs once, in one transaction; if it fails, nothing from
it is saved. The runner uses the same database as the app. Rule: the date column
(`created_at`, `tx_date`, `applied_at`) is the last column of a table. The runner moves it back
by itself after a new column was added, and keeps its indexes and rules.

## API

`GET /forms`, `GET /forms/{name}`, `POST /forms/{name}` (admin), `POST /documents` (issue),
`GET /documents`, `GET /documents/{doc_no}/{fmt}` (download), `GET /customers`, `GET /companies`.

## My cheat sheet: what I can write in the text

Write these in extra text, paragraphs or info lines. They are replaced by real values.

Customer (when the form has the customer input): `{{customer_id}}`, `{{first_name}}`,
`{{surname}}`, `{{company_name}}`, `{{phone}}`, `{{email}}`, `{{passport_no}}`,
`{{birth_date}}`, `{{address}}`

Dates: `{{date_from}}` and `{{date_to}}` (input "dates"), `{{as_of}}` (input "date"),
`{{current_date}}` (today)

Numbers: `{{count}}` = number of table rows, `{{balance}}` = result of `balance_on_date`
(any column of the query works the same way in a form without a table)

Header: `{{company_name}}`, `{{slogan}}`, `{{current_date}}`. Currency: `{{currency}}` (AMD).

Position: `{{table}}` alone on its own line = where the table goes. Lines above it print above
the table, lines below it print below.

Notes

- Header and footer are edited in the "Edit this form" boxes (company, slogan, right-side
  lines, signature text). Empty signature = no signature line.
- A `{{name}}` that nothing fills (a typo, or the form's query has no such column) is shown as
  "Not filled" and the form cannot be issued.
- Money is shown like `1,234.00 AMD`. An amount gets `AMD` unless a currency is written next to
  it: `{{balance}} AMD` stays one AMD, `{{balance}} USD` stays USD.
- Dates are shown like `17/11/2026`.
- Logos are stored in the database (PNG or JPEG, up to 2 MB). Add one with
  `python scripts/load_logos.py <company_id> <file>`.

## What is recorded

Issuing, downloading, viewing a customer's transactions and editing forms are written to
`audit_log` with the user name. Document numbers have no gaps: a failed issue gives its number
back.

## Not production-ready

A real bank deployment also needs: a server with HTTPS, access to customers per user, approval
of documents by a second person, encrypted backups and a security review.

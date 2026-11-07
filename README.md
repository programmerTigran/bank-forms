# Bank customer forms

A small Streamlit app for filling in customer forms. Pick an existing customer or type a name by hand, choose a template, and download the finished document as RTF or PDF. Customers and templates live in PostgreSQL, so changing a layout never means touching the code. All data is synthetic.

## Features

- Existing customer (dropdown from the database) or manual entry
- New customers can be saved to the database, and each one is also appended to `customers.csv`
- The same first name and surname (any upper/lower case) cannot be saved twice
- Template dropdown, always using the highest version of each template
- White-paper preview before download
- RTF and PDF for existing customers, RTF only for manual entry
- Database errors show as messages instead of crashing the app

## What you need first

- Python 3.12 or newer
- Docker, to run PostgreSQL (version 17)
- On Ubuntu/WSL: the DejaVu fonts (see "PDF fonts" below)

## Setting up the database

1. Start PostgreSQL in Docker:

   ```
   docker run -d --name sales_lab_db -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=<your password> -p 5432:5432 postgres:17
   ```
2. Open pgAdmin and create a database called `bank_forms`.
3. Open the Query Tool on `bank_forms`, load `setup.sql` and run it. It creates the tables, adds the sample customers and stores version 1 of the template. Run it before starting the app.

To start the database again later: `docker start sales_lab_db`

The app always takes the highest version of a template. For a new layout, add a row with a higher version number and leave the old one alone.

## Database settings

The app reads its connection details from environment variables, so no password sits in the code:

```
export PGHOST=localhost
export PGPORT=5432
export PGUSER=admin
export PGPASSWORD=<your password>
export PGDATABASE=bank_forms
```

## Installing

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## PDF fonts

The PDF writer embeds DejaVu Sans, so Armenian letters show correctly. The app expects the font files in `/usr/share/fonts/truetype/dejavu/`. Check with:

```
ls /usr/share/fonts/truetype/dejavu/
```

You need `DejaVuSans.ttf` and `DejaVuSans-Bold.ttf`. If they are missing:

```
sudo apt install fonts-dejavu-core
```

## Running

```
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Syncing customers.csv

`sync_csv.py` rewrites `customers.csv` from the database, so the file matches the `customers` table exactly. It overwrites the file.

```
python sync_csv.py
```

## Checking the output

`verify.py` generates both formats for the customers, reads the files back, and checks that the name, surname and date are inside each one.

```
python verify.py
```
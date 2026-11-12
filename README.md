# Bank customer forms

This is a small Streamlit app that fills in customer forms. I pick a customer, choose a template and download the finished document as RTF or PDF. The customers and templates are stored in PostgreSQL, so changing a layout does not need any change in the code. All the data is synthetic.

## Stack

- **Streamlit**: one small Python app for the screen and the logic. There is no separate frontend, no queue and no microservices.
- **PostgreSQL 17** in Docker, used through `psycopg`. It stores the customers and the versioned templates. All queries are parameterized.
- **ReportLab**: writes the PDF.
- **RTF**: I write it by hand as plain text, so it needs no library.
- **pdfplumber**: reads PDFs back, used only by the converter.
- **pgAdmin**: used only to administer the database.
- The database credentials come from environment variables (`PG...`) and are never written in the code.

## How the documents are made

One stored template produces both formats, so they always match.

1. The template is a JSON definition in the `document_templates` table (name, version, definition). It holds the page margin, the font and a list of blocks. Each block has its text, alignment, size, bold flag and the space after it. The text contains placeholders like `{{first_name}}`, `{{surname}}` and `{{current_date}}`.
2. The app loads the highest version of the chosen template and replaces the placeholders with the name and surname of the customer. The date is the day of generation in the Asia/Yerevan timezone, written as DD/MM/YYYY.
3. The filled blocks go to two renderers:
   - **RTF**: each block becomes one RTF paragraph with the same alignment, size, bold and spacing. Characters outside ASCII (Armenian, for example) are written as `\uN?` escapes, so the Unicode text is kept.
   - **PDF**: ReportLab draws each block on an A4 page with the same margin, size and alignment. It embeds DejaVu Sans, which has the Armenian letters.
4. Generation is synchronous. The file goes straight to the browser as a download and nothing is archived.

## Features

- Customer dropdown filled from the database
- Template dropdown, always using the highest version of each template
- White-paper preview before the download
- Download as RTF or PDF, both made from the same stored template
- Armenian and other Unicode text works in both formats
- Converter: upload an RTF or PDF made by this app and download it as the other format
- Database errors are shown as messages and do not crash the app

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

The app always takes the highest version of a template. For a new layout, I add a row with a higher version number and leave the old one as it is.

## Database settings

The app reads the connection details from environment variables, so no password is written in the code:

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

The PDF writer embeds DejaVu Sans, so the Armenian letters show correctly. The app expects the font files in `/usr/share/fonts/truetype/dejavu/`. To check:

```
ls /usr/share/fonts/truetype/dejavu/
```

`DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` must be there. If they are missing:

```
sudo apt install fonts-dejavu-core
```

## Running

```
streamlit run app.py
```

Then open the address Streamlit prints. It is usually http://localhost:8501, and Streamlit uses 8502 if 8501 is busy.

## Files

Every file except `app.py` is short, so I described only `app.py` here.

`app.py` has four parts:
- **Database functions**: get the customer ids, the template names, one customer and the newest version of a template.
- **Filling the template**: replaces the placeholders in each block with the real values.
- **Renderers**: `make_rtf` builds the RTF and `make_pdf` builds the PDF from the filled blocks.
- **Page and converter**: the Streamlit screen with the preview and the download buttons, and the converter at the bottom.

## Converting files

At the bottom of the page I can upload an RTF or PDF and download it as the other format.

This works only for files made by this app. The RTF reader expects the exact structure this app writes. The PDF reader guesses bold, size and alignment from the position of the text. Files from Word or other tools and scanned PDFs are not supported.

## Syncing data/customers.csv

`scripts/sync_csv.py` rewrites `data/customers.csv` from the database, so the file matches the `customers` table exactly. It overwrites the file.

```
python scripts/sync_csv.py
```

## Checking the output

`scripts/verify.py` generates both formats for the customers, reads the files back and checks that the name, surname and date are inside each one.

```
python scripts/verify.py
```
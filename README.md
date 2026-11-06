# Bank customer forms

A small app for filling in a customer form. You pick a customer, choose RTF or PDF, and download the finished document. The customers and the form template both live in PostgreSQL, so changing the layout never means touching the code. All data is synthetic.

## What you need first
- Python 3.12 or newer
- Docker, to run PostgreSQL (version 17)
- On Ubuntu/WSL: the DejaVu fonts (see "PDF fonts" below)

## Setting up the database
1. Start PostgreSQL in Docker:
   ```
   docker run -d --name bank_db -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=<your password> -p 5432:5432 postgres:17
   ```
2. Open pgAdmin and create a database called `bank_forms`.
3. Open the Query Tool on `bank_forms`, load `setup.sql` and run it. That creates the two tables, adds the 10 customers, and stores version 1 of the template. Run it before starting the app.

The app always takes the highest version of a template. If you want a new layout, add a row with a higher version number and leave the old one alone.

## Database settings
The app reads its connection details from environment variables, so no password ever sits in the code:
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
You need `DejaVuSans.ttf` and `DejaVuSans-Bold.ttf`. If the folder is missing, install them:
```
sudo apt install fonts-dejavu-core
```

## Running
```
streamlit run app.py
```
Then open http://localhost:8501 in your browser. Pick a customer, choose RTF or PDF, and click the download button. Nothing is saved on the server, the file is made on the spot.

## Checking the output
`verify.py` generates both formats for all 10 customers, reads the files back, and checks that the name, surname and date are inside each one. For RTF it decodes the `\uNNNN?` escapes back into letters. For PDF it extracts the text with pypdf.

Run it with:
```
python verify.py
```
Expected: 20 lines starting with `OK`, then `All 20 checks passed.`
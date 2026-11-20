"""
scripts/load_logos.py
Puts company logo images into the database (companies.logo_data).
  python scripts/load_logos.py                -> loads every file named in companies.logo (data/logos/...)
  python scripts/load_logos.py 7 path/to.png  -> sets the logo of company 7 from one file
Run from the project root (venv active), after python scripts/migrate.py.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from db import _fetchall, set_company_logo

def main():
    if len(sys.argv) == 3:
        set_company_logo(int(sys.argv[1]), Path(sys.argv[2]).read_bytes())
        print("Logo saved for company", sys.argv[1])
        return
    loaded = 0
    for company_id, name, path in _fetchall("SELECT company_id, name, logo FROM companies WHERE logo IS NOT NULL"):
        file = ROOT / path
        if not file.exists():
            print("  missing file for", name, ":", path)
            continue
        set_company_logo(company_id, file.read_bytes())
        loaded += 1
    print("Loaded", loaded, "logos")

main()

"""
sync_forms.py
Creates the form_definitions table (if missing) and copies every
form_templates/*.json into it (insert or update by name).
Run: python -m scripts.sync_forms
"""

import json

from psycopg.types.json import Jsonb

from db import get_connection
from form0 import FORMS_DIR

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS form_definitions (
    name       TEXT PRIMARY KEY,
    definition JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

UPSERT = """
INSERT INTO form_definitions (name, definition)
VALUES (%(name)s, %(definition)s)
ON CONFLICT (name) DO UPDATE
SET definition = EXCLUDED.definition, updated_at = now()
"""

def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE)
            for path in sorted(FORMS_DIR.glob("*.json")):
                with open(path, encoding="utf-8") as f:
                    definition = json.load(f)
                cur.execute(UPSERT, {"name": path.stem, "definition": Jsonb(definition)})
                print("saved " + path.stem)

main()

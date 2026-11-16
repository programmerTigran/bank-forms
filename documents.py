"""Seed template JSON files into the document_templates table."""
from __future__ import annotations

import json
from pathlib import Path

from db import get_connection

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "document_templates"


def main():
    with get_connection() as conn:
        cur = conn.cursor()
        for json_path in sorted(TEMPLATES_DIR.glob("*.json")):
            name = json_path.stem
            with json_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            version = 1
            cur.execute(
                "INSERT INTO document_templates (name, version, definition) VALUES (%s, %s, %s) "
                "ON CONFLICT (name, version) DO UPDATE SET definition = EXCLUDED.definition",
                (name, version, json.dumps(payload)),
            )
    print(f"Seeded {len(list(TEMPLATES_DIR.glob('*.json')))} templates.")


if __name__ == "__main__":
    main()


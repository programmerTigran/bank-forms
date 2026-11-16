"""Import versioned JSON templates into PostgreSQL without overwriting history.

Name files as <template-name>.v<positive-version>.json. Add a new version by
adding another file; do not edit an already-imported version.
"""

import json
import re
from pathlib import Path

from db import get_connection

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "document_templates"
FILENAME = re.compile(r"^(?P<name>[a-zA-Z0-9_-]+)\.v(?P<version>[1-9][0-9]*)\.json$")


def main():
    paths = sorted(TEMPLATES_DIR.glob("*.json"))
    if not paths:
        raise SystemExit(f"No versioned template JSON files found in {TEMPLATES_DIR}")

    count = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for path in paths:
                match = FILENAME.fullmatch(path.name)
                if not match:
                    raise ValueError(f"Invalid template filename: {path.name}")
                definition = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(definition, dict) or not isinstance(definition.get("blocks"), list):
                    raise ValueError(f"Template must be an object with a blocks list: {path}")
                cur.execute(
                    "INSERT INTO document_templates (name, version, definition) "
                    "VALUES (%s, %s, %s) ON CONFLICT (name, version) DO NOTHING",
                    (match.group("name"), int(match.group("version")), json.dumps(definition)),
                )
                count += cur.rowcount
    print(f"Imported {count} new template version(s).")


if __name__ == "__main__":
    main()

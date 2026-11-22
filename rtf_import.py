"""
rtf_import.py
Import for the Tables page. Reads an RTF file, turns old Armenian (Fonitech) text into Unicode,
and decides what the file is:
  "row"   one record: lines like "Name: value", or a 2-column list  label | value
  "table" a grid: the first line has the headings, then one line per row
  "form"  plain text with no grid (a letter, a certificate), maybe with {{placeholders}}
read_rtf() only reads, decide() only decides, apply_plan() saves (through service.py).
Used by pages/tables.py.
"""

# ============================================================
# 1. IMPORTS AND CONSTANTS
# ============================================================

import json
import logging
import re

import pypandoc

from armenian_encoding import fix
from db import get_custom_table, save_rtf_file
import service
from service import cell_value

log = logging.getLogger("bank_forms")

PLACEHOLDER = re.compile(r"\{\{\s*\w+\s*\}\}")
LABEL_VALUE = re.compile(r"^\s*([^:]{1,60}?)\s*:\s*(.+?)\s*$")
TITLE_MAX = 80
MAX_FILE_BYTES = 5 * 1024 * 1024

# ============================================================
# 2. READ THE FILE (pandoc turns the RTF into a tree; we take the text out of it)
# ============================================================

def fix_text(text):
    """Old Armenian -> Unicode, word by word, so one line can hold Armenian and Latin words."""
    return re.sub(r"\S+", lambda m: fix(m.group()), text)

def inline_text(items):
    out = []
    for item in items:
        kind = item["t"]
        if kind == "Str":
            out.append(item["c"])
        elif kind in ("Space", "SoftBreak"):
            out.append(" ")
        elif kind == "LineBreak":
            out.append("\n")
        elif kind in ("Emph", "Strong", "Underline", "Strikeout", "Superscript", "Subscript", "SmallCaps"):
            out.append(inline_text(item["c"]))
        elif kind == "Quoted":
            out.append(inline_text(item["c"][1]))
        elif kind in ("Span", "Link"):
            out.append(inline_text(item["c"][1]))
        elif kind == "Code":
            out.append(item["c"][1])
    return "".join(out)

def block_lines(block):
    """One block (paragraph, heading, list) -> a list of text lines."""
    kind = block["t"]
    if kind in ("Para", "Plain"):
        return inline_text(block["c"]).split("\n")
    if kind == "Header":
        return inline_text(block["c"][2]).split("\n")
    if kind == "LineBlock":
        return [inline_text(line) for line in block["c"]]
    if kind in ("BulletList", "OrderedList"):
        items = block["c"] if kind == "BulletList" else block["c"][1]
        return [line for item in items for b in item for line in block_lines(b)]
    if kind == "BlockQuote":
        return [line for b in block["c"] for line in block_lines(b)]
    if kind == "Div":
        return [line for b in block["c"][1] for line in block_lines(b)]
    return []

def table_cells(block):
    """A pandoc table -> [[cell text, ...], ...] (head rows, body rows, foot rows)."""
    _attr, _caption, _specs, head, bodies, foot = block["c"]
    rows = list(head[1])
    for body in bodies:
        rows += body[2] + body[3]
    rows += foot[1]
    return [[" ".join(line for b in cell[4] for line in block_lines(b)) for cell in row[1]]
            for row in rows]

def _parse_rtf_direct(text):
    """Pure-Python fallback parser for RTF tables and paragraphs (handles nested control codes)."""
    skip_dest = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "object",
                 "header", "footer", "headerl", "headerr", "headerf",
                 "footerl", "footerr", "footerf", "themedata", "colorschememapping", "generator"}
    skip_stack = [False]
    in_cell = False
    paragraphs, tables = [], []
    current_table, current_row, cell_buf, para_buf = [], [], [], []

    def flush_para():
        t = "".join(para_buf).strip()
        para_buf.clear()
        if t:
            paragraphs.append(t)

    i, n = 0, len(text)
    uc_skip = 1

    while i < n:
        ch = text[i]
        if ch == "{":
            skip_stack.append(skip_stack[-1])
            i += 1
        elif ch == "}":
            if len(skip_stack) > 1:
                skip_stack.pop()
            i += 1
        elif ch == "\\":
            i += 1
            if i >= n:
                break
            next_ch = text[i]
            if next_ch in ("\\", "{", "}"):
                if not skip_stack[-1]:
                    (cell_buf if in_cell else para_buf).append(next_ch)
                i += 1
            elif next_ch == "'":
                hex_digits = text[i + 1:i + 3]
                if len(hex_digits) == 2 and all(c in "0123456789abcdefABCDEF" for c in hex_digits):
                    if not skip_stack[-1]:
                        (cell_buf if in_cell else para_buf).append(chr(int(hex_digits, 16)))
                    i += 3
                else:
                    i += 1
            elif next_ch == "*":
                skip_stack[-1] = True
                i += 1
            else:
                m = re.match(r"([a-zA-Z]+)(-?\d+)? ?", text[i:])
                if m:
                    word, arg = m.group(1), m.group(2)
                    i += m.end()
                    if word in skip_dest:
                        skip_stack[-1] = True
                    elif not skip_stack[-1]:
                        if word == "uc":
                            uc_skip = int(arg) if arg else 1
                        elif word == "u":
                            val = int(arg) if arg else 0
                            if val < 0:
                                val += 65536
                            (cell_buf if in_cell else para_buf).append(chr(val))
                            i += uc_skip
                        elif word in ("par", "line"):
                            if in_cell:
                                cell_buf.append("\n")
                            else:
                                flush_para()
                                if current_table:
                                    tables.append(list(current_table))
                                    current_table.clear()
                        elif word == "cell":
                            current_row.append("".join(cell_buf).strip())
                            cell_buf.clear()
                            in_cell = True
                        elif word == "row":
                            in_cell = False
                            if current_row:
                                current_table.append(list(current_row))
                                current_row.clear()
                        elif word in ("trowd", "intbl"):
                            flush_para()
                            in_cell = True
                        elif word == "tab":
                            (cell_buf if in_cell else para_buf).append(" ")
                else:
                    if next_ch == "~" and not skip_stack[-1]:
                        (cell_buf if in_cell else para_buf).append(" ")
                    i += 1
        else:
            if not skip_stack[-1] and ch not in ("\r", "\n"):
                (cell_buf if in_cell else para_buf).append(ch)
            i += 1

    flush_para()
    if current_row:
        current_table.append(list(current_row))
    if current_table:
        tables.append(list(current_table))
    return paragraphs, tables

def read_rtf(data):
    """RTF bytes -> (paragraphs, tables). All text is Unicode.
    Uses pypandoc as primary; falls back to pure-Python direct parser if tables are lost or pandoc errors."""
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("The file is bigger than 5 MB")
    text = data.decode("latin-1")          # RTF is plain ASCII; accented letters are \'xx codes
    if not text.lstrip().startswith("{\\rtf"):
        raise ValueError("This is not an RTF file")

    paragraphs, tables = [], []

    # Try pypandoc primary
    try:
        tree = json.loads(pypandoc.convert_text(text, "json", format="rtf"))
        for block in tree["blocks"]:
            if block["t"] == "Table":
                extracted = table_cells(block)
                if extracted:
                    tables.append(extracted)
            else:
                paragraphs += block_lines(block)
    except Exception as e:
        log.warning("pandoc could not read the RTF, using the direct parser: %s", e)

    # If pandoc failed or dropped cells, use direct parser
    expected_cells = len(re.findall(r"\\cell\b", text))
    extracted_cells = sum(len(r) for t in tables for r in t)
    if (not paragraphs and not tables) or (expected_cells > 0 and extracted_cells < expected_cells):
        paragraphs, tables = _parse_rtf_direct(text)

    paragraphs = [fix_text(p).strip() for p in paragraphs if p.strip()]
    tables = [[[fix_text(c).strip() for c in row] for row in t] for t in tables]
    return paragraphs, tables

# ============================================================
# 3. DECIDE: ROW, TABLE OR FORM
# ============================================================

def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip().lower()

def known_names(table):
    """{heading or column name, lower case: column name} of the open table."""
    names = {}
    for c in table["columns"]:
        names[norm(c["name"])] = c["name"]
        names[norm(c["label"])] = c["name"]
    return names

def hits(headings, names):
    return sum(1 for h in headings if norm(h) in names)

def build_table(grid):
    """First line = headings, the rest = rows."""
    if not grid or len(grid) < 2 or len(grid[0]) < 2:
        return None
    headings = grid[0]
    rows = [(r + [""] * len(headings))[:len(headings)] for r in grid[1:]]
    rows = [r for r in rows if any(c for c in r)]
    return {"headings": headings, "rows": rows} if rows else None

def build_row(paragraphs, grid):
    """One record: from a 2-column grid (label | value) or from 'label: value' lines."""
    if grid and all(len(r) == 2 for r in grid):
        pairs = [(r[0], r[1]) for r in grid if r[0]]
    else:
        pairs = [m.groups() for m in map(LABEL_VALUE.match, paragraphs) if m]
        if len(pairs) < max(2, round(len(paragraphs) * 0.6)):
            return None
    if len(pairs) < 1:
        return None
    return {"headings": [p[0] for p in pairs], "rows": [[p[1] for p in pairs]]}

def build_form(paragraphs):
    """Text only: a short first line is the title, the rest are the paragraphs."""
    if not paragraphs:
        return None
    title = paragraphs[0] if len(paragraphs) > 1 and len(paragraphs[0]) <= TITLE_MAX else ""
    paras = paragraphs[1:] if title else paragraphs
    placeholders = sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", " ".join(paragraphs))))
    return {"title": title, "paragraphs": paras, "placeholders": placeholders}

def decide(paragraphs, tables, table=None):
    """What is this file? Returns {"kind", "why", "options": {kind: plan}}.
    'table' is the open table (or None); its columns help to tell a row from a table."""
    names = known_names(table) if table else {}
    grid = max(tables, key=len, default=None)
    options = {"table": build_table(grid), "row": build_row(paragraphs, grid),
               "form": build_form(paragraphs)}
    options = {k: v for k, v in options.items() if v}
    if not options:
        raise ValueError("Nothing usable in this file (no text, no grid)")

    if "form" in options and any(PLACEHOLDER.search(p) for p in paragraphs):
        kind, why = "form", "it has {{placeholders}}, so it is a form template"
    elif grid and len(grid) >= 2:
        if "table" in options and names and hits(options["table"]["headings"], names) * 2 >= len(options["table"]["headings"]):
            kind, why = "table", "its first line matches the columns of the open table"
        elif "row" in options and names and hits(options["row"]["headings"], names) * 2 >= len(options["row"]["headings"]):
            kind, why = "row", "it is a list of label | value that matches the open table"
        elif "table" in options:
            kind, why = "table", "it is a grid: first line = headings, then rows"
        else:
            kind, why = "row", "it is a list of label | value"
    elif "row" in options:
        kind, why = "row", "most lines look like 'name: value'"
    else:
        kind, why = "form", "it is plain text, so it becomes a form (letter)"
    return {"kind": kind, "why": why, "options": options}

# ============================================================
# 4. SAVE
# ============================================================

def slug(text, fallback):
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return s[:40] or fallback

def guess_type(values):
    """number / date / text, by trying every value of the column.
    Values like 007 or 0912345678 (codes, phone and account numbers) stay text."""
    filled = [v for v in values if str(v).strip()]
    if not filled:
        return "text"
    if any(re.match(r"^\s*[+-]?0\d", str(v)) for v in filled):
        return "text"
    for kind in ("number", "date"):
        try:
            [cell_value(v, kind) for v in filled]
            return kind
        except ValueError:
            pass
    return "text"

def default_name(filename):
    return slug(re.sub(r"\.rtf$", "", filename, flags=re.I), "rtf_import")

def apply_plan(kind, plan, table, name, username, filename="", data=None):
    """Save what the file holds, and keep the original RTF (data) in rtf_imports.
    Returns a message. ValueError if something is wrong.
    table = the open table (dict from get_table) or None; name = new table/form name."""
    message, target = save_plan(kind, plan, table, name, username)
    if data is not None:
        save_rtf_file(filename or target + ".rtf", kind, target, data, username)
    return message

def save_plan(kind, plan, table, name, username):
    """Save the content. Returns (message, name of the table or form it went into)."""
    if kind == "form":
        placeholders = plan.get("placeholders", [])
        # Auto-detect required inputs from placeholders
        inputs = ["customer"]
        if any(p in ("date_from", "date_to", "start_date", "end_date") for p in placeholders):
            inputs.append("dates")
        elif any(p in ("date", "as_of") for p in placeholders):
            inputs.append("date")
        if any(p in ("tx_id", "transaction_id", "operation_id") for p in placeholders):
            inputs.append("transaction")

        definition = {
            "title": plan["title"] or name,
            "inputs": inputs,
            "query": "customer_get",
            "paragraphs": plan["paragraphs"],
            "placeholders": placeholders,
        }
        version = service.save_new_form_version(name, definition, username)
        msg = "Form '" + name + "' saved as version " + str(version) + "."
        if placeholders:
            msg += " Found " + str(len(placeholders)) + " placeholder(s): " + ", ".join("{{" + p + "}}" for p in placeholders)
        return msg, name

    headings, rows = plan["headings"], plan["rows"]
    if len(rows) > service.MAX_IMPORT_ROWS:
        raise ValueError("More than " + str(service.MAX_IMPORT_ROWS) + " rows: split the file")
    if table and hits(headings, known_names(table)) * 2 >= len(headings):
        names = known_names(table)
        records = [{names[norm(h)]: v for h, v in zip(headings, r) if norm(h) in names} for r in rows]
        lost = [h for h in headings if norm(h) not in names]
        n = service.add_rows(table, records, username)
        return (str(n) + " row(s) added to '" + table["name"] + "'."
                + (" Not used (no such column): " + ", ".join(lost) + "." if lost else "")), table["name"]

    # no open table, or it does not match: make a new table from the headings
    if get_custom_table(name) is not None:
        raise ValueError("A table named '" + name + "' already exists. Choose another name.")
    column_rows, used = [], set()
    for i, h in enumerate(headings, start=1):
        col = slug(h, "c" + str(i))
        if col in used:
            col = "c" + str(i)
        used.add(col)
        column_rows.append({"name": col, "label": h or col,
                            "type": guess_type([r[i - 1] for r in rows])})
    service.create_table(name, name, "Imported from RTF", column_rows, username)
    new_table = service.get_table(name)
    records = [{c["name"]: v for c, v in zip(column_rows, r)} for r in rows]
    n = service.add_rows(new_table, records, username)
    return "New table '" + name + "' created with " + str(n) + " row(s).", name

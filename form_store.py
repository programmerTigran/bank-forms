"""
form_store.py
Form recipes stored in Postgres (document_templates, SQLAlchemy for reading).
Saving adds a new version through the database function create_form_version
(never overwrites). Also builds new recipes from the "New form" popup
(KINDS, COLUMN_OPTIONS, build_definition).
Used by service.py and app.py.
"""

# ============================================================
# 1. IMPORTS
# ============================================================

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from db import create_form_version
from models import engine, DocumentTemplate

# ============================================================
# 2. CONSTANTS
# ============================================================

KINDS = ["Account statement", "Balance certificate", "Customer letter",
         "Reference letter", "Transaction receipt"]

COLUMN_OPTIONS = {
    "Date": {"field": "tx_date", "label": "Date", "type": "date", "width": 1},
    "Type": {"field": "tx_type", "label": "Type", "type": "text", "width": 1},
    "Amount": {"field": "amount", "label": "Amount", "type": "money", "align": "right", "width": 1},
    "Description": {"field": "description", "label": "Description", "type": "text", "width": 3},
}

# ============================================================
# 3. READ / SAVE FORMS
# ============================================================

def list_forms():
    """All form names."""
    with Session(engine) as s:
        return list(s.scalars(
            select(DocumentTemplate.name).distinct().order_by(DocumentTemplate.name)))

def find_forms(term="", limit=10):
    """Form names matching the term (searches the database, no 500 limit)."""
    with Session(engine) as s:
        q = select(DocumentTemplate.name).distinct().order_by(DocumentTemplate.name)
        if term:
            q = q.where(DocumentTemplate.name.ilike("%" + term + "%"))
        return list(s.scalars(q.limit(limit)))

def form_exists(name):
    """True if a form with this name exists."""
    with Session(engine) as s:
        return s.scalar(select(func.count()).select_from(DocumentTemplate)
                        .where(DocumentTemplate.name == name)) > 0

def load_form(name, version=None):
    """Newest version, or a specific one."""
    with Session(engine) as s:
        q = select(DocumentTemplate).where(DocumentTemplate.name == name)
        if version is not None:
            q = q.where(DocumentTemplate.version == version)
        row = s.scalars(q.order_by(DocumentTemplate.version.desc()).limit(1)).first()
        if row is None:
            raise ValueError("Template " + name + " not found")
        return row.definition

def list_versions(name):
    """All version numbers of a form, newest first."""
    with Session(engine) as s:
        return list(s.scalars(select(DocumentTemplate.version)
                              .where(DocumentTemplate.name == name)
                              .order_by(DocumentTemplate.version.desc())))

def save_form(name, definition):
    """Insert a new version (the database function does it safely). Returns the version number."""
    return create_form_version(name, definition)

def default_form(name):
    """A minimal recipe for a new form name."""
    return {"title": name.replace("_", " ").capitalize(),
            "inputs": ["customer"],
            "query": "customer_get",
            "paragraphs": ["Customer: {{first_name}} {{surname}}."]}

# ============================================================
# 4. BUILD A NEW RECIPE (popup)
# ============================================================

def build_definition(kind, title, extra, cols):
    """Make a form recipe from what the user chose in the popup."""
    extra_lines = [x.strip() for x in extra.splitlines() if x.strip()]
    if kind == "Account statement":
        d = {"title": title, "inputs": ["customer", "dates", "filters"],
             "query": "tx_between",
             "info_lines": ["Customer: {{first_name}} {{surname}}",
                            "Period: {{date_from}} - {{date_to}}"],
             "columns": [COLUMN_OPTIONS[c] for c in cols],
             "empty_text": "No transactions in this period."}
        paragraphs = extra_lines
    elif kind == "Balance certificate":
        d = {"title": title, "inputs": ["customer", "date"], "query": "balance_on_date"}
        paragraphs = ["This is to certify that {{first_name}} {{surname}} is a customer of {{company_name}}.",
                      "The account balance on {{as_of}} is {{balance}} AMD."] + extra_lines
    elif kind == "Reference letter":
        d = {"title": title, "inputs": ["customer"], "query": "customer_get"}
        paragraphs = ["To whom it may concern,",
                      "This is to confirm that {{first_name}} {{surname}} is a customer of {{company_name}}.",
                      "Date of birth: {{birth_date}}",
                      "Address: {{address}}",
                      "This letter is issued upon the customer's request."] + extra_lines
    elif kind == "Transaction receipt":
        d = {"title": title, "inputs": ["customer", "transaction"],
             "query": "transaction_get",
             "info_lines": ["Customer: {{first_name}} {{surname}}"]}
        paragraphs = ["Transaction: {{tx_id}}",
                      "Date: {{tx_date}}",
                      "Type: {{tx_type}} ({{direction}})",
                      "Amount: {{amount}} AMD",
                      "Description: {{description}}",
                      "This receipt confirms that the transaction above was processed."] + extra_lines
    else:
        d = {"title": title, "inputs": ["customer"], "query": "customer_get"}
        paragraphs = ["Customer: {{first_name}} {{surname}}.",
                      "Company: {{company_name}}."] + extra_lines
    if paragraphs:
        d["paragraphs"] = paragraphs
    return d

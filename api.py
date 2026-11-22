"""
api.py
The REST API (FastAPI): the same logic as the Streamlit screen, no UI.
Run:   uvicorn api:app --reload
Try:   http://localhost:8000/docs   (interactive page, press "Authorize" and log in)
Every call needs HTTP Basic login (a user from the users table).
"""

import logging

from fastapi import Depends, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

import service
from auth import check_password, hash_password
from db import (get_company_summary, get_issued_files, get_user, log_audit, ping,
                search_customers, search_custom_tables, search_issued)
from form0 import MIME
from form_store import find_forms, list_versions, load_form
from rtf_import import apply_plan, decide, default_name, read_rtf

log = logging.getLogger("bank_forms")
MAX_RTF_BYTES = 5 * 1024 * 1024
_DUMMY_HASH = hash_password("not-a-real-password")   # so an unknown user takes as long as a wrong password
app = FastAPI(title="Bank forms API")
security = HTTPBasic()

# ============================================================
# 1. LOGIN AND ERRORS
# ============================================================

def current_user(creds: HTTPBasicCredentials = Depends(security)):
    user = get_user(creds.username)
    if user is None:
        check_password(creds.password, _DUMMY_HASH)
    if not user or not check_password(creds.password, user[2]):
        raise HTTPException(401, "Wrong username or password",
                            headers={"WWW-Authenticate": "Basic"})
    return {"name": user[1], "role": user[3]}

def admin_only(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admins only")
    return user

@app.exception_handler(ValueError)
async def bad_input(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(Exception)
async def server_error(request, exc):
    log.error("API error", exc_info=exc)       # the real error stays in the log
    return JSONResponse(status_code=500, content={"detail": "Something went wrong."})

# ============================================================
# 2. FORMS
# ============================================================

class FormBody(BaseModel):
    definition: dict

@app.get("/health")
def health():
    db_alive = ping()
    if not db_alive:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})
    return {"status": "ok", "database": "connected"}

@app.get("/forms")
def forms(term: str = "", limit: int = Query(20, ge=1, le=200), user=Depends(current_user)):
    return {"forms": find_forms(term.strip(), limit)}

@app.get("/forms/{name}")
def form(name: str, version: int | None = None, user=Depends(current_user)):
    versions = list_versions(name)
    if not versions or (version is not None and version not in versions):
        raise HTTPException(404, "Form or version not found")
    return {"name": name, "versions": versions, "version": version or versions[0],
            "definition": load_form(name, version)}

@app.post("/forms/{name}", status_code=201)
def create_form(name: str, body: FormBody, user=Depends(admin_only)):
    """Save a recipe as the next version of this form."""
    return {"name": name, "version": service.save_new_form_version(name, body.definition, user["name"])}

# ============================================================
# 3. DOCUMENTS
# ============================================================

class IssueBody(BaseModel):
    form: str
    version: int | None = None     # empty = newest
    inputs: dict                   # what the form asks for, e.g. customer_id, date_from, date_to

@app.post("/documents", status_code=201)
def issue(body: IssueBody, user=Depends(current_user)):
    doc_no, formats = service.issue(body.form, body.version, body.inputs, user["name"])
    return {"doc_no": doc_no, "formats": formats}

@app.get("/documents")
def documents(term: str = "", limit: int = Query(50, ge=1, le=200), user=Depends(current_user)):
    rows = search_issued(term, limit)
    return {"documents": [{"doc_no": r[0], "form": r[1], "version": r[2], "customer_id": r[3],
                           "issued_at": r[4].isoformat(), "issued_by": r[5]} for r in rows]}

@app.get("/documents/{doc_no}/{fmt}")
def download(doc_no: str, fmt: str, user=Depends(current_user)):
    files = get_issued_files(doc_no)
    fmt = fmt.upper()
    if fmt not in files:
        raise HTTPException(404, "No such document or format")
    log_audit(user["name"], "download", None, doc_no + " " + fmt)
    return Response(files[fmt], media_type=MIME[fmt],
                    headers={"Content-Disposition": 'attachment; filename="' + doc_no + "." + fmt.lower() + '"'})

# ============================================================
# 4. CUSTOMERS AND COMPANIES
# ============================================================

@app.get("/customers")
def customers(term: str = "", limit: int = Query(20, ge=1, le=200), user=Depends(current_user)):
    return {"customers": [{"customer_id": r[0], "first_name": r[1], "surname": r[2]}
                          for r in search_customers(term, limit)]}

@app.get("/companies")
def companies(user=Depends(current_user)):
    return {"companies": [{"company_id": r[0], "name": r[1], "customers": r[3],
                           "transactions": r[4], "total": str(r[5])}   # exact, as text
                          for r in get_company_summary()]}

# ============================================================
# 5. RTF IMPORT & CUSTOM TABLES
# ============================================================

@app.post("/import/rtf", status_code=201)
async def import_rtf(file: UploadFile = File(...), name: str = "", user=Depends(admin_only)):
    """Upload an RTF file (up to 5MB) to import as a reusable form template or data table."""
    data = await file.read(MAX_RTF_BYTES + 1)      # never load more than the limit into memory
    if len(data) > MAX_RTF_BYTES:
        raise HTTPException(413, "File exceeds 5MB limit")
    try:
        paras, tables = read_rtf(data)
        found = decide(paras, tables)
    except ValueError as e:
        raise HTTPException(422, str(e))

    kind = found["kind"]
    plan = found["options"][kind]
    target_name = default_name(name) if name else default_name(file.filename or "import")
    msg = apply_plan(kind, plan, None, target_name, user["name"], file.filename or "", data)
    return {"status": "success", "kind": kind, "target": target_name, "message": msg}

@app.get("/tables")
def list_tables(term: str = "", limit: int = Query(50, ge=1, le=200), user=Depends(current_user)):
    """List custom tables stored in the database."""
    rows = search_custom_tables(term.strip(), limit)
    return {"tables": [{"table_id": r[0], "name": r[1], "title": r[2], "columns": r[4], "rows": r[5]}
                       for r in rows]}

@app.get("/tables/{name}")
def get_table_details(name: str, user=Depends(current_user)):
    """Fetch schema and details for a specific custom table."""
    try:
        tbl = service.get_table(name)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return tbl

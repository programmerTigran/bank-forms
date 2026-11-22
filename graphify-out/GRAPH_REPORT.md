# Graph Report - bank-forms  (2026-11-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 497 nodes · 1023 edges · 73 communities (20 shown, 53 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fd942c00`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- app.py
- tables.py
- api.py
- rtf_import.py
- load
- form0.py
- make_page
- form_store.py
- seed_users.py
- service.py
- 001_users_audit_counter.sql
- _fetchall
- get_connection
- make_docx
- auth.py
- documents.py
- has_logo
- make_pdf
- edit_section
- db.py
- seed_demo.py
- _clean
- get_slogan
- make_files
- 005_custom_tables.sql
- fill
- Money
- 007_rtf_imports.sql

## God Nodes (most connected - your core abstractions)
1. `load()` - 37 edges
2. `log_audit()` - 17 edges
3. `_fetchall()` - 16 edges
4. `get_connection()` - 16 edges
5. `_fetchone()` - 16 edges
6. `make_page()` - 16 edges
7. `build_doc()` - 16 edges
8. `fix()` - 15 edges
9. `show_rtf_import()` - 13 edges
10. `show_table()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `cached_customer_count()` --calls--> `get_company_customer_count()`  [EXTRACTED]
  pages/companies.py → db.py
- `cached_customers()` --calls--> `get_company_customers()`  [EXTRACTED]
  pages/companies.py → db.py
- `cached_logo()` --calls--> `get_company_logo_by_id()`  [EXTRACTED]
  pages/companies.py → db.py
- `cached_summary()` --calls--> `get_company_summary()`  [EXTRACTED]
  pages/companies.py → db.py
- `show_company()` --calls--> `get_slogan()`  [EXTRACTED]
  pages/companies.py → documents.py

## Import Cycles
- None detected.

## Communities (73 total, 53 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.06
Nodes (35): input_date(), input_dates(), input_filters(), input_transaction(), issued_page(), main(), new_form_dialog(), count_customer_transactions() (+27 more)

### Community 1 - "tables.py"
Cohesion: 0.08
Nodes (25): count_custom_rows(), count_custom_tables(), search_custom_tables(), format_cell(), bump(), done(), gen(), main() (+17 more)

### Community 2 - "api.py"
Cohesion: 0.07
Nodes (22): bad_input(), companies(), create_form(), customers(), documents(), download(), FormBody, forms() (+14 more)

### Community 3 - "rtf_import.py"
Cohesion: 0.08
Nodes (21): fix(), fonitech_to_unicode(), looks_fonitech(), block_lines(), build_form(), build_row(), build_table(), decide() (+13 more)

### Community 4 - "load"
Cohesion: 0.11
Nodes (12): create_custom_table(), _fetchone(), get_company_customer_count(), get_company_logo(), get_company_logo_by_id(), get_custom_table(), get_rtf_file(), get_user() (+4 more)

### Community 5 - "form0.py"
Cohesion: 0.10
Nodes (3): add_currency(), make_csv(), total_row()

### Community 6 - "make_page"
Cohesion: 0.14
Nodes (10): form(), create_form_section(), make_page(), issue_document(), unfilled_placeholders(), list_versions(), load_form(), available_formats() (+2 more)

### Community 7 - "form_store.py"
Cohesion: 0.17
Nodes (8): default_form(), find_forms(), form_exists(), list_forms(), Base, Company, Customer, DocumentTemplate

### Community 8 - "seed_users.py"
Cohesion: 0.17
Nodes (5): add_user(), new_connection(), main(), move_dates_last(), main()

### Community 9 - "service.py"
Cohesion: 0.18
Nodes (7): get_customer(), build_doc(), format_value(), table_style(), customer_inputs(), to_date(), validate_definition()

### Community 10 - "001_users_audit_counter.sql"
Cohesion: 0.16
Nodes (10): idx_transactions_customer, transactions, audit_log, doc_counter, idx_audit_customer, idx_document_log_customer, users, create_form_version() (+2 more)

### Community 11 - "_fetchall"
Cohesion: 0.16
Nodes (7): _fetchall(), forms_using_table(), get_company_customers(), get_custom_rows(), get_transactions_between(), set_company_logo(), main()

### Community 12 - "get_connection"
Cohesion: 0.18
Nodes (5): add_custom_rows(), delete_custom_table(), get_connection(), run_query(), main()

### Community 13 - "make_docx"
Cohesion: 0.17
Nodes (5): add_text(), line_below(), make_docx(), make_rtf(), shade()

### Community 14 - "auth.py"
Cohesion: 0.25
Nodes (3): current_user(), check_password(), hash_password()

### Community 16 - "has_logo"
Cohesion: 0.22
Nodes (4): has_logo(), logo_mime(), make_html(), shares()

### Community 17 - "make_pdf"
Cohesion: 0.28
Nodes (5): make_pdf(), page_number(), para(), pdf_header(), pdf_table()

### Community 18 - "edit_section"
Cohesion: 0.25
Nodes (4): edit_section(), create_form_version(), save_form(), save_new_form_version()

### Community 21 - "_clean"
Cohesion: 0.33
Nodes (3): _clean(), columns_from_rows(), custom_columns()

### Community 24 - "005_custom_tables.sql"
Cohesion: 0.83
Nodes (3): custom_rows, custom_tables, idx_custom_rows_table

## Knowledge Gaps
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load()` connect `load` to `app.py`, `tables.py`, `api.py`, `make_page`, `seed_users.py`, `service.py`, `_fetchall`, `get_connection`, `edit_section`, `db.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `log_audit()` (e.g. with `issued_page()` and `make_page()`) actually correct?**
  _`log_audit()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05839727195225917 - nodes in this community are weakly interconnected._
- **Why does `fix()` connect `rtf_import.py` to `load`, `make_page`, `form_store.py`, `get_connection`, `edit_section`, `db.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `tables.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07777777777777778 - nodes in this community are weakly interconnected._
- **Why does `log_audit()` connect `app.py` to `tables.py`, `api.py`, `load`, `make_page`, `service.py`, `get_connection`, `edit_section`, `db.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06620209059233449 - nodes in this community are weakly interconnected._
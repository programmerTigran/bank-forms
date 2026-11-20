INSERT INTO document_templates (name, version, definition) VALUES
('balance_certificate', 1, $json$
{
  "title": "Balance certificate",
  "inputs": ["customer", "date"],
  "query": "balance_on_date",
  "paragraphs": [
    "This is to certify that {{first_name}} {{surname}} is a customer of {{company_name}}.",
    "The account balance on {{as_of}} is {{balance}} AMD.",
    "This certificate is issued upon the customer's request."
  ]
}
$json$::jsonb),
('account_statement', 1, $json$
{
  "title": "Account statement",
  "inputs": ["customer", "dates", "filters"],
  "query": "tx_between",
  "info_lines": [
    "Customer: {{first_name}} {{surname}}",
    "Period: {{date_from}} - {{date_to}}"
  ],
  "columns": [
    {"field": "tx_date", "label": "Date", "type": "date", "width": 1},
    {"field": "tx_type", "label": "Type", "type": "text", "width": 1},
    {"field": "amount", "label": "Amount", "type": "money", "align": "right", "width": 1},
    {"field": "description", "label": "Description", "type": "text", "width": 3}
  ],
  "empty_text": "No transactions in this period."
}
$json$::jsonb)
ON CONFLICT (name, version) DO NOTHING;
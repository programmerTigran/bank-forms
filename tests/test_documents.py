"""Focused regression tests for document template filling and RTF encoding."""
import json
import unittest
from pathlib import Path

from documents import fill_blocks, rtf_escape


class DocumentTests(unittest.TestCase):
    def test_customer_details_template_has_valid_block_shape(self):
        path = Path(__file__).resolve().parents[1] / "document_templates" / "customer_details.v1.json"
        template = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("page", template)
        self.assertTrue(template["blocks"])
        for block in template["blocks"]:
            self.assertTrue({"text", "size", "bold", "align", "space_after"} <= block.keys())

    def test_fill_blocks_replaces_values_without_mutating_template(self):
        template = {"blocks": [{"text": "Hello {{first_name}}", "size": 12}]}
        filled = fill_blocks(template, {"first_name": "Աննա"})
        self.assertEqual(filled[0]["text"], "Hello Աննա")
        self.assertEqual(template["blocks"][0]["text"], "Hello {{first_name}}")

    def test_rtf_escape_handles_armenian_characters(self):
        self.assertEqual(rtf_escape("Ա"), "\\u1329?")


if __name__ == "__main__":
    unittest.main()

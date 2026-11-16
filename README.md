"""Compatibility facade for the refactored document builders."""

from document_builders import *  # noqa: F401,F403

__all__ = [
    "build_values",
    "fill_blocks",
    "fill_text",
    "get_slogan",
    "today_armenia",
    "make_rtf",
    "rtf_escape",
    "rtf_paragraph",
    "make_pdf",
    "register_fonts",
    "pdf_to_blocks",
    "pdf_to_rtf",
    "rtf_to_blocks",
    "rtf_to_pdf",
    "build_letter",
    "make_letter_html",
    "make_letter_pdf",
    "make_letter_rtf",
    "build_statement",
    "make_statement_html",
    "make_statement_pdf",
    "make_statement_rtf",
]


# NOTE: the actual implementation now lives under document_builders/ and this file
# maintains backwards compatibility for the rest of the app.


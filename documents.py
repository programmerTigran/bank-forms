"""
documents.py
Shared constants and small helpers for form0.py and the pages:
money formatting, fonts, slogans, logo check.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# 1. CONSTANTS
# ============================================================

TIMEZONE = "Asia/Yerevan"
DATE_FORMAT = "%d/%m/%Y"
DEFAULT_CURRENCY = "AMD"

FONTS_DIR = Path(__file__).parent / "fonts"
PDF_FONT = "DejaVuSans"
PDF_FONT_BOLD = "DejaVuSans-Bold"
DEFAULT_FONT_NAME = "DejaVu Sans"

LETTER_MARGIN_PT = 56
LOGO_HEIGHT_PT = 50
ACCENT_HEX = "#1F4E8C"
GRAY_HEX = "#666666"
DEFAULT_SLOGAN = "We are strong together"
SLOGANS = {"Ardshin": "We are strong together",
           "Ameria": "Bank about people",
           "Adidas": "Impossible is nothing",
           "Puma": "Forever Faster"}

# ============================================================
# 2. HELPERS
# ============================================================

def today_armenia():
    """Today's date in Yerevan time as dd/mm/yyyy."""
    return datetime.now(ZoneInfo(TIMEZONE)).strftime(DATE_FORMAT)

def money(value):
    """Amount with 2 decimals and thousands commas. Decimal stays exact (no float)."""
    if value is None:
        return "0.00"
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return format(value, ",.2f")

def money_cur(value, currency=DEFAULT_CURRENCY):
    """money() plus the currency, e.g. '1,500.00 AMD'."""
    return money(value) + " " + currency

def register_fonts():
    """Register the DejaVu fonts (from fonts/) with reportlab, once."""
    if PDF_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(PDF_FONT, str(FONTS_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont(PDF_FONT_BOLD, str(FONTS_DIR / "DejaVuSans-Bold.ttf")))

def get_slogan(company_name):
    """Slogan of a company (matched by name prefix, any case)."""
    name = str(company_name).lower()
    for prefix, slogan in SLOGANS.items():
        if name.startswith(prefix.lower()):
            return slogan
    return DEFAULT_SLOGAN

def has_logo(header):
    """True if the header has a logo image (bytes)."""
    return bool(header["logo"])

def logo_mime(data):
    """'image/png' or 'image/jpeg', from the first bytes of the image."""
    return "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"

import re
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Yerevan"
DATE_FORMAT = "%d/%m/%Y"

DEFAULT_FONT_NAME = "DejaVu Sans"
DEFAULT_MARGIN_PT = 72
DEFAULT_SIZE_PT = 12

LETTER_MARGIN_PT = 56
LOGO_HEIGHT_PT = 50
ACCENT_HEX = "#1F4E8C"
GRAY_HEX = "#666666"
DEFAULT_SLOGAN = "We are strong together"
SLOGANS = {
    "Ardshin": "We are strong together",
    "Ameria": "Bank about people",
    "Adidas": "Impossible is nothing",
    "Puma": "Forever Faster",
}


def today_armenia():
    """Return today's date in Yerevan time as dd/mm/yyyy."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.strftime(DATE_FORMAT)


def build_values(first_name, surname, company_name=""):
    """Return the values that fill the {{placeholders}} in a template."""
    return {
        "first_name": first_name,
        "surname": surname,
        "company_name": company_name,
        "current_date": today_armenia(),
    }


def fill_text(text, values):
    """Replace every {{key}} in one line of text with its value."""
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def fill_blocks(template, values):
    """Return a copy of the template blocks with all placeholders filled."""
    filled = []
    for block in template["blocks"]:
        new_block = dict(block)
        new_block["text"] = fill_text(block["text"], values)
        filled.append(new_block)
    return filled


def get_slogan(company_name):
    """Return the slogan of a company (matched by name prefix, any case)."""
    name = str(company_name).lower()
    for prefix, slogan in SLOGANS.items():
        if name.startswith(prefix.lower()):
            return slogan
    return DEFAULT_SLOGAN

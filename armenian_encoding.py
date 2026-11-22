"""
armenian_encoding.py
Old Armenian fonts (Fonitech, 8-bit codes) -> modern Unicode Armenian (Ա-֏).
fix() converts old text anywhere inside a str, list, tuple or dict.
Used by db.py, form_store.py and rtf_import.py.
"""

# ============================================================
# 1. THE FONITECH MAP
# ============================================================

FONITECH_MAP = {
    # Uppercase Armenian
    "²": "Ա",
    "´": "Բ",
    "º": "Ե",
    "Ü": "Ն",

    # Lowercase Armenian
    "³": "ա",
    "µ": "բ",
    "·": "գ",
    "¹": "դ",
    "»": "ե",
    "½": "զ",
    "¨": "և",
    "Á": "ը",
    "Ã": "թ",
    "Å": "ժ",
    "Ç": "ի",
    "É": "լ",
    "Ù": "մ",
    "Ý": "ն",
    "á": "ո",
    "å": "պ",
    "ñ": "ր",
    "ë": "ս",
    "ï": "տ",
    "õ": "ւ",
    "¿": "է",
    "û": "օ",
    "ý": "ֆ",
    "ù": "ք",
    "Õ": "ղ",
    "Í": "ծ",
    "Ï": "կ",
    "Ñ": "հ",
    "×": "ճ",
    "ß": "շ",
    "é": "ռ",
    "í": "վ",
    "ó": "ց",
    "Ë": "խ",

    # Additional characters found in your sample
    "Û": "յ",
    "Ó": "Ձ",
    "÷": "փ",
    "£": "։",
    "«": ",",
}

# ============================================================
# 2. CONVERT
# ============================================================

def fonitech_to_unicode(text):
    """Convert Fonitech Armenian text to Unicode."""
    return "".join(FONITECH_MAP.get(char, char) for char in text)

def looks_fonitech(text):
    """Old-font text: has Fonitech letters, but no Armenian letters and no plain A-Z/a-z.
    (So German/French words like 'Straße' or 'Müller' are left alone.)"""
    letters = sum(1 for ch in text if FONITECH_MAP.get(ch, "").isalpha())
    if letters < 2:                      # '5 × 3' or '£100' must stay as they are
        return False
    return not any("Ա" <= ch <= "֏" or ("a" <= ch.lower() <= "z") for ch in text)

def fix(value):
    """Convert old Fonitech text to Unicode anywhere inside str / list / tuple / dict."""
    if isinstance(value, str):
        return fonitech_to_unicode(value) if looks_fonitech(value) else value
    if isinstance(value, list):
        return [fix(v) for v in value]
    if isinstance(value, tuple):
        return tuple(fix(v) for v in value)
    if isinstance(value, dict):
        return {fix(k): fix(v) for k, v in value.items()}
    return value
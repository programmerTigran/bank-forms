
# armenian_encoding.py

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

def fonitech_to_unicode(text: str) -> str:
    """Convert Fonitech Armenian text to Unicode."""
    return "".join(FONITECH_MAP.get(char, char) for char in text)

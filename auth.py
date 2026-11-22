"""
auth.py
Password hashing (scrypt, standard library only). No Streamlit here,
so scripts and tests can import it.
"""

# ============================================================
# 1. IMPORTS AND CONSTANTS
# ============================================================

import hashlib
import hmac
import os

SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}

# ============================================================
# 2. HASHING AND CHECKING
# ============================================================

def hash_password(password):
    """Return 'salt$hash' (both hex). A new random salt every time."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return salt.hex() + "$" + digest.hex()

def check_password(password, stored):
    """True if the password matches the stored 'salt$hash'."""
    salt_hex, digest_hex = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)

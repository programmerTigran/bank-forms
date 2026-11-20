"""
Create a user. Run from the project root:
    python scripts/seed_users.py <username> <clerk|admin>
The password is asked (hidden), never typed in the command.
"""

import sys
from getpass import getpass
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from auth import hash_password
from db import add_user

def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("clerk", "admin"):
        sys.exit("Usage: python scripts/seed_users.py <username> <clerk|admin>")
    password = getpass("Password (min 8 chars): ")
    if len(password) < 8:
        sys.exit("Too short.")
    if password != getpass("Repeat: "):
        sys.exit("Passwords differ.")
    add_user(sys.argv[1], hash_password(password), sys.argv[2])
    print("Created " + sys.argv[1] + " (" + sys.argv[2] + ")")

main()

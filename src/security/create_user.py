"""Create a login, or change its password.

    python -m src.security.create_user someone@example.com

The password is prompted for, or read from the APP_USER_PASSWORD variable.
"""

import getpass
import os
import sys

from src.mcp_server.db import save_user
from src.security.auth import MAX_PASSWORD_BYTES, hash_password


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m src.security.create_user <email>")

    email = sys.argv[1].strip().lower()
    password = os.environ.get("APP_USER_PASSWORD") or getpass.getpass("Password: ")

    if not 8 <= len(password.encode()) <= MAX_PASSWORD_BYTES:
        sys.exit(f"Password must be 8 to {MAX_PASSWORD_BYTES} bytes long.")

    save_user(email, hash_password(password))
    print(f"Saved login for {email}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
CLI tool to create admin accounts.

Usage:
    python create_admin.py <username> <password> [full_name]

Example:
    python create_admin.py admin123 securepassword123 "John Admin"
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.security import hash_password
from app.crud.admin import admin_exists, create_admin, get_admin_by_username
from app.db.session import SessionLocal


def main():
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password> [full_name]")
        print("Example: python create_admin.py admin123 securepassword123 'John Admin'")
        sys.exit(1)

    username = sys.argv[1].strip()
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else None

    if len(username) < 3:
        print("✗ Error: Username must be at least 3 characters long")
        sys.exit(1)

    if len(password) < 8:
        print("✗ Error: Password must be at least 8 characters long")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Check if username already exists
        existing = get_admin_by_username(db, username)
        if existing:
            print(f"✗ Error: Admin with username '{username}' already exists (ID: {existing.id})")
            sys.exit(1)

        # Create new admin
        admin = create_admin(db, username, password, full_name)
        print(f"✓ Success! Admin account created")
        print(f"  ID:       {admin.id}")
        print(f"  Username: {admin.username}")
        print(f"  Full Name: {admin.full_name or 'Not set'}")
        print(f"  Created:   {admin.created_at}")
        print(f"\n✓ You can now login at the admin dashboard with:")
        print(f"  Username: {admin.username}")
        print(f"  Password: [the password you provided]")

    except Exception as e:
        print(f"✗ Error creating admin: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

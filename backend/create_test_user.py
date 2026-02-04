#!/usr/bin/env python
"""Create test user for testing the API."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User

def create_test_user():
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            print(f"✓ Test user already exists: {existing_user.email}")
            print(f"  Email: test@example.com")
            print(f"  Password: password123")
            return
        
        # Create new user
        user = User(
            email="test@example.com",
            password_hash=hash_password("password123"),
            is_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✓ Test user created: {user.email}")
        print(f"  Email: test@example.com")
        print(f"  Password: password123")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()

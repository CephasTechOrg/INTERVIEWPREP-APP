#!/usr/bin/env python
"""Mark a user as admin."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal
from app.models.user import User

def mark_user_as_admin(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"✗ User not found: {email}")
            return
        
        user.is_admin = True
        db.commit()
        db.refresh(user)
        
        print(f"✓ User marked as admin: {user.email}")
        print(f"  Email: {user.email}")
        print(f"  Admin: {user.is_admin}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        print("Example: python make_admin.py test@example.com")
        sys.exit(1)
    
    email = sys.argv[1].strip().lower()
    mark_user_as_admin(email)

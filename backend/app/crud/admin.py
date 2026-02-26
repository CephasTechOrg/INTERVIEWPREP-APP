from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.admin import AdminAccount


def create_admin(db: Session, username: str, password: str, full_name: str | None = None) -> AdminAccount:
    """Create a new admin account."""
    admin = AdminAccount(
        username=username.strip().lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def get_admin_by_username(db: Session, username: str) -> AdminAccount | None:
    """Get admin by username."""
    return db.query(AdminAccount).filter(AdminAccount.username == username.strip().lower()).first()


def get_admin_by_id(db: Session, admin_id: int) -> AdminAccount | None:
    """Get admin by ID."""
    return db.query(AdminAccount).filter(AdminAccount.id == admin_id).first()


def authenticate_admin(db: Session, username: str, password: str) -> AdminAccount | None:
    """Authenticate admin with username and password."""
    admin = get_admin_by_username(db, username)
    if not admin or not admin.is_active:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


def update_admin_last_login(db: Session, admin_id: int) -> AdminAccount | None:
    """Update admin's last login timestamp."""
    admin = get_admin_by_id(db, admin_id)
    if admin:
        admin.last_login = datetime.now(UTC)
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin


def get_all_admins(db: Session) -> list[AdminAccount]:
    """Get all admin accounts."""
    return db.query(AdminAccount).order_by(AdminAccount.created_at.desc()).all()


def deactivate_admin(db: Session, admin_id: int) -> AdminAccount | None:
    """Deactivate an admin account."""
    admin = get_admin_by_id(db, admin_id)
    if admin:
        admin.is_active = False
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin


def admin_exists(db: Session) -> bool:
    """Check if any admin accounts exist."""
    return db.query(AdminAccount).first() is not None

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from datetime import datetime, timedelta, timezone
import secrets


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, password: str, full_name: str | None) -> User:
    token = secrets.token_urlsafe(32)
    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        is_verified=False,
        verification_token=token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_verification_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    db.add(user)
    db.commit()
    db.refresh(user)
    return token


def verify_user(db: Session, token: str) -> User | None:
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        return None
    user.is_verified = True
    user.verification_token = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_reset_token(db: Session, user: User, expires_minutes: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    db.add(user)
    db.commit()
    db.refresh(user)
    return token


def reset_password(db: Session, token: str, new_password: str) -> User | None:
    now = datetime.now(timezone.utc)
    user = (
        db.query(User)
        .filter(User.reset_token == token, User.reset_token_expires_at != None, User.reset_token_expires_at > now)
        .first()
    )
    if not user:
        return None
    user.password_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

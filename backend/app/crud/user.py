import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token, token_matches, verify_password
from app.models.user import User


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _generate_reset_code() -> str:
    return _generate_verification_code()


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str | None,
    is_verified: bool = False,
    verification_code: str | None = None,
    role_pref: str | None = None,
    profile: dict | None = None,
) -> User:
    token = None
    if not is_verified:
        token = verification_code or _generate_verification_code()
    role_pref = (role_pref or "").strip() or "SWE Intern"
    user = User(
        email=email,
        full_name=full_name,
        role_pref=role_pref,
        profile=profile or {},
        password_hash=hash_password(password),
        is_verified=is_verified,
        verification_token=token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_from_hash(
    db: Session,
    email: str,
    password_hash: str,
    full_name: str | None,
    is_verified: bool = True,
    verification_code: str | None = None,
    role_pref: str | None = None,
    profile: dict | None = None,
) -> User:
    token = None
    if not is_verified:
        token = verification_code or _generate_verification_code()
    role_pref = (role_pref or "").strip() or "SWE Intern"
    user = User(
        email=email,
        full_name=full_name,
        role_pref=role_pref,
        profile=profile or {},
        password_hash=password_hash,
        is_verified=is_verified,
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
    user.last_login_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    user: User,
    full_name: str | None = None,
    role_pref: str | None = None,
    profile: dict | None = None,
) -> User:
    if full_name is not None:
        cleaned = full_name.strip()
        user.full_name = cleaned or None
    if role_pref is not None:
        cleaned = role_pref.strip()
        user.role_pref = cleaned or "SWE Intern"
    if profile is not None:
        existing = user.profile if isinstance(user.profile, dict) else {}
        merged = dict(existing)
        merged.update(profile)
        user.profile = merged
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_verification_token(db: Session, user: User) -> str:
    token = _generate_verification_code()
    user.verification_token = hash_token(token)
    db.add(user)
    db.commit()
    db.refresh(user)
    return token


def verify_user(db: Session, email: str, code: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.verification_token:
        return None
    if not token_matches(code, user.verification_token):
        return None
    user.is_verified = True
    user.verification_token = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_reset_token(db: Session, user: User, expires_minutes: int = 30) -> str:
    token = _generate_reset_code()
    user.reset_token = hash_token(token)
    user.reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    db.add(user)
    db.commit()
    db.refresh(user)
    return token


def reset_password(db: Session, token: str, new_password: str, email: str | None = None) -> User | None:
    now = datetime.now(UTC)
    token_hash = hash_token(token)
    query = db.query(User).filter(
        User.reset_token == token_hash,
        User.reset_token_expires_at.isnot(None),
        User.reset_token_expires_at > now,
    )
    if email:
        query = query.filter(User.email == email)
    user = query.first()
    if not user:
        return None
    user.password_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ban_user(db: Session, user_id: int, reason: str | None = None) -> User | None:
    """Ban a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_banned = True
        user.ban_reason = reason
        user.banned_at = datetime.now(UTC)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def unban_user(db: Session, user_id: int) -> User | None:
    """Unban a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_banned = False
        user.ban_reason = None
        user.banned_at = None
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_all_users_paginated(
    db: Session, skip: int = 0, limit: int = 50, filter_banned: bool | None = None
) -> list[User]:
    """Get all users with optional pagination and filtering."""
    query = db.query(User)

    if filter_banned is not None:
        query = query.filter(User.is_banned == filter_banned)

    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


def get_user_count(db: Session, filter_banned: bool | None = None) -> int:
    """Get total user count with optional filtering."""
    query = db.query(User)
    if filter_banned is not None:
        query = query.filter(User.is_banned == filter_banned)
    return query.count()


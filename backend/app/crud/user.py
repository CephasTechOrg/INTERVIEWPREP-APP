import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token, token_matches, verify_password
from app.models.user import User


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str | None,
    is_verified: bool = False,
    verification_code: str | None = None,
) -> User:
    token = None
    if not is_verified:
        token = verification_code or _generate_verification_code()
    user = User(
        email=email,
        full_name=full_name,
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
) -> User:
    token = None
    if not is_verified:
        token = verification_code or _generate_verification_code()
    user = User(
        email=email,
        full_name=full_name,
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
    token = secrets.token_urlsafe(32)
    user.reset_token = hash_token(token)
    user.reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    db.add(user)
    db.commit()
    db.refresh(user)
    return token


def reset_password(db: Session, token: str, new_password: str) -> User | None:
    now = datetime.now(UTC)
    token_hash = hash_token(token)
    user = (
        db.query(User)
        .filter(
            User.reset_token.in_([token, token_hash]),
            User.reset_token_expires_at is not None,
            User.reset_token_expires_at > now,
        )
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

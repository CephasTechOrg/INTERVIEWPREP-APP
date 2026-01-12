import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.pending_signup import PendingSignup


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def get_by_email(db: Session, email: str) -> PendingSignup | None:
    return db.query(PendingSignup).filter(PendingSignup.email == email).first()


def upsert_pending_signup(
    db: Session,
    email: str,
    password_hash: str,
    full_name: str | None,
    expires_minutes: int = 30,
) -> tuple[PendingSignup, str]:
    code = _generate_verification_code()
    expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    existing = get_by_email(db, email)
    if existing:
        existing.password_hash = password_hash
        existing.full_name = full_name
        existing.verification_code = code
        existing.expires_at = expires_at
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing, code

    pending = PendingSignup(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        verification_code=code,
        expires_at=expires_at,
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return pending, code


def verify_pending(db: Session, email: str, code: str) -> PendingSignup | None:
    pending = get_by_email(db, email)
    if not pending or pending.verification_code != code:
        return None
    if pending.expires_at:
        now = datetime.now(UTC)
        if pending.expires_at < now:
            return None
    return pending


def delete_pending(db: Session, pending: PendingSignup) -> None:
    db.delete(pending)
    db.commit()

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Use Argon2 (recommended; avoids bcrypt issues on Python 3.13 Windows)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGORITHM = "HS256"


def _prehash_password(password: str) -> str:
    """
    Optional pre-hash (SHA-256) to normalize input length/encoding.
    Not strictly required for Argon2, but harmless and consistent.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    safe = _prehash_password(password)
    return pwd_context.hash(safe)


def verify_password(password: str, hashed: str) -> bool:
    safe = _prehash_password(password)
    return pwd_context.verify(safe, hashed)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

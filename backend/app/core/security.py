import hashlib
import hmac
from datetime import UTC, datetime, timedelta
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
    try:
        if pwd_context.verify(safe, hashed):
            return True
    except Exception:
        return False
    # Legacy fallback for hashes created before pre-hashing was added.
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False

def hash_token(token: str) -> str:
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def token_matches(raw: str, stored: str | None) -> bool:
    if not raw or not stored:
        return False
    try:
        hashed = hash_token(raw)
    except Exception:
        return False
    return hmac.compare_digest(stored, hashed)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_admin_access_token(admin_id: int, username: str, expires_hours: int = 24) -> str:
    """Create JWT token for admin with shorter expiry (24 hours)."""
    expire = datetime.now(UTC) + timedelta(hours=expires_hours)
    to_encode: dict[str, Any] = {
        "sub": str(admin_id),
        "username": username,
        "role": "admin",
        "type": "admin_token",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_admin_token(token: str) -> dict[str, Any]:
    """Verify and decode admin JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin" or payload.get("type") != "admin_token":
            return None
        return payload
    except Exception:
        return None


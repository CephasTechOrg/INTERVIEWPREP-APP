from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM, verify_admin_token
from app.crud.admin import get_admin_by_id
from app.crud.user import get_by_email
from app.db.session import SessionLocal
from app.models.admin import AdminAccount

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token.") from None

    user = get_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    if not getattr(user, "is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified. Use the 6-digit verification code.")
    profile = getattr(user, "profile", None) or {}
    if isinstance(profile, dict) and profile.get("deactivated"):
        raise HTTPException(status_code=403, detail="Account is deactivated.")
    return user


def get_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AdminAccount:
    """Dependency to get admin from token."""
    payload = verify_admin_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")

    admin_id = int(payload.get("sub"))
    admin = get_admin_by_id(db, admin_id)

    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account not found or inactive")

    return admin


from sqlalchemy.orm import Session
from fastapi import Request

from app.models.audit_log import AuditLog


def _safe_ip(request: Request | None) -> str | None:
    try:
        return request.client.host if request and request.client else None
    except Exception:
        return None


def _safe_agent(request: Request | None) -> str | None:
    try:
        return request.headers.get("user-agent")
    except Exception:
        return None


def log_audit(db: Session, action: str, user_id: int | None = None, metadata: dict | None = None, request: Request | None = None) -> None:
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            ip=_safe_ip(request),
            user_agent=_safe_agent(request),
            meta=metadata or {},
        )
        db.add(entry)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

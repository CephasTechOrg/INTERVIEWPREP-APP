import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_admin, get_db
from app.api.rate_limit import rate_limit
from app.core.security import create_admin_access_token
from app.crud.admin import authenticate_admin, update_admin_last_login
from app.crud.user import ban_user, get_all_users_paginated, get_user_count, unban_user
from app.models.interview_session import InterviewSession
from app.models.message import Message
from app.models.question import Question
from app.models.user import User
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    DashboardStats,
    UserBanRequest,
    UserDetailResponse,
)
from app.utils.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Admin login endpoint. Returns JWT token for admin operations."""
    username = payload.username.strip()
    rate_limit(request, key=f"admin_login:{request.client.host}:{username}", max_calls=5, window_sec=60)

    admin = authenticate_admin(db, username, payload.password)
    if not admin:
        logger.warning(f"Failed admin login attempt for username: {username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    update_admin_last_login(db, admin.id)
    token = create_admin_access_token(admin.id, admin.username)

    log_audit(db, "admin_login", user_id=None, metadata={"admin_id": admin.id}, request=request)

    return AdminLoginResponse(
        access_token=token,
        admin_id=admin.id,
        username=admin.username,
        full_name=admin.full_name,
    )


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    """Get dashboard statistics for admin panel."""
    total_users = db.query(User).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    banned_users = db.query(User).filter(User.is_banned == True).count()
    # Use 'stage' field - sessions not in 'done' stage are considered active
    active_interviews = db.query(InterviewSession).filter(InterviewSession.stage != "done").count()
    total_questions = db.query(Question).count()

    log_audit(db, "admin_view_stats", user_id=None, metadata={"admin_id": admin.id})

    return DashboardStats(
        total_users=total_users,
        verified_users=verified_users,
        banned_users=banned_users,
        active_interviews=active_interviews,
        total_questions=total_questions,
        timestamp=datetime.now(UTC),
    )


@router.get("/users", response_model=list[UserDetailResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    filter_banned: bool | None = Query(None),
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Get paginated list of all users with optional filtering."""
    users = get_all_users_paginated(db, skip=skip, limit=limit, filter_banned=filter_banned)
    log_audit(
        db,
        "admin_list_users",
        user_id=None,
        metadata={"admin_id": admin.id, "skip": skip, "limit": limit, "filter_banned": filter_banned},
    )
    return users


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user_detail(
    user_id: int,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    log_audit(db, "admin_view_user_detail", user_id=user_id, metadata={"admin_id": admin.id})
    return user


@router.post("/users/{user_id}/ban")
def ban_user_endpoint(
    user_id: int,
    payload: UserBanRequest,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Ban a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_banned:
        raise HTTPException(status_code=400, detail="User is already banned")

    banned_user = ban_user(db, user_id, payload.reason)
    log_audit(
        db,
        "admin_ban_user",
        user_id=user_id,
        metadata={"admin_id": admin.id, "reason": payload.reason},
    )

    return {
        "ok": True,
        "message": f"User {banned_user.email} has been banned",
        "user_id": banned_user.id,
    }


@router.post("/users/{user_id}/unban")
def unban_user_endpoint(
    user_id: int,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Unban a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_banned:
        raise HTTPException(status_code=400, detail="User is not banned")

    unbanned_user = unban_user(db, user_id)
    log_audit(db, "admin_unban_user", user_id=user_id, metadata={"admin_id": admin.id})

    return {
        "ok": True,
        "message": f"User {unbanned_user.email} has been unbanned",
        "user_id": unbanned_user.id,
    }


@router.get("/audit-logs")
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Get audit logs for admin actions."""
    try:
        from app.models.audit_log import AuditLog

        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        total = db.query(AuditLog).count()

        log_audit(
            db,
            "admin_view_audit_logs",
            user_id=None,
            metadata={"admin_id": admin.id, "skip": skip, "limit": limit},
        )

        # Map model fields to expected response format
        formatted_logs = [
            {
                "id": log.id,
                "action": log.action,
                "user_id": log.user_id,
                "admin_id": log.meta.get("admin_id") if log.meta else None,
                "metadata": log.meta,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "ip": log.ip,
            }
            for log in logs
        ]

        return {"logs": formatted_logs, "total": total, "skip": skip, "limit": limit}
    except ImportError:
        return {"logs": [], "total": 0, "skip": skip, "limit": limit, "note": "Audit log model not available"}


@router.get("/users-count")
def get_users_count(
    filter_banned: bool | None = Query(None),
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Get total count of users with optional filtering."""
    count = get_user_count(db, filter_banned=filter_banned)
    log_audit(
        db,
        "admin_get_user_count",
        user_id=None,
        metadata={"admin_id": admin.id, "filter_banned": filter_banned},
    )
    return {"total": count, "filter_banned": filter_banned}

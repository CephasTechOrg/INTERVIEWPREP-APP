import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_admin, get_db
from app.crud.feedback import get_feedback_stats
from app.crud.user import ban_user, get_all_users_paginated, get_user_count, unban_user
from app.models.evaluation import Evaluation
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.models.session_feedback import SessionFeedback
from app.models.user import User
from app.models.user_usage import UserUsage
from app.schemas.admin import (
    DashboardStats,
    UserBanRequest,
    UserDetailResponse,
)
from app.services.llm_client import get_llm_status
from app.utils.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


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
    search: str | None = Query(None, max_length=100),
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Get paginated list of all users with optional filtering and search."""
    q = db.query(User)
    if filter_banned is not None:
        q = q.filter(User.is_banned == filter_banned)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(
            (User.email.ilike(term)) | (User.full_name.ilike(term))
        )
    users = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    log_audit(
        db,
        "admin_list_users",
        user_id=None,
        metadata={"admin_id": admin.id, "skip": skip, "limit": limit, "filter_banned": filter_banned, "search": search},
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


@router.get("/users/{user_id}/detail")
def get_user_full_detail(
    user_id: int,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Get full user detail including usage stats and recent sessions."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    usage = db.query(UserUsage).filter(UserUsage.user_id == user_id).first()

    sessions_with_scores = (
        db.query(InterviewSession, Evaluation.overall_score)
        .outerjoin(Evaluation, Evaluation.session_id == InterviewSession.id)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.desc())
        .limit(10)
        .all()
    )

    feedback_count = db.query(SessionFeedback).filter(SessionFeedback.user_id == user_id).count()

    log_audit(db, "admin_view_user_detail", user_id=user_id, metadata={"admin_id": admin.id})

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_verified": user.is_verified,
        "is_banned": user.is_banned,
        "ban_reason": user.ban_reason,
        "banned_at": user.banned_at.isoformat() if user.banned_at else None,
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "role_pref": user.role_pref,
        "usage": {
            "chat_messages_today": usage.chat_messages_today,
            "chat_reset_date": usage.chat_reset_date.isoformat(),
            "tts_characters_month": usage.tts_characters_month,
            "usage_month": usage.usage_month.isoformat(),
            "total_chat_messages": usage.total_chat_messages,
            "total_tts_characters": usage.total_tts_characters,
            "total_interview_sessions": usage.total_interview_sessions,
        } if usage else None,
        "sessions": [
            {
                "id": s.id,
                "track": s.track,
                "difficulty": s.difficulty,
                "company_style": s.company_style,
                "stage": s.stage,
                "overall_score": score,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s, score in sessions_with_scores
        ],
        "feedback_count": feedback_count,
    }


@router.post("/users/{user_id}/reset-usage")
def reset_user_usage(
    user_id: int,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Reset a user's daily/monthly rate limit counters."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    usage = db.query(UserUsage).filter(UserUsage.user_id == user_id).first()
    if usage:
        usage.chat_messages_today = 0
        usage.tts_characters_month = 0
        db.commit()

    log_audit(
        db,
        "admin_reset_user_usage",
        user_id=user_id,
        metadata={"admin_id": admin.id},
    )
    return {"ok": True, "message": f"Usage counters reset for user {user.email}"}


@router.get("/system/health")
def get_system_health(admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    """Get system health status including AI/LLM status."""
    llm = get_llm_status()

    # Quick DB health check
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "online"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "llm": llm,
        "database": db_status,
        "timestamp": datetime.now(UTC).isoformat(),
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


@router.delete("/users/{user_id}")
def delete_user_endpoint(
    user_id: int,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete a user and all their data."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot delete admin users")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    email = user.email  # Store for audit log

    # Delete user (CASCADE will handle related records)
    db.delete(user)
    db.commit()

    log_audit(
        db,
        "admin_delete_user",
        user_id=None,  # User no longer exists
        metadata={"admin_id": admin.id, "deleted_email": email, "deleted_user_id": user_id},
    )

    return {"ok": True, "message": f"User {email} has been permanently deleted"}


@router.get("/feedback/stats")
def get_global_feedback_stats(
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Get platform-wide feedback statistics."""
    stats = get_feedback_stats(db, user_id=None)
    log_audit(db, "admin_view_feedback_stats", user_id=None, metadata={"admin_id": admin.id})
    return stats


@router.get("/feedback")
def get_all_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    min_rating: int | None = Query(None, ge=1, le=5),
    thumbs: str | None = Query(None, pattern="^(up|down)$"),
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """List all user feedback with user and session context."""
    q = db.query(SessionFeedback).order_by(SessionFeedback.created_at.desc())

    if min_rating is not None:
        q = q.filter(SessionFeedback.rating >= min_rating)
    if thumbs is not None:
        q = q.filter(SessionFeedback.thumbs == thumbs)

    total = q.count()
    records = q.offset(skip).limit(limit).all()

    # Enrich with user + session context
    result = []
    for fb in records:
        user = db.query(User).filter(User.id == fb.user_id).first()
        session = db.query(InterviewSession).filter(InterviewSession.id == fb.session_id).first()
        result.append({
            "id": fb.id,
            "session_id": fb.session_id,
            "user_id": fb.user_id,
            "user_email": user.email if user else None,
            "user_name": user.full_name if user else None,
            "session_track": session.track if session else None,
            "session_difficulty": session.difficulty if session else None,
            "session_company_style": session.company_style if session else None,
            "rating": fb.rating,
            "thumbs": fb.thumbs,
            "comment": fb.comment,
            "rating_questions": fb.rating_questions,
            "rating_feedback": fb.rating_feedback,
            "rating_difficulty": fb.rating_difficulty,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        })

    log_audit(db, "admin_view_feedback", user_id=None, metadata={"admin_id": admin.id, "skip": skip, "limit": limit})
    return {"feedback": result, "total": total, "skip": skip, "limit": limit}

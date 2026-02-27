"""CRUD operations for user usage tracking."""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.user_usage import UserUsage


def get_or_create_usage(db: Session, user_id: int) -> UserUsage:
    """Get user usage record, creating one if it doesn't exist."""
    usage = db.query(UserUsage).filter(UserUsage.user_id == user_id).first()
    if not usage:
        usage = UserUsage(user_id=user_id)
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


def _reset_daily_if_needed(usage: UserUsage) -> bool:
    """Reset daily counters if it's a new day. Returns True if reset occurred."""
    today = date.today()
    if usage.chat_reset_date < today:
        usage.chat_messages_today = 0
        usage.chat_reset_date = today
        return True
    return False


def _reset_monthly_if_needed(usage: UserUsage) -> bool:
    """Reset monthly counters if it's a new month. Returns True if reset occurred."""
    today = date.today()
    first_of_this_month = today.replace(day=1)
    if usage.usage_month < first_of_this_month:
        usage.tts_characters_month = 0
        usage.usage_month = first_of_this_month
        return True
    return False


def get_chat_usage(db: Session, user_id: int) -> tuple[int, int, date]:
    """
    Get current chat usage for a user.
    Returns: (messages_used_today, daily_limit_from_settings, reset_date)
    """
    from app.core.config import settings
    
    usage = get_or_create_usage(db, user_id)
    _reset_daily_if_needed(usage)
    db.commit()
    
    return usage.chat_messages_today, settings.FREE_CHAT_LIMIT_DAILY, usage.chat_reset_date


def get_tts_usage(db: Session, user_id: int) -> tuple[int, int, date]:
    """
    Get current TTS usage for a user.
    Returns: (characters_used_this_month, monthly_limit_from_settings, reset_date)
    """
    from app.core.config import settings
    
    usage = get_or_create_usage(db, user_id)
    _reset_monthly_if_needed(usage)
    db.commit()
    
    # Calculate next reset date (1st of next month)
    today = date.today()
    if today.month == 12:
        next_reset = date(today.year + 1, 1, 1)
    else:
        next_reset = date(today.year, today.month + 1, 1)
    
    return usage.tts_characters_month, settings.FREE_TTS_LIMIT_MONTHLY, next_reset


def increment_chat_usage(db: Session, user_id: int) -> tuple[int, int]:
    """
    Increment chat message count for a user.
    Returns: (new_count, limit)
    """
    from app.core.config import settings
    
    usage = get_or_create_usage(db, user_id)
    _reset_daily_if_needed(usage)
    
    usage.chat_messages_today += 1
    usage.total_chat_messages += 1
    usage.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return usage.chat_messages_today, settings.FREE_CHAT_LIMIT_DAILY


def increment_tts_usage(db: Session, user_id: int, characters: int) -> tuple[int, int]:
    """
    Increment TTS character count for a user.
    Returns: (new_count, limit)
    """
    from app.core.config import settings
    
    usage = get_or_create_usage(db, user_id)
    _reset_monthly_if_needed(usage)
    
    usage.tts_characters_month += characters
    usage.total_tts_characters += characters
    usage.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return usage.tts_characters_month, settings.FREE_TTS_LIMIT_MONTHLY


def increment_interview_sessions(db: Session, user_id: int) -> int:
    """
    Increment interview session count for a user.
    Returns: new total count
    """
    usage = get_or_create_usage(db, user_id)
    usage.total_interview_sessions += 1
    usage.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return usage.total_interview_sessions


def check_chat_limit(db: Session, user_id: int) -> tuple[bool, int, int]:
    """
    Check if user is within chat limit.
    Returns: (is_allowed, current_count, limit)
    """
    from app.core.config import settings
    
    usage = get_or_create_usage(db, user_id)
    _reset_daily_if_needed(usage)
    db.commit()
    
    limit = settings.FREE_CHAT_LIMIT_DAILY
    return usage.chat_messages_today < limit, usage.chat_messages_today, limit


def check_tts_limit(db: Session, user_id: int, characters_needed: int = 0) -> tuple[bool, int, int]:
    """
    Check if user is within TTS limit.
    Returns: (is_allowed, current_count, limit)
    """
    from app.core.config import settings
    
    usage = get_or_create_usage(db, user_id)
    _reset_monthly_if_needed(usage)
    db.commit()
    
    limit = settings.FREE_TTS_LIMIT_MONTHLY
    would_exceed = (usage.tts_characters_month + characters_needed) > limit
    return not would_exceed, usage.tts_characters_month, limit


def get_all_usage(db: Session, user_id: int) -> dict:
    """Get all usage data for a user (for display purposes)."""
    from app.core.config import settings
    
    usage = get_or_create_usage(db, user_id)
    _reset_daily_if_needed(usage)
    _reset_monthly_if_needed(usage)
    db.commit()
    
    # Calculate next reset dates
    today = date.today()
    tomorrow = date(today.year, today.month, today.day + 1) if today.day < 28 else today
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    
    return {
        "chat": {
            "used": usage.chat_messages_today,
            "limit": settings.FREE_CHAT_LIMIT_DAILY,
            "reset_at": tomorrow.isoformat(),
        },
        "tts": {
            "used": usage.tts_characters_month,
            "limit": settings.FREE_TTS_LIMIT_MONTHLY,
            "reset_at": next_month.isoformat(),
        },
        "lifetime": {
            "total_chat_messages": usage.total_chat_messages,
            "total_tts_characters": usage.total_tts_characters,
            "total_interview_sessions": usage.total_interview_sessions,
        },
    }

"""User usage tracking model for rate limiting."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserUsage(Base):
    """Tracks user usage for rate limiting purposes."""
    
    __tablename__ = "user_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Daily counters (reset at midnight UTC)
    chat_messages_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chat_reset_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)

    # Monthly counters (reset on 1st of month)
    tts_characters_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_month: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)

    # Lifetime stats (never reset)
    total_chat_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tts_characters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_interview_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationship to user
    user = relationship("User", backref="usage")

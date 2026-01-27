"""Session feedback model for collecting user ratings after interviews."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SessionFeedback(Base):
    """User feedback and ratings for completed interview sessions.
    
    This data powers the learning loop - identifying what makes
    high-quality interviews so we can improve prompt selection.
    """
    __tablename__ = "session_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    session_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One feedback per session
        index=True
    )
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Overall rating (1-5 stars)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Quick thumbs up/down: "up", "down", or null
    thumbs: Mapped[str | None] = mapped_column(String(10), nullable=True)
    
    # Optional written feedback
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Specific aspect ratings (optional, 1-5 each)
    rating_questions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_feedback: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )

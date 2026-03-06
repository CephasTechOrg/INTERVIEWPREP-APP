from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InterviewLevelOutcome(Base):
    """Level calibration outcome for a completed interview session."""

    __tablename__ = "interview_level_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign key to session
    session_id: Mapped[int] = mapped_column(
        Integer, 
        index=True, 
        unique=True, 
        nullable=False
    )

    # Role and company tier context
    role: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    company_tier: Mapped[str] = mapped_column(String(50), nullable=False)

    # Estimated level
    estimated_level: Mapped[str] = mapped_column(String(100), nullable=False)
    estimated_level_display: Mapped[str] = mapped_column(String(200), nullable=False)

    # Readiness metrics
    readiness_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Next level (if any)
    next_level: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Results (JSON)
    strengths: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    gaps: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    next_actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    
    # Rubric scores used for calculation
    rubric_scores_used: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )

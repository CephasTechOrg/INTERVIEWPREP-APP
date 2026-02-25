from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    role: Mapped[str] = mapped_column(String(100), default="SWE Intern", nullable=False)
    track: Mapped[str] = mapped_column(String(50), default="swe_intern", nullable=False)
    company_style: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="easy", nullable=False)
    # Adaptive difficulty: this is the current difficulty used for question selection.
    # `difficulty` remains the user's selected cap (easy|medium|hard).
    difficulty_current: Mapped[str] = mapped_column(String(20), default="easy", nullable=False)
    adaptive_difficulty_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # stage controller: "intro"|"question"|"followups"|"evaluation"|"done"
    stage: Mapped[str] = mapped_column(String(30), default="intro", nullable=False)

    # Interview progress (state machine counters)
    questions_asked_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followups_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Dynamic interviews: target 5 questions, allow up to 7; keep followups short (<=2).
    max_questions: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    max_followups_per_question: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    # Interview mix: how many behavioral questions to include (0-3).
    behavioral_questions_target: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    # Running skill state from quick rubric scores after each candidate response.
    # Shape (example):
    # {"n": 3, "sum": {"communication": 18, ...}, "last": {"communication": 6, ...}}
    skill_state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    current_question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

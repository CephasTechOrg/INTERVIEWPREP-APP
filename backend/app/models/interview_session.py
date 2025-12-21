from sqlalchemy import String, Integer, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.db.base import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(Integer, index=True)

    role: Mapped[str] = mapped_column(String(100), default="SWE Intern")
    track: Mapped[str] = mapped_column(String(50), default="swe_intern")
    company_style: Mapped[str] = mapped_column(String(50), default="general")
    difficulty: Mapped[str] = mapped_column(String(20), default="easy")
    # Adaptive difficulty: this is the current difficulty used for question selection.
    # `difficulty` remains the user's selected cap (easy|medium|hard).
    difficulty_current: Mapped[str] = mapped_column(String(20), default="easy")

    # stage controller: "intro"|"question"|"followups"|"evaluation"|"done"
    stage: Mapped[str] = mapped_column(String(30), default="intro")

    # Interview progress (state machine counters)
    questions_asked_count: Mapped[int] = mapped_column(Integer, default=0)
    followups_used: Mapped[int] = mapped_column(Integer, default=0)
    # Dynamic interviews: target 5 questions, allow up to 7; keep followups short (<=2).
    max_questions: Mapped[int] = mapped_column(Integer, default=7)
    max_followups_per_question: Mapped[int] = mapped_column(Integer, default=2)
    # Interview mix: how many behavioral questions to include (0-3).
    behavioral_questions_target: Mapped[int] = mapped_column(Integer, default=2)

    # Running skill state from quick rubric scores after each candidate response.
    # Shape (example):
    # {"n": 3, "sum": {"communication": 18, ...}, "last": {"communication": 6, ...}}
    skill_state: Mapped[dict] = mapped_column(JSON, default=dict)

    current_question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

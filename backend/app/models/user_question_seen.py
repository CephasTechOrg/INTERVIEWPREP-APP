from datetime import datetime

from sqlalchemy import DateTime, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserQuestionSeen(Base):
    __tablename__ = "user_questions_seen"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_user_questions_seen_user_question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

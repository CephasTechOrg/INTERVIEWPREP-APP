from sqlalchemy import Integer, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, index=True, unique=True)

    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    rubric: Mapped[dict] = mapped_column(JSON, default=dict)  # store JSON from evaluator
    summary: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

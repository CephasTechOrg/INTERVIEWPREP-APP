from sqlalchemy import JSON, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, index=True, unique=True, nullable=False)

    overall_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rubric: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # store JSON from evaluator
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

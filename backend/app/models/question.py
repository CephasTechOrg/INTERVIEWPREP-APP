from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    track: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # "swe_intern"
    company_style: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # "apple", "google"
    difficulty: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # "easy"|"medium"|"hard"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    tags_csv: Mapped[str] = mapped_column(String(500), default="", nullable=False)  # store tags as "arrays,hashmap"
    followups: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # optional dataset-driven followups
    question_type: Mapped[str] = mapped_column(
        String(50), default="coding", nullable=False
    )  # coding|system_design|behavioral|conceptual
    expected_topics: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # topics the answer should cover
    evaluation_focus: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # what to evaluate (e.g., complexity, edge_cases)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # optional extra metadata

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def tags(self) -> list[str]:
        return [t.strip() for t in (self.tags_csv or "").split(",") if t.strip()]

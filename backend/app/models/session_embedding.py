"""Session embedding model for RAG-based interview enhancement."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Note: pgvector's Vector type will be used in the migration.
# We use Text here as a placeholder - the actual column is created 
# with vector(1536) type in the migration for pgvector compatibility.


class SessionEmbedding(Base):
    """Vector embeddings for interview sessions to enable similarity search.
    
    Used for RAG: finding similar past sessions to inject as examples
    into prompts, improving interview quality over time.
    """
    __tablename__ = "session_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # What this embedding represents
    # "full_session" | "question_response" | "evaluation"
    embedding_type: Mapped[str] = mapped_column(String(50), nullable=False, default="full_session")
    
    # The text that was embedded (for reference/debugging)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # The embedding vector - stored as Text here, actual vector column in migration
    # Dimension 384 for sentence-transformers/all-MiniLM-L6-v2 (free, fast)
    # Dimension 1536 for OpenAI embeddings
    # We'll use 384 for the free local model
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata for filtering during retrieval
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    track: Mapped[str | None] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Quality signal from feedback (denormalized for fast filtering)
    feedback_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class QuestionEmbedding(Base):
    """Vector embeddings for questions to enable semantic question search."""
    __tablename__ = "question_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # The text that was embedded (title + prompt + tags)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # The embedding vector
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class ResponseExample(Base):
    """Curated example responses for few-shot learning.
    
    These are manually or automatically tagged as good/bad examples
    to inject into prompts for better AI behavior.
    """
    __tablename__ = "response_examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Link to original session/question (optional, for provenance)
    session_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="SET NULL"),
        nullable=True
    )
    question_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # The example content
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Quality classification: "excellent" | "good" | "poor" | "bad"
    quality_label: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Why this is a good/bad example (for prompt context)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Embedding for similarity search
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Categorization for retrieval
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "algorithm", "behavioral", etc.
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Is this example active (included in RAG)?
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

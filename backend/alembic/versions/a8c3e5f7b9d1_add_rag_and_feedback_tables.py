"""add_rag_and_feedback_tables

Revision ID: a8c3e5f7b9d1
Revises: 6b1c4df2c3e8
Create Date: 2026-01-27 00:00:00.000000

Adds tables for:
- session_feedback: User ratings and comments for completed interviews
- session_embeddings: Vector embeddings for RAG similarity search
- question_embeddings: Vector embeddings for semantic question matching
- response_examples: Curated examples for few-shot learning

Note: Embeddings are stored as TEXT (JSON arrays) initially.
If pgvector is available, a separate migration can convert to vector type.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a8c3e5f7b9d1"
down_revision = "6b1c4df2c3e8"
branch_labels = None
depends_on = None


def upgrade():
    # Session feedback table
    op.create_table(
        "session_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("thumbs", sa.String(length=10), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("rating_questions", sa.Integer(), nullable=True),
        sa.Column("rating_feedback", sa.Integer(), nullable=True),
        sa.Column("rating_difficulty", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_session_feedback_session_id"), "session_feedback", ["session_id"], unique=True)
    op.create_index(op.f("ix_session_feedback_user_id"), "session_feedback", ["user_id"], unique=False)
    op.create_index(op.f("ix_session_feedback_rating"), "session_feedback", ["rating"], unique=False)
    
    # Session embeddings table
    # Embeddings stored as TEXT (JSON array of floats) - works without pgvector
    op.create_table(
        "session_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("embedding_type", sa.String(length=50), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),  # JSON array of floats
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("track", sa.String(length=50), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("feedback_rating", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_session_embeddings_session_id"), "session_embeddings", ["session_id"], unique=True)
    op.create_index(op.f("ix_session_embeddings_feedback_rating"), "session_embeddings", ["feedback_rating"], unique=False)
    
    # Question embeddings table
    op.create_table(
        "question_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),  # JSON array of floats
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("question_id"),
    )
    op.create_index(op.f("ix_question_embeddings_question_id"), "question_embeddings", ["question_id"], unique=True)
    
    # Response examples table (curated few-shot examples)
    op.create_table(
        "response_examples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("question_id", sa.Integer(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("quality_label", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=True),  # JSON array of floats
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_response_examples_quality_label"), "response_examples", ["quality_label"], unique=False)
    op.create_index(op.f("ix_response_examples_category"), "response_examples", ["category"], unique=False)
    op.create_index(op.f("ix_response_examples_is_active"), "response_examples", ["is_active"], unique=False)


def downgrade():
    op.drop_table("response_examples")
    op.drop_table("question_embeddings")
    op.drop_table("session_embeddings")
    op.drop_table("session_feedback")

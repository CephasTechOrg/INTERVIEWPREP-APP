"""add adaptive difficulty enabled

Revision ID: c1f2a8d5b6e7
Revises: a8c3e5f7b9d1
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c1f2a8d5b6e7"
down_revision = "a8c3e5f7b9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column(
            "adaptive_difficulty_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "adaptive_difficulty_enabled")
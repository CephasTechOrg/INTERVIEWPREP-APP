"""fix sessions track constraint

Revision ID: 7b9f2d3a4c1e
Revises: 5d8533fcfb18
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7b9f2d3a4c1e"
down_revision = "5d8533fcfb18"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("ALTER TABLE interview_sessions DROP CONSTRAINT IF EXISTS ck_sessions_track"))
    op.create_check_constraint(
        "ck_sessions_track",
        "interview_sessions",
        "track IN ('behavioral','swe_intern','swe_engineer','cybersecurity','data_science','devops_cloud','product_management')",
    )


def downgrade():
    op.execute(sa.text("ALTER TABLE interview_sessions DROP CONSTRAINT IF EXISTS ck_sessions_track"))

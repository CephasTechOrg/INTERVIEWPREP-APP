"""fix_questions_track_constraint

Revision ID: 6da623e40726
Revises: 2e847a45e9b6
Create Date: 2026-02-25 13:07:27.934479
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6da623e40726'
down_revision = '2e847a45e9b6'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing constraint if it exists
    op.execute(sa.text("ALTER TABLE questions DROP CONSTRAINT IF EXISTS ck_questions_track"))
    # Create new constraint with all tracks
    op.create_check_constraint(
        "ck_questions_track",
        "questions",
        "track IN ('behavioral','swe_intern','swe_engineer','cybersecurity','data_science','devops_cloud','product_management')",
    )


def downgrade():
    op.execute(sa.text("ALTER TABLE questions DROP CONSTRAINT IF EXISTS ck_questions_track"))

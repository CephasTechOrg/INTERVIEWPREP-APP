"""add user profile fields

Revision ID: 6b1c4df2c3e8
Revises: 9f4a0b4b7a1a
Create Date: 2026-01-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6b1c4df2c3e8"
down_revision = "9f4a0b4b7a1a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("role_pref", sa.String(length=100), nullable=False, server_default="SWE Intern"),
    )
    op.add_column(
        "users",
        sa.Column("profile", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade():
    op.drop_column("users", "profile")
    op.drop_column("users", "role_pref")

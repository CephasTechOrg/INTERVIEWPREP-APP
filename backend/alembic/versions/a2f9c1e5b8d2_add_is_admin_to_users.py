"""add is_admin to users

Revision ID: a2f9c1e5b8d2
Revises: 19a640d64cf5
Create Date: 2026-02-26 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2f9c1e5b8d2'
down_revision = '19a640d64cf5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    op.drop_column('users', 'is_admin')

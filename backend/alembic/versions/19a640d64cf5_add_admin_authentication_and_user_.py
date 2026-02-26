"""add admin authentication and user banning

Revision ID: 19a640d64cf5
Revises: 8e86f6bb0649
Create Date: 2026-02-26 17:31:30.142656
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19a640d64cf5'
down_revision = '8e86f6bb0649'
branch_labels = None
depends_on = None


def upgrade():
    # Create admin_accounts table
    op.create_table(
        'admin_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index(op.f('ix_admin_accounts_username'), 'admin_accounts', ['username'], unique=True)

    # Add ban fields to users table
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('ban_reason', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('banned_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove ban fields from users table
    op.drop_column('users', 'banned_at')
    op.drop_column('users', 'ban_reason')
    op.drop_column('users', 'is_banned')

    # Drop admin_accounts table
    op.drop_index(op.f('ix_admin_accounts_username'), table_name='admin_accounts')
    op.drop_table('admin_accounts')

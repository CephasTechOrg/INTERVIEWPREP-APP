"""add_user_usage_table

Revision ID: ac4c2ebfd4af
Revises: a2f9c1e5b8d2
Create Date: 2026-02-26 22:06:21.203994
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ac4c2ebfd4af'
down_revision = 'a2f9c1e5b8d2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chat_messages_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chat_reset_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('tts_characters_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_month', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('total_chat_messages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tts_characters', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_interview_sessions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_usage_user_id', 'user_usage', ['user_id'], unique=True)


def downgrade():
    op.drop_index('ix_user_usage_user_id', table_name='user_usage')
    op.drop_table('user_usage')

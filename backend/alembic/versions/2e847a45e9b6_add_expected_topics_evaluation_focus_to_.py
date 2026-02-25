"""add_expected_topics_evaluation_focus_to_questions

Revision ID: 2e847a45e9b6
Revises: 41ba5ea0c1f6
Create Date: 2026-02-25 12:59:26.677819
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e847a45e9b6'
down_revision = '41ba5ea0c1f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('questions', sa.Column('expected_topics', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('questions', sa.Column('evaluation_focus', sa.JSON(), nullable=False, server_default='[]'))


def downgrade():
    op.drop_column('questions', 'evaluation_focus')
    op.drop_column('questions', 'expected_topics')

"""create hello table

Revision ID: dc1cf3323bd8
Revises: 
Create Date: 2025-11-01 18:39:17.664064

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc1cf3323bd8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'hello',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hello_id'), 'hello', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_hello_id'), table_name='hello')
    op.drop_table('hello')

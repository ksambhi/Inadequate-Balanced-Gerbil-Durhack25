"""change_joined_opinion_answer_to_integer

Revision ID: aecd72b5639f
Revises: 9065788b4a4c
Create Date: 2025-11-02 11:23:40.210935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aecd72b5639f'
down_revision: Union[str, Sequence[str], None] = '9065788b4a4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop all existing joined opinions (they have string answers)
    op.execute('DELETE FROM joined_opinion')
    
    # Change answer column from String to Integer using USING clause
    op.execute('ALTER TABLE joined_opinion ALTER COLUMN answer TYPE INTEGER USING answer::integer')


def downgrade() -> None:
    """Downgrade schema."""
    # Change answer column back from Integer to String
    op.execute('ALTER TABLE joined_opinion ALTER COLUMN answer TYPE VARCHAR USING answer::text')

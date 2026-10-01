"""merge_heads

Revision ID: 3b87437408a5
Revises: 001, e6a5b8151526
Create Date: 2026-09-27 01:07:06.111763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b87437408a5'
down_revision: Union[str, Sequence[str], None] = ('001', 'e6a5b8151526')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

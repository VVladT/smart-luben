"""movimiento_producto_nullable

Revision ID: 5dec68c6aa38
Revises: db99adea4afd
Create Date: 2026-10-01 00:01:43.860433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dec68c6aa38'
down_revision: Union[str, Sequence[str], None] = 'db99adea4afd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('movimientos', 'producto_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # Los movimientos sin producto (salidas de espacios "desconocido")
    # se reasignan a NULL-safe: downgrade solo si no hay NULLs.
    op.alter_column('movimientos', 'producto_id',
                    existing_type=sa.Integer(),
                    nullable=False)

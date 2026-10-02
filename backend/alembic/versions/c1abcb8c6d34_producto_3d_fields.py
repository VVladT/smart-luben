"""producto_3d_fields

Revision ID: c1abcb8c6d34
Revises: 5dec68c6aa38
Create Date: 2026-10-02 12:32:22.337061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1abcb8c6d34'
down_revision: Union[str, Sequence[str], None] = '5dec68c6aa38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('productos', sa.Column('modelo_url', sa.String(length=500), nullable=True))
    op.add_column('productos', sa.Column('scale', sa.Float(), nullable=False, server_default='1.0'))
    op.add_column('productos', sa.Column('rotation_x', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('productos', sa.Column('rotation_y', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('productos', sa.Column('rotation_z', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('productos', sa.Column('version', sa.String(length=20), nullable=False, server_default='v1.0.0'))


def downgrade() -> None:
    op.drop_column('productos', 'version')
    op.drop_column('productos', 'rotation_z')
    op.drop_column('productos', 'rotation_y')
    op.drop_column('productos', 'rotation_x')
    op.drop_column('productos', 'scale')
    op.drop_column('productos', 'modelo_url')

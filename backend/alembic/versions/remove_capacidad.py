"""remove_capacidad_from_espacios

Revision ID: remove_capacidad
Revises: 3b87437408a5
Create Date: 2026-09-27 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'remove_capacidad'
down_revision = '3b87437408a5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('espacios', 'capacidad')


def downgrade() -> None:
    op.add_column('espacios', sa.Column('capacidad', sa.Integer(), nullable=False, server_default='1'))

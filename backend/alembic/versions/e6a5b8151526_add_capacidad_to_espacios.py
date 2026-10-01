"""add_capacidad_to_espacios

Revision ID: e6a5b8151526
Revises: 
Create Date: 2026-09-27 01:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e6a5b8151526'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('espacios', sa.Column('capacidad', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('espacios', 'capacidad')
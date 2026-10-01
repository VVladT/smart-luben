"""create_ml_features_table

Revision ID: create_ml_features
Revises: remove_capacidad
Create Date: 2026-09-27 01:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'create_ml_features'
down_revision = 'remove_capacidad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ml_features',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('espacio_id', sa.Integer(), sa.ForeignKey('espacios.id'), nullable=False),
        sa.Column('producto_id', sa.Integer(), sa.ForeignKey('productos.id'), nullable=False),
        sa.Column('dow', sa.SmallInteger(), nullable=False),  # 0-6
        sa.Column('hour', sa.SmallInteger(), nullable=False),  # 0-23
        # Demand features
        sa.Column('salida_count_7d', sa.Integer(), default=0, nullable=False),
        sa.Column('salida_count_30d', sa.Integer(), default=0, nullable=False),
        sa.Column('salida_freq_dow', sa.Float(), default=0.0, nullable=False),
        sa.Column('salida_freq_hour', sa.Float(), default=0.0, nullable=False),
        sa.Column('salida_trend_7d', sa.Float(), default=0.0, nullable=False),
        # Affinity features
        sa.Column('reposicion_count', sa.Integer(), default=0, nullable=False),
        sa.Column('reposicion_recency_days', sa.Integer(), nullable=True),
        sa.Column('space_product_share', sa.Float(), default=0.0, nullable=False),
        # Space features
        sa.Column('espacio_zona', sa.String(20), nullable=False),  # 'Fila 1', 'Fila 2'
        # Metadata
        sa.Column('computed_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('espacio_id', 'producto_id', 'dow', 'hour', name='uq_ml_features_lookup')
    )
    op.create_index('ix_ml_features_dow_hour_espacio', 'ml_features', ['dow', 'hour', 'espacio_id'])


def downgrade() -> None:
    op.drop_index('ix_ml_features_dow_hour_espacio', table_name='ml_features')
    op.drop_table('ml_features')

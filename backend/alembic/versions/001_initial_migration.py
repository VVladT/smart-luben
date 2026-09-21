"""initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'productos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('categoria', sa.String(length=50), nullable=False),
        sa.Column('imagen_url', sa.String(length=500), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('creado_en', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre')
    )
    op.create_index(op.f('ix_productos_id'), 'productos', ['id'], unique=False)
    op.create_index(op.f('ix_productos_nombre'), 'productos', ['nombre'], unique=True)

    op.create_table(
        'espacios',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('codigo', sa.String(length=10), nullable=False),
        sa.Column('ubicacion', sa.String(length=100), nullable=False),
        sa.Column('estado', sa.Enum('libre', 'ocupado', name='estadoespacio'), nullable=False, server_default='libre'),
        sa.Column('producto_actual_id', sa.Integer(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['producto_actual_id'], ['productos.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo')
    )
    op.create_index(op.f('ix_espacios_id'), 'espacios', ['id'], unique=False)
    op.create_index(op.f('ix_espacios_codigo'), 'espacios', ['codigo'], unique=True)

    op.create_table(
        'movimientos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('espacio_id', sa.Integer(), nullable=False),
        sa.Column('producto_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.Enum('reposicion', 'salida', name='tipomovimiento'), nullable=False),
        sa.Column('fecha_hora', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['espacio_id'], ['espacios.id'], ),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_movimientos_id'), 'movimientos', ['id'], unique=False)
    op.create_index(op.f('ix_movimientos_espacio_id'), 'movimientos', ['espacio_id'], unique=False)
    op.create_index(op.f('ix_movimientos_producto_id'), 'movimientos', ['producto_id'], unique=False)
    op.create_index(op.f('ix_movimientos_fecha_hora'), 'movimientos', ['fecha_hora'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_movimientos_fecha_hora'), table_name='movimientos')
    op.drop_index(op.f('ix_movimientos_producto_id'), table_name='movimientos')
    op.drop_index(op.f('ix_movimientos_espacio_id'), table_name='movimientos')
    op.drop_index(op.f('ix_movimientos_id'), table_name='movimientos')
    op.drop_table('movimientos')
    op.drop_index(op.f('ix_espacios_codigo'), table_name='espacios')
    op.drop_index(op.f('ix_espacios_id'), table_name='espacios')
    op.drop_table('espacios')
    op.drop_index(op.f('ix_productos_nombre'), table_name='productos')
    op.drop_index(op.f('ix_productos_id'), table_name='productos')
    op.drop_table('productos')
    op.execute('DROP TYPE estadoespacio')
    op.execute('DROP TYPE tipomovimiento')
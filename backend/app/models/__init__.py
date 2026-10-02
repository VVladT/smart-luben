from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, SmallInteger, Float
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class EstadoEspacio(str, enum.Enum):
    libre = "libre"
    ocupado = "ocupado"


class TipoMovimiento(str, enum.Enum):
    reposicion = "reposicion"
    salida = "salida"


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    categoria = Column(String(50), nullable=False)
    imagen_url = Column(String(500), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    # Assets 3D para el módulo AR (opcionales; version bumpea al cambiar modelo_url)
    modelo_url = Column(String(500), nullable=True)
    scale = Column(Float, default=1.0, nullable=False)
    rotation_x = Column(Float, default=0.0, nullable=False)
    rotation_y = Column(Float, default=0.0, nullable=False)
    rotation_z = Column(Float, default=0.0, nullable=False)
    version = Column(String(20), default="v1.0.0", nullable=False)

    movimientos = relationship("Movimiento", back_populates="producto")


class Espacio(Base):
    __tablename__ = "espacios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(10), unique=True, nullable=False, index=True)
    ubicacion = Column(String(100), nullable=False)
    estado = Column(SQLEnum(EstadoEspacio), default=EstadoEspacio.libre, nullable=False)
    producto_actual_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    producto_actual = relationship("Producto", foreign_keys=[producto_actual_id])
    movimientos = relationship("Movimiento", back_populates="espacio")


class Movimiento(Base):
    __tablename__ = "movimientos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    espacio_id = Column(Integer, ForeignKey("espacios.id"), nullable=False, index=True)
    # Nullable: un espacio ocupado sin producto conocido (situación "desconocido")
    # igual registra su movimiento de salida.
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True, index=True)
    tipo = Column(SQLEnum(TipoMovimiento), nullable=False)
    fecha_hora = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    espacio = relationship("Espacio", back_populates="movimientos")
    producto = relationship("Producto", back_populates="movimientos")


class MlFeature(Base):
    __tablename__ = "ml_features"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    espacio_id = Column(Integer, ForeignKey("espacios.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    dow = Column(SmallInteger, nullable=False)
    hour = Column(SmallInteger, nullable=False)
    salida_count_7d = Column(Integer, default=0, nullable=False)
    salida_count_30d = Column(Integer, default=0, nullable=False)
    salida_freq_dow = Column(Float, default=0.0, nullable=False)
    salida_freq_hour = Column(Float, default=0.0, nullable=False)
    salida_trend_7d = Column(Float, default=0.0, nullable=False)
    reposicion_count = Column(Integer, default=0, nullable=False)
    reposicion_recency_days = Column(Integer, nullable=True)
    space_product_share = Column(Float, default=0.0, nullable=False)
    espacio_zona = Column(String(20), nullable=False)
    computed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    espacio = relationship("Espacio")
    producto = relationship("Producto")
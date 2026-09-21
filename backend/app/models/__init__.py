from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
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
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    movimientos = relationship("Movimiento", back_populates="producto")


class Espacio(Base):
    __tablename__ = "espacios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(10), unique=True, nullable=False, index=True)
    ubicacion = Column(String(100), nullable=False)
    estado = Column(SQLEnum(EstadoEspacio), default=EstadoEspacio.libre, nullable=False)
    producto_actual_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    producto_actual = relationship("Producto", foreign_keys=[producto_actual_id])
    movimientos = relationship("Movimiento", back_populates="espacio")


class Movimiento(Base):
    __tablename__ = "movimientos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    espacio_id = Column(Integer, ForeignKey("espacios.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    tipo = Column(SQLEnum(TipoMovimiento), nullable=False)
    fecha_hora = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    espacio = relationship("Espacio", back_populates="movimientos")
    producto = relationship("Producto", back_populates="movimientos")
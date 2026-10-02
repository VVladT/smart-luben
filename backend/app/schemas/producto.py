from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProductoBase(BaseModel):
    nombre: str
    categoria: str
    imagen_url: Optional[str] = None
    modelo_url: Optional[str] = None
    scale: float = 1.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    imagen_url: Optional[str] = None
    modelo_url: Optional[str] = None
    scale: Optional[float] = None
    rotation_x: Optional[float] = None
    rotation_y: Optional[float] = None
    rotation_z: Optional[float] = None
    activo: Optional[bool] = None
    # version es de solo lectura: el backend la bumpea al cambiar modelo_url


class ProductoResponse(ProductoBase):
    id: int
    activo: bool
    creado_en: datetime
    version: str = "v1.0.0"

    model_config = ConfigDict(from_attributes=True)


class ProductoListResponse(BaseModel):
    id: int
    nombre: str
    categoria: str
    imagen_url: Optional[str]
    activo: bool
    creado_en: datetime
    modelo_url: Optional[str] = None
    scale: float = 1.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    version: str = "v1.0.0"

    model_config = ConfigDict(from_attributes=True)
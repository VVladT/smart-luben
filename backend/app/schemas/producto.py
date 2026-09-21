from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProductoBase(BaseModel):
    nombre: str
    categoria: str
    imagen_url: Optional[str] = None


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    imagen_url: Optional[str] = None
    activo: Optional[bool] = None


class ProductoResponse(ProductoBase):
    id: int
    activo: bool
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductoListResponse(BaseModel):
    id: int
    nombre: str
    categoria: str
    imagen_url: Optional[str]
    activo: bool
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)
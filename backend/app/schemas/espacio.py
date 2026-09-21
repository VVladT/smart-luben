from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models import EstadoEspacio


class EspacioBase(BaseModel):
    codigo: str
    ubicacion: str


class EspacioCreate(EspacioBase):
    pass


class EspacioUpdate(BaseModel):
    codigo: Optional[str] = None
    ubicacion: Optional[str] = None


class EspacioResponse(EspacioBase):
    id: int
    estado: EstadoEspacio
    producto_actual_id: Optional[int] = None
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


class EspacioConProductoResponse(EspacioResponse):
    producto_actual: Optional["ProductoSimpleResponse"] = None

    model_config = ConfigDict(from_attributes=True)


class ProductoSimpleResponse(BaseModel):
    id: int
    nombre: str
    categoria: str
    imagen_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


EspacioConProductoResponse.model_rebuild()
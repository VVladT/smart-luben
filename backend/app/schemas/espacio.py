from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, computed_field
from app.models import EstadoEspacio


SituacionEspacio = Literal["libre", "pendiente", "ocupado", "desconocido"]


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

    @computed_field
    @property
    def situacion(self) -> SituacionEspacio:
        """Estado visual calculado (response-only, no se persiste):
        libre+producto = pendiente de reposición,
        ocupado sin producto = desconocido."""
        if self.estado == EstadoEspacio.libre:
            return "pendiente" if self.producto_actual_id is not None else "libre"
        return "desconocido" if self.producto_actual_id is None else "ocupado"


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
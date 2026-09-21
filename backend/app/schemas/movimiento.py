from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models import TipoMovimiento


class MovimientoBase(BaseModel):
    espacio_id: int
    producto_id: int
    tipo: TipoMovimiento


class MovimientoCreate(MovimientoBase):
    pass


class MovimientoResponse(MovimientoBase):
    id: int
    fecha_hora: datetime

    model_config = ConfigDict(from_attributes=True)


class MovimientoDetalleResponse(MovimientoResponse):
    espacio_codigo: str
    producto_nombre: str
    producto_categoria: str

    model_config = ConfigDict(from_attributes=True)


class ReponerRequest(BaseModel):
    producto_id: int


class MovimientoFiltros(BaseModel):
    espacio_id: Optional[int] = None
    producto_id: Optional[int] = None
    tipo: Optional[TipoMovimiento] = None
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
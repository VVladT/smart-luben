from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models import TipoMovimiento


class MovimientoBase(BaseModel):
    espacio_id: int
    producto_id: int
    tipo: TipoMovimiento


class MovimientoCreate(MovimientoBase):
    fecha_hora: datetime | None = None


class MovimientoResponse(MovimientoBase):
    id: int
    fecha_hora: datetime
    # Nullable en respuesta: salidas de espacios "desconocido" no tienen producto.
    producto_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class MovimientoDetalleResponse(MovimientoResponse):
    espacio_codigo: str
    producto_nombre: str
    producto_categoria: str

    model_config = ConfigDict(from_attributes=True)


class ReponerRequest(BaseModel):
    # Opcional e ignorado: la ocupación siempre usa el producto planificado
    # (pendiente) o NULL (desconocido). Se mantiene por compatibilidad.
    producto_id: Optional[int] = None


class PlanificarRequest(BaseModel):
    producto_id: int


class MovimientoFiltros(BaseModel):
    espacio_id: Optional[int] = None
    producto_id: Optional[int] = None
    tipo: Optional[TipoMovimiento] = None
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
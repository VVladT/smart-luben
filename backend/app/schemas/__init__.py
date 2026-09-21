from app.schemas.producto import (
    ProductoBase,
    ProductoCreate,
    ProductoUpdate,
    ProductoResponse,
    ProductoListResponse,
)
from app.schemas.espacio import (
    EspacioBase,
    EspacioCreate,
    EspacioUpdate,
    EspacioResponse,
    EspacioConProductoResponse,
    ProductoSimpleResponse,
)
from app.schemas.movimiento import (
    MovimientoBase,
    MovimientoCreate,
    MovimientoResponse,
    MovimientoDetalleResponse,
    ReponerRequest,
    MovimientoFiltros,
)
from app.schemas.dashboard import DashboardResumen

__all__ = [
    "ProductoBase",
    "ProductoCreate",
    "ProductoUpdate",
    "ProductoResponse",
    "ProductoListResponse",
    "EspacioBase",
    "EspacioCreate",
    "EspacioUpdate",
    "EspacioResponse",
    "EspacioConProductoResponse",
    "ProductoSimpleResponse",
    "MovimientoBase",
    "MovimientoCreate",
    "MovimientoResponse",
    "MovimientoDetalleResponse",
    "ReponerRequest",
    "MovimientoFiltros",
    "DashboardResumen",
]
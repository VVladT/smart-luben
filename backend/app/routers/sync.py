from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import EspacioService, ProductoService


router = APIRouter(prefix="/sync", tags=["sync"])


class SyncChangesRequest(BaseModel):
    versions: Dict[str, str] = {}
    assignments: Dict[str, int | None] = {}
    estados: Dict[str, str] = {}


class SyncChange(BaseModel):
    type: str
    productoId: int | None = None
    espacio_codigo: str | None = None
    estado: str | None = None
    version: str | None = None


class SyncChangesResponse(BaseModel):
    changes: List[SyncChange] = []


@router.post(
    "/changes",
    response_model=SyncChangesResponse,
    summary="Cambios desde versiones",
    description="Compara versiones de productos del cliente AR y devuelve los que cambiaron + asignaciones actuales.",
)
async def sync_changes(request: SyncChangesRequest, db: AsyncSession = Depends(get_db)):
    changes: List[SyncChange] = []

    productos = await ProductoService.get_all(db, activo=True)
    for p in productos:
        if request.versions.get(str(p.id)) != p.version:
            changes.append(SyncChange(type="producto_update", productoId=p.id, version=p.version))

    espacios = await EspacioService.get_all(db)
    for e in espacios:
        actual = request.assignments.get(e.codigo, "__desconocido__")
        if actual != e.producto_actual_id:
            changes.append(
                SyncChange(
                    type="espacio_assignment",
                    productoId=e.producto_actual_id,
                    espacio_codigo=e.codigo,
                    version=None,
                )
            )
        estado_actual = request.estados.get(e.codigo)
        if estado_actual != e.estado.value:
            changes.append(
                SyncChange(
                    type="espacio_estado",
                    espacio_codigo=e.codigo,
                    estado=e.estado.value,
                )
            )

    return SyncChangesResponse(changes=changes)

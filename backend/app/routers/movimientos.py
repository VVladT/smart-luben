from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.services import MovimientoService
from app.schemas import (
    MovimientoResponse,
    MovimientoDetalleResponse,
    MovimientoFiltros,
)
from app.models import TipoMovimiento


router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.get(
    "",
    response_model=List[MovimientoDetalleResponse],
    summary="Listar movimientos con filtros",
    description="Obtiene el historial de movimientos con filtros opcionales: espacio_id, producto_id, tipo, desde, hasta."
)
async def listar_movimientos(
    espacio_id: Optional[int] = Query(None, description="Filtrar por espacio"),
    producto_id: Optional[int] = Query(None, description="Filtrar por producto"),
    tipo: Optional[TipoMovimiento] = Query(None, description="Filtrar por tipo de movimiento"),
    desde: Optional[datetime] = Query(None, description="Fecha desde (ISO 8601)"),
    hasta: Optional[datetime] = Query(None, description="Fecha hasta (ISO 8601)"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    db: AsyncSession = Depends(get_db)
):
    filtros = MovimientoFiltros(
        espacio_id=espacio_id,
        producto_id=producto_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta
    )
    movimientos = await MovimientoService.get_all(db, filtros, skip, limit)
    
    result = []
    for mov in movimientos:
        result.append(MovimientoDetalleResponse(
            id=mov.id,
            espacio_id=mov.espacio_id,
            producto_id=mov.producto_id,
            tipo=mov.tipo,
            fecha_hora=mov.fecha_hora,
            espacio_codigo=mov.espacio.codigo if mov.espacio else "",
            producto_nombre=mov.producto.nombre if mov.producto else "",
            producto_categoria=mov.producto.categoria if mov.producto else ""
        ))
    return result


@router.get(
    "/espacio/{espacio_id}",
    response_model=List[MovimientoDetalleResponse],
    summary="Movimientos de un espacio",
    description="Obtiene el historial de movimientos de un espacio específico."
)
async def movimientos_por_espacio(espacio_id: int, db: AsyncSession = Depends(get_db)):
    movimientos = await MovimientoService.get_by_espacio(db, espacio_id)
    
    result = []
    for mov in movimientos:
        result.append(MovimientoDetalleResponse(
            id=mov.id,
            espacio_id=mov.espacio_id,
            producto_id=mov.producto_id,
            tipo=mov.tipo,
            fecha_hora=mov.fecha_hora,
            espacio_codigo=mov.espacio.codigo if mov.espacio else "",
            producto_nombre=mov.producto.nombre if mov.producto else "",
            producto_categoria=mov.producto.categoria if mov.producto else ""
        ))
    return result
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.services import EspacioService, MovimientoService
from app.schemas import (
    EspacioCreate,
    EspacioUpdate,
    EspacioResponse,
    EspacioConProductoResponse,
    ReponerRequest,
    MovimientoResponse,
    MovimientoDetalleResponse,
)
from app.models import TipoMovimiento


router = APIRouter(prefix="/espacios", tags=["espacios"])


@router.post(
    "",
    response_model=EspacioResponse,
    status_code=201,
    summary="Crear un nuevo espacio",
    description="Crea un nuevo espacio de exhibición. El código debe ser único."
)
async def crear_espacio(espacio: EspacioCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await EspacioService.create(db, espacio)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "",
    response_model=List[EspacioConProductoResponse],
    summary="Listar espacios",
    description="Obtiene la lista de todos los espacios con su estado y producto actual."
)
async def listar_espacios(db: AsyncSession = Depends(get_db)):
    return await EspacioService.get_all(db)


@router.get(
    "/{espacio_id}",
    response_model=EspacioConProductoResponse,
    summary="Obtener espacio por ID",
    description="Obtiene los detalles de un espacio específico con su producto actual."
)
async def obtener_espacio(espacio_id: int, db: AsyncSession = Depends(get_db)):
    espacio = await EspacioService.get_by_id(db, espacio_id)
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    return espacio


@router.put(
    "/{espacio_id}",
    response_model=EspacioResponse,
    summary="Actualizar espacio",
    description="Actualiza los datos de un espacio. El código debe seguir siendo único."
)
async def actualizar_espacio(
    espacio_id: int,
    espacio_data: EspacioUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        espacio = await EspacioService.update(db, espacio_id, espacio_data)
        if not espacio:
            raise HTTPException(status_code=404, detail="Espacio no encontrado")
        return espacio
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete(
    "/{espacio_id}",
    response_model=EspacioResponse,
    summary="Eliminar espacio",
    description="Elimina un espacio solo si está libre."
)
async def eliminar_espacio(espacio_id: int, db: AsyncSession = Depends(get_db)):
    try:
        espacio = await EspacioService.delete(db, espacio_id)
        if not espacio:
            raise HTTPException(status_code=404, detail="Espacio no encontrado")
        return espacio
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{espacio_id}/reponer",
    response_model=MovimientoDetalleResponse,
    summary="Reponer espacio",
    description="Repone un espacio libre con un producto. Cambia el estado a OCUPADO y registra el movimiento."
)
async def reponer_espacio(
    espacio_id: int,
    request: ReponerRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        movimiento = await MovimientoService.reponer(db, espacio_id, request)
        espacio = await EspacioService.get_by_id(db, espacio_id)
        return MovimientoDetalleResponse(
            id=movimiento.id,
            espacio_id=movimiento.espacio_id,
            producto_id=movimiento.producto_id,
            tipo=movimiento.tipo,
            fecha_hora=movimiento.fecha_hora,
            espacio_codigo=espacio.codigo,
            producto_nombre=espacio.producto_actual.nombre if espacio.producto_actual else "",
            producto_categoria=espacio.producto_actual.categoria if espacio.producto_actual else ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{espacio_id}/liberar",
    response_model=MovimientoDetalleResponse,
    summary="Liberar espacio",
    description="Libera un espacio ocupado. Cambia el estado a LIBRE y registra el movimiento de salida."
)
async def liberar_espacio(espacio_id: int, db: AsyncSession = Depends(get_db)):
    try:
        movimiento = await MovimientoService.liberar(db, espacio_id)
        espacio = await EspacioService.get_by_id(db, espacio_id)
        producto = await EspacioService.get_by_id(db, espacio_id)  # We need the product that was there
        
        # Get the product from the movement
        from app.services import ProductoService
        producto_obj = await ProductoService.get_by_id(db, movimiento.producto_id)
        
        return MovimientoDetalleResponse(
            id=movimiento.id,
            espacio_id=movimiento.espacio_id,
            producto_id=movimiento.producto_id,
            tipo=movimiento.tipo,
            fecha_hora=movimiento.fecha_hora,
            espacio_codigo=espacio.codigo,
            producto_nombre=producto_obj.nombre if producto_obj else "",
            producto_categoria=producto_obj.categoria if producto_obj else ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
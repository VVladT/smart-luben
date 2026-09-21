from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.services import ProductoService, MovimientoService
from app.schemas import (
    ProductoCreate,
    ProductoUpdate,
    ProductoResponse,
    ProductoListResponse,
    MovimientoResponse,
    MovimientoDetalleResponse,
    ReponerRequest,
    MovimientoFiltros,
)
from app.models import TipoMovimiento


router = APIRouter(prefix="/productos", tags=["productos"])


@router.post(
    "",
    response_model=ProductoResponse,
    status_code=201,
    summary="Crear un nuevo producto",
    description="Crea un nuevo producto en el sistema. El nombre debe ser único."
)
async def crear_producto(producto: ProductoCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await ProductoService.create(db, producto)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "",
    response_model=List[ProductoListResponse],
    summary="Listar productos",
    description="Obtiene la lista de productos. Se puede filtrar por estado activo."
)
async def listar_productos(
    activo: Optional[bool] = Query(None, description="Filtrar por productos activos/inactivos"),
    db: AsyncSession = Depends(get_db)
):
    return await ProductoService.get_all(db, activo=activo)


@router.get(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Obtener producto por ID",
    description="Obtiene los detalles de un producto específico."
)
async def obtener_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    producto = await ProductoService.get_by_id(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.put(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Actualizar producto",
    description="Actualiza los datos de un producto. El nombre debe seguir siendo único."
)
async def actualizar_producto(
    producto_id: int,
    producto_data: ProductoUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        producto = await ProductoService.update(db, producto_id, producto_data)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Eliminar producto (soft delete)",
    description="Desactiva un producto (soft delete). No lo elimina físicamente."
)
async def eliminar_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    producto = await ProductoService.soft_delete(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.models import Producto, Espacio, Movimiento, EstadoEspacio, TipoMovimiento
from app.schemas import (
    ProductoCreate,
    ProductoUpdate,
    EspacioCreate,
    EspacioUpdate,
    MovimientoCreate,
    ReponerRequest,
    MovimientoFiltros,
    DashboardResumen,
)


class ProductoService:
    @staticmethod
    async def get_all(db: AsyncSession, activo: Optional[bool] = None) -> List[Producto]:
        query = select(Producto)
        if activo is not None:
            query = query.where(Producto.activo == activo)
        query = query.order_by(Producto.id)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, producto_id: int) -> Optional[Producto]:
        result = await db.execute(select(Producto).where(Producto.id == producto_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_nombre(db: AsyncSession, nombre: str) -> Optional[Producto]:
        result = await db.execute(select(Producto).where(Producto.nombre == nombre))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, producto_data: ProductoCreate) -> Producto:
        existing = await ProductoService.get_by_nombre(db, producto_data.nombre)
        if existing:
            raise ValueError("Ya existe un producto con este nombre")
        
        producto = Producto(**producto_data.model_dump())
        db.add(producto)
        await db.commit()
        await db.refresh(producto)
        return producto

    @staticmethod
    async def update(db: AsyncSession, producto_id: int, producto_data: ProductoUpdate) -> Optional[Producto]:
        producto = await ProductoService.get_by_id(db, producto_id)
        if not producto:
            return None
        
        update_data = producto_data.model_dump(exclude_unset=True)
        
        if "nombre" in update_data:
            existing = await ProductoService.get_by_nombre(db, update_data["nombre"])
            if existing and existing.id != producto_id:
                raise ValueError("Ya existe un producto con este nombre")
        
        for key, value in update_data.items():
            setattr(producto, key, value)
        
        await db.commit()
        await db.refresh(producto)
        return producto

    @staticmethod
    async def soft_delete(db: AsyncSession, producto_id: int) -> Optional[Producto]:
        producto = await ProductoService.get_by_id(db, producto_id)
        if not producto:
            return None
        
        producto.activo = False
        await db.commit()
        await db.refresh(producto)
        return producto


class EspacioService:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Espacio]:
        query = select(Espacio).options(selectinload(Espacio.producto_actual)).order_by(Espacio.id)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, espacio_id: int) -> Optional[Espacio]:
        query = select(Espacio).options(selectinload(Espacio.producto_actual)).where(Espacio.id == espacio_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_codigo(db: AsyncSession, codigo: str) -> Optional[Espacio]:
        result = await db.execute(select(Espacio).where(Espacio.codigo == codigo))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, espacio_data: EspacioCreate) -> Espacio:
        existing = await EspacioService.get_by_codigo(db, espacio_data.codigo)
        if existing:
            raise ValueError("Ya existe un espacio con este código")
        
        espacio = Espacio(**espacio_data.model_dump())
        db.add(espacio)
        await db.commit()
        await db.refresh(espacio)
        return espacio

    @staticmethod
    async def update(db: AsyncSession, espacio_id: int, espacio_data: EspacioUpdate) -> Optional[Espacio]:
        espacio = await EspacioService.get_by_id(db, espacio_id)
        if not espacio:
            return None
        
        update_data = espacio_data.model_dump(exclude_unset=True)
        
        if "codigo" in update_data:
            existing = await EspacioService.get_by_codigo(db, update_data["codigo"])
            if existing and existing.id != espacio_id:
                raise ValueError("Ya existe un espacio con este código")
        
        for key, value in update_data.items():
            setattr(espacio, key, value)
        
        await db.commit()
        await db.refresh(espacio)
        return espacio

    @staticmethod
    async def delete(db: AsyncSession, espacio_id: int) -> Optional[Espacio]:
        espacio = await EspacioService.get_by_id(db, espacio_id)
        if not espacio:
            return None
        
        if espacio.estado == EstadoEspacio.ocupado:
            raise ValueError("No se puede eliminar un espacio ocupado")
        
        await db.delete(espacio)
        await db.commit()
        return espacio


class MovimientoService:
    @staticmethod
    async def get_all(
        db: AsyncSession,
        filtros: Optional[MovimientoFiltros] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Movimiento]:
        query = select(Movimiento).options(
            selectinload(Movimiento.espacio),
            selectinload(Movimiento.producto)
        ).order_by(Movimiento.fecha_hora.desc())
        
        if filtros:
            if filtros.espacio_id:
                query = query.where(Movimiento.espacio_id == filtros.espacio_id)
            if filtros.producto_id:
                query = query.where(Movimiento.producto_id == filtros.producto_id)
            if filtros.tipo:
                query = query.where(Movimiento.tipo == filtros.tipo)
            if filtros.desde:
                query = query.where(Movimiento.fecha_hora >= filtros.desde)
            if filtros.hasta:
                query = query.where(Movimiento.fecha_hora <= filtros.hasta)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_espacio(db: AsyncSession, espacio_id: int) -> List[Movimiento]:
        query = select(Movimiento).options(
            selectinload(Movimiento.producto)
        ).where(Movimiento.espacio_id == espacio_id).order_by(Movimiento.fecha_hora.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, movimiento_data: MovimientoCreate) -> Movimiento:
        movimiento = Movimiento(**movimiento_data.model_dump())
        db.add(movimiento)
        await db.commit()
        await db.refresh(movimiento)
        return movimiento

    @staticmethod
    async def reponer(db: AsyncSession, espacio_id: int, request: ReponerRequest) -> Movimiento:
        espacio = await EspacioService.get_by_id(db, espacio_id)
        if not espacio:
            raise ValueError("Espacio no encontrado")
        
        if espacio.estado == EstadoEspacio.ocupado:
            raise ValueError("El espacio ya está ocupado")
        
        producto = await ProductoService.get_by_id(db, request.producto_id)
        if not producto:
            raise ValueError("Producto no encontrado")
        
        if not producto.activo:
            raise ValueError("El producto no está activo")
        
        espacio.estado = EstadoEspacio.ocupado
        espacio.producto_actual_id = request.producto_id
        
        movimiento = Movimiento(
            espacio_id=espacio_id,
            producto_id=request.producto_id,
            tipo=TipoMovimiento.reposicion
        )
        db.add(movimiento)
        await db.commit()
        await db.refresh(movimiento)
        await db.refresh(espacio)
        return movimiento

    @staticmethod
    async def liberar(db: AsyncSession, espacio_id: int) -> Movimiento:
        espacio = await EspacioService.get_by_id(db, espacio_id)
        if not espacio:
            raise ValueError("Espacio no encontrado")
        
        if espacio.estado == EstadoEspacio.libre:
            raise ValueError("El espacio ya está libre")
        
        producto_id = espacio.producto_actual_id
        
        espacio.estado = EstadoEspacio.libre
        espacio.producto_actual_id = None
        
        movimiento = Movimiento(
            espacio_id=espacio_id,
            producto_id=producto_id,
            tipo=TipoMovimiento.salida
        )
        db.add(movimiento)
        await db.commit()
        await db.refresh(movimiento)
        await db.refresh(espacio)
        return movimiento


class DashboardService:
    @staticmethod
    async def get_resumen(db: AsyncSession) -> DashboardResumen:
        total_espacios = await db.execute(select(func.count(Espacio.id)))
        espacios_libres = await db.execute(
            select(func.count(Espacio.id)).where(Espacio.estado == EstadoEspacio.libre)
        )
        espacios_ocupados = await db.execute(
            select(func.count(Espacio.id)).where(Espacio.estado == EstadoEspacio.ocupado)
        )
        productos_activos = await db.execute(
            select(func.count(Producto.id)).where(Producto.activo == True)
        )
        
        return DashboardResumen(
            total_espacios=total_espacios.scalar() or 0,
            espacios_libres=espacios_libres.scalar() or 0,
            espacios_ocupados=espacios_ocupados.scalar() or 0,
            productos_activos=productos_activos.scalar() or 0
        )
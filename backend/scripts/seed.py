import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.database import Base
from app.models import Producto, Espacio, EstadoEspacio, Movimiento


# Mostrador: exactamente 4 espacios
ESPACIOS_DESEADOS = [
    ("E01", "Fila 1, Col 1"),
    ("E02", "Fila 1, Col 2"),
    ("E03", "Fila 1, Col 3"),
    ("E04", "Fila 1, Col 4"),
]

PRODUCTOS_DESEADOS = [
    ("Empanada de pollo", "Salados", "https://ejemplo.com/empanada-pollo.jpg"),
    ("Cheesecake de fresa", "Postres", "https://ejemplo.com/cheesecake-fresa.jpg"),
    ("Carrot cake", "Postres", "https://ejemplo.com/carrot-cake.jpg"),
    ("Red velvet", "Postres", "https://ejemplo.com/red-velvet.jpg"),
    ("Milhojas", "Postres", "https://ejemplo.com/milhojas.jpg"),
    ("Croissant", "Desayuno", "https://ejemplo.com/croissant.jpg"),
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # --- Productos: upsert por nombre (idempotente, apto para cada deploy) ---
        productos_creados = 0
        for nombre, categoria, imagen_url in PRODUCTOS_DESEADOS:
            existing = await db.execute(select(Producto).where(Producto.nombre == nombre))
            if existing.scalars().first():
                continue
            db.add(Producto(nombre=nombre, categoria=categoria, imagen_url=imagen_url, activo=True))
            productos_creados += 1
        await db.commit()
        print(f"Productos nuevos: {productos_creados}")

        # --- Espacios: garantizar exactamente E01-E04 ---
        for codigo, ubicacion in ESPACIOS_DESEADOS:
            existing = await db.execute(select(Espacio).where(Espacio.codigo == codigo))
            if existing.scalars().first():
                continue
            db.add(Espacio(codigo=codigo, ubicacion=ubicacion, estado=EstadoEspacio.libre))
        await db.commit()

        # --- Reconciliación: eliminar extras (E05-E08 u otros) solo si están libres y sin historial ---
        codigos_deseados = {c for c, _ in ESPACIOS_DESEADOS}
        result = await db.execute(select(Espacio))
        todos = result.scalars().all()
        eliminados = 0
        for e in todos:
            if e.codigo in codigos_deseados:
                continue
            if e.estado != EstadoEspacio.libre:
                print(f"Espacio extra {e.codigo} ocupado, se conserva.")
                continue
            mov = await db.execute(select(Movimiento).where(Movimiento.espacio_id == e.id).limit(1))
            if mov.scalars().first():
                print(f"Espacio extra {e.codigo} con historial, se conserva.")
                continue
            await db.delete(e)
            eliminados += 1
        await db.commit()
        print(f"Espacios extra eliminados: {eliminados}")

        result = await db.execute(select(Espacio))
        print(f"Espacios totales: {len(result.scalars().all())} (deseados: {len(ESPACIOS_DESEADOS)})")
        print("Seed completado exitosamente!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.database import Base
from app.models import Producto, Espacio, EstadoEspacio


async def seed():
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        existing_productos = await db.execute(select(Producto))
        if existing_productos.scalars().first():
            print("Datos ya existen, saltando seed...")
            return
        
        productos = [
            Producto(nombre="Empanada de pollo", categoria="Salados", imagen_url="https://ejemplo.com/empanada-pollo.jpg", activo=True),
            Producto(nombre="Cheesecake de fresa", categoria="Postres", imagen_url="https://ejemplo.com/cheesecake-fresa.jpg", activo=True),
            Producto(nombre="Carrot cake", categoria="Postres", imagen_url="https://ejemplo.com/carrot-cake.jpg", activo=True),
            Producto(nombre="Red velvet", categoria="Postres", imagen_url="https://ejemplo.com/red-velvet.jpg", activo=True),
            Producto(nombre="Milhojas", categoria="Postres", imagen_url="https://ejemplo.com/milhojas.jpg", activo=True),
            Producto(nombre="Croissant", categoria="Desayuno", imagen_url="https://ejemplo.com/croissant.jpg", activo=True),
        ]
        
        for p in productos:
            db.add(p)
        await db.commit()
        
        for p in productos:
            await db.refresh(p)
        
        print(f"Creados {len(productos)} productos")
        
        espacios = [
            Espacio(codigo="E01", ubicacion="Fila 1, Col 1", estado=EstadoEspacio.libre),
            Espacio(codigo="E02", ubicacion="Fila 1, Col 2", estado=EstadoEspacio.libre),
            Espacio(codigo="E03", ubicacion="Fila 1, Col 3", estado=EstadoEspacio.libre),
            Espacio(codigo="E04", ubicacion="Fila 1, Col 4", estado=EstadoEspacio.libre),
            Espacio(codigo="E05", ubicacion="Fila 2, Col 1", estado=EstadoEspacio.libre),
            Espacio(codigo="E06", ubicacion="Fila 2, Col 2", estado=EstadoEspacio.libre),
            Espacio(codigo="E07", ubicacion="Fila 2, Col 3", estado=EstadoEspacio.libre),
            Espacio(codigo="E08", ubicacion="Fila 2, Col 4", estado=EstadoEspacio.libre),
        ]
        
        for e in espacios:
            db.add(e)
        await db.commit()
        
        print(f"Creados {len(espacios)} espacios")
        
        print("Seed completado exitosamente!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
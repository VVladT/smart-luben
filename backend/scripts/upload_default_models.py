"""Sube los GLB por defecto de ar/assets a MinIO y los asigna a productos.

Uso (una vez por entorno, con MinIO arriba):
    cd backend && ./venv/bin/python scripts/upload_default_models.py

Requiere: modelos en ../ar/assets/models/*.glb y productos seedados.
"""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Producto
from app.services.storage import ensure_buckets, get_client, public_url

AR_MODELS_DIR = os.getenv(
    "AR_MODELS_DIR",
    # En docker dev: ./ar/assets montado en /ar-assets (ver compose).
    "/ar-assets/models"
    if os.path.isdir("/ar-assets/models")
    else os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "ar", "assets", "models"),
)

# nombre en BD -> (archivo, scale, rotation_x_rad)
# rotation_x = pi/2 "acuesta" el modelo (GLB en Y-up sobre plano del target)
MODELOS = {
    "Empanada de pollo": ("empanada.glb", 1.0, 1.5708),
    "Cheesecake de fresa": ("strawberry_cheesecake.glb", 1.5, 1.5708),
    "Carrot cake": ("carrot_cake.glb", 1.4, 1.5708),
    "Red velvet": ("red_velvet.glb", 1.5, 1.5708),
    "Milhojas": ("milhojas.glb", 8.0, 1.5708),
    "Croissant": ("croissant.glb", 1.2, 1.5708),
}


async def main() -> None:
    ensure_buckets()
    client = get_client()

    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        for nombre, (archivo, scale, rot_x) in MODELOS.items():
            ruta = os.path.normpath(os.path.join(AR_MODELS_DIR, archivo))
            if not os.path.isfile(ruta):
                print(f"OMITIDO {nombre}: no existe {ruta}")
                continue

            result = await db.execute(select(Producto).where(Producto.nombre == nombre))
            producto = result.scalars().first()
            if not producto:
                print(f"OMITIDO {nombre}: producto no existe en BD (corre seed primero)")
                continue

            objeto = f"modelos/{archivo}"
            client.fput_object("smart-luben", objeto, ruta, content_type="model/gltf-binary")
            producto.modelo_url = public_url("smart-luben", objeto)
            producto.scale = scale
            producto.rotation_x = rot_x
            producto.rotation_y = 0.0
            producto.rotation_z = 0.0
            print(f"OK {nombre} -> {producto.modelo_url} (scale={scale})")

        await db.commit()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

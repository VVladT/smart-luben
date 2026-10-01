"""Limpieza total del historial de movimientos y features ML.

Borra ml_features + movimientos y deja los espacios en libre/sin producto,
para partir de un historial coherente (los huérfanos existentes no se pueden
reparar: se eliminan). Uso:

    python scripts/clean_movements.py --yes
    make clean-movements
"""
import argparse
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Espacio, EstadoEspacio, MlFeature, Movimiento


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        n_feat = (await db.execute(MlFeature.__table__.delete())).rowcount
        n_mov = (await db.execute(Movimiento.__table__.delete())).rowcount
        await db.execute(
            Espacio.__table__.update().values(estado=EstadoEspacio.libre, producto_actual_id=None)
        )
        await db.commit()
        print(f"ml_features eliminadas: {n_feat}")
        print(f"movimientos eliminados: {n_mov}")
        print("Espacios reseteados a libre/sin producto.")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpia movimientos y features ML")
    parser.add_argument("--yes", action="store_true", help="Confirmar borrado (obligatorio)")
    args = parser.parse_args()
    if not args.yes and os.getenv("FORCE") != "true":
        print("Esto BORRA todos los movimientos y features ML. Re-ejecuta con --yes para confirmar.")
        sys.exit(1)
    asyncio.run(main())

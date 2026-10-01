import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.ml_features import MLFeatureService


async def main():
    dias_atras = 180
    if len(sys.argv) > 1:
        try:
            dias_atras = int(sys.argv[1])
        except ValueError:
            print("Uso: python scripts/materialize_ml_features.py [dias_atras]")
            return
    
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        count = await MLFeatureService.materialize_features(db, dias_atras=dias_atras)
        print(f"Features materializadas: {count}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
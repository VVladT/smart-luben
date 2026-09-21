import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.database import Base, get_db
from app.config import settings

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/smart_luben_test"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine_test
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(db_engine):
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_producto(db_session):
    from app.models import Producto
    producto = Producto(nombre="Test Product", categoria="Test", activo=True)
    db_session.add(producto)
    await db_session.commit()
    await db_session.refresh(producto)
    return producto


@pytest_asyncio.fixture
async def sample_espacio(db_session):
    from app.models import Espacio, EstadoEspacio
    espacio = Espacio(codigo="E01", ubicacion="Fila 1, Col 1", estado=EstadoEspacio.libre)
    db_session.add(espacio)
    await db_session.commit()
    await db_session.refresh(espacio)
    return espacio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import productos, espacios, movimientos, dashboard, chatbot, ml_suggestions, uploads, sync
from app.routers.uploads import storage_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.services.storage import ensure_buckets

        ensure_buckets()
        print("S3 buckets listos")
    except Exception as e:
        # Sin S3 (tests/CI/dev sin garage) la API sigue viva; presign lo reintenta
        print(f"S3 no disponible al arrancar: {e}")
    yield


app = FastAPI(
    title="SmartLuben API",
    description="API para gestión de exhibición y reposición de productos en mostrador de confitería",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(productos.router, prefix="/api")
app.include_router(espacios.router, prefix="/api")
app.include_router(movimientos.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")
app.include_router(ml_suggestions.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(storage_router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "SmartLuben API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}

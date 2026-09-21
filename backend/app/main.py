from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import productos, espacios, movimientos, dashboard


app = FastAPI(
    title="SmartLuben API",
    description="API para gestión de exhibición y reposición de productos en mostrador de confitería",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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

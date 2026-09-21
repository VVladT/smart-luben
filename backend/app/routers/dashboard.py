from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import DashboardService
from app.schemas import DashboardResumen


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/resumen",
    response_model=DashboardResumen,
    summary="Resumen del dashboard",
    description="Obtiene un resumen del estado actual: total de espacios, libres, ocupados y productos activos."
)
async def obtener_resumen(db: AsyncSession = Depends(get_db)):
    return await DashboardService.get_resumen(db)
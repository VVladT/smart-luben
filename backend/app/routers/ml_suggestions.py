from datetime import datetime, timezone
from typing import List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import MLFeatureService, ProductoService, EspacioService
from app.services.demand_predictor import DemandPredictor
from app.services.space_product_ranker import SpaceProductRanker
from app.services.disposition_optimizer import (
    GreedyDispositionOptimizer,
    build_space_info_from_db,
)
from app.models import EstadoEspacio, Espacio


router = APIRouter(prefix="/ml", tags=["ML"])


class MLSuggestionRequest(BaseModel):
    target_datetime: datetime
    top_k: int = 5


class SpaceProductRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    espacio_id: int
    espacio_codigo: str
    producto_id: int
    producto_nombre: str
    score: float
    demand_score: float
    ranker_score: float
    reason: str


class SuggestionMetadata(BaseModel):
    free_spaces_count: int
    productos_recommended: int
    max_per_product: int
    model_version: str
    generated_at: datetime


class MLSuggestionResponse(BaseModel):
    recommendations: List[SpaceProductRecommendation]
    disposition: dict[str, str]  # espacio_codigo -> producto_nombre
    occupied: dict[str, str] = {}  # espacios ocupados (sin sugerencia) codigo -> producto_nombre
    metadata: SuggestionMetadata


class MLPlanNowResponse(BaseModel):
    target_datetime: datetime
    planned: List[SpaceProductRecommendation]
    skipped: List[str]  # Códigos sin recomendación (p. ej. modelo sin candidatos)


@router.post("/suggest", response_model=MLSuggestionResponse)
async def suggest_replenishment(
    request: MLSuggestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Genera recomendaciones de reposición y disposición para una fecha/hora específica.
    
    Pipeline:
    1. Obtener espacios libres y productos activos
    2. Extraer features ML para (espacios_libres × productos × target_dow/hour)
    3. DemandPredictor → demand_score por producto
    4. SpaceProductRanker → ranker_score por (espacio, producto)
    5. GreedyDispositionOptimizer → asignación final con límite 50%
    7. Construir respuesta con recomendaciones, disposición y razones
    """
    target_dt = request.target_datetime
    
    # Validar y normalizar target_datetime
    if target_dt.tzinfo is None:
        raise HTTPException(
            status_code=400,
            detail="target_datetime debe incluir zona horaria (ej: 2026-09-29T10:00:00-05:00 o 2026-09-29T15:00:00+00:00)"
        )
    
    return await _suggest_for_datetime(db, target_dt.astimezone(timezone.utc))


async def _suggest_for_datetime(db: AsyncSession, target_dt: datetime) -> MLSuggestionResponse:
    """Calcula recomendaciones sin modificar el mostrador."""
    # 1. Obtener datos base
    productos = await ProductoService.get_all(db, activo=True)
    producto_ids = [p.id for p in productos]
    producto_map = {p.id: p.nombre for p in productos}
    
    espacios = await EspacioService.get_all(db)
    free_spaces = [
        e for e in espacios
        if e.estado == EstadoEspacio.libre and e.producto_actual_id is None
    ]
    free_space_ids = [e.id for e in free_spaces]
    
    if not free_spaces or not productos:
        return MLSuggestionResponse(
            recommendations=[],
            disposition={},
            occupied={
                e.codigo: (producto_map.get(e.producto_actual_id, "desconocido"))
                for e in espacios
                if e.estado == EstadoEspacio.ocupado
            },
            metadata=SuggestionMetadata(
                free_spaces_count=len(free_spaces),
                productos_recommended=0,
                max_per_product=0,
                model_version="v1.0",
                generated_at=datetime.now(timezone.utc)
            )
        )
    
    # 2. Features para inferencia
    inference_feats = await MLFeatureService.get_features_for_inference(
        db, target_dt, free_space_ids, producto_ids
    )
    
    for f in inference_feats:
        f['dow'] = target_dt.weekday()
        f['hour'] = target_dt.hour
    
    # 3. DemandPredictor
    demand_predictor = DemandPredictor()
    demand_ranking = demand_predictor.get_demand_ranking(inference_feats, top_k=len(productos))
    demand_scores = {r['producto_id']: r['demand_score'] for r in demand_ranking}
    
    # 4. SpaceProductRanker
    ranker = SpaceProductRanker()
    space_product_scores = {}
    for f in inference_feats:
        score = ranker.get_space_product_score(f)
        space_product_scores[(f['espacio_id'], f['producto_id'])] = score
    
    # 5. Optimizador Greedy
    space_infos = build_space_info_from_db(free_spaces)
    
    optimizer = GreedyDispositionOptimizer(max_product_share=0.5)
    assignments = optimizer.optimize(
        free_spaces=space_infos,
        demand_scores=demand_scores,
        space_product_scores=space_product_scores,
        current_occupancy={}
    )
    
    # 6. Construir respuesta
    recommendations = []
    disposition = {}
    
    for espacio_id, (producto_id, combined_score, reason) in assignments.items():
        space = next(s for s in space_infos if s.espacio_id == espacio_id)
        producto_nombre = producto_map.get(producto_id, f"Producto {producto_id}")
        
        # Obtener scores individuales
        demand_score = demand_scores.get(producto_id, 0.0)
        ranker_score = space_product_scores.get((espacio_id, producto_id), 0.0)
        
        recommendations.append(SpaceProductRecommendation(
            espacio_id=espacio_id,
            espacio_codigo=space.espacio_codigo,
            producto_id=producto_id,
            producto_nombre=producto_nombre,
            score=combined_score,
            demand_score=demand_score,
            ranker_score=ranker_score,
            reason=reason
        ))
        
        disposition[space.espacio_codigo] = producto_nombre
    
    # Metadata
    max_per_product = max(1, int(len(free_spaces) * 0.5))

    occupied = {
        e.codigo: producto_map.get(e.producto_actual_id, "desconocido")
        for e in espacios
        if e.estado == EstadoEspacio.ocupado
    }

    return MLSuggestionResponse(
        recommendations=recommendations,
        disposition=disposition,
        occupied=occupied,
        metadata=SuggestionMetadata(
            free_spaces_count=len(free_spaces),
            productos_recommended=len(set(disposition.values())),
            max_per_product=max_per_product,
            model_version="v1.0",
            generated_at=datetime.now(timezone.utc)
        )
    )


@router.post("/plan-now", response_model=MLPlanNowResponse)
async def plan_replenishment_now(db: AsyncSession = Depends(get_db)):
    """Planifica ahora los espacios vacíos; no ocupa ni registra movimientos."""
    target_dt = datetime.now(ZoneInfo("America/Lima"))
    try:
        # Bloquear en orden estable para serializar ejecuciones automáticas.
        # Mantener los bloqueos durante el cálculo y todas las asignaciones.
        await db.execute(select(Espacio.id).order_by(Espacio.id).with_for_update())
        suggestion = await _suggest_for_datetime(db, target_dt.astimezone(timezone.utc))
        for item in suggestion.recommendations:
            await EspacioService.planificar(db, item.espacio_id, item.producto_id, commit=False)

        planned_codes = {item.espacio_codigo for item in suggestion.recommendations}
        espacios = await EspacioService.get_all(db)
        skipped = [
            e.codigo for e in espacios
            if e.estado == EstadoEspacio.libre
            and e.producto_actual_id is None
            and e.codigo not in planned_codes
        ]
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        await db.rollback()
        raise

    return MLPlanNowResponse(
        target_datetime=target_dt,
        planned=suggestion.recommendations,
        skipped=skipped,
    )


@router.get("/health")
async def ml_health():
    """Health check del servicio ML"""
    return {
        "status": "healthy",
        "service": "ml-suggestions",
        "models": ["demand_predictor", "space_product_ranker", "greedy_optimizer"]
    }

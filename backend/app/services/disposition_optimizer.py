from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SpaceInfo:
    espacio_id: int
    espacio_codigo: str
    zona: str
    prioridad: int  # menor = mayor prioridad


@dataclass
class ProductScore:
    producto_id: int
    demand_score: float  # del DemandPredictor (0-1+)
    ranker_scores: Dict[int, float]  # espacio_id -> score


class GreedyDispositionOptimizer:
    """
    Optimizador greedy para asignación espacio-producto.
    
    Reglas:
    - Cada espacio → 1 producto máximo
    - Un producto puede ocupar múltiples espacios
    - Límite: un producto no puede exceder 50% del mostrador (espacios libres)
    - Prioridad de espacios: por zona/trafico (Fila 1 > Fila 2 > ...)
    - Score combinado: demand_score * ranker_score
    """
    
    MAX_PRODUCT_SHARE = 0.5  # 50% del mostrador
    
    # Prioridad por zona (menor = mejor ubicación)
    ZONE_PRIORITY = {
        "Fila 1": 1,
        "Fila 2": 2,
        "Fila 3": 3,
        "Fila 4": 4,
    }
    
    def __init__(self, max_product_share: float = 0.5):
        self.max_product_share = max_product_share
    
    def optimize(
        self,
        free_spaces: List[SpaceInfo],
        demand_scores: Dict[int, float],  # producto_id -> demand_score
        space_product_scores: Dict[Tuple[int, int], float],  # (espacio_id, producto_id) -> ranker_score
        current_occupancy: Optional[Dict[int, int]] = None,  # producto_id -> count espacios ocupados actualmente
    ) -> Dict[int, Tuple[int, float, str]]:
        """
        Ejecuta asignación greedy.
        
        Args:
            free_spaces: Lista de espacios libres con info
            demand_scores: Score de demanda por producto (0-1+)
            space_product_scores: Score de ranker por (espacio, producto)
            current_occupancy: Espacios ya ocupados por producto (para límite 50% total)
        
        Returns:
            Dict {espacio_id: (producto_id, combined_score, reason)}
        """
        if not free_spaces:
            return {}
        
        current_occupancy = current_occupancy or {}
        total_free = len(free_spaces)
        max_per_product = max(1, int(total_free * self.max_product_share))
        
        # Contar ocupados actuales + asignaciones nuevas
        product_assignments = {pid: count for pid, count in current_occupancy.items()}
        
        # Ordenar espacios por prioridad
        sorted_spaces = sorted(free_spaces, key=lambda s: (s.prioridad, s.espacio_id))
        
        assignments = {}
        
        for space in sorted_spaces:
            espacio_id = space.espacio_id
            
            # Candidatos: productos con demand_score > 0 y que no exceden límite
            candidates = []
            # Default ranker score for missing combinations
            default_ranker_score = 0.5
            for producto_id, demand_score in demand_scores.items():
                if demand_score <= 0:
                    continue
                
                current_count = product_assignments.get(producto_id, 0)
                if current_count >= max_per_product:
                    continue  # Límite 50% alcanzado
                
                ranker_score = space_product_scores.get((espacio_id, producto_id), default_ranker_score)
                # Always consider candidates, even with default ranker score
                combined_score = demand_score * ranker_score
                candidates.append((producto_id, combined_score, demand_score, ranker_score))
            
            if not candidates:
                continue
            
            # Elegir mejor candidato
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_producto_id, best_combined, best_demand, best_ranker = candidates[0]
            
            # Asignar
            assignments[espacio_id] = (best_producto_id, best_combined, self._build_reason(
                space, best_producto_id, best_demand, best_ranker, len(candidates)
            ))
            product_assignments[best_producto_id] = product_assignments.get(best_producto_id, 0) + 1
        
        return assignments
    
    def _build_reason(
        self, 
        space: SpaceInfo, 
        producto_id: int, 
        demand_score: float, 
        ranker_score: float,
        n_candidates: int
    ) -> str:
        """Genera explicación rule-based"""
        reasons = []
        
        if demand_score > 0.7:
            reasons.append("alta demanda")
        elif demand_score > 0.3:
            reasons.append("demanda media")
        else:
            reasons.append("demanda baja")
        
        if ranker_score > 0.8:
            reasons.append("afinidad histórica alta")
        elif ranker_score > 0.5:
            reasons.append("afinidad histórica media")
        else:
            reasons.append("afinidad histórica baja")
        
        if space.prioridad == 1:
            reasons.append("ubicación prioritaria")
        
        if n_candidates > 1:
            reasons.append(f"{n_candidates} opciones evaluadas")
        
        return f"Producto {producto_id}: {', '.join(reasons)} (score={demand_score * ranker_score:.3f})"


def build_space_info_from_db(espacios) -> List[SpaceInfo]:
    """Convierte espacios de BD a SpaceInfo con prioridad por zona"""
    result = []
    for e in espacios:
        zona = "Fila 1" if "Fila 1" in e.ubicacion else "Fila 2" if "Fila 2" in e.ubicacion else "Otra"
        prioridad = GreedyDispositionOptimizer.ZONE_PRIORITY.get(zona, 99)
        result.append(SpaceInfo(
            espacio_id=e.id,
            espacio_codigo=e.codigo,
            zona=zona,
            prioridad=prioridad
        ))
    return result


async def main():
    """Test rápido"""
    from app.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.services import EspacioService, ProductoService
    from app.services.demand_predictor import DemandPredictor
    from app.services.space_product_ranker import SpaceProductRanker
    from app.services.ml_features import MLFeatureService
    from datetime import datetime
    
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        target_dt = datetime(2026, 9, 28, 8, 0)
        productos = await ProductoService.get_all(db, activo=True)
        producto_ids = [p.id for p in productos]
        espacios = await EspacioService.get_all(db)
        free_space_ids = [e.id for e in espacios]  # todos libres
        
        inference_feats = await MLFeatureService.get_features_for_inference(
            db, target_dt, free_space_ids, producto_ids
        )
        
        for f in inference_feats:
            f['dow'] = target_dt.weekday()
            f['hour'] = target_dt.hour
    
    await engine.dispose()
    
    # 1. Demand scores
    demand_predictor = DemandPredictor()
    demand_ranking = demand_predictor.get_demand_ranking(inference_feats, top_k=20)
    demand_scores = {r['producto_id']: r['demand_score'] for r in demand_ranking}
    
    # 2. Ranker scores
    ranker = SpaceProductRanker()
    space_product_scores = {}
    for f in inference_feats:
        score = ranker.get_space_product_score(f)
        space_product_scores[(f['espacio_id'], f['producto_id'])] = score
    
    # 3. Espacios libres
    free_spaces = [e for e in espacios if e.estado.value == 'libre']
    space_infos = build_space_info_from_db(free_spaces)
    
    # 4. Optimizar
    optimizer = GreedyDispositionOptimizer(max_product_share=0.5)
    assignments = optimizer.optimize(
        free_spaces=space_infos,
        demand_scores=demand_scores,
        space_product_scores=space_product_scores,
        current_occupancy={}
    )
    
    print(f"\n=== Disposición Greedy para {target_dt.strftime('%A %H:%M')} ===")
    print(f"Espacios libres: {len(free_spaces)}, Límite por producto: {max(1, int(len(free_spaces) * 0.5))}")
    
    for espacio_id, (producto_id, score, reason) in sorted(assignments.items()):
        space = next(s for s in space_infos if s.espacio_id == espacio_id)
        print(f"  {space.espacio_codigo} ({space.zona}) → Producto {producto_id} | Score: {score:.4f} | {reason}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
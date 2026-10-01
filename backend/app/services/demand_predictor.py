import json
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class DemandPredictor:
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            model_path = str(MODEL_DIR / "demand_model_latest.pkl")
            meta_path = str(MODEL_DIR / "demand_model_latest_meta.json")
        else:
            model_path = str(model_path)
            meta_path = str(Path(model_path).with_suffix("_meta.json"))
        
        self.model = joblib.load(model_path)
        
        with open(meta_path, "r") as f:
            self.metadata = json.load(f)
        
        self.feature_names = self.metadata["features"]
        self.categorical_features = self.metadata.get("categorical_features", [])
        
        print(f"DemandPredictor cargado: {Path(model_path).name}")
        print(f"  Features: {len(self.feature_names)}")
        print(f"  Entrenado: {self.metadata.get('trained_at', 'unknown')}")
    
    def predict(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Predice demanda para cada fila del DataFrame.
        
        Args:
            features_df: DataFrame con columnas [dow, hour, salida_count_7d, ...]
        
        Returns:
            Array con predicciones (salidas esperadas en 7 días)
        """
        # Asegurar orden de columnas
        missing = set(self.feature_names) - set(features_df.columns)
        if missing:
            raise ValueError(f"Faltan features: {missing}")
        
        X = features_df[self.feature_names].copy()
        
        # Convertir categóricas
        for cat in self.categorical_features:
            if cat in X.columns:
                X[cat] = X[cat].astype("category")
        
        preds = self.model.predict(X)
        
        # Poisson puede dar negativos pequeños, clamp a 0
        return np.maximum(preds, 0)
    
    def predict_single(self, features: Dict) -> float:
        """Predice para un solo registro"""
        df = pd.DataFrame([features])
        return float(self.predict(df)[0])
    
    def get_demand_ranking(
        self, 
        features_list: List[Dict], 
        top_k: int = 10
    ) -> List[Dict]:
        """
        Dada una lista de features (una por producto), retorna ranking por demanda predicha.
        """
        if not features_list:
            return []
        
        df = pd.DataFrame(features_list)
        preds = self.predict(df)
        
        results = []
        for i, feat in enumerate(features_list):
            results.append({
                **feat,
                "demand_score": float(preds[i]),
                "demand_rank": 0,  # Se llena después
            })
        
        # Ordenar por demanda descendente
        results.sort(key=lambda x: x["demand_score"], reverse=True)
        
        # Asignar rank
        for rank, r in enumerate(results, 1):
            r["demand_rank"] = rank
        
        return results[:top_k]


async def main():
    """Test rápido"""
    from app.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.services import MLFeatureService, ProductoService, EspacioService
    from datetime import datetime
    
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # Obtener features para Lunes 8am
        target_dt = datetime(2026, 9, 28, 8, 0)
        productos = await ProductoService.get_all(db, activo=True)
        producto_ids = [p.id for p in productos]
        espacios = await EspacioService.get_all(db)
        free_space_ids = [e.id for e in espacios]
        
        inference_feats = await MLFeatureService.get_features_for_inference(
            db, target_dt, free_space_ids, producto_ids
        )
        
        # Preparar para demand predictor (agregar dow, hour)
        for f in inference_feats:
            f["dow"] = target_dt.weekday()
            f["hour"] = target_dt.hour
    
    await engine.dispose()
    
    # Test predictor
    predictor = DemandPredictor()
    ranking = predictor.get_demand_ranking(inference_feats, top_k=10)
    
    print(f"\n=== Ranking Demanda para {target_dt.strftime('%A %H:%M')} ===")
    for r in ranking:
        print(f"  Rank {r['demand_rank']}: Espacio={r['espacio_id']}, Producto={r['producto_id']}, "
              f"Demanda={r['demand_score']:.4f}, Share={r['space_product_share']:.3f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
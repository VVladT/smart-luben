import json
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class SpaceProductRanker:
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            model_path = str(MODEL_DIR / "ranker_model_latest.pkl")
            meta_path = str(MODEL_DIR / "ranker_model_latest_meta.json")
        else:
            model_path = str(model_path)
            meta_path = str(Path(model_path).with_suffix("_meta.json"))
        
        self.model = joblib.load(model_path)
        
        with open(meta_path, "r") as f:
            self.metadata = json.load(f)
        
        self.feature_names = self.metadata["features"]
        self.categorical_features = self.metadata.get("categorical_features", [])
        
        print(f"SpaceProductRanker cargado: {Path(model_path).name}")
        print(f"  Features: {len(self.feature_names)}")
        print(f"  Entrenado: {self.metadata.get('trained_at', 'unknown')}")
    
    def predict(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Predice score de afinidad para cada (espacio, producto).
        
        Args:
            features_df: DataFrame con columnas [dow, hour, salida_count_7d, ...]
        
        Returns:
            Array con scores de ranking (mayor = mejor match)
        """
        missing = set(self.feature_names) - set(features_df.columns)
        if missing:
            raise ValueError(f"Faltan features: {missing}")
        
        X = features_df[self.feature_names].copy()
        
        for cat in self.categorical_features:
            if cat in X.columns:
                X[cat] = X[cat].astype("category")
        
        scores = self.model.predict(X)
        
        # Para combinaciones no vistas durante entrenamiento, el modelo puede devolver 0
        # Asignamos un score pequeño positivo para permitir exploración
        scores = np.where(scores <= 0, 0.01, scores)
        return scores
    
    def rank_for_spaces(
        self, 
        features_list: List[Dict], 
        top_k_per_space: int = 3
    ) -> Dict[int, List[Dict]]:
        """
        Dada lista de features (espacio × producto), retorna top-K productos por espacio.
        
        Returns:
            Dict {espacio_id: [{producto_id, score, rank}, ...]}
        """
        if not features_list:
            return {}
        
        df = pd.DataFrame(features_list)
        scores = self.predict(df)
        
        results = []
        for i, feat in enumerate(features_list):
            results.append({
                "espacio_id": feat["espacio_id"],
                "producto_id": feat["producto_id"],
                "ranker_score": float(scores[i]),
            })
        
        # Agrupar por espacio y ordenar
        df_results = pd.DataFrame(results)
        ranked = {}
        
        for espacio_id, group in df_results.groupby("espacio_id"):
            group = group.sort_values("ranker_score", ascending=False).head(top_k_per_space)
            ranked[espacio_id] = [
                {"producto_id": int(row["producto_id"]), "ranker_score": float(row["ranker_score"])}
                for _, row in group.iterrows()
            ]
        
        return ranked
    
    def get_space_product_score(self, features: Dict) -> float:
        """Score para un par (espacio, producto)"""
        df = pd.DataFrame([features])
        return float(self.predict(df)[0])


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
        target_dt = datetime(2026, 9, 28, 8, 0)
        productos = await ProductoService.get_all(db, activo=True)
        producto_ids = [p.id for p in productos]
        espacios = await EspacioService.get_all(db)
        free_space_ids = [e.id for e in espacios]
        
        inference_feats = await MLFeatureService.get_features_for_inference(
            db, target_dt, free_space_ids, producto_ids
        )
        
        for f in inference_feats:
            f['dow'] = target_dt.weekday()
            f['hour'] = target_dt.hour
    
    await engine.dispose()
    
    ranker = SpaceProductRanker()
    ranked = ranker.rank_for_spaces(inference_feats, top_k_per_space=3)
    
    print(f"\n=== Top-3 Ranker por Espacio para {target_dt.strftime('%A %H:%M')} ===")
    for espacio_id, items in sorted(ranked.items()):
        print(f"  Espacio {espacio_id}:")
        for item in items:
            print(f"    Producto {item['producto_id']}: score={item['ranker_score']:.4f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import ndcg_score
from sklearn.model_selection import GroupShuffleSplit

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import MlFeature, Movimiento, Producto, TipoMovimiento


MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURE_COLS = [
    "dow",
    "hour",
    "salida_count_7d",
    "salida_count_30d",
    "salida_freq_dow",
    "salida_freq_hour",
    "salida_trend_7d",
    "reposicion_count",
    "reposicion_recency_days",
    "space_product_share",
    "categoria",
    "espacio_zona",
]

TARGET_COL = "label"  # 1 = reposicion historica, 0 = negativo sampleado


async def load_training_data() -> pd.DataFrame:
    """Crea dataset de Learning-to-Rank:
    - Positivos: (espacio, producto, dow, hour) de reposiciones históricas
    - Negativos: muestreo de (espacio, producto_libre) no colocados en ese contexto
    """
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # 1. POSITIVOS: reposiciones históricas con features
        pos_query = select(
            Movimiento.espacio_id,
            Movimiento.producto_id,
            func.extract('dow', Movimiento.fecha_hora).label('dow'),
            func.extract('hour', Movimiento.fecha_hora).label('hour'),
            MlFeature.salida_count_7d,
            MlFeature.salida_count_30d,
            MlFeature.salida_freq_dow,
            MlFeature.salida_freq_hour,
            MlFeature.salida_trend_7d,
            MlFeature.reposicion_count,
            MlFeature.reposicion_recency_days,
            MlFeature.space_product_share,
            MlFeature.espacio_zona,
            Producto.categoria,
        ).join(
            MlFeature,
            (MlFeature.espacio_id == Movimiento.espacio_id) &
            (MlFeature.producto_id == Movimiento.producto_id) &
            (MlFeature.dow == func.extract('dow', Movimiento.fecha_hora)) &
            (MlFeature.hour == func.extract('hour', Movimiento.fecha_hora))
        ).join(
            Producto, Producto.id == Movimiento.producto_id
        ).where(
            Movimiento.tipo == TipoMovimiento.reposicion
        )
        
        pos_result = await db.execute(pos_query)
        positivos = pos_result.all()
        
        # 2. Obtener todos los espacios y productos para muestreo negativo
        espacios_result = await db.execute(select(MlFeature.espacio_id).distinct())
        espacio_ids = [r[0] for r in espacios_result.all()]
        
        productos_result = await db.execute(select(Producto.id, Producto.categoria).where(Producto.activo == True))
        productos = [(r[0], r[1]) for r in productos_result.all()]
        
        dow_hour_result = await db.execute(select(MlFeature.dow, MlFeature.hour).distinct())
        dow_hours = [(r[0], r[1]) for r in dow_hour_result.all()]
    
    await engine.dispose()
    
    print(f"Positivos (reposiciones): {len(positivos)}")
    print(f"Espacios: {len(espacio_ids)}, Productos: {len(productos)}, Dow/Hour combos: {len(dow_hours)}")
    
    # Convertir positivos a DataFrame
    pos_data = []
    for row in positivos:
        pos_data.append({
            "espacio_id": row[0],
            "producto_id": row[1],
            "dow": int(row[2]),
            "hour": int(row[3]),
            "salida_count_7d": row[4] or 0,
            "salida_count_30d": row[5] or 0,
            "salida_freq_dow": row[6] or 0.0,
            "salida_freq_hour": row[7] or 0.0,
            "salida_trend_7d": row[8] or 0.0,
            "reposicion_count": row[9] or 0,
            "reposicion_recency_days": row[10] if row[10] is not None else 999,
            "space_product_share": row[11] or 0.0,
            "espacio_zona": row[12],
            "categoria": row[13],
            "label": 1,
        })
    
    pos_df = pd.DataFrame(pos_data)
    
    # 3. NEGATIVOS: muestreo estratificado
    # Para cada (espacio, dow, hour) positivo, samplear K productos que NO fueron colocados ahí
    negativos = []
    K_NEG_PER_POS = 3  # ratio 1:3
    
    # Agrupar positivos por (espacio, dow, hour) para saber qué productos ya están
    pos_groups = pos_df.groupby(['espacio_id', 'dow', 'hour'])['producto_id'].apply(set).to_dict()
    
    for (espacio_id, dow, hour), productos_positivos in pos_groups.items():
        productos_disponibles = [pid for pid, _ in productos if pid not in productos_positivos]
        if not productos_disponibles:
            continue
        
        n_neg = min(K_NEG_PER_POS * len(productos_positivos), len(productos_disponibles))
        productos_neg = np.random.choice(productos_disponibles, size=n_neg, replace=False)
        
        for pid in productos_neg:
            # Obtener features de este (espacio, producto, dow, hour) si existen
            feat_row = pos_df[
                (pos_df['espacio_id'] == espacio_id) & 
                (pos_df['dow'] == dow) & 
                (pos_df['hour'] == hour)
            ].head(1)
            
            if len(feat_row) > 0:
                base_feat = feat_row.iloc[0]
                negativos.append({
                    "espacio_id": espacio_id,
                    "producto_id": pid,
                    "dow": dow,
                    "hour": hour,
                    "salida_count_7d": base_feat['salida_count_7d'],
                    "salida_count_30d": base_feat['salida_count_30d'],
                    "salida_freq_dow": base_feat['salida_freq_dow'],
                    "salida_freq_hour": base_feat['salida_freq_hour'],
                    "salida_trend_7d": base_feat['salida_trend_7d'],
                    "reposicion_count": 0,  # nunca se colocó aquí
                    "reposicion_recency_days": 999,
                    "space_product_share": 0.0,
                    "espacio_zona": base_feat['espacio_zona'],
                    "categoria": next(cat for p_id, cat in productos if p_id == pid),
                    "label": 0,
                })
    
    neg_df = pd.DataFrame(negativos)
    print(f"Negativos sampleados: {len(neg_df)}")
    
    # Combinar
    df = pd.concat([pos_df, neg_df], ignore_index=True)
    print(f"Total registros: {len(df)} (pos={len(pos_df)}, neg={len(neg_df)})")
    print(f"Ratio pos/neg: {len(pos_df)/len(neg_df):.2f}")
    
    return df


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, np.ndarray]:
    """Prepara X, y y groups para LightGBM Ranker"""
    df = df.copy()
    df["categoria"] = df["categoria"].astype("category")
    df["espacio_zona"] = df["espacio_zona"].astype("category")
    
    # Group ID = (espacio_id, dow, hour) - cada grupo es un espacio en un contexto temporal
    df["group_id"] = df["espacio_id"].astype(str) + "_" + df["dow"].astype(str) + "_" + df["hour"].astype(str)
    groups = df.groupby("group_id").size().values
    
    # Ordenar por group_id para que LightGBM reciba grupos contiguos
    df = df.sort_values("group_id").reset_index(drop=True)
    groups = df.groupby("group_id").size().values
    
    X = df[FEATURE_COLS]
    y = df["label"]
    
    return X, y, groups


def train_ranker(X: pd.DataFrame, y: pd.Series, groups: np.ndarray) -> lgb.LGBMRanker:
    """Entrena LightGBM Ranker con validación por grupos"""
    
    # Split temporal por grupos (no mezclar grupos entre train/val)
    unique_groups = np.unique(np.repeat(np.arange(len(groups)), groups))
    n_groups = len(groups)
    
    # 70/15/15 split por grupos
    n_train = int(n_groups * 0.7)
    n_val = int(n_groups * 0.15)
    
    group_indices = np.arange(n_groups)
    np.random.seed(42)
    np.random.shuffle(group_indices)
    
    train_group_idx = group_indices[:n_train]
    val_group_idx = group_indices[n_train:n_train + n_val]
    test_group_idx = group_indices[n_train + n_val:]
    
    # Crear máscaras a nivel de fila
    train_mask = np.isin(np.repeat(np.arange(n_groups), groups), train_group_idx)
    val_mask = np.isin(np.repeat(np.arange(n_groups), groups), val_group_idx)
    test_mask = np.isin(np.repeat(np.arange(n_groups), groups), test_group_idx)
    
    X_train, y_train, g_train = X[train_mask], y[train_mask], groups[train_group_idx]
    X_val, y_val, g_val = X[val_mask], y[val_mask], groups[val_group_idx]
    X_test, y_test, g_test = X[test_mask], y[test_mask], groups[test_group_idx]
    
    print(f"Train: {len(X_train)} filas, {len(g_train)} grupos")
    print(f"Val: {len(X_val)} filas, {len(g_val)} grupos")
    print(f"Test: {len(X_test)} filas, {len(g_test)} grupos")
    
    model = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
        n_jobs=-1,
        label_gain=[0, 1],  # binary relevance
    )
    
    model.fit(
        X_train, y_train, group=g_train,
        eval_set=[(X_val, y_val)], eval_group=[g_val],
        eval_metric="ndcg",
        eval_at=[5, 10],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(50)],
        categorical_feature=["categoria", "espacio_zona"],
    )
    
    # Evaluación
    for name, X_split, y_split, g_split in [
        ("Train", X_train, y_train, g_train),
        ("Val", X_val, y_val, g_val),
        ("Test", X_test, y_test, g_test),
    ]:
        preds = model.predict(X_split)
        # NDCG por grupo
        ndcg_scores = []
        start = 0
        for g in g_split:
            end = start + g
            if end - start >= 2:  # necesita al menos 2 items para NDCG
                ndcg = ndcg_score([y_split[start:end]], [preds[start:end]], k=5)
                ndcg_scores.append(ndcg)
            start = end
        avg_ndcg = np.mean(ndcg_scores) if ndcg_scores else 0
        print(f"{name} - NDCG@5: {avg_ndcg:.4f}")
    
    # Feature importance
    importance = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    print("\nFeature Importance:")
    print(importance.to_string(index=False))
    
    return model


def save_model(model: lgb.LGBMRanker, feature_names: list):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODEL_DIR / f"ranker_model_{timestamp}.pkl"
    meta_path = MODEL_DIR / f"ranker_model_{timestamp}_meta.json"
    
    joblib.dump(model, model_path)
    
    metadata = {
        "model_type": "LightGBMRanker",
        "objective": "lambdarank",
        "features": feature_names,
        "categorical_features": ["categoria", "espacio_zona"],
        "trained_at": timestamp,
        "n_features": len(feature_names),
    }
    
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    latest_model = MODEL_DIR / "ranker_model_latest.pkl"
    latest_meta = MODEL_DIR / "ranker_model_latest_meta.json"
    if latest_model.exists():
        latest_model.unlink()
    if latest_meta.exists():
        latest_meta.unlink()
    latest_model.symlink_to(model_path.name)
    latest_meta.symlink_to(meta_path.name)
    
    print(f"\nModelo guardado: {model_path}")
    print(f"Metadatos: {meta_path}")


async def main():
    print("=== Entrenamiento Ranker Espacio-Producto ===\n")
    
    df = await load_training_data()
    X, y, groups = prepare_features(df)
    print(f"\nFeatures shape: {X.shape}")
    print(f"Grupos: {len(groups)}, items por grupo: {groups.mean():.1f} avg")
    
    model = train_ranker(X, y, groups)
    save_model(model, X.columns.tolist())
    
    print("\n=== Entrenamiento completado ===")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
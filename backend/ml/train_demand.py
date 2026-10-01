import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import MlFeature, Producto


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
]

TARGET_COL = "salida_count_7d"  # Predecir salidas próximas 7 días


async def load_training_data() -> pd.DataFrame:
    """Carga features de ml_features y agrega target real (salidas siguientes 7 días)"""
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # Obtener todas las features con info de producto
        query = select(MlFeature, Producto.categoria).join(Producto, MlFeature.producto_id == Producto.id)
        result = await db.execute(query)
        rows = result.all()
    
    await engine.dispose()
    
    if not rows:
        raise ValueError("No hay features en ml_features")
    
    # Convertir a DataFrame
    data = []
    for feat, categoria in rows:
        row = {
            "espacio_id": feat.espacio_id,
            "producto_id": feat.producto_id,
            "dow": feat.dow,
            "hour": feat.hour,
            "categoria": categoria,
            "espacio_zona": feat.espacio_zona,
        }
        for col in FEATURE_COLS:
            row[col] = getattr(feat, col)
        data.append(row)
    
    df = pd.DataFrame(data)
    print(f"Features cargadas: {len(df)} registros")
    print(f"Productos únicos: {df['producto_id'].nunique()}")
    print(f"Combinaciones dow/hour únicas: {df[['dow', 'hour']].drop_duplicates().shape[0]}")
    
    return df


def create_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea target: salidas reales en los próximos 7 días para cada (producto, dow, hour)
    Como no tenemos datos futuros en la misma tabla, usamos salida_count_7d como proxy
    En producción, esto se calcularía con ventanas temporales deslizantes
    """
    # Para entrenamiento, usamos salida_count_7d como target (es lo que queremos predecir)
    # En inferencia real, predecimos para una fecha futura
    df["target"] = df[TARGET_COL]
    return df


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepara X, y para entrenamiento"""
    # Features categóricas
    df = df.copy()
    df["categoria"] = df["categoria"].astype("category")
    df["espacio_zona"] = df["espacio_zona"].astype("category")
    
    # Features numéricas
    numeric_features = FEATURE_COLS
    categorical_features = ["categoria", "espacio_zona"]
    
    X = df[numeric_features + categorical_features]
    y = df["target"]
    
    return X, y


def train_model(X: pd.DataFrame, y: pd.Series) -> lgb.LGBMRegressor:
    """Entrena LightGBM Regressor con validación temporal"""
    
    # Split temporal: 70% train, 15% val, 15% test (por dow/hora)
    # Usamos dow/hour como proxy temporal
    unique_times = X[["dow", "hour"]].drop_duplicates().sort_values(["dow", "hour"])
    n_times = len(unique_times)
    
    train_times = unique_times.iloc[:int(n_times * 0.7)]
    val_times = unique_times.iloc[int(n_times * 0.7):int(n_times * 0.85)]
    test_times = unique_times.iloc[int(n_times * 0.85):]
    
    train_mask = X.set_index(["dow", "hour"]).index.isin(train_times.set_index(["dow", "hour"]).index)
    val_mask = X.set_index(["dow", "hour"]).index.isin(val_times.set_index(["dow", "hour"]).index)
    test_mask = X.set_index(["dow", "hour"]).index.isin(test_times.set_index(["dow", "hour"]).index)
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Modelo LightGBM
    model = lgb.LGBMRegressor(
        objective="poisson",
        metric="mae",
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
        n_jobs=-1,
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric="mae",
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
        categorical_feature=["categoria", "espacio_zona"],
    )
    
    # Evaluación
    for name, X_split, y_split in [("Train", X_train, y_train), ("Val", X_val, y_val), ("Test", X_test, y_test)]:
        preds = model.predict(X_split)
        mae = mean_absolute_error(y_split, preds)
        rmse = np.sqrt(mean_squared_error(y_split, preds))
        print(f"{name} - MAE: {mae:.4f}, RMSE: {rmse:.4f}")
    
    # Feature importance
    importance = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    print("\nFeature Importance:")
    print(importance.to_string(index=False))
    
    return model


def save_model(model: lgb.LGBMRegressor, feature_names: list):
    """Guarda modelo y metadatos"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODEL_DIR / f"demand_model_{timestamp}.pkl"
    meta_path = MODEL_DIR / f"demand_model_{timestamp}_meta.json"
    
    joblib.dump(model, model_path)
    
    metadata = {
        "model_type": "LightGBMRegressor",
        "objective": "poisson",
        "target": TARGET_COL,
        "features": feature_names,
        "categorical_features": ["categoria", "espacio_zona"],
        "trained_at": timestamp,
        "n_features": len(feature_names),
    }
    
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Symlink al modelo más reciente
    latest_model = MODEL_DIR / "demand_model_latest.pkl"
    latest_meta = MODEL_DIR / "demand_model_latest_meta.json"
    if latest_model.exists():
        latest_model.unlink()
    if latest_meta.exists():
        latest_meta.unlink()
    latest_model.symlink_to(model_path.name)
    latest_meta.symlink_to(meta_path.name)
    
    print(f"\nModelo guardado: {model_path}")
    print(f"Metadatos: {meta_path}")
    print(f"Enlaces latest creados")


async def main():
    print("=== Entrenamiento Modelo de Demanda ===\n")
    
    # 1. Cargar datos
    df = await load_training_data()
    
    # 2. Crear target
    df = create_target(df)
    
    # 3. Preparar features
    X, y = prepare_features(df)
    print(f"\nFeatures shape: {X.shape}")
    print(f"Target stats: mean={y.mean():.2f}, std={y.std():.2f}, max={y.max()}")
    
    # 4. Entrenar
    model = train_model(X, y)
    
    # 5. Guardar
    feature_names = X.columns.tolist()
    save_model(model, feature_names)
    
    print("\n=== Entrenamiento completado ===")


if __name__ == "__main__":
    asyncio.run(main())
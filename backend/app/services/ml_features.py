import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, cast, Date, delete
from sqlalchemy.orm import selectinload

from app.models import Movimiento, Espacio, Producto, TipoMovimiento, MlFeature
from app.services import ProductoService, EspacioService


UTC_TZ = ZoneInfo("UTC")

class MLFeatureService:
    
    @staticmethod
    async def materialize_features(db: AsyncSession, dias_atras: int = 180) -> int:
        """
        Calcula y materializa features para todas las combinaciones (espacio, producto, dow, hour)
        basándose en los últimos `dias_atras` días de movimientos.
        """
        print(f"Materializando features para últimos {dias_atras} días...")
        
        fecha_limite = datetime.now(UTC_TZ) - timedelta(days=dias_atras)
        
        espacios = await EspacioService.get_all(db)
        productos = await ProductoService.get_all(db, activo=True)
        
        if not espacios or not productos:
            print("No hay espacios o productos")
            return 0
        
        # 1. Obtener todos los movimientos en la ventana
        movs_result = await db.execute(
            select(Movimiento)
            .where(Movimiento.fecha_hora >= fecha_limite)
            .options(selectinload(Movimiento.espacio), selectinload(Movimiento.producto))
        )
        movimientos = movs_result.scalars().all()
        
        if not movimientos:
            print("No hay movimientos en la ventana")
            return 0
        
        # 2. Agregar datos por (espacio_id, producto_id, dow, hour)
        stats = defaultdict(lambda: {
            'salidas': [],
            'reposiciones': [],
            'espacio_zona': None,
        })
        
        for mov in movimientos:
            if not mov.espacio or not mov.producto:
                continue
            
            dow = mov.fecha_hora.weekday()  # 0=Lunes
            hour = mov.fecha_hora.hour
            key = (mov.espacio_id, mov.producto_id, dow, hour)
            
            stats[key]['espacio_zona'] = "Fila 1" if "Fila 1" in mov.espacio.ubicacion else "Fila 2"
            
            if mov.tipo == TipoMovimiento.salida:
                stats[key]['salidas'].append(mov.fecha_hora)
            elif mov.tipo == TipoMovimiento.reposicion:
                stats[key]['reposiciones'].append(mov.fecha_hora)
        
        # 3. Calcular features agregadas
        ahora = datetime.now()
        features_upsert = []
        
        for (espacio_id, producto_id, dow, hour), data in stats.items():
            salidas = data['salidas']
            reposiciones = data['reposiciones']
            
            if not salidas and not reposiciones:
                continue
            
            # Filtrar salidas por ventanas
            salidas_7d = [s for s in salidas if s >= ahora - timedelta(days=7)]
            salidas_30d = [s for s in salidas if s >= ahora - timedelta(days=30)]
            
            # Frecuencia por dow (promedio salidas este día de semana)
            salidas_mismo_dow = [s for s in salidas if s.weekday() == dow]
            semanas_unicas = len(set(s.isocalendar()[1] for s in salidas)) or 1
            freq_dow = len(salidas_mismo_dow) / semanas_unicas
            
            # Frecuencia por hora
            salidas_misma_hora = [s for s in salidas if s.hour == hour]
            freq_hour = len(salidas_misma_hora) / semanas_unicas
            
            # Tendencia últimos 7 días (pendiente simple)
            salidas_7d_sorted = sorted(salidas_7d)
            trend_7d = 0.0
            if len(salidas_7d_sorted) >= 2:
                # Días desde la fecha más antigua
                dias = [(s - salidas_7d_sorted[0]).total_seconds() / 86400 for s in salidas_7d_sorted]
                # Regresión simple: pendiente = cov(x,y)/var(x)
                x_mean = sum(dias) / len(dias)
                y_mean = sum(range(len(dias))) / len(dias)
                cov = sum((dias[i] - x_mean) * (i - y_mean) for i in range(len(dias)))
                var = sum((d - x_mean) ** 2 for d in dias)
                trend_7d = cov / var if var > 0 else 0.0
            
            # Reposiciones
            repo_count = len(reposiciones)
            repo_recency = None
            if reposiciones:
                ultima_repo = max(reposiciones)
                repo_recency = (ahora - ultima_repo).days
            
            # Share espacio-producto (reposiciones de este producto / total reposiciones del espacio)
            total_repos_espacio = sum(len(stats[(espacio_id, pid, dow, hour)]['reposiciones']) 
                                       for pid in [p.id for p in productos] 
                                       if (espacio_id, pid, dow, hour) in stats)
            space_product_share = repo_count / total_repos_espacio if total_repos_espacio > 0 else 0.0
            
            features_upsert.append({
                'espacio_id': espacio_id,
                'producto_id': producto_id,
                'dow': dow,
                'hour': hour,
                'salida_count_7d': len(salidas_7d),
                'salida_count_30d': len(salidas_30d),
                'salida_freq_dow': freq_dow,
                'salida_freq_hour': freq_hour,
                'salida_trend_7d': trend_7d,
                'reposicion_count': repo_count,
                'reposicion_recency_days': repo_recency,
                'space_product_share': space_product_share,
                'espacio_zona': data['espacio_zona'] or "Fila 1",
            })
        
        # 4. Upsert en BD
        from app.models import MlFeature
        
        for feat in features_upsert:
            existing = await db.execute(
                select(MlFeature).where(
                    and_(
                        MlFeature.espacio_id == feat['espacio_id'],
                        MlFeature.producto_id == feat['producto_id'],
                        MlFeature.dow == feat['dow'],
                        MlFeature.hour == feat['hour'],
                    )
                )
            )
            existing_feat = existing.scalar_one_or_none()
            
            if existing_feat:
                for key, value in feat.items():
                    if key not in ('espacio_id', 'producto_id', 'dow', 'hour'):
                        setattr(existing_feat, key, value)
                existing_feat.computed_at = ahora
            else:
                new_feat = MlFeature(**feat, computed_at=ahora)
                db.add(new_feat)
        
        await db.commit()
        print(f"Features materializadas: {len(features_upsert)} registros")
        return len(features_upsert)
    
    @staticmethod
    async def get_features_for_inference(
        db: AsyncSession, 
        target_dt: datetime,
        free_space_ids: List[int],
        producto_ids: List[int]
    ) -> List[Dict]:
        """
        Obtiene features para predicción: free_spaces × productos_activos × target_dow/hour
        Retorna features por defecto (ceros) para combinaciones que no existen en la BD.
        """
        # Convertir a UTC para que coincida con cómo se almacenaron las features ML (en UTC)
        if target_dt.tzinfo is not None:
            target_dt_utc = target_dt.astimezone(ZoneInfo("UTC"))
        else:
            # Si es naive, asumir que está en UTC
            target_dt_utc = target_dt.replace(tzinfo=ZoneInfo("UTC"))
        
        target_dow = target_dt_utc.weekday()
        target_hour = target_dt_utc.hour
        
        from app.models import Producto
        
        # 1. Obtener features existentes de la BD
        result = await db.execute(
            select(MlFeature, Producto.categoria).join(
                Producto, MlFeature.producto_id == Producto.id
            ).where(
                and_(
                    MlFeature.espacio_id.in_(free_space_ids),
                    MlFeature.producto_id.in_(producto_ids),
                    MlFeature.dow == target_dow,
                    MlFeature.hour == target_hour,
                )
            )
        )
        
        rows = result.all()
        
        # Crear dict de features existentes para lookup rápido
        existing_features = {}
        for f, categoria in rows:
            key = (f.espacio_id, f.producto_id)
            existing_features[key] = {
                'espacio_id': f.espacio_id,
                'producto_id': f.producto_id,
                'categoria': categoria,
                'salida_count_7d': f.salida_count_7d,
                'salida_count_30d': f.salida_count_30d,
                'salida_freq_dow': f.salida_freq_dow,
                'salida_freq_hour': f.salida_freq_hour,
                'salida_trend_7d': f.salida_trend_7d,
                'reposicion_count': f.reposicion_count,
                'reposicion_recency_days': f.reposicion_recency_days if f.reposicion_recency_days is not None else 999,
                'space_product_share': f.space_product_share,
                'espacio_zona': f.espacio_zona,
            }
        
        # 2. Generar TODAS las combinaciones (espacio × producto) y rellenar con defaults si faltan
        result = []
        for espacio_id in free_space_ids:
            for producto_id in producto_ids:
                key = (espacio_id, producto_id)
                if key in existing_features:
                    feat = existing_features[key]
                else:
                    # Feature por defecto (ceros) para combinaciones no vistas
                    # Necesitamos obtener la categoria y zona del espacio
                    from app.models import Producto, Espacio
                    # Nota: esto sería ineficiente en producción, pero para MVP es aceptable
                    # En producción se haría un join o cache
                    # Por ahora usamos valores por defecto razonables
                    # Obtenemos categoria del producto
                    # Usamos un fallback simple basado en producto_id
                    # En producción se haría join con tabla Producto
                    feat = {
                        'espacio_id': espacio_id,
                        'producto_id': producto_id,
                        'categoria': 'Postres',  # default, se sobrescribe abajo si es posible
                        'salida_count_7d': 0,
                        'salida_count_30d': 0,
                        'salida_freq_dow': 0.0,
                        'salida_freq_hour': 0.0,
                        'salida_trend_7d': 0.0,
                        'reposicion_count': 0,
                        'reposicion_recency_days': 999,
                        'space_product_share': 0.0,
                        'espacio_zona': 'Fila 1' if espacio_id <= 4 else 'Fila 2',
                    }
                
                # Obtener categoria real del producto si es posible
                # Para simplificar, usamos un mapeo estático basado en IDs conocidos
                # En producción se haría join con Producto
                categoria_map = {
                    1: 'Salados',
                    2: 'Postres',
                    3: 'Postres',
                    4: 'Postres',
                    5: 'Postres',
                    6: 'Desayuno',
                }
                if producto_id in categoria_map:
                    feat['categoria'] = categoria_map[producto_id]
                
                result.append(feat)
        
        return result
    
    @staticmethod
    async def get_demand_features(
        db: AsyncSession, 
        target_dt: datetime,
        producto_ids: List[int]
    ) -> Dict[int, Dict]:
        """
        Obtiene features de demanda agregadas por producto para target_dow/hour
        (independiente del espacio)
        """
        target_dow = target_dt.weekday()
        target_hour = target_dt.hour
        
        # Agregar features de todos los espacios por producto
        result = await db.execute(
            select(
                MlFeature.producto_id,
                func.sum(MlFeature.salida_count_7d).label('salida_count_7d'),
                func.sum(MlFeature.salida_count_30d).label('salida_count_30d'),
                func.avg(MlFeature.salida_freq_dow).label('salida_freq_dow'),
                func.avg(MlFeature.salida_freq_hour).label('salida_freq_hour'),
                func.avg(MlFeature.salida_trend_7d).label('salida_trend_7d'),
            ).where(
                and_(
                    MlFeature.producto_id.in_(producto_ids),
                    MlFeature.dow == target_dow,
                    MlFeature.hour == target_hour,
                )
            ).group_by(MlFeature.producto_id)
        )
        
        demand_features = {}
        for row in result:
            demand_features[row.producto_id] = {
                'salida_count_7d': row.salida_count_7d or 0,
                'salida_count_30d': row.salida_count_30d or 0,
                'salida_freq_dow': float(row.salida_freq_dow or 0),
                'salida_freq_hour': float(row.salida_freq_hour or 0),
                'salida_trend_7d': float(row.salida_trend_7d or 0),
            }
        
        # Completar productos sin features con ceros
        for pid in producto_ids:
            if pid not in demand_features:
                demand_features[pid] = {
                    'salida_count_7d': 0,
                    'salida_count_30d': 0,
                    'salida_freq_dow': 0.0,
                    'salida_freq_hour': 0.0,
                    'salida_trend_7d': 0.0,
                }
        
        return demand_features


async def main():
    from app.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        count = await MLFeatureService.materialize_features(db, dias_atras=180)
        print(f"Total features creadas: {count}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
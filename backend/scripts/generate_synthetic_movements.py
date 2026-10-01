import asyncio
import random
import sys
import os
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple
from zoneinfo import ZoneInfo

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete

from app.config import settings
from app.database import Base
from app.models import Producto, Espacio, Movimiento, EstadoEspacio, TipoMovimiento
from app.services import MovimientoService, ProductoService, EspacioService
from app.schemas import MovimientoCreate


# Zona horaria de Lima (Perú)
LIMA_TZ = ZoneInfo("America/Lima")
UTC_TZ = ZoneInfo("UTC")

FERIADOS_PERU_2024 = {
    date(2024, 1, 1), date(2024, 3, 28), date(2024, 3, 29),
    date(2024, 5, 1), date(2024, 6, 29), date(2024, 7, 28),
    date(2024, 7, 29), date(2024, 8, 30), date(2024, 10, 8),
    date(2024, 11, 1), date(2024, 12, 8), date(2024, 12, 25),
}
FERIADOS_PERU_2025 = {
    date(2025, 1, 1), date(2025, 4, 17), date(2025, 4, 18),
    date(2025, 5, 1), date(2025, 6, 29), date(2025, 7, 28),
    date(2025, 7, 29), date(2025, 8, 30), date(2025, 10, 8),
    date(2025, 11, 1), date(2025, 12, 8), date(2025, 12, 25),
}
FERIADOS_PERU = FERIADOS_PERU_2024 | FERIADOS_PERU_2025


AFINIDAD_FILA_CATEGORIA = {
    "Fila 1": {"Desayuno": 0.50, "Postres": 0.35, "Salados": 0.15},
    "Fila 2": {"Postres": 0.60, "Desayuno": 0.25, "Salados": 0.15},
}

PATRONES_HORARIOS = {
    "laborable": {
        (7, 10): {"Desayuno": 1.5, "Postres": 0.8, "Salados": 0.5},
        (10, 13): {"Desayuno": 0.3, "Postres": 1.2, "Salados": 1.0},
        (13, 16): {"Desayuno": 0.2, "Postres": 1.0, "Salados": 0.8},
        (16, 20): {"Desayuno": 0.5, "Postres": 1.3, "Salados": 1.0},
    },
    "fin_semana": {
        (7, 10): {"Desayuno": 1.2, "Postres": 0.6, "Salados": 0.4},
        (10, 13): {"Desayuno": 0.8, "Postres": 1.4, "Salados": 0.6},
        (13, 16): {"Desayuno": 0.4, "Postres": 1.2, "Salados": 0.7},
        (16, 20): {"Desayuno": 0.3, "Postres": 1.0, "Salados": 0.5},
    },
    "feriado": {
        (7, 10): {"Desayuno": 1.0, "Postres": 0.5, "Salados": 0.3},
        (10, 13): {"Desayuno": 0.6, "Postres": 1.5, "Salados": 0.5},
        (13, 16): {"Desayuno": 0.3, "Postres": 1.3, "Salados": 0.6},
        (16, 20): {"Desayuno": 0.2, "Postres": 0.8, "Salados": 0.4},
    },
}

FACTOR_VARIACION_DIARIA = 0.3
PICO_PROBABILIDAD = 0.15
PICO_FACTOR = 2.0
VALLE_PROBABILIDAD = 0.10
VALLE_FACTOR = 0.4

REPOSICION_LEAD_TIME_HORAS = (1, 4)
HORARIO_INICIO = 7
HORARIO_FIN = 20
DIAS_HISTORIA = 180
MOVIMIENTOS_BASE_DIA = 40


def es_feriado(fecha: date) -> bool:
    return fecha in FERIADOS_PERU


def es_fin_semana(fecha: date) -> bool:
    return fecha.weekday() >= 5


def obtener_tipo_dia(fecha: date) -> str:
    if es_feriado(fecha):
        return "feriado"
    elif es_fin_semana(fecha):
        return "fin_semana"
    return "laborable"


def obtener_factor_dia(fecha: date) -> float:
    r = random.random()
    if r < PICO_PROBABILIDAD:
        return PICO_FACTOR
    elif r < PICO_PROBABILIDAD + VALLE_PROBABILIDAD:
        return VALLE_FACTOR
    return 1.0 + random.uniform(-FACTOR_VARIACION_DIARIA, FACTOR_VARIACION_DIARIA)


def obtener_patron_hora(tipo_dia: str, hora: int) -> Dict[str, float]:
    patrones = PATRONES_HORARIOS[tipo_dia]
    for (h_inicio, h_fin), pesos in patrones.items():
        if h_inicio <= hora < h_fin:
            return pesos
    return {c: 0.1 for c in ["Desayuno", "Postres", "Salados"]}


def obtener_afinidad_fila(fila: str) -> Dict[str, float]:
    return AFINIDAD_FILA_CATEGORIA.get(fila, {"Desayuno": 0.33, "Postres": 0.34, "Salados": 0.33})


def extraer_fila(ubicacion: str) -> str:
    if "Fila 1" in ubicacion:
        return "Fila 1"
    elif "Fila 2" in ubicacion:
        return "Fila 2"
    return "Fila 1"


def calcular_peso_producto(
    producto: Producto,
    fila: str,
    tipo_dia: str,
    hora: int,
    factor_dia: float
) -> float:
    patron_hora = obtener_patron_hora(tipo_dia, hora)
    afinidad_fila = obtener_afinidad_fila(fila)
    peso = (
        patron_hora.get(producto.categoria, 0.1) *
        afinidad_fila.get(producto.categoria, 0.33) *
        factor_dia
    )
    return max(peso, 0.01)


def seleccionar_producto_ponderado(
    productos: List[Producto],
    fila: str,
    tipo_dia: str,
    hora: int,
    factor_dia: float
) -> Producto:
    pesos = [
        calcular_peso_producto(p, fila, tipo_dia, hora, factor_dia)
        for p in productos
    ]
    total = sum(pesos)
    if total == 0:
        return random.choice(productos)
    pesos_norm = [w / total for w in pesos]
    return random.choices(productos, weights=pesos_norm, k=1)[0]


class SpaceState:
    def __init__(self, espacio: Espacio):
        self.espacio = espacio
        self.estado = EstadoEspacio.libre
        self.producto_actual_id = None
        self.fila = extraer_fila(espacio.ubicacion)
    
    def ocupar(self, producto_id: int):
        self.estado = EstadoEspacio.ocupado
        self.producto_actual_id = producto_id
    
    def liberar(self):
        self.estado = EstadoEspacio.libre
        self.producto_actual_id = None
    
    @property
    def esta_libre(self) -> bool:
        return self.estado == EstadoEspacio.libre
    
    @property
    def esta_ocupado(self) -> bool:
        return self.estado == EstadoEspacio.ocupado


async def generate_synthetic_movements(db: AsyncSession):
    print("Cargando productos y espacios existentes...")
    
    productos = await ProductoService.get_all(db, activo=True)
    espacios_db = await EspacioService.get_all(db)
    
    if not productos or not espacios_db:
        print("ERROR: No hay productos o espacios. Ejecuta 'make seed' primero.")
        return
    
    print(f"Productos: {len(productos)} | Espacios: {len(espacios_db)}")
    
    space_states = {e.id: SpaceState(e) for e in espacios_db}
    salidas_pendientes: List[Tuple[datetime, int, int]] = []  # (fecha_utc, espacio_id, producto_id)
    
    # Usar zona horaria de Lima para la generación
    ahora_lima = datetime.now(LIMA_TZ)
    fecha_inicio = ahora_lima - timedelta(days=DIAS_HISTORIA)
    fecha_fin = datetime.now(LIMA_TZ)
    
    total_reposiciones = 0
    total_salidas = 0
    
    print(f"Generando movimientos desde {fecha_inicio.date()} hasta {fecha_fin.date()} (zona horaria: America/Lima)...")
    
    dia_actual = fecha_inicio
    while dia_actual <= fecha_fin:
        fecha_date = dia_actual.date()
        tipo_dia = obtener_tipo_dia(fecha_date)
        factor_dia = obtener_factor_dia(fecha_date)
        movimientos_objetivo = int(MOVIMIENTOS_BASE_DIA * factor_dia)
        movimientos_objetivo = max(movimientos_objetivo, 5)
        
        reposiciones_hoy = 0
        salidas_hoy = 0
        
        for hora in range(HORARIO_INICIO, HORARIO_FIN):
            # Procesar salidas pendientes para ESTA hora (en zona horaria de Lima)
            fecha_hora_actual_lima = dia_actual.replace(hour=hora, minute=0, second=0, microsecond=0)
            fecha_hora_actual_utc = fecha_hora_actual_lima.astimezone(UTC_TZ)
            
            i = 0
            while i < len(salidas_pendientes):
                salida_fecha_utc, espacio_id, producto_id = salidas_pendientes[i]
                if salida_fecha_utc <= fecha_hora_actual_utc:
                    if space_states[espacio_id].esta_ocupado:
                        space_states[espacio_id].liberar()
                        await MovimientoService.create(db, MovimientoCreate(
                            espacio_id=espacio_id,
                            producto_id=producto_id,
                            tipo=TipoMovimiento.salida,
                            fecha_hora=salida_fecha_utc
                        ))
                        salidas_hoy += 1
                    salidas_pendientes.pop(i)
                else:
                    i += 1
            
            # Intentar reposiciones en esta hora
            patron = obtener_patron_hora(tipo_dia, hora)
            intensidad_hora = sum(patron.values())
            if intensidad_hora < 0.5:
                continue
            
            n_eventos_hora = max(1, int(intensidad_hora * factor_dia * 2))
            
            for _ in range(n_eventos_hora):
                if reposiciones_hoy + salidas_hoy >= movimientos_objetivo:
                    break
                
                espacios_libres = [s for s in space_states.values() if s.esta_libre]
                if not espacios_libres:
                    break
                
                espacio_state = random.choice(espacios_libres)
                fila = espacio_state.fila
                
                producto = seleccionar_producto_ponderado(
                    productos, fila, tipo_dia, hora, factor_dia
                )
                
                fecha_reposicion_lima = dia_actual.replace(
                    hour=hora,
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                fecha_reposicion_utc = fecha_reposicion_lima.astimezone(UTC_TZ)
                
                # REPOSICIÓN
                espacio_state.ocupar(producto.id)
                
                await MovimientoService.create(db, MovimientoCreate(
                    espacio_id=espacio_state.espacio.id,
                    producto_id=producto.id,
                    tipo=TipoMovimiento.reposicion,
                    fecha_hora=fecha_reposicion_utc
                ))
                reposiciones_hoy += 1
                
                # Programar SALIDA correspondiente - siempre, incluso si pasa de horario
                lead_time = random.randint(*REPOSICION_LEAD_TIME_HORAS)
                fecha_salida_lima = fecha_reposicion_lima + timedelta(hours=lead_time)
                fecha_salida_utc = fecha_salida_lima.astimezone(UTC_TZ)
                
                salidas_pendientes.append((fecha_salida_utc, espacio_state.espacio.id, producto.id))
        
        # Fin del día: procesar TODAS las salidas pendientes restantes
        for salida_fecha, espacio_id, producto_id in salidas_pendientes:
            if space_states[espacio_id].esta_ocupado:
                space_states[espacio_id].liberar()
                await MovimientoService.create(db, MovimientoCreate(
                    espacio_id=espacio_id,
                    producto_id=producto_id,
                    tipo=TipoMovimiento.salida,
                    fecha_hora=salida_fecha
                ))
                salidas_hoy += 1
        
        salidas_pendientes.clear()
        
        total_reposiciones += reposiciones_hoy
        total_salidas += salidas_hoy
        
        if dia_actual.day == 1 or dia_actual == fecha_inicio:
            print(f"  {dia_actual.date()} ({tipo_dia}): {reposiciones_hoy} reposiciones, {salidas_hoy} salidas (factor: {factor_dia:.2f})")
        
        dia_actual += timedelta(days=1)
    
    print(f"\nTotal movimientos creados: {total_reposiciones + total_salidas}")
    print(f"  Reposiciones: {total_reposiciones}")
    print(f"  Salidas: {total_salidas}")


async def main(force: bool = False):
    engine = create_async_engine(settings.database_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Movimiento))
        if existing.scalars().first() and not force:
            # No interactivo (CI/deploy): exigir --force en vez de colgarse en input()
            if os.getenv("CI") == "true" or os.getenv("FORCE") == "true" or not sys.stdin.isatty():
                print("Ya existen movimientos. Usa --force para agregar más en modo no interactivo.")
                await engine.dispose()
                return
            print("Ya existen movimientos en la base de datos.")
            respuesta = input("¿Desea continuar y agregar más? (s/N): ")
            if respuesta.lower() != 's':
                print("Cancelado.")
                await engine.dispose()
                return

        await generate_synthetic_movements(db)

    await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Genera movimientos sintéticos")
    parser.add_argument("--force", action="store_true", help="No pedir confirmación aunque existan movimientos")
    args = parser.parse_args()
    force = args.force or os.getenv("FORCE") == "true"
    asyncio.run(main(force=force))
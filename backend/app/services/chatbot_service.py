import json
import re
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
import dateparser
from zoneinfo import ZoneInfo

from app.config import settings
from app.services.demand_predictor import DemandPredictor
from app.services.space_product_ranker import SpaceProductRanker
from app.services.disposition_optimizer import GreedyDispositionOptimizer, build_space_info_from_db
from app.services.ml_features import MLFeatureService
from app.services import (
    ProductoService,
    EspacioService,
    MovimientoService,
    DashboardService,
)
from app.models import EstadoEspacio
from sqlalchemy.ext.asyncio import AsyncSession


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.txt"


# Zona horaria de Lima (Perú)
LIMA_TZ = ZoneInfo("America/Lima")

# Override para testing via env var TEST_NOW_OVERRIDE (ISO format: YYYY-MM-DDTHH:MM:SS)
def _get_now() -> datetime:
    """Retorna la fecha/hora actual en zona horaria de Lima, considerando override para testing via env var."""
    override_str = os.getenv("TEST_NOW_OVERRIDE")
    if override_str:
        try:
            dt = datetime.fromisoformat(override_str)
            if dt.tzinfo is None:
                # Si no tiene zona horaria, asumir UTC (estándar para testing)
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(LIMA_TZ)
        except ValueError:
            pass
    return datetime.now(LIMA_TZ)


def cargar_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as archivo:
        return archivo.read()


PATRONES_TEMPORALES = [
    (r"\bmañana\b", 1),
    (r"\bpasado mañana\b", 2),
    (r"\blunes\b", 0),
    (r"\bmartes\b", 1),
    (r"\bmi[eé]rcoles\b", 2),
    (r"\bjueves\b", 3),
    (r"\bviernes\b", 4),
    (r"\bs[áa]bado\b", 5),
    (r"\bdomingo\b", 6),
    (r"\bhoy\b", 0),
    (r"\bahora\b", 0),
    (r"\bahora mismo\b", 0),
    (r"\ben este momento\b", 0),
    (r"\bright now\b", 0),
]


def _parse_with_dateparser(mensaje: str, ahora: datetime) -> Optional[datetime]:
    """
    Intenta parsear la fecha/hora usando dateparser.
    Returns None si no puede parsear.
    """
    # Pre-procesar: normalizar horas sin minutos (ej: "a las 9" -> "a las 9:00")
    def _add_minutes(match):
        prefix = match.group(1)
        hour = match.group(2)
        return f'{prefix}{hour}:00'
    
    # Normalizar "a las H" / "para las H" -> "a las H:00" / "para las H:00"
    # solo si no tiene minutos ni am/pm después
    mensaje_normalizado = re.sub(
        r'(?:a|para)\s+las\s+(\d{1,2})(?![:\d]|(?:\s*(?:am|pm)))',
        lambda m: f'{m.group(0)}:00',
        mensaje,
        flags=re.IGNORECASE
    )
    
    try:
        parsed = dateparser.parse(
            mensaje_normalizado,
            languages=['es'],
            settings={
                'RELATIVE_BASE': ahora,
                'PREFER_DATES_FROM': 'future',
                'TIMEZONE': 'America/Lima',
                'RETURN_AS_TIMEZONE_AWARE': False,
            }
        )
        if not parsed:
            return None

        # dateparser con TIMEZONE devuelve hora pared de Lima naive:
        # adjuntar LIMA_TZ para que el downstream la convierta bien a UTC.
        # (Antes se asumía naive=UTC → desplazamiento de 5h en las sugerencias.)
        def _en_lima(dt):
            dt = dt.replace(second=0, microsecond=0)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=LIMA_TZ)
            return dt

        # Si dateparser no detectó hora (hour=0, minute=0, second=0),
        # puede ser que solo detectó fecha. Verificamos si hay hora explícita en el mensaje.
        if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
            # Verificar si hay hora explícita en el mensaje original
            has_explicit_time = bool(re.search(
                r"(?:a|para)\s+las\s+\d{1,2}(?::\d{2})?\s*(am|pm)?|"
                r"\b\d{1,2}:\d{2}\b|"
                r"\b\d{1,2}\s*(am|pm)\b|"
                r"\b\d{1,2}(am|pm)\b",
                mensaje,
                re.IGNORECASE
            ))
            if not has_explicit_time:
                # dateparser no detectó hora explícita, no confiar en la hora
                pass
            else:
                # Hora detectada por dateparser, confiar pero normalizar minutos a 0 si no se especificaron
                return _en_lima(parsed)
        else:
            # Hora detectada por dateparser, confiar pero normalizar minutos a 0 si no se especificaron minutos
            if parsed.minute != 0:
                # Verificar si el mensaje original especificaba minutos
                has_explicit_minutes = bool(re.search(
                    r"\d{1,2}:\d{2}",
                    mensaje
                ))
                if not has_explicit_minutes:
                    parsed = parsed.replace(minute=0)
            return _en_lima(parsed)
    except Exception:
        pass
    return None


def detectar_intencion_temporal(mensaje: str) -> Optional[datetime]:
    """
    Detecta si el mensaje pide sugerencias para un día/hora específico.
    Usa dateparser como parser principal con regex como fallback.
    """
    ahora = _get_now()
    
    # Manejo explícito de "ahora mismo", "ahora", "en este momento", "right now"
    mensaje_lower = mensaje.lower()
    if any(p in mensaje_lower for p in ["ahora mismo", "ahora ", "en este momento", "right now"]):
        # Para "ahora mismo" usar la hora actual exacta (con minutos)
        return ahora.replace(second=0, microsecond=0)
    
    # 1. Intentar con dateparser (parser robusto para lenguaje natural)
    parsed = _parse_with_dateparser(mensaje, ahora)
    if parsed:
        return parsed
    
    # Fallback: regex-based parsing (código original como fallback)
    mensaje_lower = mensaje.lower()
    ahora_dt = _get_now()
    
    # 1. Buscar día del mes explícito (ej: "21 de septiembre", "21/09", "21-09", "día 21")
    dia_mes_match = re.search(
        r"\b(?:d[ií]a\s+)?(\d{1,2})\s*(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b",
        mensaje_lower
    )
    if not dia_mes_match:
        # Formatos numéricos: 21/09, 21-09, 21.09
        dia_mes_match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})\b", mensaje)
    
    # 2. Buscar hora explícita (ej: "a las 8", "8:00", "8 am", "6pm", "18:00")
    hora = 8  # Default 8am
    
    # Patrón 1: "a las HH:MM" o "a las HH" o "a las HHam/pm" o "para las HH:MM"
    hora_match = re.search(
        r"(?:a|para)\s+las\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        mensaje,
        re.IGNORECASE
    )
    
    if hora_match:
        hora = int(hora_match.group(1))
        ampm = hora_match.group(3)
        if ampm and ampm.lower() == 'pm' and hora != 12:
            hora += 12
        elif ampm and ampm.lower() == 'am' and hora == 12:
            hora = 0
        if hora < 0 or hora > 23:
            hora = 8
    else:
        # Patrón 2: HH:MM am/pm (formato 12h con minutos)
        hora_match = re.search(
            r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b",
            mensaje,
            re.IGNORECASE
        )
        if hora_match:
            hora = int(hora_match.group(1))
            ampm = hora_match.group(3).lower()
            if ampm == 'pm' and hora != 12:
                hora += 12
            elif ampm == 'am' and hora == 12:
                hora = 0
            if hora < 0 or hora > 23:
                hora = 8
        else:
            # Patrón 3: HH:MM (formato 24h)
            hora_match = re.search(
                r"\b(\d{1,2}):(\d{2})\b",
                mensaje
            )
            if hora_match:
                hora = int(hora_match.group(1))
                if hora < 0 or hora > 23:
                    hora = 8
            else:
                # Patrón 4: H am/pm (formato 12h con espacio)
                hora_match = re.search(
                    r"\b(\d{1,2})\s*(am|pm)\b",
                    mensaje,
                    re.IGNORECASE
                )
                if hora_match:
                    hora = int(hora_match.group(1))
                    ampm = hora_match.group(2).lower()
                    if ampm == 'pm' and hora != 12:
                        hora += 12
                    elif ampm == 'am' and hora == 12:
                        hora = 0
                    if hora < 0 or hora > 23:
                        hora = 8
                else:
                    # Patrón 5: HHpm/ HHam (sin espacio)
                    hora_match = re.search(
                        r"\b(\d{1,2})(am|pm)\b",
                        mensaje,
                        re.IGNORECASE
                    )
                    if hora_match:
                        hora = int(hora_match.group(1))
                        ampm = hora_match.group(2).lower()
                        if ampm == 'pm' and hora != 12:
                            hora += 12
                        elif ampm == 'am' and hora == 12:
                            hora = 0
                        if hora < 0 or hora > 23:
                            hora = 8
                        else:
                            # Si no hay hora explícita pero hay "mañana/tarde/noche", inferir
                            mensaje_lower = mensaje.lower()
                            if re.search(r"\bmañana\b", mensaje.lower()) and not re.search(r"\btarde\b|\bnoche\b", mensaje.lower()):
                                hora = 8  # Mañana = 8am
                            elif re.search(r"\btarde\b", mensaje.lower()):
                                hora = 15  # Tarde = 3pm
                            elif re.search(r"\bnoche\b", mensaje.lower()):
                                hora = 20  # Noche = 8pm
                            else:
                                hora = 8  # Default 8am
    
    # 3. Determinar fecha objetivo
    target_date = None
    encontrado = False
    
    # Caso A: Día de mes explícito encontrado
    if dia_mes_match:
        try:
            if len(dia_mes_match.groups()) == 2:
                # Formato dd/mm
                dia = int(dia_mes_match.group(1))
                mes = int(dia_mes_match.group(2))
            else:
                # Formato "21 de septiembre" - extraer mes del texto
                dia = int(dia_mes_match.group(1))
                # Buscar mes en el texto
                meses = {
                    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
                    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
                    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                }
                mes = 9  # default
                for nombre_mes, num_mes in meses.items():
                    if nombre_mes in mensaje.lower():
                        mes = num_mes
                        break
                
                # Determinar año (este o siguiente si ya pasó)
                año = _get_now().year
                candidate = datetime(año, mes, dia, hour=hora, tzinfo=LIMA_TZ)
                if candidate < _get_now():
                    candidate = datetime(año + 1, mes, dia, hour=hora, tzinfo=LIMA_TZ)
                target_date = candidate
                encontrado = True
        except ValueError:
            pass
    
    # Caso B: día relativo ("mañana", "pasado mañana") o día de semana (lunes, etc.)
    # OJO: "mañana"/"pasado mañana" son relativos (+1/+2 días), NO días de semana.
    # Se chequean antes que PATRONES_TEMPORALES porque \bmañana\b matchea
    # dentro de "pasado mañana" y "esta mañana".
    if not encontrado:
        dias_offset = None
        if re.search(r"\bpasado\s+mañana\b", mensaje_lower):
            dias_offset = 2
        elif re.search(r"\besta\s+mañana\b", mensaje_lower):
            dias_offset = 0
        elif re.search(r"\bmañana\b", mensaje_lower) and not re.search(
            r"\bpor\s+la\s+mañana\b|\bde\s+mañana\b|\ben\s+la\s+mañana\b|\blas\s+mañanas\b",
            mensaje_lower,
        ):
            dias_offset = 1

        if dias_offset is not None:
            target_date = (_get_now() + timedelta(days=dias_offset)).replace(
                hour=hora, minute=0, second=0, microsecond=0
            )
            encontrado = True

    if not encontrado:
        for patron, dow in PATRONES_TEMPORALES:
            if patron in (r"\bmañana\b", r"\bpasado mañana\b"):
                continue  # ya manejados arriba como relativos
            if re.search(patron, mensaje.lower()):
                if patron == r"\bhoy\b":
                    dias_offset = 0
                else:
                    dias_offset = (dow - _get_now().weekday()) % 7
                    if dias_offset == 0 and patron != r"\bhoy\b":
                        dias_offset = 7  # Próxima semana
                encontrado = True
                break
        
        if not encontrado:
            for patron, dow in PATRONES_TEMPORALES:
                if re.search(rf"(?:para\s+)?el\s+{patron}", mensaje.lower()):
                    dias_offset = (dow - _get_now().weekday()) % 7
                    if dias_offset == 0:
                        dias_offset = 7
                    encontrado = True
                    break
        
        if encontrado:
            target_date = (_get_now() + timedelta(days=dias_offset)).replace(hour=hora, minute=0, second=0, microsecond=0)
    
    if not encontrado:
        # Si solo se especificó hora sin fecha, asumir "hoy" si la hora no pasó, sino "mañana"
        # Buscar si hay alguna referencia temporal en el mensaje
        hay_hora = False
        for pattern in [
            r"a\s+las\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
            r"\b(\d{1,2}):(\d{2})\b",
            r"\b(\d{1,2})\s*(am|pm)\b",
            r"\b(\d{1,2})(am|pm)\b",
        ]:
            if re.search(pattern, mensaje, re.IGNORECASE):
                hay_hora = True
                break
        
        if hay_hora:
            # Si hay hora pero no fecha, usar hoy si la hora no pasó, sino mañana
            target_date = _get_now().replace(hour=hora, minute=0, second=0, microsecond=0)
            if target_date < _get_now():
                target_date += timedelta(days=1)
            encontrado = True
    
    if target_date is None:
        target_date = (_get_now() + timedelta(days=dias_offset)).replace(hour=hora, minute=0, second=0, microsecond=0)
    
    return target_date
def formatear_sugerencias_ml(sugerencias: Dict[str, Any], target_dt: Optional[datetime] = None) -> str:
    """Convierte sugerencias ML a texto natural para el contexto de DeepSeek."""
    if not sugerencias or not sugerencias.get("recommendations"):
        return ""
    
    recs = sugerencias["recommendations"]
    disposition = sugerencias.get("disposition", {})
    metadata = sugerencias.get("metadata", {})
    max_score = max((r.get("score", 0) for r in recs), default=0)
    
    lineas = [
        "SUGERENCIAS ML DE REPOSICIÓN (basadas en patrones históricos):"
    ]
    
    # Incluir fecha/hora objetivo si está disponible
    if target_dt:
        lineas.append(f"Para {target_dt.isoformat()}:")
    
    for rec in recs:
        space = rec["espacio_codigo"]
        product = rec["producto_nombre"]
        score = rec["score"]
        reason = rec.get("reason", "")
        demand_score = rec.get("demand_score", 0)
        ranker_score = rec.get("ranker_score", 0)

        # Confianza relativa al mejor score (la escala absoluta de
        # demand*ranker es ~1e-4..1e-2, los umbrales absolutos no aplican).
        conf = "alta" if score >= 0.8 * max_score else "media" if score >= 0.4 * max_score else "baja"
        lineas.append(f"  - {space}: {product} (confianza {conf}, demanda={demand_score:.2f}, afinidad={ranker_score:.2f}) - {reason}")
    
    if disposition:
        lineas.append("\nDISPOSICIÓN SUGERIDA:")
        for space, product in disposition.items():
            lineas.append(f"  {space} → {product}")

    occupied = sugerencias.get("occupied", {})
    if occupied:
        lineas.append("\nESPACIOS OCUPADOS (sin sugerencia, ya tienen producto):")
        for space, product in occupied.items():
            lineas.append(f"  {space} → {product}")
    
    lineas.append(f"\nMetadatos: {metadata.get('free_spaces_count', 0)} espacios libres, "
                   f"{metadata.get('productos_recommended', 0)} productos, "
                   f"máx {metadata.get('max_per_product', 4)}/producto")
    
    return "\n".join(lineas)


def serializar_productos(productos) -> list:
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "categoria": p.categoria,
            "imagen_url": p.imagen_url,
            "activo": p.activo,
        }
        for p in productos
    ]


def serializar_espacios(espacios) -> list:
    result = []
    for e in espacios:
        espacio_data = {
            "id": e.id,
            "codigo": e.codigo,
            "estado": e.estado.value if hasattr(e.estado, "value") else str(e.estado),
            "producto_actual_id": e.producto_actual_id,
        }
        if e.producto_actual:
            espacio_data["producto_actual"] = {
                "id": e.producto_actual.id,
                "nombre": e.producto_actual.nombre,
            }
        result.append(espacio_data)
    return result


def serializar_movimientos(movimientos) -> list:
    return [
        {
            "id": m.id,
            "espacio_id": m.espacio_id,
            "producto_id": m.producto_id,
            "tipo": m.tipo.value if hasattr(m.tipo, "value") else str(m.tipo),
            "fecha_hora": m.fecha_hora.isoformat() if m.fecha_hora else None,
        }
        for m in movimientos
    ]


async def process_message(message: str, db: AsyncSession) -> str:
    if not settings.deepseek_api_key:
        return (
            "LubenBot no está configurado. "
            "Agrega DEEPSEEK_API_KEY en .env para consultas inteligentes."
        )

    system_prompt = cargar_prompt()

    # Detectar intención temporal primero
    target_dt = detectar_intencion_temporal(message)
    es_consulta_temporal = target_dt is not None
    
    # Obtener sugerencias ML si hay intención temporal
    ml_context = ""
    if target_dt:
        ml_context = await obtener_sugerencias_ml_safe(target_dt, db)

    # Obtener datos necesarios según el tipo de consulta
    if es_consulta_temporal:
        # Para consultas temporales: contexto enfocado + ML suggestions prominentes
        productos = await ProductoService.get_all(db, activo=True)
        espacios = await EspacioService.get_all(db)
        resumen = await DashboardService.get_resumen(db)
        
        # Contexto enfocado: solo datos esenciales para reposición
        free_spaces = [e for e in await EspacioService.get_all(db) if e.estado == EstadoEspacio.libre]
        productos_activos = [p for p in await ProductoService.get_all(db, activo=True)]
        
        datos_enfocados = {
            "espacios_libres": len(free_spaces),
            "espacios_ocupados": resumen.espacios_ocupados,
            "productos_activos": len(productos_activos),
            "productos": [{"id": p.id, "nombre": p.nombre, "categoria": p.categoria} for p in productos_activos],
            "espacios_libres_detalle": [{"codigo": e.codigo, "ubicacion": e.ubicacion} for e in free_spaces],
        }
        
        # ML suggestions prominently featured in system prompt
        ml_section = f"\n\n{ml_context}\n" if ml_context else ""
        mensaje_sistema = f"""
{system_prompt}

DATOS ACTUALES PARA REPOSICIÓN (SmartLuben):
- Espacios libres: {len(free_spaces)} de {resumen.total_espacios}
- Productos activos: {len(productos_activos)}

{ml_context}
DATOS DETALLADOS:
{json.dumps(datos_enfocados, ensure_ascii=False, indent=2, default=str)}
"""
    else:
        # Consulta general: contexto completo
        productos = await ProductoService.get_all(db, activo=True)
        espacios = await EspacioService.get_all(db)
        movimientos = await MovimientoService.get_all(db)
        resumen = await DashboardService.get_resumen(db)

        datos = {
            "productos": serializar_productos(productos),
            "espacios": serializar_espacios(espacios),
            "movimientos": serializar_movimientos(movimientos),
            "resumen": {
                "total_espacios": resumen.total_espacios,
                "espacios_libres": resumen.espacios_libres,
                "espacios_ocupados": resumen.espacios_ocupados,
                "productos_activos": resumen.productos_activos,
            },
        }

        contexto = json.dumps(datos, ensure_ascii=False, indent=2, default=str)

        mensaje_sistema = f"""
{system_prompt}

DATOS ACTUALES DEL SISTEMA SMARTLUBEN:

{contexto}

{ml_context}
"""

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": mensaje_sistema},
            {"role": "user", "content": message},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    base_url = settings.deepseek_base_url.strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    url = f"{base_url}/chat/completions"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        respuesta = data["choices"][0]["message"]["content"]
        respuesta = respuesta.replace("**", "").replace("```", "")

        return respuesta.strip()

async def _get_ml_suggestions_internal(target_dt: datetime, db: AsyncSession) -> str:
    """Obtiene sugerencias ML directamente usando los servicios (sin HTTP)."""
    try:
        # Convertir a UTC para que coincida con cómo se almacenaron las features ML (en UTC).
        # Un naive se interpreta como hora pared de Lima (no UTC).
        if target_dt.tzinfo is not None:
            target_dt_utc = target_dt.astimezone(timezone.utc)
        else:
            target_dt_utc = target_dt.replace(tzinfo=LIMA_TZ).astimezone(timezone.utc)
        
        print(f"DEBUG _get_ml_suggestions_internal: target_dt={target_dt}, tzinfo={target_dt.tzinfo}, target_dt_utc={target_dt_utc}, hour_utc={target_dt_utc.hour}, minute={target_dt_utc.minute}")
        # 1. Obtener espacios libres y productos activos
        productos = await ProductoService.get_all(db, activo=True)
        producto_ids = [p.id for p in productos]
        producto_map = {p.id: p.nombre for p in productos}
        
        from app.services import EspacioService
        from app.models import EstadoEspacio
        espacios = await EspacioService.get_all(db)
        free_spaces = [e for e in espacios if e.estado == EstadoEspacio.libre]
        free_space_ids = [e.id for e in free_spaces]
        
        if not free_spaces or not productos:
            return ""
        
        # 2. Obtener features para inferencia
        inference_feats = await MLFeatureService.get_features_for_inference(
            db, target_dt_utc, free_space_ids, producto_ids
        )
        
        # Agregar dow y hour a las features para el modelo
        for f in inference_feats:
            f['dow'] = target_dt_utc.weekday()
            f['hour'] = target_dt_utc.hour
        
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
        
        # 6. Construir respuesta tipo ML API
        recommendations = []
        disposition = {}
        
        for espacio_id, (producto_id, combined_score, reason) in assignments.items():
            space = next(s for s in space_infos if s.espacio_id == espacio_id)
            producto_nombre = producto_map.get(producto_id, f"Producto {producto_id}")
            
            demand_score = demand_scores.get(producto_id, 0.0)
            ranker_score = space_product_scores.get((espacio_id, producto_id), 0.0)
            
            recommendations.append({
                "espacio_id": espacio_id,
                "espacio_codigo": space.espacio_codigo,
                "producto_id": producto_id,
                "producto_nombre": producto_nombre,
                "score": combined_score,
                "demand_score": demand_score,
                "ranker_score": ranker_score,
                "reason": reason
            })
            
            disposition[space.espacio_codigo] = producto_nombre
        
        metadata = {
            "free_spaces_count": len(free_spaces),
            "productos_recommended": len(set(disposition.values())),
            "max_per_product": max(1, int(len(free_spaces) * 0.5)),
            "model_version": "v1.0",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Formatear como texto para el contexto
        occupied = {
            e.codigo: producto_map.get(e.producto_actual_id, "desconocido")
            for e in espacios
            if e.estado == EstadoEspacio.ocupado
        }
        sugerencias = {
            "recommendations": recommendations,
            "disposition": disposition,
            "occupied": occupied,
            "metadata": metadata
        }
        
        return formatear_sugerencias_ml(sugerencias, target_dt)
        
    except Exception as e:
        print(f"ERROR getting ML suggestions: {e}")
        import traceback
        traceback.print_exc()
        return ""


async def obtener_sugerencias_ml_safe(target_dt: datetime, db: AsyncSession) -> str:
    """Wrapper seguro que retorna string vacío si falla."""
    try:
        return await _get_ml_suggestions_internal(target_dt, db)
    except Exception:
        return ""

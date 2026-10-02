from typing import Dict, List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class SugerenciaRecomendacion(BaseModel):
    espacio_id: int
    espacio_codigo: str
    producto_id: int
    producto_nombre: str
    producto_categoria: str = ""
    producto_imagen_url: Optional[str] = None
    score: float
    demand_score: float = 0.0
    ranker_score: float = 0.0
    reason: str = ""


class SugerenciasDisposicion(BaseModel):
    recommendations: List[SugerenciaRecomendacion] = []
    disposition: Dict[str, str] = {}


class ChatResponse(BaseModel):
    response: str
    sugerencias: Optional[SugerenciasDisposicion] = None

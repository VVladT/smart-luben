from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from app.models import Espacio, EstadoEspacio, Producto
from app.routers import ml_suggestions
from app.services import EspacioService


@pytest.fixture
def fake_ml(monkeypatch):
    class Demand:
        def get_demand_ranking(self, features, top_k):
            return [{"producto_id": f["producto_id"], "demand_score": 1.0} for f in features]

    class Ranker:
        def get_space_product_score(self, feature):
            return 1.0

    monkeypatch.setattr(ml_suggestions, "DemandPredictor", Demand)
    monkeypatch.setattr(ml_suggestions, "SpaceProductRanker", Ranker)


@pytest.mark.asyncio
async def test_plan_now_only_empty_and_idempotent(
    client: AsyncClient, db_session, sample_producto, sample_espacio, fake_ml, monkeypatch
):
    fixed_time = datetime(2026, 11, 1, 10, 30, tzinfo=ZoneInfo("America/Lima"))
    original_datetime = ml_suggestions.datetime

    class FixedDatetime(original_datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_time.astimezone(tz)

    monkeypatch.setattr(ml_suggestions, "datetime", FixedDatetime)

    pendiente = Espacio(codigo="E02", ubicacion="Fila 1", estado=EstadoEspacio.libre,
                       producto_actual_id=sample_producto.id)
    ocupado = Espacio(codigo="E03", ubicacion="Fila 2", estado=EstadoEspacio.ocupado,
                      producto_actual_id=sample_producto.id)
    db_session.add_all([pendiente, ocupado])
    await db_session.commit()

    suggestion = await client.post("/api/ml/suggest", json={"target_datetime": fixed_time.isoformat()})
    assert suggestion.status_code == 200
    assert suggestion.json()["metadata"]["free_spaces_count"] == 1
    assert [r["espacio_codigo"] for r in suggestion.json()["recommendations"]] == ["E01"]

    response = await client.post("/api/ml/plan-now")
    assert response.status_code == 200
    assert response.json()["target_datetime"] == fixed_time.isoformat()
    assert [r["espacio_codigo"] for r in response.json()["planned"]] == ["E01"]
    assert response.json()["skipped"] == []

    spaces = {e["codigo"]: e for e in (await client.get("/api/espacios")).json()}
    assert spaces["E01"]["situacion"] == "pendiente"
    assert spaces["E02"]["situacion"] == "pendiente"
    assert spaces["E03"]["situacion"] == "ocupado"
    assert (await client.get("/api/movimientos")).json() == []

    repeat = await client.post("/api/ml/plan-now")
    assert repeat.status_code == 200
    assert repeat.json()["planned"] == []
    assert (await client.get("/api/movimientos")).json() == []

    # Tampoco la ruta manual puede sobrescribir el plan generado.
    overwrite = await client.post(f"/api/espacios/{sample_espacio.id}/planificar",
                                  json={"producto_id": sample_producto.id})
    assert overwrite.status_code == 400


@pytest.mark.asyncio
async def test_plan_now_rolls_back_entire_batch(
    client: AsyncClient, db_session, sample_producto, sample_espacio, fake_ml, monkeypatch
):
    second = Espacio(codigo="E02", ubicacion="Fila 2", estado=EstadoEspacio.libre)
    another_product = Producto(nombre="Segundo", categoria="Test", activo=True)
    db_session.add_all([second, another_product])
    await db_session.commit()

    original_planificar = EspacioService.planificar
    calls = 0

    async def fail_on_second(db, espacio_id, producto_id, *, commit=True):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("conflicto de planificación")
        return await original_planificar(db, espacio_id, producto_id, commit=commit)

    monkeypatch.setattr(EspacioService, "planificar", fail_on_second)
    response = await client.post("/api/ml/plan-now")
    assert response.status_code == 409
    spaces = (await client.get("/api/espacios")).json()
    assert all(e["situacion"] == "libre" for e in spaces)
    assert (await client.get("/api/movimientos")).json() == []


@pytest.mark.asyncio
async def test_plan_now_without_products_or_empty_spaces(
    client: AsyncClient, sample_espacio, fake_ml
):
    response = await client.post("/api/ml/plan-now")
    assert response.status_code == 200
    assert response.json()["planned"] == []
    assert response.json()["skipped"] == ["E01"]

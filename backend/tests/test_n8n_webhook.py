from datetime import datetime

import httpx
import pytest

from app.config import settings
from app.routers import espacios
from app.services import n8n_webhook


@pytest.mark.asyncio
async def test_release_notifies_once_after_success(client, sample_espacio, monkeypatch):
    received = []

    async def capture(event):
        received.append(event)

    monkeypatch.setattr(espacios, "notify_space_released", capture)

    await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={})
    response = await client.post(f"/api/espacios/{sample_espacio.id}/liberar")
    assert response.status_code == 200
    assert len(received) == 1
    assert datetime.fromisoformat(received[0].pop("occurred_at")) == datetime.fromisoformat(response.json()["fecha_hora"])
    assert received[0] == {
        "event": "space_released",
        "movement_id": response.json()["id"],
        "space_id": sample_espacio.id,
        "space_code": sample_espacio.codigo,
    }

    repeated = await client.post(f"/api/espacios/{sample_espacio.id}/liberar")
    assert repeated.status_code == 400
    assert len(received) == 1


@pytest.mark.asyncio
async def test_webhook_uses_internal_url_and_ignores_failures(monkeypatch, caplog):
    url = "http://n8n:5678/webhook/smart-luben-espacio-liberado"
    monkeypatch.setattr(settings, "n8n_empty_counter_webhook_url", url)
    received = []

    def respond(request):
        received.append((str(request.url), request.method, request.content))
        return httpx.Response(503)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        n8n_webhook.httpx, "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    await n8n_webhook.notify_space_released({"event": "space_released"})
    assert received == [(url, "POST", b'{"event":"space_released"}')]
    assert "No se pudo notificar" in caplog.text

    monkeypatch.setattr(settings, "n8n_empty_counter_webhook_url", None)
    received.clear()
    await n8n_webhook.notify_space_released({"event": "space_released"})
    assert received == []

import logging

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


async def notify_space_released(event: dict) -> None:
    """Notify n8n after a committed release, without blocking the release on errors."""
    webhook_url = (settings.n8n_empty_counter_webhook_url or "").strip()
    if not webhook_url:
        return

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(webhook_url, json=event)
            response.raise_for_status()
    except (httpx.HTTPError, httpx.InvalidURL):
        logger.exception("No se pudo notificar a n8n la liberación del espacio")

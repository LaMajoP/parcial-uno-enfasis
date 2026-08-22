"""Llamadas salientes a otros microservicios.

Regla del spec (§6): son *fire-and-forget*. Si Notification o Dispatch están
caídos, la emergencia igual queda creada y el POST responde 201. El fallo se
registra en el log y ahí termina: no hay reintentos ni cola.

No se usan tareas de fondo que sobrevivan a la respuesta —en Lambda el proceso se
congela al devolverla y nunca se ejecutarían—, así que las llamadas se esperan
con timeout corto y se lanzan en paralelo.
"""
import logging

import httpx

from ..config import get_settings
from ..log import request_id_var

logger = logging.getLogger(__name__)


async def post_fire_and_forget(url: str, payload: dict, *, purpose: str) -> bool:
    """Hace un POST y se traga cualquier fallo. Devuelve si tuvo éxito."""
    settings = get_settings()
    headers = {}
    if request_id := request_id_var.get():
        headers["X-Request-Id"] = request_id

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Outbound call rejected",
            extra={
                "purpose": purpose,
                "url": url,
                "status_code": exc.response.status_code,
                "response_body": exc.response.text[:500],
            },
        )
        return False
    except (httpx.HTTPError, OSError) as exc:
        # Servicio caído, DNS que no resuelve o timeout: se registra y se sigue.
        logger.warning(
            "Outbound call failed",
            extra={"purpose": purpose, "url": url, "error": str(exc)},
        )
        return False

    logger.info("Outbound call ok", extra={"purpose": purpose, "url": url})
    return True

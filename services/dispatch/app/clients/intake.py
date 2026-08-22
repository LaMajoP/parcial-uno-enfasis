"""Cliente del servicio Intake.

Dispatch no puede leer `intake.emergencies`: los datos de la emergencia se piden
por HTTP. Hay dos llamadas con exigencias distintas:

- `fetch_emergency` es **obligatoria**: sin el tipo, la ciudad y la ubicación no
  hay forma de elegir un recurso. Si falla, el auto-despacho responde que no pudo
  asignar, pero nunca revienta.
- `mark_assigned` / `mark_status` son best-effort, como el resto de llamadas
  salientes del sistema: la asignación ya está hecha y guardada.
"""
import logging
from typing import Any
from uuid import UUID

import httpx

from ..config import get_settings
from ..log import request_id_var
from .base import post_fire_and_forget
from ..schemas.enums import EmergencyStatus

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    return {"X-Request-Id": rid} if (rid := request_id_var.get()) else {}


async def fetch_emergency(emergency_id: UUID) -> dict[str, Any] | None:
    """Devuelve los datos de la emergencia, o None si no se pudo obtener."""
    settings = get_settings()
    url = f"{settings.intake_url}/v1/emergencies/{emergency_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.get(url, headers=_headers())
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning(
            "Could not fetch emergency",
            extra={"emergency_id": str(emergency_id), "url": url, "error": str(exc)},
        )
        return None

    return body.get("data")


async def mark_status(emergency_id: UUID, status: EmergencyStatus) -> bool:
    """PATCH del estado de la emergencia. Best-effort, como el resto."""
    settings = get_settings()
    url = f"{settings.intake_url}/v1/emergencies/{emergency_id}/status"
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.patch(
                url, json={"status": status.value}, headers=_headers()
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Intake rejected the status change",
            extra={
                "emergency_id": str(emergency_id),
                "target_status": status.value,
                "status_code": exc.response.status_code,
                "response_body": exc.response.text[:500],
            },
        )
        return False
    except (httpx.HTTPError, OSError) as exc:
        logger.warning(
            "Could not update emergency status",
            extra={
                "emergency_id": str(emergency_id),
                "target_status": status.value,
                "error": str(exc),
            },
        )
        return False

    return True


__all__ = ["fetch_emergency", "mark_status", "post_fire_and_forget"]

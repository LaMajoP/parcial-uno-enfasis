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
from .base import invoke_lambda_http, post_fire_and_forget
from ..schemas.enums import EmergencyStatus

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    return {"X-Request-Id": rid} if (rid := request_id_var.get()) else {}


async def fetch_emergency(emergency_id: UUID) -> dict[str, Any] | None:
    """Devuelve los datos de la emergencia, o None si no se pudo obtener."""
    settings = get_settings()

    if settings.service_transport == "lambda":
        if not settings.intake_function_name:
            logger.error("INTAKE_FUNCTION_NAME is not configured")
            return None

        result = await invoke_lambda_http(
            settings.intake_function_name,
            "GET",
            f"/v1/emergencies/{emergency_id}",
            purpose="fetch_emergency",
        )

        if result is None:
            return None

        status_code, body, _ = result

        if not 200 <= status_code < 300 or not isinstance(body, dict):
            return None

        return body.get("data")

    if not settings.intake_url:
        logger.error("INTAKE_URL is not configured")
        return None

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

    if settings.service_transport == "lambda":
        if not settings.intake_function_name:
            logger.error("INTAKE_FUNCTION_NAME is not configured")
            return False

        result = await invoke_lambda_http(
            settings.intake_function_name,
            "PATCH",
            f"/v1/emergencies/{emergency_id}/status",
            payload={"status": status.value},
            purpose="mark_emergency_status",
        )

        return result is not None and 200 <= result[0] < 300

    if not settings.intake_url:
        logger.error("INTAKE_URL is not configured")
        return False

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

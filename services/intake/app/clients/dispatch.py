"""Cliente interno de auto-despacho de Dispatch."""

import logging
from uuid import UUID

from ..config import get_settings
from .base import invoke_lambda_http, post_fire_and_forget

logger = logging.getLogger(__name__)


async def request_auto_dispatch(emergency_id: UUID) -> bool:
    settings = get_settings()

    payload = {"emergencyId": str(emergency_id)}
    path = "/v1/internal/dispatches/auto"

    if settings.service_transport == "lambda":
        if not settings.dispatch_function_name:
            logger.error("DISPATCH_FUNCTION_NAME is not configured")
            return False

        result = await invoke_lambda_http(
            settings.dispatch_function_name,
            "POST",
            path,
            payload=payload,
            purpose="auto_dispatch",
        )

        return result is not None and 200 <= result[0] < 300

    if not settings.dispatch_url:
        logger.error("DISPATCH_URL is not configured")
        return False

    return await post_fire_and_forget(
        f"{settings.dispatch_url}{path}",
        payload,
        purpose="auto_dispatch",
    )

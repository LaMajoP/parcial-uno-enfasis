"""Cliente del servicio Notification (§5.4)."""
from typing import Any
from uuid import UUID

from ..config import get_settings
from ..schemas.enums import NotificationChannel, NotificationEvent
from .base import invoke_lambda_http, post_fire_and_forget


async def notify(
    emergency_id: UUID,
    event_type: NotificationEvent,
    payload: dict[str, Any],
) -> bool:
    settings = get_settings()

    body = {
        "emergencyId": str(emergency_id),
        "eventType": event_type.value,
        "channel": NotificationChannel.REALTIME.value,
        "payload": payload,
    }

    path = "/v1/notifications"

    if settings.service_transport == "lambda":
        if not settings.notification_function_name:
            return False

        result = await invoke_lambda_http(
            settings.notification_function_name,
            "POST",
            path,
            payload=body,
            purpose="notification",
        )

        return result is not None and 200 <= result[0] < 300

    if not settings.notification_url:
        return False

    return await post_fire_and_forget(
        f"{settings.notification_url}{path}",
        body,
        purpose="notification",
    )

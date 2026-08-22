"""Cliente del servicio Notification (§5.4)."""
from typing import Any
from uuid import UUID

from ..config import get_settings
from ..schemas.enums import NotificationChannel, NotificationEvent
from .base import post_fire_and_forget


async def notify(
    emergency_id: UUID,
    event_type: NotificationEvent,
    payload: dict[str, Any],
) -> bool:
    settings = get_settings()
    return await post_fire_and_forget(
        f"{settings.notification_url}/v1/notifications",
        {
            "emergencyId": str(emergency_id),
            "eventType": event_type.value,
            "channel": NotificationChannel.REALTIME.value,
            "payload": payload,
        },
        purpose="notification",
    )

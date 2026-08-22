"""Cliente del endpoint interno de auto-despacho de Dispatch (§5.2).

Es un endpoint `/v1/internal/...`: no se expone en el API Gateway, solo se llama
de servicio a servicio.
"""
from uuid import UUID

from ..config import get_settings
from .base import post_fire_and_forget


async def request_auto_dispatch(emergency_id: UUID) -> bool:
    settings = get_settings()
    return await post_fire_and_forget(
        f"{settings.dispatch_url}/v1/internal/dispatches/auto",
        {"emergencyId": str(emergency_id)},
        purpose="auto_dispatch",
    )

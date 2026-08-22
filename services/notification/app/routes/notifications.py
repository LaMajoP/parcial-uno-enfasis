"""Endpoints de notificaciones (§5.4): registro, consulta y stream SSE."""
import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..repositories import notifications as repo
from ..responses import success
from ..schemas.notification import NotificationCreate, NotificationOut
from ..services.broadcaster import broadcaster

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])

settings = get_settings()


@router.post("", status_code=201)
async def create_notification(
    payload: NotificationCreate, session: AsyncSession = Depends(get_session)
):
    """Registra el evento y lo difunde a los clientes SSE conectados."""
    row = await repo.create_sent(
        session,
        emergency_id=payload.emergency_id,
        event_type=payload.event_type,
        channel=payload.channel,
        payload=payload.payload,
        recipient_id=payload.recipient_id,
    )
    await session.commit()

    notification = NotificationOut(**row)
    body = notification.model_dump(by_alias=True, mode="json")

    # La difusión va después del commit: anunciar un evento que todavía podría
    # deshacerse por un rollback haría que el dashboard mostrara algo inexistente.
    delivered = broadcaster.publish(body)

    logger.info(
        "Notification registered",
        extra={
            "notification_id": str(notification.id),
            "emergency_id": str(notification.emergency_id),
            "event_type": notification.event_type.value,
            "sse_delivered": delivered,
        },
    )
    return success(body, status_code=201)


@router.get("")
async def list_notifications(
    emergency_id: UUID | None = Query(default=None, alias="emergencyId"),
    limit: int = Query(default=settings.default_limit, gt=0, le=200),
    session: AsyncSession = Depends(get_session),
):
    rows = await repo.list_notifications(
        session, emergency_id=emergency_id, limit=limit
    )
    return success(
        [NotificationOut(**row).model_dump(by_alias=True, mode="json") for row in rows]
    )


@router.get("/stream")
async def stream(request: Request):
    """Server-Sent Events para que el dashboard no tenga que hacer polling.

    En la fase Supabase este endpoint desaparece y lo sustituye Realtime.
    """

    async def event_source() -> AsyncIterator[str]:
        async with broadcaster.subscribe() as queue:
            # Evento inicial: le confirma al cliente que la conexión está viva sin
            # que tenga que esperar a que ocurra una emergencia.
            yield "event: connected\ndata: {}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=settings.sse_heartbeat_seconds
                    )
                except TimeoutError:
                    # Comentario SSE: mantiene viva la conexión a través de
                    # proxies que cierran las que llevan rato en silencio.
                    yield ": keep-alive\n\n"
                    continue

                yield f"event: notification\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Nginx almacena la respuesta en búfer por defecto y eso rompe SSE:
            # los eventos llegarían a golpes o no llegarían. Hace falta ya, para
            # cuando el gateway de la fase 5 se ponga delante.
            "X-Accel-Buffering": "no",
        },
    )

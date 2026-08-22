"""Acceso a datos de notification.notifications."""
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import notifications
from ..schemas.notification import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)

_COLUMNS = (
    notifications.c.id,
    notifications.c.emergency_id,
    notifications.c.recipient_id,
    notifications.c.channel,
    notifications.c.event_type,
    notifications.c.payload,
    notifications.c.status,
    notifications.c.created_at,
    notifications.c.sent_at,
)


async def create_sent(
    session: AsyncSession,
    *,
    emergency_id: UUID,
    event_type: NotificationEvent,
    channel: NotificationChannel,
    payload: dict[str, Any],
    recipient_id: UUID | None = None,
) -> dict[str, Any]:
    """Registra la notificación ya como SENT.

    En la fase local no hay entrega asíncrona que pueda fallar: escribir la fila
    ES la entrega, y la difusión por SSE ocurre acto seguido. Cuando entre
    Supabase Realtime, este es el punto donde volvería a tener sentido PENDING.
    """
    stmt = (
        notifications.insert()
        .values(
            emergency_id=emergency_id,
            event_type=event_type,
            channel=channel,
            payload=payload,
            recipient_id=recipient_id,
            status=NotificationStatus.SENT,
            sent_at=func.now(),
        )
        .returning(*_COLUMNS)
    )
    return dict((await session.execute(stmt)).mappings().one())


async def list_notifications(
    session: AsyncSession,
    *,
    emergency_id: UUID | None = None,
    limit: int,
) -> list[dict[str, Any]]:
    """Las más recientes primero, que es como las quiere el dashboard."""
    stmt = select(*_COLUMNS)
    if emergency_id is not None:
        stmt = stmt.where(notifications.c.emergency_id == emergency_id)

    stmt = stmt.order_by(notifications.c.created_at.desc()).limit(limit)
    return [dict(row) for row in (await session.execute(stmt)).mappings()]

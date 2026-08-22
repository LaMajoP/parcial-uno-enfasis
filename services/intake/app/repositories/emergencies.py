"""Acceso a datos de intake.emergencies. Aquí vive el SQL; el resto del servicio
no sabe cómo están guardadas las emergencias.
"""
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import emergencies
from ..schemas.enums import City, EmergencyStatus, EmergencyType, Priority

# `location` se omite a propósito en las lecturas: se reconstruye desde latitude y
# longitude, que el trigger mantiene sincronizadas con ella.
_COLUMNS = (
    emergencies.c.id,
    emergencies.c.type,
    emergencies.c.priority,
    emergencies.c.city,
    emergencies.c.status,
    emergencies.c.latitude,
    emergencies.c.longitude,
    emergencies.c.details,
    emergencies.c.created_at,
)


async def insert_triaged(
    session: AsyncSession,
    *,
    emergency_type: EmergencyType,
    priority: Priority,
    city: City,
    latitude: float,
    longitude: float,
    details: dict[str, Any],
    citizen_id: UUID | None = None,
) -> dict[str, Any]:
    """Crea la emergencia y la deja en TRIAGED dentro de la misma transacción.

    El spec pide explícitamente que el paso RECEIVED → TRIAGED ocurra en la misma
    transacción que la escritura, así que se insertan las dos operaciones juntas:
    nunca queda visible una emergencia a medio triar.
    """
    insert_stmt = (
        emergencies.insert()
        .values(
            type=emergency_type,
            priority=priority,
            city=city,
            status=EmergencyStatus.RECEIVED,
            latitude=latitude,
            longitude=longitude,
            details=details,
            citizen_id=citizen_id,
        )
        .returning(emergencies.c.id)
    )
    emergency_id = (await session.execute(insert_stmt)).scalar_one()

    triage_stmt = (
        update(emergencies)
        .where(emergencies.c.id == emergency_id)
        .values(status=EmergencyStatus.TRIAGED)
        .returning(*_COLUMNS)
    )
    return (await session.execute(triage_stmt)).mappings().one()


async def get_by_id(session: AsyncSession, emergency_id: UUID) -> dict[str, Any] | None:
    stmt = select(*_COLUMNS).where(emergencies.c.id == emergency_id)
    row = (await session.execute(stmt)).mappings().one_or_none()
    return dict(row) if row else None


async def get_status_for_update(
    session: AsyncSession, emergency_id: UUID
) -> EmergencyStatus | None:
    """Lee el estado bloqueando la fila, para que dos cambios simultáneos no
    puedan validarse ambos contra el mismo estado de partida."""
    stmt = (
        select(emergencies.c.status)
        .where(emergencies.c.id == emergency_id)
        .with_for_update()
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_status(
    session: AsyncSession, emergency_id: UUID, status: EmergencyStatus
) -> dict[str, Any]:
    stmt = (
        update(emergencies)
        .where(emergencies.c.id == emergency_id)
        .values(status=status)
        .returning(*_COLUMNS)
    )
    return (await session.execute(stmt)).mappings().one()

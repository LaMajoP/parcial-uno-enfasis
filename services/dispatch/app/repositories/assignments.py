"""Acceso a datos de dispatch.assignments."""
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import assignments
from ..schemas.enums import AssignmentStatus

_COLUMNS = (
    assignments.c.id,
    assignments.c.emergency_id,
    assignments.c.resource_id,
    assignments.c.status,
    assignments.c.assigned_at,
    assignments.c.completed_at,
)


async def create(
    session: AsyncSession, *, emergency_id: UUID, resource_id: UUID
) -> dict[str, Any]:
    stmt = (
        assignments.insert()
        .values(
            emergency_id=emergency_id,
            resource_id=resource_id,
            status=AssignmentStatus.ASSIGNED,
        )
        .returning(*_COLUMNS)
    )
    return dict((await session.execute(stmt)).mappings().one())


async def get_by_id(session: AsyncSession, dispatch_id: UUID) -> dict[str, Any] | None:
    stmt = select(*_COLUMNS).where(assignments.c.id == dispatch_id)
    row = (await session.execute(stmt)).mappings().one_or_none()
    return dict(row) if row else None


async def get_for_update(
    session: AsyncSession, dispatch_id: UUID
) -> dict[str, Any] | None:
    """Bloquea la asignación para que dos cambios de estado simultáneos no se
    validen ambos contra el mismo estado de partida."""
    stmt = select(*_COLUMNS).where(assignments.c.id == dispatch_id).with_for_update()
    row = (await session.execute(stmt)).mappings().one_or_none()
    return dict(row) if row else None


async def update_status(
    session: AsyncSession,
    dispatch_id: UUID,
    status: AssignmentStatus,
    *,
    set_completed_at: bool = False,
) -> dict[str, Any]:
    values: dict[str, Any] = {"status": status}
    if set_completed_at:
        values["completed_at"] = func.now()

    stmt = (
        update(assignments)
        .where(assignments.c.id == dispatch_id)
        .values(**values)
        .returning(*_COLUMNS)
    )
    return dict((await session.execute(stmt)).mappings().one())


async def list_with_resource(
    session: AsyncSession,
    *,
    emergency_id: UUID | None = None,
    limit: int,
) -> list[dict[str, Any]]:
    """Despachos con los datos de su recurso, los más recientes primero."""
    from ..db import resources

    stmt = (
        select(
            *_COLUMNS,
            resources.c.name.label("resource_name"),
            resources.c.type.label("resource_type"),
            resources.c.status.label("resource_status"),
        )
        .select_from(
            assignments.join(resources, resources.c.id == assignments.c.resource_id)
        )
        .order_by(assignments.c.assigned_at.desc())
        .limit(limit)
    )
    if emergency_id is not None:
        stmt = stmt.where(assignments.c.emergency_id == emergency_id)

    return [dict(row) for row in (await session.execute(stmt)).mappings()]


async def find_active_for_emergency(
    session: AsyncSession, emergency_id: UUID
) -> dict[str, Any] | None:
    """Asignación viva de una emergencia, si la tiene.

    Sirve para no despachar dos veces la misma emergencia: el auto-despacho puede
    llegar repetido si Intake reintenta.
    """
    stmt = (
        select(*_COLUMNS)
        .where(assignments.c.emergency_id == emergency_id)
        .where(
            assignments.c.status.notin_(
                [AssignmentStatus.COMPLETED, AssignmentStatus.CANCELLED]
            )
        )
        .limit(1)
    )
    row = (await session.execute(stmt)).mappings().one_or_none()
    return dict(row) if row else None

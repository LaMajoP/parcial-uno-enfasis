"""Orquestación de una asignación: recurso, asignación, emergencia y aviso.

Se mantiene fuera de las rutas porque el mismo camino lo usan la asignación
manual del operador (`POST /v1/dispatches`) y el auto-despacho interno.
"""
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..clients import intake as intake_client
from ..clients import notification as notification_client
from ..errors import NotFoundError, ResourceUnavailableError
from ..repositories import assignments as assignments_repo
from ..repositories import resources as resources_repo
from ..schemas.enums import (
    EmergencyStatus,
    NotificationEvent,
    ResourceStatus,
)

logger = logging.getLogger(__name__)


async def assign(
    session: AsyncSession, *, emergency_id: UUID, resource_id: UUID
) -> dict[str, Any]:
    """Asigna un recurso a una emergencia y devuelve la asignación creada.

    El recurso se bloquea antes de comprobar su estado: sin eso, dos peticiones
    simultáneas podrían leer ambas `AVAILABLE` y asignar el mismo recurso dos
    veces. Si al bloquearlo ya no está libre, sale `RESOURCE_UNAVAILABLE`.
    """
    resource = await resources_repo.lock_if_available(session, resource_id)
    if resource is None:
        raise NotFoundError(f"Resource {resource_id} not found")

    if resource["status"] != ResourceStatus.AVAILABLE:
        raise ResourceUnavailableError(
            f"Resource {resource_id} is {resource['status'].value}, not AVAILABLE"
        )

    assignment = await assignments_repo.create(
        session, emergency_id=emergency_id, resource_id=resource_id
    )
    await resources_repo.set_status(session, resource_id, ResourceStatus.ASSIGNED)

    # Se cierra la transacción antes de salir a la red: mantener abierta una
    # transacción con el recurso bloqueado mientras se espera a otro servicio
    # bloquearía a cualquier otra asignación durante esos segundos.
    await session.commit()

    logger.info(
        "Resource assigned",
        extra={
            "dispatch_id": str(assignment["id"]),
            "emergency_id": str(emergency_id),
            "resource_id": str(resource_id),
            "resource_name": resource["name"],
        },
    )

    await _propagate(
        emergency_id,
        EmergencyStatus.ASSIGNED,
        NotificationEvent.RESOURCE_ASSIGNED,
        {
            "resourceId": str(resource_id),
            "resourceName": resource["name"],
            "resourceType": resource["type"].value,
            "status": EmergencyStatus.ASSIGNED.value,
        },
    )

    return assignment


async def _propagate(
    emergency_id: UUID,
    emergency_status: EmergencyStatus | None,
    event: NotificationEvent,
    payload: dict[str, Any],
) -> None:
    """Comunica el cambio a Intake y a Notification. Ambas son best-effort.

    No se lanzan en paralelo: la notificación describe un estado que Intake debe
    haber registrado antes, y encadenarlas evita anunciar un cambio que todavía
    no ocurrió.
    """
    if emergency_status is not None:
        await intake_client.mark_status(emergency_id, emergency_status)
    await notification_client.notify(emergency_id, event, payload)

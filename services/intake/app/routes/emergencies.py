"""Endpoints de emergencias (§5.1).

Contratos fijos: POST /v1/emergencies, GET /v1/emergencies/{id} y
PATCH /v1/emergencies/{id}/status.
"""
import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients import dispatch as dispatch_client
from ..clients import notification as notification_client
from ..db import get_session
from ..errors import NotFoundError
from ..repositories import emergencies as repo
from ..responses import success
from ..schemas.emergency import (
    EmergencyCreate,
    EmergencyCreated,
    EmergencyDetail,
    Location,
    StatusUpdate,
)
from ..schemas.enums import NotificationEvent
from ..services.state_machine import assert_transition
from ..services.triage import calculate_priority

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/emergencies", tags=["emergencies"])


def _to_created(row: dict[str, Any]) -> EmergencyCreated:
    """La fila trae más columnas de las que expone el contrato de creación
    (latitude, longitude, details): se toman solo las que el contrato define."""
    return EmergencyCreated(
        id=row["id"],
        type=row["type"],
        priority=row["priority"],
        city=row["city"],
        status=row["status"],
        created_at=row["created_at"],
    )


def _to_detail(row: dict[str, Any]) -> EmergencyDetail:
    return EmergencyDetail(
        id=row["id"],
        type=row["type"],
        priority=row["priority"],
        city=row["city"],
        status=row["status"],
        location=Location(latitude=row["latitude"], longitude=row["longitude"]),
        details=row["details"],
        created_at=row["created_at"],
    )


@router.post("", status_code=201)
async def create_emergency(
    payload: EmergencyCreate, session: AsyncSession = Depends(get_session)
):
    """Valida, calcula prioridad, persiste como TRIAGED y avisa a los demás.

    Las dos llamadas salientes son fire-and-forget y van *después* del commit: si
    fallan, la emergencia ya está guardada y la respuesta sigue siendo 201.
    """
    priority = calculate_priority(payload.type, payload.details)

    row = await repo.insert_triaged(
        session,
        emergency_type=payload.type,
        priority=priority,
        city=payload.city,
        latitude=payload.location.latitude,
        longitude=payload.location.longitude,
        details=payload.details.model_dump(by_alias=True, mode="json"),
    )
    # Se cierra la transacción aquí y no al final del request: lo que venga
    # después son llamadas de red que no deben mantener abierta una transacción.
    await session.commit()

    created = _to_created(row)
    logger.info(
        "Emergency created",
        extra={
            "emergency_id": str(created.id),
            "emergency_type": created.type.value,
            "priority": created.priority.value,
            "city": created.city.value,
        },
    )

    # En paralelo: dos timeouts de 3 s en serie sumarían 6 s de latencia.
    await asyncio.gather(
        notification_client.notify(
            created.id,
            NotificationEvent.EMERGENCY_CREATED,
            {
                "type": created.type.value,
                "priority": created.priority.value,
                "city": created.city.value,
                "status": created.status.value,
            },
        ),
        dispatch_client.request_auto_dispatch(created.id),
    )

    return success(created, status_code=201)


@router.get("/{emergency_id}")
async def get_emergency(
    emergency_id: UUID, session: AsyncSession = Depends(get_session)
):
    row = await repo.get_by_id(session, emergency_id)
    if row is None:
        raise NotFoundError(f"Emergency {emergency_id} not found")
    return success(_to_detail(row))


@router.patch("/{emergency_id}/status")
async def update_emergency_status(
    emergency_id: UUID,
    payload: StatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Cambia el estado validando la transición contra la máquina de estados.

    La fila se bloquea antes de validar: sin el bloqueo, dos peticiones a la vez
    podrían leer el mismo estado de partida y aplicar ambas su transición.
    """
    current = await repo.get_status_for_update(session, emergency_id)
    if current is None:
        raise NotFoundError(f"Emergency {emergency_id} not found")

    if current == payload.status:
        # Reintento del mismo cambio: no es un conflicto, ya está donde se pide.
        row = await repo.get_by_id(session, emergency_id)
        return success(_to_detail(row))

    assert_transition(current, payload.status)
    row = await repo.update_status(session, emergency_id, payload.status)
    await session.commit()

    logger.info(
        "Emergency status changed",
        extra={
            "emergency_id": str(emergency_id),
            "from_status": current.value,
            "to_status": payload.status.value,
        },
    )

    await notification_client.notify(
        emergency_id,
        NotificationEvent.STATUS_CHANGED,
        {"status": payload.status.value, "previousStatus": current.value},
    )

    return success(_to_detail(row))

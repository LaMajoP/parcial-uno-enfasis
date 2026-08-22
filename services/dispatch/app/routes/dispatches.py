"""Endpoints de despacho (§5.2): asignación manual, cambio de estado y
auto-despacho interno.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients import intake as intake_client
from ..clients import notification as notification_client
from ..config import get_settings
from ..db import get_session
from ..errors import NotFoundError
from ..repositories import assignments as assignments_repo
from ..repositories import resources as resources_repo
from ..responses import success
from ..schemas.dispatch import (
    AutoDispatchRequest,
    AutoDispatchResult,
    DispatchCreate,
    DispatchOut,
    DispatchStatusUpdate,
    DispatchWithResource,
)
from ..schemas.enums import (
    AssignmentStatus,
    City,
    EmergencyType,
    NotificationEvent,
    ResourceStatus,
)
from ..services import dispatcher
from ..services.assignment_rules import preferred_types
from ..services.state_machine import (
    EMERGENCY_STATUS_FOR,
    RELEASES_RESOURCE,
    assert_transition,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dispatches"])


@router.post("/v1/dispatches", status_code=201)
async def create_dispatch(
    payload: DispatchCreate, session: AsyncSession = Depends(get_session)
):
    """Asignación manual, la que dispara el operador desde el dashboard."""
    assignment = await dispatcher.assign(
        session, emergency_id=payload.emergency_id, resource_id=payload.resource_id
    )
    return success(DispatchOut(**assignment), status_code=201)


@router.get("/v1/dispatches")
async def list_dispatches(
    emergency_id: UUID | None = Query(default=None, alias="emergencyId"),
    limit: int = Query(default=100, gt=0, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Despachos con su recurso. Lo necesita la tabla del operador (§9), que
    muestra qué recurso atiende cada emergencia."""
    rows = await assignments_repo.list_with_resource(
        session, emergency_id=emergency_id, limit=limit
    )
    return success(
        [
            DispatchWithResource(**row).model_dump(by_alias=True, mode="json")
            for row in rows
        ]
    )


@router.patch("/v1/dispatches/{dispatch_id}")
async def update_dispatch(
    dispatch_id: UUID,
    payload: DispatchStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Cambia el estado del despacho y arrastra sus efectos.

    Al llegar a COMPLETED: se sella `completed_at`, el recurso vuelve a
    AVAILABLE y la emergencia pasa a RESOLVED. CANCELLED también libera el
    recurso, pero deja la emergencia como está para que se pueda reasignar.
    """
    current = await assignments_repo.get_for_update(session, dispatch_id)
    if current is None:
        raise NotFoundError(f"Dispatch {dispatch_id} not found")

    if current["status"] == payload.status:
        # Reintento del mismo cambio: ya está donde se pide, no es un conflicto.
        return success(DispatchOut(**current))

    assert_transition(current["status"], payload.status)

    releases = payload.status in RELEASES_RESOURCE
    assignment = await assignments_repo.update_status(
        session,
        dispatch_id,
        payload.status,
        set_completed_at=payload.status is AssignmentStatus.COMPLETED,
    )
    if releases:
        await resources_repo.set_status(
            session, current["resource_id"], ResourceStatus.AVAILABLE
        )
    await session.commit()

    logger.info(
        "Dispatch status changed",
        extra={
            "dispatch_id": str(dispatch_id),
            "from_status": current["status"].value,
            "to_status": payload.status.value,
            "resource_released": releases,
        },
    )

    emergency_status = EMERGENCY_STATUS_FOR[payload.status]
    if emergency_status is not None:
        await intake_client.mark_status(current["emergency_id"], emergency_status)
    # El payload habla solo del despacho. El cambio de estado de la *emergencia*
    # lo anuncia Intake al recibir el PATCH de arriba: si se repitiera aquí, cada
    # transición generaría dos eventos anunciando el mismo hecho y el dashboard
    # se refrescaría dos veces por nada.
    await notification_client.notify(
        current["emergency_id"],
        NotificationEvent.STATUS_CHANGED,
        {
            "dispatchId": str(dispatch_id),
            "dispatchStatus": payload.status.value,
            "resourceReleased": releases,
        },
    )

    return success(DispatchOut(**assignment))


@router.post("/v1/internal/dispatches/auto")
async def auto_dispatch(
    payload: AutoDispatchRequest, session: AsyncSession = Depends(get_session)
):
    """Auto-despacho interno. No se expone en el API Gateway.

    Nunca devuelve error por no haber podido asignar: quien llama es Intake, en
    mitad de la creación de una emergencia, y un fallo aquí no puede tumbar el
    reporte. Cuando no se asigna, se responde 200 explicando por qué.
    """
    settings = get_settings()
    emergency_id = payload.emergency_id

    existing = await assignments_repo.find_active_for_emergency(session, emergency_id)
    if existing is not None:
        # El auto-despacho puede llegar repetido si Intake reintenta: se hace
        # idempotente en vez de asignar un segundo recurso a la misma emergencia.
        return _not_assigned("ALREADY_ASSIGNED", emergency_id)

    emergency = await intake_client.fetch_emergency(emergency_id)
    if emergency is None:
        return _not_assigned("EMERGENCY_NOT_AVAILABLE", emergency_id)

    try:
        emergency_type = EmergencyType(emergency["type"])
        city = City(emergency["city"])
        latitude = float(emergency["location"]["latitude"])
        longitude = float(emergency["location"]["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "Unusable emergency payload from Intake",
            extra={"emergency_id": str(emergency_id), "error": str(exc)},
        )
        return _not_assigned("EMERGENCY_NOT_AVAILABLE", emergency_id)

    candidate = await resources_repo.find_best_candidate(
        session,
        city=city,
        latitude=latitude,
        longitude=longitude,
        radius_meters=settings.auto_dispatch_radius_meters,
        preferred_types=preferred_types(emergency_type),
    )
    if candidate is None:
        return _not_assigned("NO_RESOURCE_AVAILABLE", emergency_id)

    assignment = await dispatcher.assign(
        session, emergency_id=emergency_id, resource_id=candidate["id"]
    )
    result = AutoDispatchResult(assigned=True, dispatch=DispatchOut(**assignment))
    return success(result.model_dump(by_alias=True, mode="json", exclude_none=True))


def _not_assigned(reason: str, emergency_id: UUID):
    logger.info(
        "Auto dispatch did not assign",
        extra={"emergency_id": str(emergency_id), "reason": reason},
    )
    # exclude_none para que la respuesta sea exactamente {assigned, reason},
    # como el ejemplo del spec, sin un "dispatch": null de relleno.
    result = AutoDispatchResult(assigned=False, reason=reason)
    return success(result.model_dump(by_alias=True, mode="json", exclude_none=True))

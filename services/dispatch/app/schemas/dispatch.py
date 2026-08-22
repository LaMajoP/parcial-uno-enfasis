"""Schemas de request y response de la §5.2 del spec."""
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_serializer

from .base import CamelModel, to_iso_z
from .enums import AssignmentStatus, City, ResourceStatus, ResourceType


# ── GET /v1/resources/nearby ────────────────────────────────────────────────

class NearbyResource(CamelModel):
    """Forma exacta de la respuesta del §5.2: no se le añaden campos."""

    id: UUID
    name: str
    type: ResourceType
    status: ResourceStatus
    distance_meters: int


class ResourceLocation(CamelModel):
    latitude: float
    longitude: float


class ResourceOut(CamelModel):
    """Recurso con su ubicación, para pintarlo en el mapa del operador (§9).

    Es un endpoint nuevo en vez de campos nuevos en `nearby`: el spec fija la
    forma de esa respuesta y el mapa necesita todos los recursos de la ciudad,
    no solo los cercanos a un punto.
    """

    id: UUID
    name: str
    type: ResourceType
    city: City
    status: ResourceStatus
    location: ResourceLocation


# ── POST /v1/dispatches ─────────────────────────────────────────────────────

class DispatchCreate(CamelModel):
    emergency_id: UUID
    resource_id: UUID


class DispatchOut(CamelModel):
    id: UUID
    emergency_id: UUID
    resource_id: UUID
    status: AssignmentStatus
    assigned_at: datetime
    completed_at: datetime | None = None

    @field_serializer("assigned_at")
    def _assigned_at(self, value: datetime) -> str:
        return to_iso_z(value)

    @field_serializer("completed_at")
    def _completed_at(self, value: datetime | None) -> str | None:
        return to_iso_z(value) if value else None


class DispatchWithResource(DispatchOut):
    """Despacho con los datos del recurso, para la tabla del operador.

    El dashboard tiene que mostrar el recurso asignado de cada emergencia (§9) y
    el spec no define ningún endpoint que lo devuelva. Se añade uno nuevo en vez
    de tocar los contratos existentes: `POST` y `PATCH /v1/dispatches` siguen
    respondiendo exactamente lo que el spec fija.
    """

    resource_name: str
    resource_type: ResourceType
    resource_status: ResourceStatus


# ── PATCH /v1/dispatches/{dispatchId} ───────────────────────────────────────

class DispatchStatusUpdate(CamelModel):
    status: AssignmentStatus


# ── POST /v1/internal/dispatches/auto ───────────────────────────────────────

class AutoDispatchRequest(CamelModel):
    emergency_id: UUID


class AutoDispatchResult(CamelModel):
    """El auto-despacho nunca falla: o asigna, o explica por qué no pudo.

    Hacer fallar esta llamada tumbaría el reporte de la emergencia, que es
    justamente lo que el spec prohíbe.
    """

    assigned: bool
    reason: str | None = None
    dispatch: DispatchOut | None = Field(default=None)

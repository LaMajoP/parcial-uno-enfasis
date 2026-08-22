"""Schemas de request y response de la §5.1 del spec.

El `details` es un Union discriminado por `type`: cada tipo de emergencia admite
exactamente su propio conjunto de campos. Como los modelos heredan de CamelModel
(`extra="forbid"`), mandar un `details` de SHELTER declarando `type: RESCUE` se
rechaza con INVALID_PAYLOAD en vez de colarse con los valores por defecto.
"""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_serializer

from .base import CamelModel, to_iso_z
from .enums import City, EmergencyStatus, EmergencyType, Priority

# Bounding box de Colombia (§5.1). Una coordenada fuera de aqui no es un reporte
# valido: o es un error del cliente o son coordenadas invertidas.
MIN_LATITUDE, MAX_LATITUDE = -4.5, 13.0
MIN_LONGITUDE, MAX_LONGITUDE = -82.0, -66.0


class Location(CamelModel):
    latitude: float = Field(ge=MIN_LATITUDE, le=MAX_LATITUDE)
    longitude: float = Field(ge=MIN_LONGITUDE, le=MAX_LONGITUDE)


# ── details por tipo ─────────────────────────────────────────────────────────
# Todos los campos son opcionales: el spec (§4) dice que un campo que no viene se
# trata como 0 / false, asi que el valor por defecto ES la regla de negocio.

class RescueDetails(CamelModel):
    injured: int = Field(default=0, ge=0)
    trapped: int = Field(default=0, ge=0)
    fire: bool = False
    gas_leak: bool = False


class ShelterDetails(CamelModel):
    adults: int = Field(default=0, ge=0)
    children: int = Field(default=0, ge=0)
    elderly: int = Field(default=0, ge=0)
    accessibility_required: bool = False
    # Por defecto False, siguiendo la regla "lo que no viene es 0 / false".
    house_habitable: bool = False


class SuppliesDetails(CamelModel):
    categories: list[str] = Field(default_factory=list)
    people: int = Field(default=0, ge=0)


class StructuralDamageDetails(CamelModel):
    building_type: str | None = None
    crack_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None
    collapse_risk: bool = False
    photo_url: str | None = None


EmergencyDetails = (
    RescueDetails | ShelterDetails | SuppliesDetails | StructuralDamageDetails
)


# ── request ──────────────────────────────────────────────────────────────────
# El discriminador es `type` y vive en el nivel superior del payload, no dentro
# de `details`. Por eso el Union se hace sobre el request completo: es la forma
# de que Pydantic escoja el modelo de `details` correcto segun el tipo.

class _EmergencyCreateBase(CamelModel):
    city: City
    location: Location


class RescueCreate(_EmergencyCreateBase):
    type: Literal[EmergencyType.RESCUE]
    details: RescueDetails = Field(default_factory=RescueDetails)


class ShelterCreate(_EmergencyCreateBase):
    type: Literal[EmergencyType.SHELTER]
    details: ShelterDetails = Field(default_factory=ShelterDetails)


class SuppliesCreate(_EmergencyCreateBase):
    type: Literal[EmergencyType.SUPPLIES]
    details: SuppliesDetails = Field(default_factory=SuppliesDetails)


class StructuralDamageCreate(_EmergencyCreateBase):
    type: Literal[EmergencyType.STRUCTURAL_DAMAGE]
    details: StructuralDamageDetails = Field(default_factory=StructuralDamageDetails)


EmergencyCreate = Annotated[
    RescueCreate | ShelterCreate | SuppliesCreate | StructuralDamageCreate,
    Field(discriminator="type"),
]


class StatusUpdate(CamelModel):
    status: EmergencyStatus


# ── response ─────────────────────────────────────────────────────────────────

class EmergencyCreated(CamelModel):
    """Respuesta de POST /v1/emergencies (201)."""

    id: UUID
    type: EmergencyType
    priority: Priority
    city: City
    status: EmergencyStatus
    created_at: datetime

    @field_serializer("created_at")
    def _created_at(self, value: datetime) -> str:
        return to_iso_z(value)


class EmergencyDetail(CamelModel):
    """Respuesta de GET /v1/emergencies/{id} y del PATCH de estado."""

    id: UUID
    type: EmergencyType
    priority: Priority
    city: City
    status: EmergencyStatus
    location: Location
    details: dict
    created_at: datetime

    @field_serializer("created_at")
    def _created_at(self, value: datetime) -> str:
        return to_iso_z(value)

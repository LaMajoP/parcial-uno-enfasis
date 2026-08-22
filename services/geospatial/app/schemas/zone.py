"""Schemas de la §5.3 del spec."""
from datetime import datetime
from uuid import UUID

from pydantic import field_serializer

from .base import CamelModel, to_iso_z
from .enums import City, EmergencyStatus, EmergencyType, Priority


class Location(CamelModel):
    latitude: float
    longitude: float


class ZoneEmergency(CamelModel):
    """Emergencia vista desde el mapa del operador.

    No incluye `details`: el dashboard los pide a Intake cuando el operador abre
    una emergencia concreta, y arrastrarlos aquí engordaría cada refresco de la
    lista sin que nadie los mire.
    """

    id: UUID
    type: EmergencyType
    priority: Priority
    city: City
    status: EmergencyStatus
    location: Location
    created_at: datetime

    @field_serializer("created_at")
    def _created_at(self, value: datetime) -> str:
        return to_iso_z(value)


class Hotspot(CamelModel):
    latitude: float
    longitude: float
    radius_meters: int
    emergency_count: int
    highest_priority: Priority

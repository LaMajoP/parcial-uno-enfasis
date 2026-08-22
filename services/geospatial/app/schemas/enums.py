"""Enums del dominio, espejo de los tipos de PostgreSQL (003_enums.sql)."""
from enum import StrEnum


class EmergencyType(StrEnum):
    RESCUE = "RESCUE"
    SHELTER = "SHELTER"
    SUPPLIES = "SUPPLIES"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"


class Priority(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class City(StrEnum):
    CHOCO = "CHOCO"
    PEREIRA = "PEREIRA"
    CALI = "CALI"
    MANIZALES = "MANIZALES"


class EmergencyStatus(StrEnum):
    RECEIVED = "RECEIVED"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


# Una emergencia deja de contar para zonas y hotspots cuando llega a un estado
# final: ya no representa algo que esté pasando.
INACTIVE_STATUSES: frozenset[EmergencyStatus] = frozenset(
    {EmergencyStatus.RESOLVED, EmergencyStatus.CANCELLED}
)

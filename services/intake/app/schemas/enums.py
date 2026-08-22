"""Enums del dominio. Los valores son contrato: coinciden uno a uno con los tipos
enumerados de PostgreSQL definidos en database/migrations/003_enums.sql.
"""
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


class NotificationEvent(StrEnum):
    EMERGENCY_CREATED = "EMERGENCY_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    RESOURCE_ASSIGNED = "RESOURCE_ASSIGNED"
    HOTSPOT_DETECTED = "HOTSPOT_DETECTED"


class NotificationChannel(StrEnum):
    REALTIME = "REALTIME"
    WEBHOOK = "WEBHOOK"

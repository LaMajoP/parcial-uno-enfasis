"""Enums del dominio, espejo de los tipos de PostgreSQL (003_enums.sql).

Se duplican en cada servicio a propósito: el spec prohíbe un paquete de dominio
compartido entre microservicios.
"""
from enum import StrEnum


class EmergencyType(StrEnum):
    RESCUE = "RESCUE"
    SHELTER = "SHELTER"
    SUPPLIES = "SUPPLIES"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"


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


class ResourceType(StrEnum):
    AMBULANCE = "AMBULANCE"
    FIRE_BRIGADE = "FIRE_BRIGADE"
    RESCUE_TEAM = "RESCUE_TEAM"
    CIVIL_DEFENSE = "CIVIL_DEFENSE"
    HUMANITARIAN_TEAM = "HUMANITARIAN_TEAM"


class ResourceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    UNAVAILABLE = "UNAVAILABLE"


class AssignmentStatus(StrEnum):
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class NotificationEvent(StrEnum):
    EMERGENCY_CREATED = "EMERGENCY_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    RESOURCE_ASSIGNED = "RESOURCE_ASSIGNED"
    HOTSPOT_DETECTED = "HOTSPOT_DETECTED"


class NotificationChannel(StrEnum):
    REALTIME = "REALTIME"
    WEBHOOK = "WEBHOOK"

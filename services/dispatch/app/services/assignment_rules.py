"""Mapeo emergencia → tipo de recurso preferido (§6 del spec).

Función pura: dado un tipo de emergencia, devuelve los tipos de recurso en orden
de preferencia. La búsqueda real de candidatos vive en el repositorio; aquí solo
está la política, que es lo que hay que poder leer y discutir sin abrir SQL.
"""
from ..schemas.enums import EmergencyType, ResourceType

RESOURCE_PREFERENCES: dict[EmergencyType, tuple[ResourceType, ...]] = {
    EmergencyType.RESCUE: (ResourceType.AMBULANCE, ResourceType.RESCUE_TEAM),
    EmergencyType.SHELTER: (
        ResourceType.CIVIL_DEFENSE,
        ResourceType.HUMANITARIAN_TEAM,
    ),
    EmergencyType.SUPPLIES: (
        ResourceType.HUMANITARIAN_TEAM,
        ResourceType.CIVIL_DEFENSE,
    ),
    EmergencyType.STRUCTURAL_DAMAGE: (
        ResourceType.FIRE_BRIGADE,
        ResourceType.RESCUE_TEAM,
    ),
}


def preferred_types(emergency_type: EmergencyType) -> tuple[ResourceType, ...]:
    """Tipos de recurso en orden de preferencia para ese tipo de emergencia."""
    return RESOURCE_PREFERENCES[emergency_type]

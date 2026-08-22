"""Reglas de triage de la §4 del spec.

`calculate_priority` es una función pura: mismos argumentos, mismo resultado, sin
tocar base de datos, reloj ni red. Es la única parte del servicio con lógica de
negocio de verdad, así que se mantiene aislada y cubierta por tests.
"""
from ..schemas.emergency import (
    EmergencyDetails,
    RescueDetails,
    ShelterDetails,
    StructuralDamageDetails,
    SuppliesDetails,
)
from ..schemas.enums import EmergencyType, Priority

# Prioridad base por tipo, antes de los ajustes.
BASE_PRIORITY: dict[EmergencyType, Priority] = {
    EmergencyType.RESCUE: Priority.P1,
    EmergencyType.SHELTER: Priority.P2,
    EmergencyType.SUPPLIES: Priority.P3,
    EmergencyType.STRUCTURAL_DAMAGE: Priority.P4,
}


def calculate_priority(
    emergency_type: EmergencyType, details: EmergencyDetails
) -> Priority:
    """Devuelve la prioridad P1–P4 de una emergencia.

    Los campos que no vienen ya llegan aquí como 0 / false: es el valor por
    defecto de los modelos de `details`, no una decisión que se tome aquí.
    """
    match emergency_type:
        case EmergencyType.RESCUE:
            return _rescue(details)
        case EmergencyType.SHELTER:
            return _shelter(details)
        case EmergencyType.SUPPLIES:
            return _supplies(details)
        case EmergencyType.STRUCTURAL_DAMAGE:
            return _structural_damage(details)

    raise ValueError(f"Unknown emergency type: {emergency_type}")


def _rescue(d: RescueDetails) -> Priority:
    """P1 salvo que no haya heridos, ni atrapados, ni fuego, ni fuga de gas."""
    critical = d.injured > 0 or d.trapped > 0 or d.fire or d.gas_leak
    return Priority.P1 if critical else Priority.P2


def _shelter(d: ShelterDetails) -> Priority:
    """Sube a P1 por accesibilidad, por población vulnerable o por grupo grande
    sin vivienda habitable."""
    total_people = d.adults + d.children + d.elderly
    urgent = (
        d.accessibility_required
        or (d.children + d.elderly) >= 3
        or (not d.house_habitable and total_people >= 5)
    )
    return Priority.P1 if urgent else Priority.P2


def _supplies(d: SuppliesDetails) -> Priority:
    """El agua y el volumen de gente son los dos disparadores."""
    urgent = d.people >= 20 or "WATER" in d.categories
    return Priority.P2 if urgent else Priority.P3


def _structural_damage(d: StructuralDamageDetails) -> Priority:
    """El riesgo de colapso manda sobre el nivel de fisura."""
    if d.collapse_risk:
        return Priority.P2
    if d.crack_level == "HIGH":
        return Priority.P3
    return Priority.P4

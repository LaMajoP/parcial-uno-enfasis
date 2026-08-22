"""Mapeo emergencia → recurso preferido (§6 del spec)."""
import pytest

from app.schemas.enums import EmergencyType, ResourceType
from app.services.assignment_rules import RESOURCE_PREFERENCES, preferred_types


def test_preferences_match_the_spec_table_exactly():
    assert RESOURCE_PREFERENCES == {
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


@pytest.mark.parametrize("emergency_type", list(EmergencyType))
def test_every_emergency_type_has_preferences(emergency_type):
    """Si se añade un tipo y no su preferencia, esto lo detecta antes del KeyError
    en producción."""
    assert len(preferred_types(emergency_type)) >= 1


@pytest.mark.parametrize("emergency_type", list(EmergencyType))
def test_preference_order_matters_and_has_no_duplicates(emergency_type):
    types = preferred_types(emergency_type)
    assert len(set(types)) == len(types)


def test_supplies_and_shelter_share_types_in_opposite_order():
    """Ambos usan los mismos dos equipos, pero con la prioridad invertida: es un
    detalle fácil de copiar mal entre las dos filas de la tabla."""
    assert preferred_types(EmergencyType.SUPPLIES) == tuple(
        reversed(preferred_types(EmergencyType.SHELTER))
    )


def test_rescue_prefers_ambulance_first():
    """§11: el rescate en Cali de la prueba de aceptación tiene que terminar con
    una ambulancia, no con un equipo de rescate."""
    assert preferred_types(EmergencyType.RESCUE)[0] is ResourceType.AMBULANCE

"""Cobertura de las reglas de triage de la §4 del spec.

Cada regla del spec tiene aquí su caso que la activa y su caso que no, más los
límites exactos de cada umbral (>=3, >=5, >=20), que son donde de verdad se
rompen estas reglas.
"""
import pytest

from app.schemas.emergency import (
    RescueDetails,
    ShelterDetails,
    StructuralDamageDetails,
    SuppliesDetails,
)
from app.schemas.enums import EmergencyType, Priority
from app.services.triage import BASE_PRIORITY, calculate_priority


# ── Prioridad base por tipo ──────────────────────────────────────────────────

def test_base_priority_table_matches_spec():
    assert BASE_PRIORITY == {
        EmergencyType.RESCUE: Priority.P1,
        EmergencyType.SHELTER: Priority.P2,
        EmergencyType.SUPPLIES: Priority.P3,
        EmergencyType.STRUCTURAL_DAMAGE: Priority.P4,
    }


# ── RESCUE: P1 si hay heridos, atrapados, fuego o gas; si no, baja a P2 ──────

@pytest.mark.parametrize(
    "details",
    [
        RescueDetails(injured=1),
        RescueDetails(trapped=1),
        RescueDetails(fire=True),
        RescueDetails(gas_leak=True),
        RescueDetails(injured=3, trapped=2, fire=True, gas_leak=True),
    ],
    ids=["injured", "trapped", "fire", "gas_leak", "todos"],
)
def test_rescue_stays_p1_when_critical(details):
    assert calculate_priority(EmergencyType.RESCUE, details) == Priority.P1


def test_rescue_drops_to_p2_without_any_critical_factor():
    details = RescueDetails(injured=0, trapped=0, fire=False, gas_leak=False)
    assert calculate_priority(EmergencyType.RESCUE, details) == Priority.P2


def test_rescue_with_empty_details_drops_to_p2():
    """Sin datos, todo es 0/false: no hay nada que justifique P1."""
    assert calculate_priority(EmergencyType.RESCUE, RescueDetails()) == Priority.P2


# ── SHELTER: P1 por accesibilidad, vulnerables >=3, o >=5 sin vivienda ──────

def test_shelter_p1_when_accessibility_required():
    details = ShelterDetails(adults=1, accessibility_required=True, house_habitable=True)
    assert calculate_priority(EmergencyType.SHELTER, details) == Priority.P1


@pytest.mark.parametrize(
    ("children", "elderly", "expected"),
    [
        (3, 0, Priority.P1),  # limite exacto por ninos
        (0, 3, Priority.P1),  # limite exacto por adultos mayores
        (2, 1, Priority.P1),  # la regla suma ambos grupos
        (2, 0, Priority.P2),  # justo por debajo
        (1, 1, Priority.P2),
    ],
)
def test_shelter_vulnerable_threshold(children, elderly, expected):
    details = ShelterDetails(adults=0, children=children, elderly=elderly, house_habitable=True)
    assert calculate_priority(EmergencyType.SHELTER, details) == expected


@pytest.mark.parametrize(
    ("adults", "habitable", "expected"),
    [
        (5, False, Priority.P1),  # 5 personas y casa inhabitable
        (4, False, Priority.P2),  # justo por debajo del umbral
        (9, True, Priority.P2),   # grupo grande pero la casa sirve
    ],
)
def test_shelter_uninhabitable_house_threshold(adults, habitable, expected):
    details = ShelterDetails(adults=adults, house_habitable=habitable)
    assert calculate_priority(EmergencyType.SHELTER, details) == expected


def test_shelter_falls_back_to_p2():
    details = ShelterDetails(adults=2, children=1, house_habitable=True)
    assert calculate_priority(EmergencyType.SHELTER, details) == Priority.P2


def test_shelter_empty_details_is_p2():
    """houseHabitable ausente cuenta como false, pero sin gente no llega a 5."""
    assert calculate_priority(EmergencyType.SHELTER, ShelterDetails()) == Priority.P2


# ── SUPPLIES: P2 si >=20 personas o hay agua; si no, P3 ─────────────────────

@pytest.mark.parametrize(
    ("people", "categories", "expected"),
    [
        (20, [], Priority.P2),               # limite exacto
        (19, [], Priority.P3),               # justo por debajo
        (1, ["WATER"], Priority.P2),         # el agua sola basta
        (1, ["FOOD", "WATER"], Priority.P2),
        (1, ["FOOD"], Priority.P3),
        (0, [], Priority.P3),
        (50, ["WATER"], Priority.P2),        # ambas condiciones
    ],
)
def test_supplies_rules(people, categories, expected):
    details = SuppliesDetails(people=people, categories=categories)
    assert calculate_priority(EmergencyType.SUPPLIES, details) == expected


def test_supplies_water_match_is_case_sensitive_enum_value():
    """El contrato usa 'WATER' en mayusculas; 'water' no es la misma categoria."""
    details = SuppliesDetails(people=1, categories=["water"])
    assert calculate_priority(EmergencyType.SUPPLIES, details) == Priority.P3


# ── STRUCTURAL_DAMAGE: colapso -> P2, fisura HIGH -> P3, si no P4 ───────────

@pytest.mark.parametrize(
    ("collapse_risk", "crack_level", "expected"),
    [
        (True, None, Priority.P2),
        (True, "HIGH", Priority.P2),    # el colapso manda sobre la fisura
        (True, "LOW", Priority.P2),
        (False, "HIGH", Priority.P3),
        (False, "MEDIUM", Priority.P4),
        (False, "LOW", Priority.P4),
        (False, None, Priority.P4),
    ],
)
def test_structural_damage_rules(collapse_risk, crack_level, expected):
    details = StructuralDamageDetails(
        collapse_risk=collapse_risk, crack_level=crack_level
    )
    assert calculate_priority(EmergencyType.STRUCTURAL_DAMAGE, details) == expected


def test_structural_damage_empty_details_is_p4():
    assert (
        calculate_priority(EmergencyType.STRUCTURAL_DAMAGE, StructuralDamageDetails())
        == Priority.P4
    )


# ── Invariantes generales ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("emergency_type", "details"),
    [
        (EmergencyType.RESCUE, RescueDetails()),
        (EmergencyType.SHELTER, ShelterDetails()),
        (EmergencyType.SUPPLIES, SuppliesDetails()),
        (EmergencyType.STRUCTURAL_DAMAGE, StructuralDamageDetails()),
    ],
)
def test_priority_is_always_within_p1_p4(emergency_type, details):
    assert calculate_priority(emergency_type, details) in set(Priority)


def test_triage_is_pure():
    """Misma entrada, mismo resultado, y no muta el objeto que recibe."""
    details = RescueDetails(injured=2, trapped=1, fire=True)
    snapshot = details.model_dump()

    results = {calculate_priority(EmergencyType.RESCUE, details) for _ in range(5)}

    assert results == {Priority.P1}
    assert details.model_dump() == snapshot


def test_spec_acceptance_example_is_p1():
    """§11: rescate en Cali con 3 heridos tiene que dar P1."""
    details = RescueDetails(injured=3)
    assert calculate_priority(EmergencyType.RESCUE, details) == Priority.P1

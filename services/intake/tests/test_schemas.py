"""Validación del contrato de payloads (§5.1): union discriminado, camelCase y
bounding box de Colombia.
"""
import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.emergency import (
    EmergencyCreate,
    RescueCreate,
    ShelterCreate,
    StructuralDamageCreate,
    SuppliesCreate,
)
from app.schemas.enums import City, EmergencyType

adapter = TypeAdapter(EmergencyCreate)

CALI = {"latitude": 3.4516, "longitude": -76.532}


# ── Los cuatro ejemplos literales del spec §5.1 ──────────────────────────────

def test_rescue_example_from_spec():
    payload = adapter.validate_python({
        "type": "RESCUE", "city": "CALI", "location": CALI,
        "details": {"injured": 2, "trapped": 1, "fire": True, "gasLeak": False},
    })
    assert isinstance(payload, RescueCreate)
    assert payload.details.gas_leak is False
    assert payload.details.injured == 2


def test_shelter_example_from_spec():
    payload = adapter.validate_python({
        "type": "SHELTER", "city": "PEREIRA",
        "location": {"latitude": 4.8143, "longitude": -75.6946},
        "details": {"adults": 4, "children": 2, "elderly": 1,
                    "accessibilityRequired": False, "houseHabitable": False},
    })
    assert isinstance(payload, ShelterCreate)
    assert payload.city is City.PEREIRA
    assert payload.details.house_habitable is False


def test_supplies_example_from_spec():
    payload = adapter.validate_python({
        "type": "SUPPLIES", "city": "CHOCO",
        "location": {"latitude": 5.6947, "longitude": -76.6611},
        "details": {"categories": ["WATER", "FOOD"], "people": 15},
    })
    assert isinstance(payload, SuppliesCreate)
    assert payload.details.categories == ["WATER", "FOOD"]


def test_structural_damage_example_from_spec():
    payload = adapter.validate_python({
        "type": "STRUCTURAL_DAMAGE", "city": "MANIZALES",
        "location": {"latitude": 5.0703, "longitude": -75.5138},
        "details": {"buildingType": "RESIDENTIAL", "crackLevel": "HIGH",
                    "collapseRisk": True, "photoUrl": "https://example.com/a.jpg"},
    })
    assert isinstance(payload, StructuralDamageCreate)
    assert payload.type is EmergencyType.STRUCTURAL_DAMAGE
    assert payload.details.building_type == "RESIDENTIAL"


# ── El union discriminado rechaza details que no corresponden al tipo ───────

def test_details_of_another_type_is_rejected():
    """RESCUE con details de SHELTER: el spec exige INVALID_PAYLOAD, no que se
    cuele con los valores por defecto."""
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "type": "RESCUE", "city": "CALI", "location": CALI,
            "details": {"adults": 4, "children": 2, "elderly": 1},
        })


def test_unknown_field_in_details_is_rejected():
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "type": "RESCUE", "city": "CALI", "location": CALI,
            "details": {"injured": 1, "unexpectedField": 9},
        })


def test_unknown_emergency_type_is_rejected():
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "type": "EARTHQUAKE", "city": "CALI", "location": CALI, "details": {},
        })


def test_unknown_city_is_rejected():
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "type": "RESCUE", "city": "BOGOTA", "location": CALI, "details": {},
        })


def test_invalid_crack_level_is_rejected():
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "type": "STRUCTURAL_DAMAGE", "city": "CALI", "location": CALI,
            "details": {"crackLevel": "CRITICAL"},
        })


def test_negative_counts_are_rejected():
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "type": "RESCUE", "city": "CALI", "location": CALI,
            "details": {"injured": -1},
        })


def test_details_is_optional_and_defaults_to_empty():
    payload = adapter.validate_python({"type": "RESCUE", "city": "CALI", "location": CALI})
    assert payload.details.injured == 0
    assert payload.details.fire is False


# ── Bounding box de Colombia (§5.1) ─────────────────────────────────────────

@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (13.5, -74.0),    # al norte del limite
        (-5.0, -74.0),    # al sur del limite
        (4.0, -83.0),     # al oeste del limite
        (4.0, -65.0),     # al este del limite
        (-76.532, 3.4516),  # lat/lon invertidas: el caso real que esto atrapa
    ],
)
def test_coordinates_outside_colombia_are_rejected(latitude, longitude):
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "type": "RESCUE", "city": "CALI",
            "location": {"latitude": latitude, "longitude": longitude},
            "details": {},
        })


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(-4.5, -82.0), (13.0, -66.0), (3.4516, -76.532)],
)
def test_coordinates_inside_colombia_are_accepted(latitude, longitude):
    payload = adapter.validate_python({
        "type": "RESCUE", "city": "CALI",
        "location": {"latitude": latitude, "longitude": longitude},
        "details": {},
    })
    assert payload.location.latitude == latitude


# ── Las respuestas salen siempre en camelCase ───────────────────────────────

def test_created_response_serializes_camel_case_and_iso_z():
    from datetime import UTC, datetime
    from uuid import UUID

    from app.schemas.emergency import EmergencyCreated

    created = EmergencyCreated(
        id=UUID("11111111-2222-4333-8444-555555555555"),
        type="RESCUE", priority="P1", city="CALI", status="TRIAGED",
        created_at=datetime(2026, 8, 17, 17, 0, 0, tzinfo=UTC),
    )

    body = created.model_dump(by_alias=True, mode="json")

    assert body == {
        "id": "11111111-2222-4333-8444-555555555555",
        "type": "RESCUE", "priority": "P1", "city": "CALI", "status": "TRIAGED",
        "createdAt": "2026-08-17T17:00:00Z",
    }


def test_detail_response_nests_location_in_camel_case():
    from datetime import UTC, datetime
    from uuid import UUID

    from app.schemas.emergency import EmergencyDetail, Location

    detail = EmergencyDetail(
        id=UUID("11111111-2222-4333-8444-555555555555"),
        type="RESCUE", priority="P1", city="CALI", status="ASSIGNED",
        location=Location(latitude=3.4516, longitude=-76.532),
        details={"injured": 3},
        created_at=datetime(2026, 8, 17, 17, 0, 0, tzinfo=UTC),
    )

    body = detail.model_dump(by_alias=True, mode="json")

    assert body["location"] == {"latitude": 3.4516, "longitude": -76.532}
    assert body["createdAt"] == "2026-08-17T17:00:00Z"

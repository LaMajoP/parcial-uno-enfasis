"""Contrato de la API de zonas (§5.3)."""
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app


async def _fake_session():
    yield None


app.dependency_overrides[get_session] = _fake_session


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _assert_error(response, *, status: int, code: str):
    assert response.status_code == status
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert "data" not in body


def test_unknown_city_is_rejected(client):
    _assert_error(client.get("/v1/zones/BOGOTA/emergencies"), status=400,
                  code="INVALID_PAYLOAD")


def test_unknown_priority_is_rejected(client):
    _assert_error(client.get("/v1/zones/CALI/emergencies?priority=P9"), status=400,
                  code="INVALID_PAYLOAD")


def test_unknown_status_is_rejected(client):
    _assert_error(client.get("/v1/zones/CALI/emergencies?status=DONE"), status=400,
                  code="INVALID_PAYLOAD")


@pytest.mark.parametrize("query", ["limit=0", "limit=-5", "limit=501"])
def test_out_of_range_limit_is_rejected(client, query):
    _assert_error(client.get(f"/v1/zones/CALI/emergencies?{query}"), status=400,
                  code="INVALID_PAYLOAD")


@pytest.mark.parametrize("query", ["radiusMeters=0", "radiusMeters=-1"])
def test_non_positive_radius_is_rejected(client, query):
    """Un radio de 0 daría un eps de 0 y DBSCAN no agruparía nada, en silencio."""
    _assert_error(client.get(f"/v1/zones/CALI/hotspots?{query}"), status=400,
                  code="INVALID_PAYLOAD")


def test_unknown_route_is_not_found(client):
    _assert_error(client.get("/v1/zones"), status=404, code="NOT_FOUND")


def test_request_id_is_echoed_back(client):
    response = client.get("/v1/nope", headers={"X-Request-Id": "abc-123"})
    assert response.headers["X-Request-Id"] == "abc-123"


# ── Serialización ───────────────────────────────────────────────────────────

def test_hotspot_serializes_camel_case():
    from app.schemas.zone import Hotspot

    body = Hotspot(
        latitude=3.452, longitude=-76.531, radius_meters=5000,
        emergency_count=18, highest_priority="P1",
    ).model_dump(by_alias=True, mode="json")

    assert body == {
        "latitude": 3.452, "longitude": -76.531, "radiusMeters": 5000,
        "emergencyCount": 18, "highestPriority": "P1",
    }


def test_zone_emergency_serializes_camel_case_and_iso_z():
    from datetime import UTC, datetime
    from uuid import UUID

    from app.schemas.zone import Location, ZoneEmergency

    body = ZoneEmergency(
        id=UUID("11111111-2222-4333-8444-555555555555"),
        type="RESCUE", priority="P1", city="CALI", status="ASSIGNED",
        location=Location(latitude=3.4516, longitude=-76.532),
        created_at=datetime(2026, 8, 17, 17, 0, 0, tzinfo=UTC),
    ).model_dump(by_alias=True, mode="json")

    assert body["createdAt"] == "2026-08-17T17:00:00Z"
    assert body["location"] == {"latitude": 3.4516, "longitude": -76.532}
    # `details` no viaja en la vista de zona.
    assert "details" not in body


def test_inactive_statuses_are_the_two_final_ones():
    from app.schemas.enums import INACTIVE_STATUSES, EmergencyStatus

    assert INACTIVE_STATUSES == frozenset(
        {EmergencyStatus.RESOLVED, EmergencyStatus.CANCELLED}
    )

"""Contrato de la API: envoltorio de respuesta, validación de query params y
formato de los schemas de la §5.2.
"""
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


# ── GET /v1/resources/nearby ────────────────────────────────────────────────

def test_nearby_requires_coordinates(client):
    _assert_error(client.get("/v1/resources/nearby"), status=400,
                  code="INVALID_PAYLOAD")


def test_nearby_rejects_coordinates_outside_colombia(client):
    response = client.get("/v1/resources/nearby?latitude=40.7&longitude=-74.0")
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_nearby_rejects_inverted_coordinates(client):
    response = client.get("/v1/resources/nearby?latitude=-76.532&longitude=3.4516")
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


@pytest.mark.parametrize("query", ["radiusMeters=0", "radiusMeters=-1", "limit=0"])
def test_nearby_rejects_nonsensical_bounds(client, query):
    response = client.get(f"/v1/resources/nearby?latitude=3.45&longitude=-76.53&{query}")
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_nearby_rejects_unknown_resource_type(client):
    response = client.get(
        "/v1/resources/nearby?latitude=3.45&longitude=-76.53&type=HELICOPTER"
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


# ── POST /v1/dispatches ─────────────────────────────────────────────────────

def test_create_dispatch_requires_both_ids(client):
    response = client.post("/v1/dispatches", json={"emergencyId": "not-a-uuid"})
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_create_dispatch_rejects_unknown_fields(client):
    response = client.post(
        "/v1/dispatches",
        json={"emergencyId": "11111111-2222-4333-8444-555555555555",
              "resourceId": "11111111-2222-4333-8444-555555555556",
              "priority": "P1"},
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_patch_dispatch_rejects_unknown_status(client):
    response = client.patch(
        "/v1/dispatches/11111111-2222-4333-8444-555555555555",
        json={"status": "DONE"},
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


# ── Errores genéricos ───────────────────────────────────────────────────────

def test_unknown_route_is_not_found(client):
    _assert_error(client.get("/v1/nope"), status=404, code="NOT_FOUND")


def test_method_not_allowed_is_a_client_error(client):
    _assert_error(client.delete("/v1/dispatches"), status=400,
                  code="INVALID_PAYLOAD")


def test_request_id_is_echoed_back(client):
    response = client.get("/v1/nope", headers={"X-Request-Id": "abc-123"})
    assert response.headers["X-Request-Id"] == "abc-123"


# ── Serialización de las respuestas ─────────────────────────────────────────

def test_dispatch_out_serializes_camel_case_and_iso_z():
    from datetime import UTC, datetime
    from uuid import UUID

    from app.schemas.dispatch import DispatchOut

    body = DispatchOut(
        id=UUID("11111111-2222-4333-8444-555555555555"),
        emergency_id=UUID("22222222-3333-4444-8555-666666666666"),
        resource_id=UUID("33333333-4444-4555-8666-777777777777"),
        status="ASSIGNED",
        assigned_at=datetime(2026, 8, 17, 17, 10, 0, tzinfo=UTC),
    ).model_dump(by_alias=True, mode="json")

    assert body["emergencyId"] == "22222222-3333-4444-8555-666666666666"
    assert body["resourceId"] == "33333333-4444-4555-8666-777777777777"
    assert body["assignedAt"] == "2026-08-17T17:10:00Z"
    assert body["completedAt"] is None


def test_auto_dispatch_failure_matches_the_spec_shape():
    """El spec muestra exactamente {assigned, reason}, sin campos de relleno."""
    from app.schemas.dispatch import AutoDispatchResult

    body = AutoDispatchResult(
        assigned=False, reason="NO_RESOURCE_AVAILABLE"
    ).model_dump(by_alias=True, mode="json", exclude_none=True)

    assert body == {"assigned": False, "reason": "NO_RESOURCE_AVAILABLE"}


def test_nearby_resource_serializes_distance_as_camel_case():
    from uuid import UUID

    from app.schemas.dispatch import NearbyResource

    body = NearbyResource(
        id=UUID("11111111-2222-4333-8444-555555555555"),
        name="Ambulancia Cali 01", type="AMBULANCE", status="AVAILABLE",
        distance_meters=1350,
    ).model_dump(by_alias=True, mode="json")

    assert body["distanceMeters"] == 1350
    assert body["name"] == "Ambulancia Cali 01"

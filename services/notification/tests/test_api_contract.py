"""Contrato de la API de notificaciones (§5.4)."""
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


def test_unknown_event_type_is_rejected(client):
    response = client.post(
        "/v1/notifications",
        json={"emergencyId": "11111111-2222-4333-8444-555555555555",
              "eventType": "SOMETHING_ELSE", "channel": "REALTIME", "payload": {}},
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_unknown_channel_is_rejected(client):
    response = client.post(
        "/v1/notifications",
        json={"emergencyId": "11111111-2222-4333-8444-555555555555",
              "eventType": "STATUS_CHANGED", "channel": "SMS", "payload": {}},
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_missing_emergency_id_is_rejected(client):
    response = client.post("/v1/notifications", json={"eventType": "STATUS_CHANGED"})
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_invalid_emergency_id_filter_is_rejected(client):
    _assert_error(client.get("/v1/notifications?emergencyId=nope"), status=400,
                  code="INVALID_PAYLOAD")


@pytest.mark.parametrize("query", ["limit=0", "limit=201"])
def test_out_of_range_limit_is_rejected(client, query):
    _assert_error(client.get(f"/v1/notifications?{query}"), status=400,
                  code="INVALID_PAYLOAD")


def test_unknown_route_is_not_found(client):
    _assert_error(client.get("/v1/nope"), status=404, code="NOT_FOUND")


# ── Serialización ───────────────────────────────────────────────────────────

def test_notification_serializes_camel_case_and_iso_z():
    from datetime import UTC, datetime
    from uuid import UUID

    from app.schemas.notification import NotificationOut

    body = NotificationOut(
        id=UUID("11111111-2222-4333-8444-555555555555"),
        emergency_id=UUID("22222222-3333-4444-8555-666666666666"),
        recipient_id=None,
        channel="REALTIME", event_type="STATUS_CHANGED",
        payload={"status": "IN_PROGRESS"}, status="SENT",
        created_at=datetime(2026, 8, 17, 17, 0, 0, tzinfo=UTC),
        sent_at=datetime(2026, 8, 17, 17, 0, 1, tzinfo=UTC),
    ).model_dump(by_alias=True, mode="json")

    assert body["emergencyId"] == "22222222-3333-4444-8555-666666666666"
    assert body["eventType"] == "STATUS_CHANGED"
    assert body["createdAt"] == "2026-08-17T17:00:00Z"
    assert body["sentAt"] == "2026-08-17T17:00:01Z"
    assert body["recipientId"] is None


def test_channel_defaults_to_realtime():
    """El spec manda el canal explícito, pero los servicios internos no deberían
    tener que repetirlo en cada llamada."""
    from app.schemas.notification import NotificationCreate

    payload = NotificationCreate.model_validate({
        "emergencyId": "11111111-2222-4333-8444-555555555555",
        "eventType": "EMERGENCY_CREATED",
    })

    assert payload.channel.value == "REALTIME"
    assert payload.payload == {}

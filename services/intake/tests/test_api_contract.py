"""El envoltorio de respuesta de la §5 aplica a TODAS las respuestas.

Estos tests cubren los caminos que no tocan base de datos: validación, rutas y
métodos inexistentes, errores no controlados y propagación de X-Request-Id. La
sesión se sustituye por una falsa para que el servicio no necesite Postgres.
"""
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

CALI = {"latitude": 3.4516, "longitude": -76.532}


async def _fake_session():
    """Nunca se llega a usar: estas pruebas fallan antes de tocar la base."""
    yield None


app.dependency_overrides[get_session] = _fake_session


@pytest.fixture
def client():
    # raise_server_exceptions=False para que el handler global de Exception
    # produzca su respuesta en vez de propagar la excepcion al test.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _assert_error(response, *, status: int, code: str):
    assert response.status_code == status
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    # Un error nunca lleva `data`, y una respuesta de exito nunca lleva `error`.
    assert "data" not in body


def test_validation_error_uses_the_envelope(client):
    response = client.post(
        "/v1/emergencies",
        json={"type": "RESCUE", "city": "CALI", "location": CALI,
              "details": {"adults": 4}},
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_coordinates_outside_colombia_are_rejected(client):
    response = client.post(
        "/v1/emergencies",
        json={"type": "RESCUE", "city": "CALI",
              "location": {"latitude": 40.7, "longitude": -74.0}, "details": {}},
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_malformed_json_uses_the_envelope(client):
    response = client.post(
        "/v1/emergencies",
        content=b'{"type":',
        headers={"Content-Type": "application/json"},
    )
    _assert_error(response, status=400, code="INVALID_PAYLOAD")


def test_unknown_route_is_not_found(client):
    _assert_error(client.get("/v1/nope"), status=404, code="NOT_FOUND")


def test_method_not_allowed_is_a_client_error_not_a_server_error(client):
    """405 no puede salir como INTERNAL_ERROR / 500: el fallo es de quien llama."""
    _assert_error(client.delete("/v1/emergencies"), status=400, code="INVALID_PAYLOAD")


def test_invalid_uuid_in_path_is_rejected(client):
    _assert_error(client.get("/v1/emergencies/not-a-uuid"), status=400,
                  code="INVALID_PAYLOAD")


def test_unexpected_exception_becomes_internal_error_without_leaking(client):
    """Un fallo no previsto sale con el envoltorio y sin filtrar el detalle."""

    @app.get("/v1/_boom")
    async def _boom():
        raise RuntimeError("credenciales secretas en el mensaje")

    response = client.get("/v1/_boom")

    _assert_error(response, status=500, code="INTERNAL_ERROR")
    assert "credenciales" not in response.text


# Se usa una ruta que no toca la base: /health si abre conexion, y estas pruebas
# solo hablan del middleware de request id.

def test_request_id_is_echoed_back(client):
    response = client.get("/v1/nope", headers={"X-Request-Id": "abc-123"})
    assert response.headers["X-Request-Id"] == "abc-123"


def test_request_id_is_generated_when_absent(client):
    response = client.get("/v1/nope")
    assert response.headers.get("X-Request-Id")


def test_request_id_is_set_even_on_error_responses(client):
    """La trazabilidad no puede perderse justo cuando algo falla."""
    response = client.post("/v1/emergencies", json={"type": "NOPE"})
    assert response.status_code == 400
    assert response.headers.get("X-Request-Id")

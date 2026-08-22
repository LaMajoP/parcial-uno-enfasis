"""Prueba de aceptación end-to-end (§11 del spec).

Reproduce contra el gateway los once pasos de la demo:

    1-3.  Se crea una emergencia de rescate en Cali con 3 heridos.
    4-5.  Intake la recibe y calcula P1.
    6.    La guarda como TRIAGED.
    7-8.  Dispatch busca recurso disponible y asigna la ambulancia.
    9.    Geospatial la ve en su zona y la cuenta en el hotspot.
    10.   Notification registra el cambio a ASSIGNED.
    11.   El dashboard tiene todo lo que necesita para pintarla.

Se ejecuta contra la plataforma levantada, hablando **solo** con el gateway
(:8080), igual que el navegador: si algo solo funcionara llamando directamente a
los puertos de los servicios, esta prueba lo detectaría.

    make reset      # imprescindible: ver abajo
    make e2e

**Requiere el estado sembrado limpio.** El paso 8 del spec exige que se asigne
"Ambulancia Cali 01" concretamente, así que la prueba falla —correctamente— si
esa ambulancia ya está ocupada por una emergencia anterior: el auto-despacho
caería al segundo tipo preferido. `make e2e` hace el reset antes de ejecutarla.
"""
import os
import time

import httpx
import pytest

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")

# El auto-despacho es fire-and-forget: Intake responde 201 sin esperarlo, así que
# la asignación aparece unos instantes después de crear la emergencia.
ASSIGNMENT_TIMEOUT_SECONDS = 15.0
POLL_INTERVAL_SECONDS = 0.5

CALI = {"latitude": 3.4516, "longitude": -76.532}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=GATEWAY_URL, timeout=10.0) as client:
        yield client


def unwrap(response: httpx.Response) -> dict:
    """Comprueba el envoltorio de la §5 y devuelve `data`."""
    body = response.json()
    assert body["success"] is True, body
    return body["data"]


def wait_until(predicate, timeout: float = ASSIGNMENT_TIMEOUT_SECONDS):
    """Espera activa hasta que `predicate` devuelva algo verdadero."""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(POLL_INTERVAL_SECONDS)
    return last


# ── Paso 0: la plataforma está en pie ───────────────────────────────────────

def test_gateway_reports_all_services_healthy(client):
    data = unwrap(client.get("/health"))

    assert data["services"] == {
        "intake": "up",
        "dispatch": "up",
        "geospatial": "up",
        "notification": "up",
    }


def test_internal_endpoints_are_not_exposed(client):
    """El auto-despacho es servicio-a-servicio y no debe verse desde fuera."""
    response = client.post(
        "/v1/internal/dispatches/auto",
        json={"emergencyId": "11111111-2222-4333-8444-555555555555"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# ── El flujo completo ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def emergency(client) -> dict:
    """Pasos 1-6: crear la emergencia de la demo y comprobar el triage."""
    created = unwrap(
        client.post(
            "/v1/emergencies",
            json={
                "type": "RESCUE",
                "city": "CALI",
                "location": CALI,
                "details": {"injured": 3},
            },
        )
    )
    return created


def test_step_5_priority_is_p1(emergency):
    """Rescate con heridos: la regla base de RESCUE se mantiene en P1."""
    assert emergency["priority"] == "P1"


def test_step_6_emergency_is_stored_as_triaged(emergency):
    assert emergency["city"] == "CALI"
    assert emergency["type"] == "RESCUE"
    assert emergency["status"] == "TRIAGED"
    assert emergency["id"]
    assert emergency["createdAt"].endswith("Z")


def test_steps_7_and_8_a_resource_gets_assigned(client, emergency):
    """El auto-despacho asigna una ambulancia sin intervención del operador."""
    dispatches = wait_until(
        lambda: unwrap(
            client.get("/v1/dispatches", params={"emergencyId": emergency["id"]})
        )
    )

    assert dispatches, "el auto-despacho no asignó ningún recurso"
    dispatch = dispatches[0]
    assert dispatch["emergencyId"] == emergency["id"]
    assert dispatch["status"] == "ASSIGNED"
    # §6: para RESCUE el primer tipo preferido es AMBULANCE.
    assert dispatch["resourceType"] == "AMBULANCE"
    assert dispatch["resourceName"].startswith("Ambulancia Cali")


def test_step_10_emergency_moves_to_assigned(client, emergency):
    detail = wait_until(
        lambda: (
            data := unwrap(client.get(f"/v1/emergencies/{emergency['id']}"))
        )
        and data["status"] == "ASSIGNED"
        and data
    )

    assert detail["status"] == "ASSIGNED"
    assert detail["priority"] == "P1"


def test_step_9_geospatial_sees_it_in_the_zone(client, emergency):
    emergencies = unwrap(client.get("/v1/zones/CALI/emergencies"))
    ids = [item["id"] for item in emergencies]

    assert emergency["id"] in ids


def test_step_9_hotspot_includes_the_new_emergency(client):
    """La emergencia se creó en el centro de Cali, dentro del cluster sembrado."""
    hotspots = unwrap(client.get("/v1/zones/CALI/hotspots"))

    assert hotspots, "no se detectó ninguna zona de concentración en Cali"
    biggest = max(hotspots, key=lambda h: h["emergencyCount"])
    assert biggest["emergencyCount"] >= 8
    assert biggest["highestPriority"] == "P1"
    assert biggest["radiusMeters"] == 5000


def test_step_10_notifications_record_the_whole_chain(client, emergency):
    notifications = wait_until(
        lambda: (
            items := unwrap(
                client.get(
                    "/v1/notifications", params={"emergencyId": emergency["id"]}
                )
            )
        )
        and len(items) >= 3
        and items
    )

    events = {item["eventType"] for item in notifications}
    assert "EMERGENCY_CREATED" in events
    assert "RESOURCE_ASSIGNED" in events
    assert "STATUS_CHANGED" in events
    assert all(item["status"] == "SENT" for item in notifications)


def test_step_11_dashboard_has_everything_it_needs(client, emergency):
    """Lo que la tabla del operador pinta: la emergencia con su prioridad, su
    estado y el recurso que la atiende."""
    emergencies = unwrap(client.get("/v1/zones/CALI/emergencies"))
    dispatches = unwrap(client.get("/v1/dispatches"))
    resources = unwrap(client.get("/v1/resources", params={"city": "CALI"}))

    row = next(item for item in emergencies if item["id"] == emergency["id"])
    dispatch = next(
        item for item in dispatches if item["emergencyId"] == emergency["id"]
    )

    assert row["priority"] == "P1"
    assert row["city"] == "CALI"
    assert row["status"] == "ASSIGNED"
    assert dispatch["resourceName"]
    # El mapa necesita coordenadas tanto de la emergencia como de los recursos.
    assert row["location"]["latitude"] == pytest.approx(CALI["latitude"])
    assert all("location" in resource for resource in resources)


# ── Cierre del ciclo: en curso → resuelta ───────────────────────────────────

def test_dispatch_lifecycle_closes_the_emergency(client, emergency):
    dispatches = unwrap(
        client.get("/v1/dispatches", params={"emergencyId": emergency["id"]})
    )
    dispatch_id = dispatches[0]["id"]

    in_progress = unwrap(
        client.patch(f"/v1/dispatches/{dispatch_id}", json={"status": "IN_PROGRESS"})
    )
    assert in_progress["status"] == "IN_PROGRESS"

    completed = unwrap(
        client.patch(f"/v1/dispatches/{dispatch_id}", json={"status": "COMPLETED"})
    )
    assert completed["status"] == "COMPLETED"
    assert completed["completedAt"] is not None

    detail = wait_until(
        lambda: (data := unwrap(client.get(f"/v1/emergencies/{emergency['id']}")))
        and data["status"] == "RESOLVED"
        and data
    )
    assert detail["status"] == "RESOLVED"

    # El recurso vuelve a estar disponible para la siguiente emergencia.
    resources = unwrap(client.get("/v1/resources", params={"city": "CALI"}))
    released = next(
        r for r in resources if r["id"] == dispatches[0]["resourceId"]
    )
    assert released["status"] == "AVAILABLE"


# ── El contrato de errores también pasa por el gateway ──────────────────────

def test_invalid_payload_keeps_the_envelope_through_the_gateway(client):
    response = client.post(
        "/v1/emergencies",
        json={"type": "RESCUE", "city": "CALI", "location": CALI,
              "details": {"adults": 4}},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_PAYLOAD"


def test_coordinates_outside_colombia_are_rejected(client):
    response = client.post(
        "/v1/emergencies",
        json={"type": "RESCUE", "city": "CALI",
              "location": {"latitude": 40.7, "longitude": -74.0}, "details": {}},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PAYLOAD"


def test_unknown_emergency_is_not_found(client):
    response = client.get("/v1/emergencies/11111111-2222-4333-8444-555555555555")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

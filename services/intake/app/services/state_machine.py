"""Máquina de estados de una emergencia (§6 del spec).

    RECEIVED → TRIAGED → ASSIGNED → IN_PROGRESS → RESOLVED

`CANCELLED` es alcanzable desde cualquier estado no final. Cualquier otra
transición se rechaza con CONFLICT.
"""
from ..errors import ConflictError
from ..schemas.enums import EmergencyStatus

FINAL_STATES: frozenset[EmergencyStatus] = frozenset(
    {EmergencyStatus.RESOLVED, EmergencyStatus.CANCELLED}
)

ALLOWED_TRANSITIONS: dict[EmergencyStatus, frozenset[EmergencyStatus]] = {
    EmergencyStatus.RECEIVED: frozenset(
        {EmergencyStatus.TRIAGED, EmergencyStatus.CANCELLED}
    ),
    EmergencyStatus.TRIAGED: frozenset(
        {EmergencyStatus.ASSIGNED, EmergencyStatus.CANCELLED}
    ),
    EmergencyStatus.ASSIGNED: frozenset(
        {EmergencyStatus.IN_PROGRESS, EmergencyStatus.CANCELLED}
    ),
    EmergencyStatus.IN_PROGRESS: frozenset(
        {EmergencyStatus.RESOLVED, EmergencyStatus.CANCELLED}
    ),
    EmergencyStatus.RESOLVED: frozenset(),
    EmergencyStatus.CANCELLED: frozenset(),
}


def can_transition(current: EmergencyStatus, target: EmergencyStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: EmergencyStatus, target: EmergencyStatus) -> None:
    """Valida la transición o lanza ConflictError (409), como exige la §6."""
    if not can_transition(current, target):
        raise ConflictError(
            f"Invalid status transition from {current.value} to {target.value}"
        )

"""Máquina de estados de una asignación.

El spec fija la de la *emergencia* (§6) pero no la de la *asignación*: solo dice
que `PATCH /v1/dispatches/{id}` cambia el estado y qué debe pasar al llegar a
COMPLETED. El grafo de abajo es una decisión de diseño de este servicio, hecha
para que sea coherente con la de la emergencia:

    ASSIGNED → ACCEPTED → IN_PROGRESS → COMPLETED

con CANCELLED alcanzable desde cualquier estado no final, y ACCEPTED opcional
(se puede ir de ASSIGNED directo a IN_PROGRESS).

Cada estado de la asignación arrastra el de la emergencia, y ahí está el motivo
de que ACCEPTED no la mueva: la emergencia no tiene un estado equivalente.
"""
from ..errors import ConflictError
from ..schemas.enums import AssignmentStatus as A
from ..schemas.enums import EmergencyStatus

FINAL_STATES: frozenset[A] = frozenset({A.COMPLETED, A.CANCELLED})

ALLOWED_TRANSITIONS: dict[A, frozenset[A]] = {
    A.ASSIGNED: frozenset({A.ACCEPTED, A.IN_PROGRESS, A.CANCELLED}),
    A.ACCEPTED: frozenset({A.IN_PROGRESS, A.CANCELLED}),
    A.IN_PROGRESS: frozenset({A.COMPLETED, A.CANCELLED}),
    A.COMPLETED: frozenset(),
    A.CANCELLED: frozenset(),
}

# Qué estado de la emergencia corresponde a cada estado de la asignación.
# ACCEPTED y CANCELLED no mueven la emergencia: el primero no tiene equivalente,
# y cancelar un despacho no cancela la emergencia —solo la deja sin recurso, para
# que el operador pueda reasignarla—.
EMERGENCY_STATUS_FOR: dict[A, EmergencyStatus | None] = {
    A.ASSIGNED: EmergencyStatus.ASSIGNED,
    A.ACCEPTED: None,
    A.IN_PROGRESS: EmergencyStatus.IN_PROGRESS,
    A.COMPLETED: EmergencyStatus.RESOLVED,
    A.CANCELLED: None,
}

# Estados en los que el recurso vuelve a estar libre.
RELEASES_RESOURCE: frozenset[A] = frozenset({A.COMPLETED, A.CANCELLED})


def can_transition(current: A, target: A) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: A, target: A) -> None:
    if not can_transition(current, target):
        raise ConflictError(
            f"Invalid dispatch status transition from {current.value} to {target.value}"
        )

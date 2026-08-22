"""Máquina de estados de la asignación y sus efectos acoplados."""
import pytest

from app.errors import ConflictError, ErrorCode
from app.schemas.enums import AssignmentStatus as A
from app.schemas.enums import EmergencyStatus as E
from app.services.state_machine import (
    ALLOWED_TRANSITIONS,
    EMERGENCY_STATUS_FOR,
    FINAL_STATES,
    RELEASES_RESOURCE,
    assert_transition,
    can_transition,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (A.ASSIGNED, A.ACCEPTED),
        (A.ASSIGNED, A.IN_PROGRESS),  # ACCEPTED es opcional
        (A.ACCEPTED, A.IN_PROGRESS),
        (A.IN_PROGRESS, A.COMPLETED),
    ],
)
def test_forward_transitions_are_allowed(current, target):
    assert can_transition(current, target)


@pytest.mark.parametrize("current", [A.ASSIGNED, A.ACCEPTED, A.IN_PROGRESS])
def test_cancelled_reachable_from_any_non_final_state(current):
    assert can_transition(current, A.CANCELLED)


@pytest.mark.parametrize("final", sorted(FINAL_STATES))
@pytest.mark.parametrize("target", list(A))
def test_final_states_are_final(final, target):
    assert not can_transition(final, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (A.ASSIGNED, A.COMPLETED),     # se salta la ejecucion
        (A.ACCEPTED, A.COMPLETED),
        (A.IN_PROGRESS, A.ASSIGNED),   # hacia atras
        (A.IN_PROGRESS, A.ACCEPTED),
        (A.COMPLETED, A.IN_PROGRESS),  # reabrir
        (A.CANCELLED, A.ASSIGNED),     # revivir
    ],
)
def test_invalid_transitions_raise_conflict(current, target):
    with pytest.raises(ConflictError) as exc_info:
        assert_transition(current, target)

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert exc_info.value.status_code == 409


@pytest.mark.parametrize("state", list(A))
def test_no_state_transitions_to_itself(state):
    assert not can_transition(state, state)


def test_every_status_has_transitions_and_effects_declared():
    assert set(ALLOWED_TRANSITIONS) == set(A)
    assert set(EMERGENCY_STATUS_FOR) == set(A)


# ── Efectos acoplados al estado de la emergencia ────────────────────────────

def test_completed_resolves_the_emergency_and_frees_the_resource():
    assert EMERGENCY_STATUS_FOR[A.COMPLETED] is E.RESOLVED
    assert A.COMPLETED in RELEASES_RESOURCE


def test_cancelled_frees_the_resource_without_touching_the_emergency():
    """Cancelar un despacho no cancela la emergencia: la deja reasignable."""
    assert EMERGENCY_STATUS_FOR[A.CANCELLED] is None
    assert A.CANCELLED in RELEASES_RESOURCE


def test_accepted_does_not_move_the_emergency():
    """La emergencia no tiene un estado equivalente a ACCEPTED."""
    assert EMERGENCY_STATUS_FOR[A.ACCEPTED] is None


def test_in_progress_moves_the_emergency_so_it_can_later_be_resolved():
    """Sin este paso, COMPLETED intentaría ASSIGNED → RESOLVED, que la máquina de
    estados de la emergencia rechaza con CONFLICT."""
    assert EMERGENCY_STATUS_FOR[A.IN_PROGRESS] is E.IN_PROGRESS


def test_active_states_never_free_the_resource():
    for state in (A.ASSIGNED, A.ACCEPTED, A.IN_PROGRESS):
        assert state not in RELEASES_RESOURCE


def test_emergency_status_chain_is_reachable_in_the_emergency_machine():
    """Los estados que Dispatch pide a Intake, en el orden en que los pide, tienen
    que formar un camino válido de la máquina de la §6."""
    chain = [
        EMERGENCY_STATUS_FOR[A.ASSIGNED],
        EMERGENCY_STATUS_FOR[A.IN_PROGRESS],
        EMERGENCY_STATUS_FOR[A.COMPLETED],
    ]
    assert chain == [E.ASSIGNED, E.IN_PROGRESS, E.RESOLVED]

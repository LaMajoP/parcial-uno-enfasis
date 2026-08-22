"""Máquina de estados de la §6: el camino feliz, CANCELLED desde cualquier estado
no final, y el rechazo con CONFLICT de todo lo demás.
"""
import pytest

from app.errors import ErrorCode
from app.errors import ConflictError
from app.schemas.enums import EmergencyStatus as S
from app.services.state_machine import (
    ALLOWED_TRANSITIONS,
    FINAL_STATES,
    assert_transition,
    can_transition,
)

HAPPY_PATH = [
    (S.RECEIVED, S.TRIAGED),
    (S.TRIAGED, S.ASSIGNED),
    (S.ASSIGNED, S.IN_PROGRESS),
    (S.IN_PROGRESS, S.RESOLVED),
]


@pytest.mark.parametrize(("current", "target"), HAPPY_PATH)
def test_happy_path_transitions_are_allowed(current, target):
    assert can_transition(current, target)


@pytest.mark.parametrize(
    "current", [S.RECEIVED, S.TRIAGED, S.ASSIGNED, S.IN_PROGRESS]
)
def test_cancelled_is_reachable_from_any_non_final_state(current):
    assert can_transition(current, S.CANCELLED)


@pytest.mark.parametrize("final", sorted(FINAL_STATES))
@pytest.mark.parametrize("target", list(S))
def test_final_states_allow_no_transition(final, target):
    assert not can_transition(final, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.RECEIVED, S.ASSIGNED),      # se salta el triage
        (S.RECEIVED, S.RESOLVED),      # se salta todo
        (S.TRIAGED, S.IN_PROGRESS),    # se salta la asignacion
        (S.ASSIGNED, S.RESOLVED),      # se salta la ejecucion
        (S.IN_PROGRESS, S.ASSIGNED),   # hacia atras
        (S.TRIAGED, S.RECEIVED),       # hacia atras
        (S.RESOLVED, S.IN_PROGRESS),   # reabrir una resuelta
        (S.CANCELLED, S.TRIAGED),      # revivir una cancelada
    ],
)
def test_invalid_transitions_raise_conflict(current, target):
    with pytest.raises(ConflictError) as exc_info:
        assert_transition(current, target)

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert exc_info.value.status_code == 409


@pytest.mark.parametrize("state", list(S))
def test_no_state_transitions_to_itself(state):
    assert not can_transition(state, state)


def test_every_status_has_an_entry():
    """Si se añade un estado al enum y no a la tabla, esto lo detecta antes de que
    reviente en runtime con un KeyError."""
    assert set(ALLOWED_TRANSITIONS) == set(S)


def test_transition_graph_matches_spec_exactly():
    assert ALLOWED_TRANSITIONS == {
        S.RECEIVED: frozenset({S.TRIAGED, S.CANCELLED}),
        S.TRIAGED: frozenset({S.ASSIGNED, S.CANCELLED}),
        S.ASSIGNED: frozenset({S.IN_PROGRESS, S.CANCELLED}),
        S.IN_PROGRESS: frozenset({S.RESOLVED, S.CANCELLED}),
        S.RESOLVED: frozenset(),
        S.CANCELLED: frozenset(),
    }

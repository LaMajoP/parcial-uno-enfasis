"""Circuit breaker liviano para dependencias síncronas de Intake.

El estado vive en el proceso de Lambda. Eso protege cada entorno de ejecución
caliente sin convertir el circuito en una dependencia adicional de la ruta de
emergencias. El Kill Switch global vive en AppConfig y complementa este control
local cuando se necesita aislar Dispatch de inmediato.
"""
from __future__ import annotations

from enum import StrEnum
from threading import Lock
from time import monotonic
from typing import Callable


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Abre tras varios fallos y permite una única sonda de recuperación."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 60.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._half_open_probe_in_flight = False
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    def allow_request(self) -> bool:
        """Indica si la llamada puede salir hacia la dependencia."""
        with self._lock:
            if self._state is CircuitState.CLOSED:
                return True

            if self._state is CircuitState.OPEN:
                assert self._opened_at is not None
                elapsed = self._clock() - self._opened_at
                if elapsed < self.recovery_timeout_seconds:
                    return False
                self._state = CircuitState.HALF_OPEN

            if self._half_open_probe_in_flight:
                return False

            self._half_open_probe_in_flight = True
            return True

    def record_success(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = None
            self._half_open_probe_in_flight = False

    def record_failure(self) -> None:
        with self._lock:
            self._half_open_probe_in_flight = False
            if self._state is CircuitState.HALF_OPEN:
                self._open()
                return

            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._open()

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()


_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = Lock()


def get_circuit_breaker(dependency: str) -> CircuitBreaker:
    """Obtiene un circuito estable por dependencia durante la vida del proceso."""
    with _breakers_lock:
        if dependency not in _breakers:
            _breakers[dependency] = CircuitBreaker()
        return _breakers[dependency]


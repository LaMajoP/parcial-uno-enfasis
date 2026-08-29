from app.clients.circuit_breaker import CircuitBreaker, CircuitState


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_opens_after_threshold_and_rejects_calls_until_recovery_window():
    clock = Clock()
    breaker = CircuitBreaker(
        failure_threshold=3, recovery_timeout_seconds=60, clock=clock
    )

    for _ in range(3):
        assert breaker.allow_request()
        breaker.record_failure()

    assert breaker.state is CircuitState.OPEN
    assert not breaker.allow_request()

    clock.now = 59.9
    assert not breaker.allow_request()


def test_successful_half_open_probe_closes_and_resets_circuit():
    clock = Clock()
    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout_seconds=10, clock=clock
    )
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN

    clock.now = 10
    assert breaker.allow_request()
    assert breaker.state is CircuitState.HALF_OPEN
    # Mientras la sonda está en vuelo no se permite una segunda llamada.
    assert not breaker.allow_request()

    breaker.record_success()
    assert breaker.state is CircuitState.CLOSED
    assert breaker.allow_request()


def test_failed_half_open_probe_reopens_circuit():
    clock = Clock()
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=5, clock=clock)
    breaker.record_failure()

    clock.now = 5
    assert breaker.allow_request()
    breaker.record_failure()

    assert breaker.state is CircuitState.OPEN
    assert not breaker.allow_request()

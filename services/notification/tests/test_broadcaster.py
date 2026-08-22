"""Difusor SSE en proceso.

Lo que importa aquí es que un cliente lento nunca bloquee al publicador ni haga
crecer la memoria sin límite, y que las bajas se den siempre —también cuando el
cliente se corta a mitad—.
"""

import pytest

from app.services.broadcaster import Broadcaster


async def test_publish_without_subscribers_is_a_noop():
    broadcaster = Broadcaster(queue_size=10)
    assert broadcaster.publish({"id": 1}) == 0


async def test_event_reaches_every_subscriber():
    broadcaster = Broadcaster(queue_size=10)

    async with broadcaster.subscribe() as first, broadcaster.subscribe() as second:
        delivered = broadcaster.publish({"id": 1})

        assert delivered == 2
        assert await first.get() == {"id": 1}
        assert await second.get() == {"id": 1}


async def test_events_keep_their_order():
    broadcaster = Broadcaster(queue_size=10)

    async with broadcaster.subscribe() as queue:
        for i in range(5):
            broadcaster.publish({"id": i})

        assert [(await queue.get())["id"] for _ in range(5)] == [0, 1, 2, 3, 4]


async def test_subscriber_is_removed_on_exit():
    broadcaster = Broadcaster(queue_size=10)

    async with broadcaster.subscribe():
        assert broadcaster.subscriber_count == 1

    assert broadcaster.subscriber_count == 0


async def test_subscriber_is_removed_even_if_the_client_crashes():
    """Sin esto, cada desconexión abrupta dejaría una cola huérfana acumulando
    eventos para siempre."""
    broadcaster = Broadcaster(queue_size=10)

    with pytest.raises(RuntimeError):
        async with broadcaster.subscribe():
            raise RuntimeError("cliente cortado a mitad")

    assert broadcaster.subscriber_count == 0


async def test_slow_subscriber_never_blocks_the_publisher():
    """Con la cola llena, publicar sigue siendo inmediato: se descarta lo más
    viejo en vez de esperar a que el cliente lento consuma.

    `publish` es síncrona a propósito —usa put_nowait, no await—, así que basta
    con llamarla: si bloqueara, este test no terminaría.
    """
    broadcaster = Broadcaster(queue_size=3)

    async with broadcaster.subscribe() as queue:
        for i in range(10):
            broadcaster.publish({"id": i})

        assert queue.qsize() == 3
        # Sobreviven los tres más recientes.
        assert [(await queue.get())["id"] for _ in range(3)] == [7, 8, 9]


async def test_one_subscriber_filling_up_does_not_affect_the_others():
    """El que se satura pierde eventos; el que va al día no pierde ninguno."""
    broadcaster = Broadcaster(queue_size=2)

    async with broadcaster.subscribe() as slow, broadcaster.subscribe() as fast:
        received = []
        for i in range(5):
            broadcaster.publish({"id": i})
            # El rápido consume en cuanto llega, así que su cola nunca se llena.
            received.append((await fast.get())["id"])

        assert received == [0, 1, 2, 3, 4]
        # El lento no consumió nada: se queda solo con los dos últimos.
        assert slow.qsize() == 2
        assert [(await slow.get())["id"] for _ in range(2)] == [3, 4]

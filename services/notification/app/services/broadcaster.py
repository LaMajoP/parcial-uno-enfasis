"""Difusión en proceso de las notificaciones hacia los clientes SSE.

Cada cliente conectado tiene su propia cola. Publicar es copiar el evento a todas
las colas; ninguna se espera, así que un cliente lento no frena al servicio ni al
resto de suscriptores: se le descartan los eventos más viejos y se sigue.

**Esto es de la fase local y no viaja a Lambda.** Vive en la memoria del proceso,
así que solo funciona con un worker, y una conexión SSE es de larga duración —dos
cosas incompatibles con el modelo de ejecución de Lambda—. En la fase Supabase lo
reemplaza Realtime, que es exactamente el mismo contrato visto desde el navegador.
"""
import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from ..config import get_settings

logger = logging.getLogger(__name__)


class Broadcaster:
    def __init__(self, queue_size: int) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._queue_size = queue_size

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def publish(self, event: dict[str, Any]) -> int:
        """Reparte el evento. Devuelve a cuántos suscriptores llegó."""
        delivered = 0
        for queue in self._subscribers:
            if queue.full():
                # Cliente que no consume a la velocidad a la que se publica: se
                # tira su evento más viejo. Preferimos perder historia antigua
                # antes que bloquear al publicador o dejar crecer la memoria.
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:  # pragma: no cover - carrera improbable
                    pass
            queue.put_nowait(event)
            delivered += 1
        return delivered

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        """Alta y baja garantizadas del suscriptor, pase lo que pase."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.add(queue)
        logger.info("SSE client connected", extra={"subscribers": len(self._subscribers)})
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)
            logger.info(
                "SSE client disconnected", extra={"subscribers": len(self._subscribers)}
            )


broadcaster = Broadcaster(get_settings().sse_queue_size)

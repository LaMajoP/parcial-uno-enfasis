"""Logs estructurados en JSON a stdout, con request_id, service y level.

En AWS los recoge CloudWatch tal cual. El request_id viaja en un ContextVar para
que cualquier log emitido durante una petición lo lleve sin tener que pasarlo por
parámetro hasta el último rincón del código.
"""
import json
import logging
import sys
from contextvars import ContextVar

from .config import get_settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Atributos propios de LogRecord: todo lo demás que traiga el record es contexto
# que el llamante añadió con `extra=` y que queremos volcar en el JSON.
_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"asctime", "message", "taskName"}


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": self.service,
            "request_id": request_id_var.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(settings.service_name))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # Uvicorn trae sus propios handlers con formato de texto: se los quitamos para
    # que sus logs salgan tambien como JSON por el handler de arriba.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

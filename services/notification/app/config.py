"""Configuración local por entorno y de producción desde Parameter Store."""
import json
import os
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


_RUNTIME_CONFIG_PARAMETER = "/emergency-platform/prod/services/notification/runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    service_name: str = "notification"
    log_level: str = "INFO"


    # Notification no llama a nadie: solo registra y difunde.
    http_timeout_seconds: float = 3.0

    # Origen del navegador autorizado. None en local a proposito: alli las
    # cabeceras CORS las pone el gateway Nginx y duplicarlas romperia la peticion.
    # Ver el comentario extenso en services/intake/app/config.py.
    allowed_origin: str | None = None

    default_limit: int = 50

    # SSE: cada cuántos segundos se manda un comentario de keep-alive. Sin él, un
    # proxy intermedio puede cerrar una conexión que lleva rato en silencio.
    sse_heartbeat_seconds: float = 15.0
    # Cuántos eventos se acumulan por cliente antes de descartar los más viejos.
    sse_queue_size: int = 100


@lru_cache
def get_settings() -> Settings:
    if not os.getenv("AWS_EXECUTION_ENV"):
        return Settings()

    response = boto3.client("ssm").get_parameter(
        Name=_RUNTIME_CONFIG_PARAMETER,
        WithDecryption=True,
    )
    values = json.loads(response["Parameter"]["Value"])
    if not isinstance(values, dict):
        raise RuntimeError("Notification runtime configuration must be a JSON object")
    return Settings(**values)

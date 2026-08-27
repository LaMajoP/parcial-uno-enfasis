"""Configuración del servicio, siempre desde variables de entorno."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "notification"
    log_level: str = "INFO"


    # Notification no llama a nadie: solo registra y difunde.
    http_timeout_seconds: float = 3.0

    default_limit: int = 50

    # SSE: cada cuántos segundos se manda un comentario de keep-alive. Sin él, un
    # proxy intermedio puede cerrar una conexión que lleva rato en silencio.
    sse_heartbeat_seconds: float = 15.0
    # Cuántos eventos se acumulan por cliente antes de descartar los más viejos.
    sse_queue_size: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()

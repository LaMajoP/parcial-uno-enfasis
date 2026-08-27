"""Configuración del servicio, siempre desde variables de entorno."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "dispatch"
    log_level: str = "INFO"

    service_transport: Literal["http", "lambda"] = "http"

    # Desarrollo local
    intake_url: str | None = None
    notification_url: str | None = None

    # Producción AWS
    intake_function_name: str | None = None
    notification_function_name: str | None = None

    http_timeout_seconds: float = 3.0

    default_radius_meters: int = 10_000
    default_limit: int = 10
    auto_dispatch_radius_meters: int = 10_000


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Configuración del servicio, siempre desde variables de entorno.

En AWS estas variables vendrán de Secrets Manager en vez del archivo .env, por eso
no hay ningún valor de configuración embebido en el código.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "intake"
    log_level: str = "INFO"

    service_transport: Literal["http", "lambda"] = "http"

    # Desarrollo local
    notification_url: str | None = None
    dispatch_url: str | None = None

    # Producción AWS
    notification_function_name: str | None = None
    dispatch_function_name: str | None = None

    http_timeout_seconds: float = 3.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

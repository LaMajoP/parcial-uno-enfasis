"""Configuración del servicio, siempre desde variables de entorno.

En AWS estas variables vendrán de Secrets Manager en vez del archivo .env, por eso
no hay ningún valor de configuración embebido en el código.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "intake"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://emergency:emergency@postgres:5432/emergency"

    # Servicios a los que llama Intake. Ambas llamadas son fire-and-forget.
    notification_url: str = "http://notification:8000"
    dispatch_url: str = "http://dispatch:8000"
    http_timeout_seconds: float = 3.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

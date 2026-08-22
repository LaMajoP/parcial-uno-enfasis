"""Configuración del servicio, siempre desde variables de entorno."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "dispatch"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://emergency:emergency@postgres:5432/emergency"

    # Dispatch no puede leer el esquema `intake`: pide los datos de la emergencia
    # por HTTP y le comunica los cambios de estado por HTTP.
    intake_url: str = "http://intake:8000"
    notification_url: str = "http://notification:8000"
    http_timeout_seconds: float = 3.0

    # Valores por defecto de la búsqueda de recursos (§5.2).
    default_radius_meters: int = 10_000
    default_limit: int = 10
    # Radio del auto-despacho. Si dentro de él no hay ningún recurso del tipo
    # preferido, la búsqueda cae al resto de la ciudad sin límite de distancia.
    auto_dispatch_radius_meters: int = 10_000


@lru_cache
def get_settings() -> Settings:
    return Settings()

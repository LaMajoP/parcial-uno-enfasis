"""Configuración del servicio, siempre desde variables de entorno."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "geospatial"
    log_level: str = "INFO"


    http_timeout_seconds: float = 3.0

    default_zone_limit: int = 50
    default_hotspot_radius_meters: int = 5_000
    # Emergencias mínimas para que un grupo cuente como hotspot. Con 2, cualquier
    # par de reportes cercanos sería un "punto caliente" y el mapa se llenaría de
    # ruido; 3 es el mínimo que ya describe una concentración.
    hotspot_min_points: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()

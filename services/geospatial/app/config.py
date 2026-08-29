"""Configuración local por entorno y de producción desde Parameter Store."""
import json
import os
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


_RUNTIME_CONFIG_PARAMETER = "/emergency-platform/prod/services/geospatial/runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

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
    if not os.getenv("AWS_EXECUTION_ENV"):
        return Settings()

    response = boto3.client("ssm").get_parameter(
        Name=_RUNTIME_CONFIG_PARAMETER,
        WithDecryption=True,
    )
    values = json.loads(response["Parameter"]["Value"])
    if not isinstance(values, dict):
        raise RuntimeError("Geospatial runtime configuration must be a JSON object")
    return Settings(**values)

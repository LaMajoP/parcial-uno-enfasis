"""Configuración local por entorno y de producción desde Parameter Store."""
import json
import os
from functools import lru_cache
from typing import Literal

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


_RUNTIME_CONFIG_PARAMETER = "/emergency-platform/prod/services/dispatch/runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

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

    # Origen del navegador autorizado. None en local a proposito: alli las
    # cabeceras CORS las pone el gateway Nginx y duplicarlas romperia la peticion.
    # Ver el comentario extenso en services/intake/app/config.py.
    allowed_origin: str | None = None

    default_radius_meters: int = 10_000
    default_limit: int = 10
    auto_dispatch_radius_meters: int = 10_000


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
        raise RuntimeError("Dispatch runtime configuration must be a JSON object")
    return Settings(**values)

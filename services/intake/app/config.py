"""Configuración local por entorno y de producción desde Parameter Store."""
import json
import os
from functools import lru_cache
from typing import Literal

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


_RUNTIME_CONFIG_PARAMETER = "/emergency-platform/prod/services/intake/runtime"


class Settings(BaseSettings):
    # Docker Compose inyecta los valores locales. Nunca se carga un archivo .env.
    model_config = SettingsConfigDict(extra="ignore")

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
    if not os.getenv("AWS_EXECUTION_ENV"):
        return Settings()

    response = boto3.client("ssm").get_parameter(
        Name=_RUNTIME_CONFIG_PARAMETER,
        WithDecryption=True,
    )
    values = json.loads(response["Parameter"]["Value"])
    if not isinstance(values, dict):
        raise RuntimeError("Intake runtime configuration must be a JSON object")
    return Settings(**values)

import os
from functools import lru_cache

import boto3


@lru_cache(maxsize=1)
def get_database_url() -> str:
    """Obtiene la URL de PostgreSQL sin guardar secretos en el código."""

    # Desarrollo local: Docker Compose proporciona DATABASE_URL.
    if database_url := os.getenv("DATABASE_URL"):
        return database_url

    # Producción: Lambda recibe solamente el NOMBRE del parámetro.
    parameter_name = os.getenv("DATABASE_URL_PARAMETER")

    if not parameter_name:
        raise RuntimeError(
            "DATABASE_URL or DATABASE_URL_PARAMETER must be configured"
        )

    ssm = boto3.client("ssm")

    response = ssm.get_parameter(
        Name=parameter_name,
        WithDecryption=True,
    )

    return response["Parameter"]["Value"]

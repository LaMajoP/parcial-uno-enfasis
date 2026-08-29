import json
import os
from functools import lru_cache

import boto3


_DATABASE_SECRET_ID = "emergency-platform/prod/database"


def _database_url_from_secret(secret: str) -> str:
    try:
        value = json.loads(secret)
    except json.JSONDecodeError:
        return secret
    if not isinstance(value, dict):
        raise RuntimeError("Database secret must be a URL or JSON object")
    for key in ("database_url", "DATABASE_URL", "url"):
        if isinstance(value.get(key), str) and value[key]:
            return value[key]
    raise RuntimeError("Database secret does not contain database_url")


@lru_cache(maxsize=1)
def get_database_url() -> str:
    """Obtiene la URL de PostgreSQL sin guardar secretos en el código."""

    if not os.getenv("AWS_EXECUTION_ENV") and (database_url := os.getenv("DATABASE_URL")):
        return database_url

    response = boto3.client("secretsmanager").get_secret_value(
        SecretId=_DATABASE_SECRET_ID
    )
    secret = response.get("SecretString")
    if not isinstance(secret, str) or not secret:
        raise RuntimeError("Database secret has no SecretString")
    return _database_url_from_secret(secret)

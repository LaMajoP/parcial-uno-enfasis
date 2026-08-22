"""Base de todos los modelos de la API.

La API habla camelCase y la base de datos snake_case. El alias generator hace esa
traducción en un solo sitio: el código Python usa siempre snake_case.
"""
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        # Un payload con campos que no existen en el modelo es un error, no algo
        # que se ignora en silencio: asi un `details` que no corresponde al tipo
        # de emergencia se rechaza con INVALID_PAYLOAD.
        extra="forbid",
    )


def to_iso_z(value: datetime) -> str:
    """Formatea en UTC con sufijo Z, como los ejemplos del spec.

    Pydantic serializaria `+00:00`; el contrato muestra `2026-08-17T17:00:00Z`.
    """
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")

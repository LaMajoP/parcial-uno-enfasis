"""Acceso a base de datos del servicio Geospatial.

Aquí está la **única lectura cruzada permitida de toda la plataforma**:
`intake.emergencies` se declara en modo solo lectura para poder agregar por zona y
calcular hotspots con PostGIS. El permiso se concede con el rol `geo_reader`
(007_grants.sql), que tiene revocados INSERT/UPDATE/DELETE de forma explícita: si
este servicio intentara escribir ahí, la base de datos se lo impediría.

Escribe únicamente en su propio esquema, `geo`.
"""
from collections.abc import AsyncIterator

from geoalchemy2 import Geography
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    MetaData,
    Table,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .schemas.enums import City, EmergencyStatus, EmergencyType, Priority
from .secrets import get_database_url

# Dos MetaData porque son dos esquemas distintos con dueños distintos.
geo_metadata = MetaData(schema="geo")
intake_metadata = MetaData(schema="intake")


def _pg_enum(python_enum: type, name: str) -> Enum:
    return Enum(
        python_enum,
        name=name,
        schema="public",
        create_type=False,
        values_callable=lambda e: [member.value for member in e],
    )


# SOLO LECTURA. Ninguna sentencia de escritura debe apuntar a esta tabla.
emergencies = Table(
    "emergencies",
    intake_metadata,
    Column("id", Uuid, primary_key=True),
    Column("type", _pg_enum(EmergencyType, "emergency_type"), nullable=False),
    Column("priority", _pg_enum(Priority, "priority_type"), nullable=False),
    Column("city", _pg_enum(City, "city_type"), nullable=False),
    Column("status", _pg_enum(EmergencyStatus, "emergency_status"), nullable=False),
    Column("latitude", Float, nullable=False),
    Column("longitude", Float, nullable=False),
    Column("location", Geography("POINT", 4326), nullable=False),
    Column("details", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

hotspots = Table(
    "hotspots",
    geo_metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    Column("city", _pg_enum(City, "city_type"), nullable=False),
    # A diferencia de emergencies y resources, esta tabla no tiene latitude ni
    # longitude: el centro es un dato calculado, así que aquí sí se escribe la
    # geografía directamente y no hay trigger que la derive.
    Column("center", Geography("POINT", 4326), nullable=False),
    Column("radius_meters", Integer, nullable=False),
    Column("emergency_count", Integer, nullable=False),
    Column("highest_priority", _pg_enum(Priority, "priority_type"), nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
)

engine = create_async_engine(
    get_database_url(), pool_pre_ping=True, pool_size=5, max_overflow=5
)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

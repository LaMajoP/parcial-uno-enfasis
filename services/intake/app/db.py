"""Acceso a base de datos: engine async, sesión por request y tabla de emergencias.

Intake es dueño del esquema `intake` y no toca ningún otro: esa es la regla de
autonomía entre microservicios del spec.
"""
from collections.abc import AsyncIterator

from geoalchemy2 import Geography
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    MetaData,
    String,
    Table,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .schemas.enums import City, EmergencyStatus, EmergencyType, Priority
from .secrets import get_database_url

metadata = MetaData(schema="intake")


def _pg_enum(python_enum: type, name: str) -> Enum:
    """Enum de Postgres ya existente: lo crean las migraciones, no la aplicación."""
    return Enum(
        python_enum,
        name=name,
        schema="public",
        create_type=False,
        values_callable=lambda e: [member.value for member in e],
    )


emergencies = Table(
    "emergencies",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    Column("type", _pg_enum(EmergencyType, "emergency_type"), nullable=False),
    Column("priority", _pg_enum(Priority, "priority_type"), nullable=False),
    Column("city", _pg_enum(City, "city_type"), nullable=False),
    Column("status", _pg_enum(EmergencyStatus, "emergency_status"), nullable=False),
    Column("latitude", Float, nullable=False),
    Column("longitude", Float, nullable=False),
    # La escribe el trigger emergencies_sync_location a partir de latitude y
    # longitude. La aplicación NUNCA la manda: por eso no aparece en ningún INSERT.
    Column("location", Geography("POINT", 4326), nullable=False),
    Column("details", JSONB, nullable=False),
    Column("citizen_id", Uuid, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

engine = create_async_engine(
    get_database_url(),
    # `pool_pre_ping` evita servir una conexión que el servidor ya cerró, algo
    # habitual cuando el contenedor lleva rato ocioso.
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI: una sesión por request, con commit o rollback."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

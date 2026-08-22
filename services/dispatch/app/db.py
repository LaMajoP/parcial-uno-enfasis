"""Acceso a base de datos del servicio Dispatch.

Dispatch es dueño del esquema `dispatch` y solo de ese: la tabla
`intake.emergencies` no está declarada aquí ni puede estarlo. Los datos de una
emergencia se piden a Intake por HTTP.
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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .schemas.enums import AssignmentStatus, City, ResourceStatus, ResourceType

metadata = MetaData(schema="dispatch")


def _pg_enum(python_enum: type, name: str) -> Enum:
    """Enum de Postgres ya existente: lo crean las migraciones, no la aplicación."""
    return Enum(
        python_enum,
        name=name,
        schema="public",
        create_type=False,
        values_callable=lambda e: [member.value for member in e],
    )


resources = Table(
    "resources",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    Column("name", String(120), nullable=False),
    Column("type", _pg_enum(ResourceType, "resource_type"), nullable=False),
    Column("city", _pg_enum(City, "city_type"), nullable=False),
    Column("status", _pg_enum(ResourceStatus, "resource_status"), nullable=False),
    Column("latitude", Float, nullable=False),
    Column("longitude", Float, nullable=False),
    # La mantiene el trigger resources_sync_location. La aplicación no la escribe.
    Column("location", Geography("POINT", 4326), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

assignments = Table(
    "assignments",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    # Sin ForeignKey: apunta a intake.emergencies, que es de otro servicio.
    Column("emergency_id", Uuid, nullable=False),
    Column("resource_id", Uuid, nullable=False),
    Column("status", _pg_enum(AssignmentStatus, "assignment_status"), nullable=False),
    Column("assigned_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
)

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Una sesión por request, con commit al salir o rollback si algo falla."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

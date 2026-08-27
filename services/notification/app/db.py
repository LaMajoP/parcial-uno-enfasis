"""Acceso a base de datos del servicio Notification.

Es dueño del esquema `notification` y solo de ese.
"""
from collections.abc import AsyncIterator

from sqlalchemy import Column, DateTime, Enum, MetaData, Table, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .schemas.notification import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)
from .secrets import get_database_url

metadata = MetaData(schema="notification")


def _pg_enum(python_enum: type, name: str) -> Enum:
    return Enum(
        python_enum,
        name=name,
        schema="public",
        create_type=False,
        values_callable=lambda e: [member.value for member in e],
    )


notifications = Table(
    "notifications",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    # Sin ForeignKey: apunta a intake.emergencies, de otro servicio.
    Column("emergency_id", Uuid, nullable=False),
    Column("recipient_id", Uuid, nullable=True),
    Column("channel", _pg_enum(NotificationChannel, "notification_channel"), nullable=False),
    Column("event_type", _pg_enum(NotificationEvent, "notification_event"), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("status", _pg_enum(NotificationStatus, "notification_status"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("sent_at", DateTime(timezone=True), nullable=True),
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

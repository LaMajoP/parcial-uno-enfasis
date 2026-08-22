"""Schemas de la §5.4 del spec."""
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_serializer

from .base import CamelModel, to_iso_z


class NotificationChannel(StrEnum):
    REALTIME = "REALTIME"
    WEBHOOK = "WEBHOOK"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationEvent(StrEnum):
    EMERGENCY_CREATED = "EMERGENCY_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    RESOURCE_ASSIGNED = "RESOURCE_ASSIGNED"
    HOTSPOT_DETECTED = "HOTSPOT_DETECTED"


class NotificationCreate(CamelModel):
    emergency_id: UUID
    event_type: NotificationEvent
    channel: NotificationChannel = NotificationChannel.REALTIME
    payload: dict[str, Any] = Field(default_factory=dict)
    recipient_id: UUID | None = None


class NotificationOut(CamelModel):
    id: UUID
    emergency_id: UUID
    recipient_id: UUID | None
    channel: NotificationChannel
    event_type: NotificationEvent
    payload: dict[str, Any]
    status: NotificationStatus
    created_at: datetime
    sent_at: datetime | None

    @field_serializer("created_at")
    def _created_at(self, value: datetime) -> str:
        return to_iso_z(value)

    @field_serializer("sent_at")
    def _sent_at(self, value: datetime | None) -> str | None:
        return to_iso_z(value) if value else None

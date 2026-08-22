"""Health check con verificación real de conectividad a base de datos (§13).

Un /health que solo devuelve 200 no sirve: en AWS este endpoint decide si la
Lambda se considera sana, así que tiene que tocar la base.
"""
import logging

from fastapi import APIRouter
from sqlalchemy import text

from ..config import get_settings
from ..db import SessionFactory
from ..responses import success

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    settings = get_settings()
    database_ok = True
    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        database_ok = False
        logger.error("Health check failed", extra={"error": str(exc)})

    return success(
        {"service": settings.service_name, "status": "ok" if database_ok else "degraded",
         "database": "up" if database_ok else "down"},
        status_code=200 if database_ok else 503,
    )

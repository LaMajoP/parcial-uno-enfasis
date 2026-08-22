"""Consultas por zona y cálculo de hotspots.

El clustering se resuelve entero dentro de PostgreSQL. Traerse las emergencias a
Python para agruparlas ahí significaría reimplementar DBSCAN y mover por la red
un volumen que crece con la ciudad; es justamente el trabajo que la base de datos
hace mejor, y la razón por la que se concedió la lectura cruzada.
"""
import logging
from datetime import UTC, datetime
from typing import Any

from geoalchemy2 import Geography, Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import emergencies, hotspots
from ..schemas.enums import (
    INACTIVE_STATUSES,
    City,
    EmergencyStatus,
    Priority,
)

logger = logging.getLogger(__name__)


async def list_zone_emergencies(
    session: AsyncSession,
    *,
    city: City,
    priority: Priority | None = None,
    status: EmergencyStatus | None = None,
    limit: int,
) -> list[dict[str, Any]]:
    """Emergencias de una ciudad, filtrables por prioridad y estado.

    Sin filtro de estado se devuelven solo las activas: el dashboard del operador
    trabaja sobre lo que está en curso. Pedir un estado concreto —incluido
    RESOLVED— sí lo devuelve, para poder consultar el histórico.
    """
    stmt = select(
        emergencies.c.id,
        emergencies.c.type,
        emergencies.c.priority,
        emergencies.c.city,
        emergencies.c.status,
        emergencies.c.latitude,
        emergencies.c.longitude,
        emergencies.c.created_at,
    ).where(emergencies.c.city == city)

    if status is not None:
        stmt = stmt.where(emergencies.c.status == status)
    else:
        stmt = stmt.where(emergencies.c.status.notin_(sorted(INACTIVE_STATUSES)))

    if priority is not None:
        stmt = stmt.where(emergencies.c.priority == priority)

    # Prioridad primero (el enum ordena P1 < P2 < P3 < P4) y, dentro de la misma
    # prioridad, lo más reciente arriba.
    stmt = stmt.order_by(
        emergencies.c.priority, emergencies.c.created_at.desc()
    ).limit(limit)

    return [dict(row) for row in (await session.execute(stmt)).mappings()]


async def compute_clusters(
    session: AsyncSession, *, city: City, eps_degrees: float, min_points: int
) -> list[dict[str, Any]]:
    """Agrupa las emergencias activas de la ciudad con ST_ClusterDBSCAN.

    Las filas que DBSCAN considera ruido reciben `cluster_id` NULL y se descartan:
    una emergencia aislada no es un punto caliente.
    """
    # ST_ClusterDBSCAN es una función de ventana y opera sobre `geometry`, no
    # sobre `geography`: de ahí el cast y el .over().
    cluster_id = (
        func.ST_ClusterDBSCAN(
            cast(emergencies.c.location, Geometry), eps_degrees, min_points
        )
        .over()
        .label("cluster_id")
    )

    clustered = (
        select(
            cluster_id,
            emergencies.c.priority,
            emergencies.c.location,
        )
        .where(emergencies.c.city == city)
        .where(emergencies.c.status.notin_(sorted(INACTIVE_STATUSES)))
        .subquery("clustered")
    )

    centroid = func.ST_Centroid(
        func.ST_Collect(cast(clustered.c.location, Geometry))
    )

    stmt = (
        select(
            clustered.c.cluster_id,
            func.count().label("emergency_count"),
            # El enum ordena P1 < P2 < P3 < P4, así que el mínimo es la prioridad
            # más alta del grupo.
            func.min(clustered.c.priority).label("highest_priority"),
            func.ST_Y(centroid).label("latitude"),
            func.ST_X(centroid).label("longitude"),
        )
        .where(clustered.c.cluster_id.isnot(None))
        .group_by(clustered.c.cluster_id)
        .order_by(func.count().desc())
    )

    return [dict(row) for row in (await session.execute(stmt)).mappings()]


async def replace_hotspots(
    session: AsyncSession,
    *,
    city: City,
    radius_meters: int,
    clusters: list[dict[str, Any]],
) -> None:
    """Borra los hotspots previos de la ciudad y guarda los recién calculados.

    Es un reemplazo completo por ciudad, como pide el spec: un hotspot es una
    foto del momento, no un histórico. Ambas operaciones van en la misma
    transacción, así que nunca se queda la ciudad sin hotspots a medias.
    """
    await session.execute(hotspots.delete().where(hotspots.c.city == city))

    if not clusters:
        return

    generated_at = datetime.now(UTC)
    for cluster in clusters:
        # Una sentencia por hotspot en vez de un executemany: `center` es una
        # expresión SQL (ST_SetSRID(...)), y un executemany solo admite valores
        # literales como parámetros.
        await session.execute(
            hotspots.insert().values(
                city=city,
                center=_point(cluster["longitude"], cluster["latitude"]),
                radius_meters=radius_meters,
                emergency_count=cluster["emergency_count"],
                highest_priority=cluster["highest_priority"],
                generated_at=generated_at,
            )
        )


def _point(longitude: float, latitude: float):
    """Punto geográfico en SRID 4326 (ST_MakePoint recibe lon, lat)."""
    return cast(func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326), Geography)

"""Endpoints de zona y hotspots (§5.3)."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..repositories import zones as repo
from ..responses import success
from ..schemas.enums import City, EmergencyStatus, Priority
from ..schemas.zone import Hotspot, Location, ZoneEmergency
from ..services.clustering import meters_to_degrees

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/zones", tags=["zones"])

settings = get_settings()


@router.get("/{city}/emergencies")
async def zone_emergencies(
    city: City,
    priority: Priority | None = Query(default=None),
    status: EmergencyStatus | None = Query(default=None),
    limit: int = Query(default=settings.default_zone_limit, gt=0, le=500),
    session: AsyncSession = Depends(get_session),
):
    rows = await repo.list_zone_emergencies(
        session, city=city, priority=priority, status=status, limit=limit
    )
    data = [
        ZoneEmergency(
            id=row["id"],
            type=row["type"],
            priority=row["priority"],
            city=row["city"],
            status=row["status"],
            location=Location(latitude=row["latitude"], longitude=row["longitude"]),
            created_at=row["created_at"],
        ).model_dump(by_alias=True, mode="json")
        for row in rows
    ]
    logger.info("Zone query", extra={"city": city.value, "found": len(data)})
    return success(data)


@router.get("/{city}/hotspots")
async def zone_hotspots(
    city: City,
    radius_meters: int = Query(
        default=settings.default_hotspot_radius_meters,
        alias="radiusMeters",
        gt=0,
        le=100_000,
    ),
    session: AsyncSession = Depends(get_session),
):
    """Recalcula los hotspots de la ciudad, los persiste y los devuelve.

    El cálculo se rehace en cada petición en vez de servir lo guardado: un
    hotspot describe la situación *ahora*, y devolver el de hace media hora sería
    peor que no devolver nada. La tabla `geo.hotspots` guarda el resultado para
    que el mapa pueda pintarlo sin recalcular y para dejar rastro de lo detectado.
    """
    clusters = await repo.compute_clusters(
        session,
        city=city,
        eps_degrees=meters_to_degrees(radius_meters),
        min_points=settings.hotspot_min_points,
    )
    await repo.replace_hotspots(
        session, city=city, radius_meters=radius_meters, clusters=clusters
    )
    await session.commit()

    data = [
        Hotspot(
            latitude=round(cluster["latitude"], 6),
            longitude=round(cluster["longitude"], 6),
            radius_meters=radius_meters,
            emergency_count=cluster["emergency_count"],
            highest_priority=cluster["highest_priority"],
        ).model_dump(by_alias=True, mode="json")
        for cluster in clusters
    ]

    logger.info(
        "Hotspots computed",
        extra={
            "city": city.value,
            "radius_meters": radius_meters,
            "hotspots": len(data),
            "emergencies_clustered": sum(h["emergencyCount"] for h in data),
        },
    )
    return success(data)

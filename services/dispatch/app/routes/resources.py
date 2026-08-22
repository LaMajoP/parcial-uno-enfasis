"""GET /v1/resources/nearby (§5.2)."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..repositories import resources as repo
from ..responses import success
from ..schemas.dispatch import NearbyResource, ResourceLocation, ResourceOut
from ..schemas.enums import City, ResourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/resources", tags=["resources"])

settings = get_settings()

# Mismo bounding box de Colombia que valida Intake. Aquí no lo pide el spec, pero
# una consulta fuera de él solo puede ser un error del cliente —coordenadas
# invertidas, sobre todo— y devolver una lista vacía lo escondería.
MIN_LATITUDE, MAX_LATITUDE = -4.5, 13.0
MIN_LONGITUDE, MAX_LONGITUDE = -82.0, -66.0


@router.get("")
async def list_resources(
    city: City | None = Query(default=None),
    limit: int = Query(default=200, gt=0, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Recursos con su ubicación. Lo usa el mapa del operador (§9)."""
    rows = await repo.list_by_city(session, city=city, limit=limit)
    return success(
        [
            ResourceOut(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                city=row["city"],
                status=row["status"],
                location=ResourceLocation(
                    latitude=row["latitude"], longitude=row["longitude"]
                ),
            ).model_dump(by_alias=True, mode="json")
            for row in rows
        ]
    )


@router.get("/nearby")
async def nearby(
    latitude: float = Query(ge=MIN_LATITUDE, le=MAX_LATITUDE),
    longitude: float = Query(ge=MIN_LONGITUDE, le=MAX_LONGITUDE),
    radius_meters: int = Query(
        default=settings.default_radius_meters, alias="radiusMeters", gt=0, le=500_000
    ),
    resource_type: ResourceType | None = Query(default=None, alias="type"),
    limit: int = Query(default=settings.default_limit, gt=0, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Recursos AVAILABLE dentro del radio, ordenados por distancia."""
    rows = await repo.find_nearby(
        session,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        resource_type=resource_type,
        limit=limit,
    )

    data = [
        NearbyResource(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            status=row["status"],
            # La distancia se redondea a metros enteros: la precisión submétrica
            # no significa nada aquí y ensucia la respuesta.
            distance_meters=round(row["distance_meters"]),
        ).model_dump(by_alias=True, mode="json")
        for row in rows
    ]

    logger.info(
        "Nearby search",
        extra={"found": len(data), "radius_meters": radius_meters,
               "resource_type": resource_type.value if resource_type else None},
    )
    return success(data)

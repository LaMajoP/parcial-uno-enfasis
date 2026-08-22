"""Acceso a datos de dispatch.resources, incluida la búsqueda geoespacial."""
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import Select, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import resources
from ..schemas.enums import City, ResourceStatus, ResourceType


def _point(latitude: float, longitude: float):
    """Punto geográfico en SRID 4326.

    Ojo al orden: ST_MakePoint recibe (longitud, latitud), al revés de como se
    escriben las coordenadas en el resto del sistema.
    """
    return cast(
        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326), Geography
    )


def _nearby_query(latitude: float, longitude: float) -> tuple[Select, Any]:
    point = _point(latitude, longitude)
    distance = func.ST_Distance(resources.c.location, point).label("distance_meters")
    query = select(
        resources.c.id,
        resources.c.name,
        resources.c.type,
        resources.c.status,
        resources.c.city,
        distance,
    ).where(resources.c.status == ResourceStatus.AVAILABLE)
    return query, distance


async def find_nearby(
    session: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    radius_meters: int,
    resource_type: ResourceType | None = None,
    limit: int,
) -> list[dict[str, Any]]:
    """Recursos AVAILABLE dentro del radio, del más cercano al más lejano.

    `ST_DWithin` es lo que permite usar el índice GIST; filtrar con `ST_Distance`
    en el WHERE obligaría a calcular la distancia de cada fila de la tabla.
    """
    query, distance = _nearby_query(latitude, longitude)
    query = query.where(
        func.ST_DWithin(
            resources.c.location, _point(latitude, longitude), radius_meters
        )
    )
    if resource_type is not None:
        query = query.where(resources.c.type == resource_type)

    rows = await session.execute(query.order_by(distance).limit(limit))
    return [dict(row) for row in rows.mappings()]


async def find_best_candidate(
    session: AsyncSession,
    *,
    city: City,
    latitude: float,
    longitude: float,
    radius_meters: int,
    preferred_types: tuple[ResourceType, ...],
) -> dict[str, Any] | None:
    """Elige el recurso del auto-despacho siguiendo la preferencia de la §6.

    Orden de búsqueda: el más cercano del primer tipo preferido dentro del radio;
    si no hay, del segundo tipo; y si tampoco, cualquiera disponible en la ciudad
    —este último paso sin límite de distancia, porque el criterio pasa a ser
    "que haya alguien" antes que "que esté cerca"—.
    """
    query, distance = _nearby_query(latitude, longitude)
    query = query.where(resources.c.city == city)

    for resource_type in preferred_types:
        candidate = await session.execute(
            query.where(resources.c.type == resource_type)
            .where(
                func.ST_DWithin(
                    resources.c.location, _point(latitude, longitude), radius_meters
                )
            )
            .order_by(distance)
            .limit(1)
        )
        if row := candidate.mappings().one_or_none():
            return dict(row)

    fallback = await session.execute(query.order_by(distance).limit(1))
    row = fallback.mappings().one_or_none()
    return dict(row) if row else None


async def list_by_city(
    session: AsyncSession, *, city: City | None = None, limit: int
) -> list[dict[str, Any]]:
    """Todos los recursos, con su ubicación, para el mapa del operador."""
    stmt = select(
        resources.c.id,
        resources.c.name,
        resources.c.type,
        resources.c.city,
        resources.c.status,
        resources.c.latitude,
        resources.c.longitude,
    ).order_by(resources.c.city, resources.c.name).limit(limit)

    if city is not None:
        stmt = stmt.where(resources.c.city == city)

    return [dict(row) for row in (await session.execute(stmt)).mappings()]


async def lock_if_available(
    session: AsyncSession, resource_id: UUID
) -> dict[str, Any] | None:
    """Bloquea la fila del recurso y devuelve sus datos, o None si no existe.

    `FOR UPDATE` es lo que impide la doble asignación: dos peticiones simultáneas
    sobre el mismo recurso se serializan aquí, y la segunda ve el estado que dejó
    la primera en vez de leer el original.
    """
    stmt = (
        select(
            resources.c.id,
            resources.c.name,
            resources.c.type,
            resources.c.city,
            resources.c.status,
        )
        .where(resources.c.id == resource_id)
        .with_for_update()
    )
    row = (await session.execute(stmt)).mappings().one_or_none()
    return dict(row) if row else None


async def set_status(
    session: AsyncSession, resource_id: UUID, status: ResourceStatus
) -> None:
    await session.execute(
        update(resources).where(resources.c.id == resource_id).values(status=status)
    )

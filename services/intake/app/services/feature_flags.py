"""Lectura dinámica de Feature Flags desde AWS AppConfig.

No hay flags ni nombres de recursos en variables de entorno de Lambda. En
producción el proceso mantiene una sesión de AppConfig Data y respeta el intervalo
de consulta que devuelve AWS; en desarrollo conserva el comportamiento local
original para que Docker Compose no dependa de AWS.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any

import boto3

from ..schemas.enums import City

logger = logging.getLogger(__name__)

_APPLICATION = "emergency-platform"
_ENVIRONMENT = "prod"
_PROFILE = "intake-feature-flags"
_ALL_CITIES = frozenset(City)


@dataclass(frozen=True)
class RuntimeFeatureFlags:
    """Snapshot inmutable de las flags que afectan la ruta crítica de Intake."""

    auto_dispatch_enabled: bool
    auto_dispatch_cities: frozenset[City]

    def allows_auto_dispatch(self, city: City) -> bool:
        return self.auto_dispatch_enabled and city in self.auto_dispatch_cities


SAFE_LOCAL_DEFAULTS = RuntimeFeatureFlags(
    auto_dispatch_enabled=True,
    auto_dispatch_cities=_ALL_CITIES,
)

# Si AppConfig no está disponible durante un cold start de Lambda, Intake sigue
# aceptando y persistiendo la emergencia, pero no autoasigna recursos hasta que
# haya recibido una configuración válida. Así el Kill Switch falla de forma segura.
SAFE_LAMBDA_DEFAULTS = RuntimeFeatureFlags(
    auto_dispatch_enabled=False,
    auto_dispatch_cities=frozenset(),
)


class AppConfigFeatureFlagStore:
    """Cliente con caché por proceso y último valor conocido.

    AppConfig entrega un token nuevo en cada consulta. El lock evita que dos
    invocaciones concurrentes reutilicen el mismo token, que AWS solo admite una
    vez. Ante un error se conserva el último snapshot; en un cold start sin
    snapshot se desactiva el auto-despacho, pero nunca se rechaza el reporte.
    """

    def __init__(self) -> None:
        self._client: Any | None = None
        self._token: str | None = None
        self._next_poll_at = 0.0
        self._flags = SAFE_LAMBDA_DEFAULTS
        self._lock = Lock()

    def get(self) -> RuntimeFeatureFlags:
        if not _is_lambda_runtime():
            return SAFE_LOCAL_DEFAULTS

        with self._lock:
            if monotonic() < self._next_poll_at:
                return self._flags

            try:
                self._refresh()
            except Exception as exc:  # La configuración no puede bloquear Intake.
                logger.error(
                    "Feature flag refresh failed; using last known snapshot",
                    extra={"error": str(exc), "feature_flags_source": "appconfig"},
                )
                self._next_poll_at = monotonic() + 15.0
            return self._flags

    def _refresh(self) -> None:
        client = self._get_client()
        if self._token is None:
            session = client.start_configuration_session(
                ApplicationIdentifier=_APPLICATION,
                EnvironmentIdentifier=_ENVIRONMENT,
                ConfigurationProfileIdentifier=_PROFILE,
                RequiredMinimumPollIntervalInSeconds=15,
            )
            self._token = session["InitialConfigurationToken"]

        response = client.get_latest_configuration(ConfigurationToken=self._token)
        self._token = response["NextPollConfigurationToken"]
        interval = float(response.get("NextPollIntervalInSeconds", 15))
        self._next_poll_at = monotonic() + max(interval, 15.0)

        raw = response["Configuration"].read()
        if raw:
            self._flags = _parse_flags(json.loads(raw.decode("utf-8")))
            logger.info(
                "Feature flags refreshed",
                extra={
                    "feature_flags_source": "appconfig",
                    "auto_dispatch_enabled": self._flags.auto_dispatch_enabled,
                    "auto_dispatch_cities": sorted(city.value for city in self._flags.auto_dispatch_cities),
                },
            )

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client("appconfigdata")
        return self._client


def _is_lambda_runtime() -> bool:
    return bool(os.getenv("AWS_EXECUTION_ENV"))


def _parse_flags(document: dict[str, Any]) -> RuntimeFeatureFlags:
    values = document.get("values")
    if not isinstance(values, dict):
        raise ValueError("AppConfig feature flag document has no values object")

    dispatch = values.get("auto_dispatch_enabled")
    if not isinstance(dispatch, dict):
        raise ValueError("Required AppConfig flags are missing")

    raw_cities = dispatch.get("enabled_cities", [])
    if not isinstance(raw_cities, list):
        raise ValueError("enabled_cities must be an array")

    try:
        cities = frozenset(City(city) for city in raw_cities)
    except ValueError as exc:
        raise ValueError("enabled_cities contains an unsupported city") from exc

    return RuntimeFeatureFlags(
        auto_dispatch_enabled=bool(dispatch.get("enabled", False)),
        auto_dispatch_cities=cities,
    )


feature_flags = AppConfigFeatureFlagStore()


async def get_feature_flags() -> RuntimeFeatureFlags:
    """Evita bloquear el event loop de FastAPI durante una consulta a AWS."""
    return await asyncio.to_thread(feature_flags.get)

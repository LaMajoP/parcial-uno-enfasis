"""Llamadas salientes a otros microservicios.

Regla del spec (§6): son *fire-and-forget*. Si Notification o Dispatch están
caídos, la emergencia igual queda creada y el POST responde 201. El fallo se
registra en el log y ahí termina: no hay reintentos ni cola.

No se usan tareas de fondo que sobrevivan a la respuesta —en Lambda el proceso se
congela al devolverla y nunca se ejecutarían—, así que las llamadas se esperan
con timeout corto y se lanzan en paralelo.
"""
import asyncio
import json
import logging
from functools import lru_cache
from typing import Any

import boto3
import httpx

from ..config import get_settings
from ..log import request_id_var

logger = logging.getLogger(__name__)


async def post_fire_and_forget(url: str, payload: dict, *, purpose: str) -> bool:
    """Hace un POST y se traga cualquier fallo. Devuelve si tuvo éxito."""
    settings = get_settings()
    headers = {}
    if request_id := request_id_var.get():
        headers["X-Request-Id"] = request_id

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Outbound call rejected",
            extra={
                "purpose": purpose,
                "url": url,
                "status_code": exc.response.status_code,
                "response_body": exc.response.text[:500],
            },
        )
        return False
    except (httpx.HTTPError, OSError) as exc:
        # Servicio caído, DNS que no resuelve o timeout: se registra y se sigue.
        logger.warning(
            "Outbound call failed",
            extra={"purpose": purpose, "url": url, "error": str(exc)},
        )
        return False

    logger.info("Outbound call ok", extra={"purpose": purpose, "url": url})
    return True


@lru_cache(maxsize=1)
def _get_lambda_client():
    return boto3.client("lambda")


def _build_lambda_http_event(
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict:
    """Construye un evento HTTP API v2 que Mangum puede convertir a FastAPI."""

    request_id = request_id_var.get() or "internal"

    headers = {
        "content-type": "application/json",
        "user-agent": "emergency-platform-internal",
    }

    if request_id != "internal":
        headers["x-request-id"] = request_id

    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": headers,
        "requestContext": {
            "accountId": "internal",
            "apiId": "internal",
            "domainName": "internal",
            "domainPrefix": "internal",
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "emergency-platform-internal",
            },
            "requestId": request_id,
            "routeKey": "$default",
            "stage": "$default",
            "time": "01/Jan/1970:00:00:00 +0000",
            "timeEpoch": 0,
        },
        "body": json.dumps(payload) if payload is not None else None,
        "isBase64Encoded": False,
    }


async def invoke_lambda_http(
    function_name: str,
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    purpose: str,
) -> tuple[int, Any, str] | None:
    """Invoca otra Lambda privadamente y conserva el contrato HTTP/FastAPI."""

    event = _build_lambda_http_event(method, path, payload)

    def _invoke():
        return _get_lambda_client().invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event).encode("utf-8"),
        )

    try:
        response = await asyncio.to_thread(_invoke)

        if response.get("FunctionError"):
            logger.warning(
                "Internal Lambda execution failed",
                extra={
                    "purpose": purpose,
                    "function_name": function_name,
                },
            )
            return None

        raw_payload = response["Payload"].read()
        lambda_response = json.loads(raw_payload)

        status_code = int(lambda_response.get("statusCode", 500))
        body_text = lambda_response.get("body") or ""

        try:
            body = json.loads(body_text) if body_text else None
        except json.JSONDecodeError:
            body = None

        return status_code, body, body_text

    except Exception as exc:
        logger.warning(
            "Internal Lambda invocation failed",
            extra={
                "purpose": purpose,
                "function_name": function_name,
                "error": str(exc),
            },
        )
        return None

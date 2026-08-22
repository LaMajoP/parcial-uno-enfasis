"""Geospatial & Zone Aggregation — consultas por zona y hotspots con PostGIS."""
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from mangum import Mangum
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .errors import ApiError, ErrorCode
from .log import configure_logging, request_id_var
from .responses import failure
from .routes import health, zones

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Service started", extra={"service_name": settings.service_name})
    yield


app = FastAPI(
    title="Emergency Platform — Geospatial & Zone Aggregation",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(zones.router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Propaga X-Request-Id (§7): si no viene, se genera uno.

    El gateway lo inyecta, pero el servicio no depende de ello: una petición
    directa al puerto del servicio también queda trazable.
    """
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-Id"] = request_id
    return response


# ── Exception handlers ───────────────────────────────────────────────────────
# El spec exige que TODAS las respuestas salgan con el mismo formato. Sin estos
# handlers, FastAPI devolvería sus errores de validación con la forma `detail`,
# que rompe el contrato.

@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError):
    logger.info(
        "Request rejected",
        extra={"error_code": exc.code.value, "path": request.url.path},
    )
    return failure(exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    logger.info(
        "Invalid payload",
        extra={"path": request.url.path, "errors": exc.errors()},
    )
    return failure(ErrorCode.INVALID_PAYLOAD, _describe(exc))


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    """Traduce los errores HTTP de Starlette al vocabulario de códigos del spec.

    Cualquier 4xx sin equivalente exacto (405, 415, 422…) cae en INVALID_PAYLOAD:
    son errores del cliente, y devolverlos como INTERNAL_ERROR haría que un fallo
    de quien llama se contabilizara como caída del servicio.
    """
    explicit = {
        400: ErrorCode.INVALID_PAYLOAD,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
    }
    if (code := explicit.get(exc.status_code)) is None:
        code = (
            ErrorCode.INVALID_PAYLOAD
            if 400 <= exc.status_code < 500
            else ErrorCode.INTERNAL_ERROR
        )
    return failure(code, str(exc.detail))


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception):
    """Último recinto: nada sale de aquí sin el envoltorio de error.

    El detalle real va al log, no al cliente: un stack trace en la respuesta es
    una fuga de información.
    """
    logger.exception("Unhandled error", extra={"path": request.url.path})
    return failure(ErrorCode.INTERNAL_ERROR, "Internal server error")


def _describe(exc: RequestValidationError) -> str:
    """Mensaje legible a partir del primer error de validación."""
    errors = exc.errors()
    if not errors:
        return "Invalid zone query"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    message = first.get("msg", "invalid value")
    return f"Invalid zone query: {location or 'body'}: {message}"


# Punto de entrada para AWS Lambda. En local no se usa: uvicorn arranca `app`.
handler = Mangum(app)

"""Contrato de errores de la §5 del spec.

Todas las respuestas del servicio —incluidas las de validación de FastAPI y
cualquier excepción no controlada— salen con la misma forma:

    { "success": false, "error": { "code": "...", "message": "..." } }
"""
from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.INVALID_PAYLOAD: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.RESOURCE_UNAVAILABLE: 409,
    ErrorCode.INTERNAL_ERROR: 500,
}


class ApiError(Exception):
    """Error de negocio que ya sabe con qué código y estado HTTP debe salir."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    @property
    def status_code(self) -> int:
        return STATUS_BY_CODE[self.code]


class NotFoundError(ApiError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(ErrorCode.NOT_FOUND, message)


class ResourceUnavailableError(ApiError):
    """El recurso existe pero ya no está libre: otra asignación llegó primero."""

    def __init__(self, message: str = "Resource is not available") -> None:
        super().__init__(ErrorCode.RESOURCE_UNAVAILABLE, message)


class ConflictError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.CONFLICT, message)


class InvalidPayloadError(ApiError):
    def __init__(self, message: str = "Invalid dispatch payload") -> None:
        super().__init__(ErrorCode.INVALID_PAYLOAD, message)

"""Envoltorio único de respuesta de la §5 del spec."""
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .errors import STATUS_BY_CODE, ErrorCode


def success(data: BaseModel | dict[str, Any] | list[Any], status_code: int = 200) -> JSONResponse:
    """`{ "success": true, "data": ... }` con los campos ya en camelCase."""
    if isinstance(data, BaseModel):
        data = data.model_dump(by_alias=True, mode="json")
    return JSONResponse(status_code=status_code, content={"success": True, "data": data})


def failure(code: ErrorCode, message: str) -> JSONResponse:
    """`{ "success": false, "error": { "code": ..., "message": ... } }`."""
    return JSONResponse(
        status_code=STATUS_BY_CODE[code],
        content={"success": False, "error": {"code": code.value, "message": message}},
    )

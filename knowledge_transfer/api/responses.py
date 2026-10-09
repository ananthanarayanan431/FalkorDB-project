"""Response envelopes. Every endpoint answers with one of these two shapes.

  success  {"success": true,  "message": "...", "data": ...}
  error    {"success": false, "message": "...", "error": {"code": "...", "details": ...}}
"""
from typing import Any

from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    success: bool = True
    message: str
    data: T


class ErrorBody(BaseModel):
    code: str
    details: Any = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: ErrorBody


def ok[T](data: T, message: str = "OK") -> ApiResponse[T]:
    return ApiResponse(message=message, data=data)


# Documented on every router so the OpenAPI schema shows the error shape.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse, "description": description}
    for status, description in {
        400: "Bad request",
        404: "Not found",
        409: "Conflict",
        422: "Validation error",
        500: "Internal server error",
        503: "Service unavailable",
    }.items()
}

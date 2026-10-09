"""API errors and the handlers that render them as `ErrorResponse`.

Services raise the domain errors in `knowledge_transfer.core.errors`; routes do not
catch them. `DOMAIN_ERRORS` maps each to a status and code in one place.
"""
import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from knowledge_transfer.api.responses import ErrorBody, ErrorResponse
from knowledge_transfer.core.errors import (
    InvalidInput,
    InvalidState,
    KnowledgeTransferError,
    LLMUnavailable,
    NotFound,
)

log = logging.getLogger(__name__)


class ApiError(Exception):
    """HTTP-level errors raised by the API layer itself (not by services)."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.message = message
        self.details = details


class BadRequestError(ApiError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"


class ServiceUnavailableError(ApiError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"


DOMAIN_ERRORS: dict[type[KnowledgeTransferError], tuple[int, str]] = {
    NotFound: (status.HTTP_404_NOT_FOUND, "NOT_FOUND"),
    InvalidInput: (status.HTTP_422_UNPROCESSABLE_CONTENT, "INVALID_INPUT"),
    InvalidState: (status.HTTP_409_CONFLICT, "CONFLICT"),
    LLMUnavailable: (status.HTTP_503_SERVICE_UNAVAILABLE, "LLM_UNAVAILABLE"),
}

HTTP_CODES = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    503: "SERVICE_UNAVAILABLE",
}


def _error(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = ErrorResponse(message=message, error=ErrorBody(code=code, details=details))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message, exc.details)


async def _domain_error(_: Request, exc: KnowledgeTransferError) -> JSONResponse:
    status_code, code = next(
        (v for cls, v in DOMAIN_ERRORS.items() if isinstance(exc, cls)),
        (status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR"),
    )
    return _error(status_code, code, exc.message, exc.details)


async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    return _error(exc.status_code, code, str(exc.detail))


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
    return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "VALIDATION_ERROR",
                  "Request validation failed", details)


async def _unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error", exc_info=exc)
    return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Internal server error")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(KnowledgeTransferError, _domain_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unhandled_error)

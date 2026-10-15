"""ASGI middleware: security headers and a request body size limit.

Written as plain ASGI (not BaseHTTPMiddleware) so request bodies are never buffered just
to be measured and exceptions keep their tracebacks. A reverse proxy in front of the API
should enforce its own body limit too; this one is the backstop.
"""
import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import HTTPException

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-opener-policy", b"same-origin"),
]
NO_STORE = (b"cache-control", b"no-store")


class SecurityHeadersMiddleware:
    """Adds conservative security headers to every HTTP response. API responses are
    also marked `no-store`: they contain interview answers that should not be cached."""

    def __init__(self, app: ASGIApp, api_prefix: str = "/api/"):
        self.app = app
        self.api_prefix = api_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_api = scope.get("path", "").startswith(self.api_prefix)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                extra = [*SECURITY_HEADERS, NO_STORE] if is_api else SECURITY_HEADERS
                headers += [(name, value) for name, value in extra if name not in present]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class _TooLarge(HTTPException):
    """Raised from `receive` once the body passes the limit. It must be FastAPI's
    HTTPException: FastAPI turns any other error while reading a body into a 400."""

    def __init__(self, max_bytes: int):
        super().__init__(status_code=413, detail=f"Request body is larger than {max_bytes} bytes")


def _envelope(message: str) -> bytes:
    """The API's error envelope, without importing the response models (no cycles)."""
    return json.dumps(
        {"success": False, "message": message, "error": {"code": "PAYLOAD_TOO_LARGE", "details": None}}
    ).encode()


class BodySizeLimitMiddleware:
    """Rejects request bodies larger than `max_bytes` with 413. Checks Content-Length up
    front, then counts streamed bytes, so a missing or understated length is caught too."""

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(send)
            return

        received = 0
        started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _TooLarge(self.max_bytes)
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _TooLarge:
            # Only reached when no exception handler rendered it (e.g. a non-FastAPI app).
            if not started:
                await self._reject(send)

    async def _reject(self, send: Send) -> None:
        body = _envelope(f"Request body is larger than {self.max_bytes} bytes")
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})

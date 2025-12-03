from typing import Callable, Awaitable
from app.core.logger import logger
from app.core.utils_logging import generate_request_id
import time

class RequestLoggingMiddleware:
    """
    ASGI middleware that logs incoming requests and responses,
    sets X-Request-ID header, and records duration.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request_id = generate_request_id()
        scope["request_id"] = request_id

        method = scope.get("method", "")
        path = scope.get("path", "")

        start = time.perf_counter()
        logger.info(
            "Incoming request",
            extra={"request_id": request_id, "method": method, "path": path},
        )

        # We'll capture status_code from the http.response.start message
        status_code_container = {"status": None}

        async def send_wrapper(message):
            # When response starts, message has status and headers
            if message["type"] == "http.response.start":
                status = message.get("status", 0)
                status_code_container["status"] = status

                # ensure headers include X-Request-ID (append; headers are list of [name, value] bytes)
                headers = message.get("headers", [])
                # append header (preserve existing)
                headers = list(headers) + [
                    (b"x-request-id", request_id.encode("utf-8"))
                ]
                message["headers"] = headers

                logger.info(
                    "Response start",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "path": path,
                        "status_code": status,
                    },
                )

            await send(message)

        # call downstream app
        await self.app(scope, receive, send_wrapper)

        duration = time.perf_counter() - start
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code_container["status"],
                "duration_ms": round(duration * 1000, 2),
            },
        )

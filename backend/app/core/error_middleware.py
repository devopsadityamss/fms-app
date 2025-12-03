from app.core.logger import logger
import traceback

class ExceptionLoggingMiddleware:
    """
    ASGI middleware that logs exceptions with full stack trace.
    Re-raises exception so FastAPI/Starlette can produce a response.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # full stack trace
            tb = traceback.format_exc()
            logger.exception(
                "Unhandled exception in request",
                extra={
                    "request_id": scope.get("request_id"),
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "traceback": tb,
                },
            )
            # re-raise so FastAPI's error handlers / middleware can respond
            raise

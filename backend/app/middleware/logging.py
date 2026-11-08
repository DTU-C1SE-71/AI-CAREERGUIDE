import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("careerguide.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware ghi log thời gian xử lý của mỗi request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        if request.url.path.startswith("/api"):
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} ({process_time:.1f}ms)"
            )
        return response

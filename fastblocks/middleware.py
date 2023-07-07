import typing as t
from time import perf_counter

from acb.adapters import cache
from acb.logger import logger

from asgi_htmx import HtmxMiddleware
from asgi_htmx import HtmxRequest as Request
from asgi_logger.middleware import AccessLoggerMiddleware
from brotli_asgi import BrotliMiddleware
from cashews.commands import Command
from secure import Secure
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse as Response

secure_headers = Secure()


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    @staticmethod
    async def set_secure_headers(request: Request, call_next: t.Callable) -> Response:
        response = await call_next(request)
        secure_headers.framework.starlette(response)
        return response


class ProcessTimeHeaderMiddleware(BaseHTTPMiddleware):
    @staticmethod
    async def add_process_time_header(
        request: Request, call_next: t.Callable
    ) -> Response:
        start_time = perf_counter()
        response = await call_next(request)
        process_time = perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.debug(f"Request processed in {process_time} s")
        return response


class FromCacheHeaderMiddleware(BaseHTTPMiddleware):
    @staticmethod
    async def add_from_cache_headers(request: Request, call_next) -> Response:
        with cache.detect as detector:
            response = await call_next(request)
            if request.method.lower() != "get":
                return response
            if detector.calls:
                response.headers["X-From-Cache-keys"] = ";".join(detector.calls.keys())
        return response


class DisableCacheMiddleware(BaseHTTPMiddleware):
    @staticmethod
    async def disable_middleware(request: Request, call_next: t.Callable) -> Response:
        if request.headers.get("X-No-Cache"):
            with cache.disabling(Command.GET):
                return await call_next(request)
        return await call_next(request)


middleware = [
    Middleware(HTTPSRedirectMiddleware),
    Middleware(DisableCacheMiddleware),
    Middleware(FromCacheHeaderMiddleware),
    # Middleware(CSRFMiddleware, secret=ac.secrets.app_secret_key),
    Middleware(SecureHeadersMiddleware),
    Middleware(HtmxMiddleware),
    Middleware(BrotliMiddleware, quality=3),
    Middleware(
        AccessLoggerMiddleware,
        logger=logger,
        format='{client_addr} - "{request_line}" {status_code}',
    ),
    Middleware(ProcessTimeHeaderMiddleware),
]

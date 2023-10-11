import typing as t
from time import perf_counter

from acb.adapters.cache import Cache
from acb.adapters.logger import Logger
from acb.config import Config
from acb.depends import depends

from asgi_htmx import HtmxMiddleware
from asgi_htmx import HtmxRequest
from asgi_logger.middleware import AccessLoggerMiddleware
from brotli_asgi import BrotliMiddleware
from cashews.commands import Command
from secure import Secure
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import HTMLResponse as Response
from starlette_csrf.middleware import CSRFMiddleware

secure_headers = Secure()


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    @staticmethod
    async def set_secure_headers(
        request: HtmxRequest, call_next: t.Callable[[HtmxRequest], t.Any]
    ) -> Response:
        response = await call_next(request)
        secure_headers.framework.starlette(response)
        return response


class ProcessTimeHeaderMiddleware(BaseHTTPMiddleware):
    @staticmethod
    @depends.inject
    async def add_process_time_header(
        request: HtmxRequest,
        call_next: t.Callable[[HtmxRequest], t.Any],
        logger: Logger = depends(),  # type: ignore
    ) -> Response:
        start_time = perf_counter()
        response = await call_next(request)
        process_time = perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.debug(f"Request processed in {process_time} s")
        return response


class FromCacheHeaderMiddleware(BaseHTTPMiddleware):
    @staticmethod
    @depends.inject
    async def add_from_cache_headers(
        request: HtmxRequest,
        call_next: t.Callable[[HtmxRequest], t.Any],
        cache: Cache = (depends()),  # type: ignore
    ) -> Response:
        with cache.detect as detector:
            response = await call_next(request)
            if request.method.lower() != "get":
                return response
            if detector.calls:
                response.headers["X-From-Cache-keys"] = ";".join(detector.calls.keys())
        return response


class DisableCacheMiddleware(BaseHTTPMiddleware):
    @staticmethod
    @depends.inject
    async def disable_middleware(
        request: HtmxRequest,
        call_next: t.Callable[[HtmxRequest], t.Any],
        cache: Cache = depends(),  # type: ignore
    ) -> Response:
        if request.headers.get("X-No-Cache"):
            with cache.disabling(Command.GET):
                return await call_next(request)
        return await call_next(request)


@depends.inject
def middlewares(
    config: Config = depends(), logger: Logger = depends()  # type: ignore
) -> list[Middleware]:
    return [
        Middleware(HTTPSRedirectMiddleware),
        Middleware(DisableCacheMiddleware),
        Middleware(FromCacheHeaderMiddleware),
        Middleware(CSRFMiddleware, secret=config.app.secret_key.get_secret_value()),
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

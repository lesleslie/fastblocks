import typing as t
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from time import perf_counter

from acb.adapters import import_adapter
from acb.config import Config
from acb.depends import depends
from acb.logger import Logger
from asgi_htmx import HtmxMiddleware
from brotli_asgi import BrotliMiddleware
from secure import Secure
from starlette.datastructures import URL, Headers, MutableHeaders
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette_csrf.middleware import CSRFMiddleware

from .caching import (
    CacheControlResponder,
    CacheDirectives,
    CacheResponder,
    Rule,
    delete_from_cache,
)
from .exceptions import DuplicateCaching, MissingCaching

Cache = import_adapter()  # type: ignore

secure_headers = Secure()

scope_name = "__starlette_caches__"

_request_ctx_var: ContextVar[Scope | None] = ContextVar(
    "request",
    default=None,  # type: ignore
)


def get_request() -> Scope | None:
    return _request_ctx_var.get()


class CurrentRequestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        local_scope = _request_ctx_var.set(scope)
        response = await self.app(scope, receive, send)
        _request_ctx_var.reset(local_scope)
        return response


class SecureHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @depends.inject
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        logger: Logger = depends(),
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_secure_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for k, v in secure_headers.headers.items():
                    headers.append(k, v)
            await send(message)

        await self.app(scope, receive, send_with_secure_headers)


class ProcessTimeHeaderMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @depends.inject
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        logger: Logger = depends(),
    ) -> None:
        start_time = perf_counter()
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.exception(exc)
            raise
        finally:
            process_time = perf_counter() - start_time
            logger.debug(f"Request processed in {process_time} s")


class CacheMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        cache: Cache = depends(),
        rules: Sequence[Rule] | None = None,
    ) -> None:
        if rules is None:
            rules = [Rule()]

        self.app = app
        self.cache = cache
        self.rules = rules

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if scope_name in scope:
            raise DuplicateCaching(
                "Another `CacheMiddleware` was detected in the middleware stack.\n"
                "HINT: this exception probably occurred because:\n"
                "- You wrapped an application around `CacheMiddleware` multiple "
                "times.\n"
                "- You tried to apply `@cached()` onto an endpoint, but "
                "the application is already wrapped around a `CacheMiddleware`."
            )
        scope[scope_name] = self
        responder = CacheResponder(
            self.app,
            rules=self.rules,
        )
        await responder(scope, receive, send)


class _BaseCacheMiddlewareHelper:
    def __init__(self, request: Request) -> None:
        self.request = request
        if scope_name not in request.scope:
            raise MissingCaching(
                "No CacheMiddleware instance found in the ASGI scope. Did you forget "
                "to wrap the ASGI application with `CacheMiddleware`?"
            )
        middleware = request.scope[scope_name]
        if not isinstance(middleware, CacheMiddleware):
            raise MissingCaching(
                f"A scope variable named {scope_name!r} was found, but it does not "
                "contain a `CacheMiddleware` instance. It is likely that an "
                "incompatible middleware was added to the middleware stack."
            )
        self.middleware = middleware


class CacheHelper(_BaseCacheMiddlewareHelper):
    async def invalidate_cache_for(
        self,
        url: str | URL,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(url, URL):
            url = self.request.url_for(url)
        if not isinstance(headers, Headers):
            headers = Headers(headers)
        await delete_from_cache(url, vary=headers, cache=self.middleware.cache)


class CacheControlMiddleware:
    def __init__(self, app: ASGIApp, **kwargs: t.Unpack[CacheDirectives]) -> None:
        self.app = app
        self.kwargs = kwargs

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        responder = CacheControlResponder(self.app, **self.kwargs)
        await responder(scope, receive, send)


@depends.inject
def middlewares(config: Config = depends()) -> list[Middleware]:
    middleware = [
        Middleware(ProcessTimeHeaderMiddleware),  # type: ignore
        Middleware(
            CSRFMiddleware,  # type: ignore
            secret=config.app.secret_key.get_secret_value(),
            cookie_name=f"{config.auth.token_id or config.app.name}_csrf",
            cookie_secure=config.deployed,
        ),
        Middleware(
            SessionMiddleware,  # type: ignore
            secret_key=config.app.secret_key.get_secret_value(),
            session_cookie=f"{config.auth.token_id or config.app.name}_app",
            https_only=config.deployed,
        ),
        Middleware(HtmxMiddleware),  # type: ignore
        Middleware(CurrentRequestMiddleware),  # type: ignore
        Middleware(BrotliMiddleware, quality=3),  # type: ignore
    ]
    if config.deployed or config.debug.production:
        middleware.append(Middleware(SecureHeadersMiddleware))  # type: ignore
    return middleware

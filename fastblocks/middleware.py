import sys
import typing as t
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from enum import IntEnum

from acb.depends import depends
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

MiddlewareCallable = t.Callable[[ASGIApp], ASGIApp]
MiddlewareClass = type[t.Any]
MiddlewareOptions = dict[str, t.Any]
from .exceptions import MissingCaching


class MiddlewarePosition(IntEnum):
    CSRF = 0
    SESSION = 1
    HTMX = 2
    CURRENT_REQUEST = 3
    COMPRESSION = 4
    SECURITY_HEADERS = 5


class MiddlewareUtils:
    Cache = t.Any

    secure_headers = Secure()

    scope_name = "__starlette_caches__"

    _request_ctx_var: ContextVar[Scope | None] = ContextVar("request", default=None)

    HTTP = sys.intern("http")
    WEBSOCKET = sys.intern("websocket")
    TYPE = sys.intern("type")
    METHOD = sys.intern("method")
    PATH = sys.intern("path")
    GET = sys.intern("GET")
    HEAD = sys.intern("HEAD")
    POST = sys.intern("POST")
    PUT = sys.intern("PUT")
    PATCH = sys.intern("PATCH")
    DELETE = sys.intern("DELETE")

    @classmethod
    def get_request(cls) -> Scope | None:
        return cls._request_ctx_var.get()

    @classmethod
    def set_request(cls, scope: Scope | None) -> None:
        cls._request_ctx_var.set(scope)


Cache = MiddlewareUtils.Cache
secure_headers = MiddlewareUtils.secure_headers
scope_name = MiddlewareUtils.scope_name
_request_ctx_var = MiddlewareUtils._request_ctx_var


def get_request() -> Scope | None:
    return MiddlewareUtils.get_request()


class CurrentRequestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope[MiddlewareUtils.TYPE] not in (
            MiddlewareUtils.HTTP,
            MiddlewareUtils.WEBSOCKET,
        ):
            await self.app(scope, receive, send)
            return None
        local_scope = _request_ctx_var.set(scope)
        response = await self.app(scope, receive, send)
        _request_ctx_var.reset(local_scope)
        return response


class SecureHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        try:
            self.logger = depends.get("logger")
        except Exception:
            self.logger = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_secure_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for header_name, header_value in secure_headers.headers.items():
                    headers.append(header_name, header_value)
            await send(message)

        await self.app(scope, receive, send_with_secure_headers)
        return None


class CacheValidator:
    def __init__(self, rules: Sequence[Rule] | None = None) -> None:
        self.rules = rules or [Rule()]

    def check_for_duplicate_middleware(self, app: ASGIApp) -> None:
        if hasattr(app, "middleware"):
            middleware_attr = app.middleware  # type: ignore[attr-defined]
            if callable(middleware_attr):
                return
            middleware = middleware_attr
            for middleware_item in middleware:
                if isinstance(middleware_item, CacheMiddleware):
                    from .exceptions import DuplicateCaching

                    msg = "CacheMiddleware detected in middleware stack"
                    raise DuplicateCaching(
                        msg,
                    )

    def is_duplicate_in_scope(self, scope: Scope) -> bool:
        return scope_name in scope


class CacheKeyManager:
    def __init__(self, cache: t.Any | None = None) -> None:
        self.cache = cache
        self._cache_dict = {}

    def get_cache_instance(self):
        if self.cache is None:
            from .exceptions import safe_depends_get

            self.cache = safe_depends_get("cache", self._cache_dict)
        return self.cache


class CacheMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        cache: t.Any | None = None,
        rules: Sequence[Rule] | None = None,
    ) -> None:
        self.app = app

        self.validator = CacheValidator(rules)
        self.key_manager = CacheKeyManager(cache)

        self.cache = cache

        self.rules = self.validator.rules

        self.validator.check_for_duplicate_middleware(app)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        cache = self.key_manager.get_cache_instance()
        self.cache = cache
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if self.validator.is_duplicate_in_scope(scope):
            from .exceptions import DuplicateCaching

            msg = (
                "Another `CacheMiddleware` was detected in the middleware stack.\n"
                "HINT: this exception probably occurred because:\n"
                "- You wrapped an application around `CacheMiddleware` multiple times.\n"
                "- You tried to apply `@cached()` onto an endpoint, but the application "
                "is already wrapped around a `CacheMiddleware`."
            )
            raise DuplicateCaching(
                msg,
            )
        scope[scope_name] = self
        responder = CacheResponder(self.app, rules=self.rules)
        await responder(scope, receive, send)


class _BaseCacheMiddlewareHelper:
    def __init__(self, request: Request) -> None:
        self.request = request
        if scope_name not in request.scope:
            msg = "No CacheMiddleware instance found in the ASGI scope. Did you forget to wrap the ASGI application with `CacheMiddleware`?"
            raise MissingCaching(
                msg,
            )
        middleware = request.scope[scope_name]
        if not isinstance(middleware, CacheMiddleware):
            msg = f"A scope variable named {scope_name!r} was found, but it does not contain a `CacheMiddleware` instance. It is likely that an incompatible middleware was added to the middleware stack."
            raise MissingCaching(
                msg,
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
    app: ASGIApp
    kwargs: CacheDirectives
    max_age: int | None
    s_maxage: int | None
    no_cache: bool
    no_store: bool
    no_transform: bool
    must_revalidate: bool
    proxy_revalidate: bool
    must_understand: bool
    private: bool
    public: bool
    immutable: bool
    stale_while_revalidate: int | None
    stale_if_error: int | None

    def __init__(self, app: ASGIApp, **kwargs: t.Unpack[CacheDirectives]) -> None:
        self.app = app
        self.kwargs = kwargs
        self.max_age = None
        self.s_maxage = None
        self.no_cache = False
        self.no_store = False
        self.no_transform = False
        self.must_revalidate = False
        self.proxy_revalidate = False
        self.must_understand = False
        self.private = False
        self.public = False
        self.immutable = False
        self.stale_while_revalidate = None
        self.stale_if_error = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        responder = CacheControlResponder(self.app, **self.kwargs)
        await responder(scope, receive, send)

    def process_response(self, response: t.Any) -> None:
        cache_control_parts: list[str] = []
        if getattr(self, "public", False):
            cache_control_parts.append("public")
        elif getattr(self, "private", False):
            cache_control_parts.append("private")
        if getattr(self, "no_cache", False):
            cache_control_parts.append("no-cache")
        if getattr(self, "no_store", False):
            cache_control_parts.append("no-store")
        if getattr(self, "must_revalidate", False):
            cache_control_parts.append("must-revalidate")
        max_age = getattr(self, "max_age", None)
        if max_age is not None:
            cache_control_parts.append(f"max-age={max_age}")
        if cache_control_parts:
            response.headers["Cache-Control"] = ", ".join(cache_control_parts)


def get_middleware_positions() -> dict[str, int]:
    return {position.name: position.value for position in MiddlewarePosition}


class MiddlewareStackManager:
    def __init__(
        self,
        config: t.Any | None = None,
        logger: t.Any | None = None,
    ) -> None:
        self.config = config
        self.logger = logger
        self._middleware_registry: dict[MiddlewarePosition, MiddlewareClass] = {}
        self._middleware_options: dict[MiddlewarePosition, MiddlewareOptions] = {}
        self._custom_middleware: dict[MiddlewarePosition, Middleware] = {}
        self._initialized = False

    def _ensure_dependencies(self) -> None:
        if self.config is None or self.logger is None:
            if self.config is None:
                self.config = depends.get("config")
            if self.logger is None:
                try:
                    self.logger = depends.get("logger")
                except Exception:
                    self.logger = None

    def _register_default_middleware(self) -> None:
        self._middleware_registry.update(
            {
                MiddlewarePosition.HTMX: HtmxMiddleware,
                MiddlewarePosition.CURRENT_REQUEST: CurrentRequestMiddleware,
                MiddlewarePosition.COMPRESSION: BrotliMiddleware,
            },
        )
        self._middleware_options[MiddlewarePosition.COMPRESSION] = {"quality": 3}

    def _register_conditional_middleware(self) -> None:
        self._ensure_dependencies()
        if not self.config:
            return
        from acb.adapters import get_adapter

        self._middleware_registry[MiddlewarePosition.CSRF] = CSRFMiddleware
        self._middleware_options[MiddlewarePosition.CSRF] = {
            "secret": self.config.app.secret_key.get_secret_value(),
            "cookie_name": f"{getattr(self.config.app, 'token_id', '_fb_')}_csrf",
            "cookie_secure": self.config.deployed,
        }
        if get_adapter("auth"):
            self._middleware_registry[MiddlewarePosition.SESSION] = SessionMiddleware
            self._middleware_options[MiddlewarePosition.SESSION] = {
                "secret_key": self.config.app.secret_key.get_secret_value(),
                "session_cookie": f"{getattr(self.config.app, 'token_id', '_fb_')}_app",
                "https_only": self.config.deployed,
            }
        if self.config.deployed or getattr(self.config.debug, "production", False):
            self._middleware_registry[MiddlewarePosition.SECURITY_HEADERS] = (
                SecureHeadersMiddleware
            )

    def initialize(self) -> None:
        if self._initialized:
            return
        self._register_default_middleware()
        self._register_conditional_middleware()
        self._initialized = True

    def register_middleware(
        self,
        middleware_class: MiddlewareClass,
        position: MiddlewarePosition,
        **options: t.Any,
    ) -> None:
        self._middleware_registry[position] = middleware_class
        if options:
            self._middleware_options[position] = options

    def add_custom_middleware(
        self,
        middleware: Middleware,
        position: MiddlewarePosition,
    ) -> None:
        self._custom_middleware[position] = middleware

    def build_stack(self) -> list[Middleware]:
        if not self._initialized:
            self.initialize()
        middleware_stack: dict[MiddlewarePosition, Middleware] = {}
        for position, middleware_class in self._middleware_registry.items():
            options = self._middleware_options.get(position, {})
            middleware_stack[position] = Middleware(middleware_class, **options)
        middleware_stack.update(self._custom_middleware)

        return [
            middleware_stack[position] for position in sorted(middleware_stack.keys())
        ]

    def get_middleware_info(self) -> dict[str, t.Any]:
        if not self._initialized:
            self.initialize()

        return {
            "registered": {
                pos.name: cls.__name__ for pos, cls in self._middleware_registry.items()
            },
            "custom": {
                pos.name: str(middleware)
                for pos, middleware in self._custom_middleware.items()
            },
            "positions": get_middleware_positions(),
        }


def middlewares() -> list[Middleware]:
    return MiddlewareStackManager().build_stack()

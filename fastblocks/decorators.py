import functools
import typing as t
from collections.abc import Sequence

from starlette.types import ASGIApp

from .caching import CacheDirectives, Rule
from .middleware import CacheControlMiddleware, CacheMiddleware

_P = t.ParamSpec("_P")
_T = t.TypeVar("_T", bound=ASGIApp)


class _MiddlewareFactory(t.Protocol[_P]):
    def __call__(
        self,
        app: ASGIApp,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> ASGIApp: ...


def _wrap_in_middleware[T: ASGIApp](app: T, middleware: ASGIApp) -> T:
    return t.cast("T", functools.wraps(app, updated=())(middleware))


class _CacheMiddlewareDecorator:
    def __call__(
        self,
        *,
        cache: t.Any,
        rules: Sequence[Rule] | None = None,
    ) -> t.Callable[[_T], _T]:
        def wrap(app: _T) -> _T:
            middleware = CacheMiddleware(app, cache=cache, rules=rules)
            return _wrap_in_middleware(app, middleware)

        return wrap


class _CacheControlMiddlewareDecorator:
    def __call__(self, **kwargs: t.Unpack[CacheDirectives]) -> t.Callable[[_T], _T]:
        def wrap(app: _T) -> _T:
            middleware = CacheControlMiddleware(app, **kwargs)
            return _wrap_in_middleware(app, middleware)

        return wrap


cached = _CacheMiddlewareDecorator()
cache_control = _CacheControlMiddlewareDecorator()
__all__ = ["_MiddlewareFactory", "cache_control", "cached"]

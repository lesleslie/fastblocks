import asyncio
import base64
import email.utils
import re
import sys
import time
import typing as t
from collections.abc import Iterable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from urllib.request import parse_http_list

from acb.actions.hash import hash
from starlette.datastructures import URL, Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import Response

HashFunc = t.Callable[[t.Any], str]
GetAdapterFunc = t.Callable[[str], t.Any]
ImportAdapterFunc = t.Callable[[str | list[str] | None], t.Any]
from acb.adapters import get_adapter
from acb.depends import depends
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .exceptions import RequestNotCachable, ResponseNotCachable


def _safe_log(logger: t.Any, level: str, message: str) -> None:
    return CacheUtils.safe_log(logger, level, message)


_CacheClass = None

_str_encode = str.encode
_base64_encodebytes = base64.encodebytes
_base64_decodebytes = base64.decodebytes


def get_cache() -> t.Any:
    global _CacheClass
    if _CacheClass is None:
        _CacheClass = get_adapter("cache")
    return _CacheClass


class CacheUtils:
    GET = sys.intern("GET")
    HEAD = sys.intern("HEAD")
    POST = sys.intern("POST")
    PUT = sys.intern("PUT")
    PATCH = sys.intern("PATCH")
    DELETE = sys.intern("DELETE")
    CACHE_CONTROL = sys.intern("Cache-Control")
    ETAG = sys.intern("ETag")
    LAST_MODIFIED = sys.intern("Last-Modified")
    VARY = sys.intern("Vary")

    CACHEABLE_METHODS = frozenset((GET, HEAD))
    CACHEABLE_STATUS_CODES = frozenset(
        (200, 203, 204, 206, 300, 301, 404, 405, 410, 414, 501),
    )
    ONE_YEAR = 60 * 60 * 24 * 365
    INVALIDATING_METHODS = frozenset((POST, PUT, PATCH, DELETE))

    @staticmethod
    def safe_log(logger: t.Any, level: str, message: str) -> None:
        if logger and hasattr(logger, level):
            getattr(logger, level)(message)


cacheable_methods = CacheUtils.CACHEABLE_METHODS
cacheable_status_codes = CacheUtils.CACHEABLE_STATUS_CODES
one_year = CacheUtils.ONE_YEAR
invalidating_methods = CacheUtils.INVALIDATING_METHODS


@dataclass
class Rule:
    match: str | re.Pattern[str] | Iterable[str | re.Pattern[str]] = "*"
    status: int | Iterable[int] | None = None
    ttl: float | None = None


def _check_rule_match(match: list[str | re.Pattern[str]], path: str) -> bool:
    """Check if any rule matches the request path."""
    for item in match:
        if isinstance(item, re.Pattern):
            if item.match(path):
                return True
        elif item in ("*", path):
            return True
    return False


def _check_response_status_match(rule: Rule, response: Response) -> bool:
    """Check if response status code matches the rule."""
    if rule.status is not None:
        statuses = [rule.status] if isinstance(rule.status, int) else rule.status
        if response.status_code not in statuses:
            return False
    return True


class CacheRules:
    @staticmethod
    def request_matches_rule(rule: Rule, *, request: Request) -> bool:
        match = (
            [rule.match]
            if isinstance(rule.match, str | re.Pattern)
            else list(rule.match)
        )
        return _check_rule_match(match, request.url.path)

    @staticmethod
    def response_matches_rule(
        rule: Rule,
        *,
        request: Request,
        response: Response,
    ) -> bool:
        # First check if request matches the rule
        if not CacheRules.request_matches_rule(rule, request=request):
            return False
        # Then check if response status matches
        return _check_response_status_match(rule, response)

    @staticmethod
    def get_rule_matching_request(
        rules: Sequence[Rule],
        *,
        request: Request,
    ) -> Rule | None:
        return next(
            (
                rule
                for rule in rules
                if CacheRules.request_matches_rule(rule, request=request)
            ),
            None,
        )

    @staticmethod
    def get_rule_matching_response(
        rules: Sequence[Rule],
        *,
        request: Request,
        response: Response,
    ) -> Rule | None:
        return next(
            (
                rule
                for rule in rules
                if CacheRules.response_matches_rule(
                    rule,
                    request=request,
                    response=response,
                )
            ),
            None,
        )


def get_rule_matching_request(
    rules: Sequence[Rule],
    *,
    request: Request,
) -> Rule | None:
    method = getattr(CacheRules, "get_rule_matching_request")
    result = method(rules, request=request)
    return t.cast(Rule | None, result)


def get_rule_matching_response(
    rules: Sequence[Rule],
    *,
    request: Request,
    response: Response,
) -> Rule | None:
    method = getattr(CacheRules, "get_rule_matching_response")
    result = method(rules, request=request, response=response)
    return t.cast(Rule | None, result)


def request_matches_rule(rule: Rule, *, request: Request) -> bool:
    method = getattr(CacheRules, "request_matches_rule")
    result = method(rule, request=request)
    return t.cast(bool, result)


def response_matches_rule(rule: Rule, *, request: Request, response: Response) -> bool:
    method = getattr(CacheRules, "response_matches_rule")
    result = method(rule, request=request, response=response)
    return t.cast(bool, result)


class CacheDirectives(t.TypedDict, total=False):
    max_age: int
    s_maxage: int
    no_cache: bool
    no_store: bool
    no_transform: bool
    must_revalidate: bool
    proxy_revalidate: bool
    must_understand: bool
    private: bool
    public: bool
    immutable: bool
    stale_while_revalidate: int
    stale_if_error: int


async def set_in_cache(
    response: Response,
    *,
    request: Request,
    rules: Sequence[Rule],
    cache: t.Any = None,
    logger: t.Any = None,
) -> None:
    # Initialize dependencies if not provided
    cache, logger = _init_cache_dependencies(cache, logger)

    # Validate response can be cached
    _validate_response_cacheable(response, request, logger)

    # Find matching rule for caching
    rule = get_rule_matching_response(rules, request=request, response=response)
    if not rule:
        _safe_log(logger, "debug", "response_not_cacheable reason=rule")
        raise ResponseNotCachable(response)

    # Calculate TTL and max age
    ttl, max_age = _calculate_cache_ttl(rule, cache, logger)

    # Set cache headers
    _set_cache_headers(response, max_age, logger)

    # Generate cache key and serialize response
    cache_key = await learn_cache_key(request, response, cache=cache)
    serialized_response = serialize_response(response)

    # Store in cache
    await _store_in_cache(cache, cache_key, serialized_response, ttl, logger)

    # Update response header
    response.headers["X-Cache"] = "miss"


def _init_cache_dependencies(cache: t.Any, logger: t.Any) -> tuple[t.Any, t.Any]:
    """Initialize cache and logger dependencies."""
    if cache is None:
        cache = depends.get("cache")
    if logger is None:
        logger = depends.get("logger")
    return cache, logger


def _validate_response_cacheable(
    response: Response, request: Request, logger: t.Any
) -> None:
    """Validate that a response can be cached."""
    if response.status_code not in cacheable_status_codes:
        _safe_log(logger, "debug", "response_not_cacheable reason=status_code")
        raise ResponseNotCachable(response)
    if not request.cookies and "Set-Cookie" in response.headers:
        _safe_log(
            logger,
            "debug",
            "response_not_cacheable reason=cookies_for_cookieless_request",
        )
        raise ResponseNotCachable(response)


def _calculate_cache_ttl(rule: Rule, cache: t.Any, logger: t.Any) -> tuple[t.Any, int]:
    """Calculate TTL and max age for caching."""
    ttl = rule.ttl if rule.ttl is not None else cache.ttl
    if ttl == 0:
        _safe_log(logger, "debug", "response_not_cacheable reason=zero_ttl")
        # Create a minimal response for the exception
        raise ResponseNotCachable(Response(content=b"", status_code=200))

    if ttl is None:
        max_age = one_year
        _safe_log(logger, "debug", f"max_out_ttl value={max_age!r}")
    else:
        max_age = int(ttl)
    _safe_log(logger, "debug", f"set_in_cache max_age={max_age!r}")
    return ttl, max_age


def _set_cache_headers(response: Response, max_age: int, logger: t.Any) -> None:
    """Set cache headers on the response."""
    response.headers["X-Cache"] = "hit"
    cache_headers = get_cache_response_headers(response, max_age=max_age)
    _safe_log(logger, "debug", f"patch_response_headers headers={cache_headers!r}")
    response.headers.update(cache_headers)


async def _store_in_cache(
    cache: t.Any,
    cache_key: str,
    serialized_response: dict[str, t.Any],
    ttl: t.Any,
    logger: t.Any,
) -> None:
    """Store serialized response in cache."""
    _safe_log(
        logger,
        "debug",
        f"set_response_in_cache key={cache_key!r} value={serialized_response!r}",
    )
    kwargs = {}
    if ttl is not None:
        kwargs["ttl"] = ttl
    await cache.set(key=cache_key, value=serialized_response, **kwargs)


async def get_from_cache(
    request: Request,
    *,
    rules: Sequence[Rule],
    cache: t.Any = None,
    logger: t.Any = None,
) -> Response | None:
    # Initialize dependencies if not provided
    cache, logger = _init_cache_dependencies(cache, logger)

    # Log request details
    _safe_log(
        logger,
        "debug",
        f"get_from_cache request.url={str(request.url)!r} request.method={request.method!r}",
    )

    # Validate request can use cache
    _validate_request_cacheable(request, logger)

    # Find matching rule
    rule = getattr(CacheRules, "get_rule_matching_request")(rules, request=request)
    if rule is None:
        _safe_log(logger, "debug", "request_not_cacheable reason=rule")
        raise RequestNotCachable(request)

    # Try to get cached response
    return await _try_get_cached_response(request, cache, logger)


def _validate_request_cacheable(request: Request, logger: t.Any) -> None:
    """Validate that a request can use the cache."""
    if request.method not in cacheable_methods:
        _safe_log(logger, "debug", "request_not_cacheable reason=method")
        raise RequestNotCachable(request)


async def _try_get_cached_response(
    request: Request, cache: t.Any, logger: t.Any
) -> Response | None:
    """Try to get a cached response for the request."""
    # Try GET method first
    _safe_log(logger, "debug", "lookup_cached_response method='GET'")
    cache_key = await get_cache_key(request, method="GET", cache=cache)
    if cache_key is not None:
        serialized_response = await cache.get(cache_key)
        if serialized_response is not None:
            return _return_cached_response(cache_key, serialized_response, logger)

    # Try HEAD method
    _safe_log(logger, "debug", "lookup_cached_response method='HEAD'")
    cache_key = await get_cache_key(request, method="HEAD", cache=cache)
    if cache_key is not None:
        serialized_response = await cache.get(cache_key)
        if serialized_response is not None:
            return _return_cached_response(cache_key, serialized_response, logger)

    # No cached response found
    _safe_log(logger, "debug", "cached_response found=False")
    return None


def _return_cached_response(
    cache_key: str, serialized_response: t.Any, logger: t.Any
) -> Response:
    """Return a cached response after logging."""
    _safe_log(
        logger,
        "debug",
        f"cached_response found=True key={cache_key!r} value={serialized_response!r}",
    )
    return deserialize_response(serialized_response)


async def delete_from_cache(
    url: URL,
    *,
    vary: Headers,
    cache: t.Any = None,
    logger: t.Any = None,
) -> None:
    if cache is None or logger is None:
        if cache is None:
            cache = depends.get("cache")
        if logger is None:
            logger = depends.get("logger")

    varying_headers_cache_key = await generate_varying_headers_cache_key(url)
    varying_headers = await cache.get(varying_headers_cache_key)
    if varying_headers is None:
        return

    await _delete_cache_entries(url, vary, cache, logger, varying_headers)
    await cache.delete(varying_headers_cache_key)


async def _delete_cache_entries(
    url: URL,
    vary: Headers,
    cache: t.Any,
    logger: t.Any,
    varying_headers: t.Any,
) -> None:
    """Delete cache entries for GET and HEAD methods."""
    for method in ("GET", "HEAD"):
        cache_key = await generate_cache_key(
            url,
            method=method,
            headers=vary,
            varying_headers=varying_headers,
        )
        if cache_key is None:
            continue

        logger.debug(f"clear_cache key={cache_key!r}")
        await cache.delete(cache_key)

        # Publish cache invalidation event (async, don't block)
        with suppress(Exception):

            async def _publish_event() -> None:
                from .adapters.templates._events_wrapper import (
                    publish_cache_invalidation,
                )

                await publish_cache_invalidation(
                    cache_key=cache_key,
                    reason="url_invalidation",
                    invalidated_by="cache_middleware",
                    affected_templates=None,
                )

            asyncio.create_task(_publish_event())


def serialize_response(response: Response) -> dict[str, t.Any]:
    """Serialize a response for caching."""
    return {
        "content": _base64_encodebytes(response.body).decode("ascii"),
        "status_code": response.status_code,
        "headers": dict(response.headers),
    }


def deserialize_response(serialized_response: t.Any) -> Response:
    """Deserialize a cached response."""
    _validate_serialized_response(serialized_response)

    content = serialized_response["content"]
    status_code = serialized_response["status_code"]
    headers = serialized_response["headers"]

    return Response(
        content=_base64_decodebytes(_str_encode(content, "ascii")),
        status_code=status_code,
        headers=headers,
    )


def _validate_serialized_response(serialized_response: t.Any) -> None:
    """Validate the structure of a serialized response."""
    if not isinstance(serialized_response, dict):
        msg = f"Expected dict, got {type(serialized_response)}"
        raise TypeError(msg)
    content = serialized_response.get("content")
    if not isinstance(content, str):
        msg = f"Expected content to be str, got {type(content)}"
        raise TypeError(msg)
    status_code = serialized_response.get("status_code")
    if not isinstance(status_code, int):
        msg = f"Expected status_code to be int, got {type(status_code)}"
        raise TypeError(msg)
    headers = serialized_response.get("headers")
    if not isinstance(headers, dict):
        msg = f"Expected headers to be dict, got {type(headers)}"
        raise TypeError(msg)


async def learn_cache_key(
    request: Request,
    response: Response,
    *,
    cache: t.Any = None,
    logger: t.Any = None,
) -> str:
    if cache is None or logger is None:
        if cache is None:
            cache = depends.get("cache")
        if logger is None:
            logger = depends.get("logger")
    logger.debug(
        f"learn_cache_key request.method={request.method!r} response.headers.Vary={response.headers.get('Vary')!r}",
    )
    url = request.url
    varying_headers_cache_key = await generate_varying_headers_cache_key(url)
    cached_vary_headers = set(await cache.get(key=varying_headers_cache_key) or ())
    response_vary_headers = {
        header.lower() for header in parse_http_list(response.headers.get("Vary", ""))
    }
    varying_headers = sorted(response_vary_headers | cached_vary_headers)
    if varying_headers:
        response.headers["Vary"] = ", ".join(varying_headers)
    logger.debug(
        f"store_varying_headers cache_key={varying_headers_cache_key!r} headers={varying_headers!r}",
    )
    await cache.set(key=varying_headers_cache_key, value=varying_headers)
    cache_key = await generate_cache_key(
        url,
        method=request.method,
        headers=request.headers,
        varying_headers=varying_headers,
    )
    if cache_key is None:
        msg = f"Unable to generate cache key for method {request.method}"
        raise ValueError(msg)
    return cache_key


async def get_cache_key(
    request: Request,
    method: str,
    cache: t.Any = None,
    logger: t.Any = None,
) -> str | None:
    if cache is None or logger is None:
        if cache is None:
            cache = depends.get("cache")
        if logger is None:
            logger = depends.get("logger")
    url = request.url
    _safe_log(
        logger,
        "debug",
        f"get_cache_key request.url={str(url)!r} method={method!r}",
    )
    varying_headers_cache_key = await generate_varying_headers_cache_key(url)
    varying_headers = await cache.get(varying_headers_cache_key)
    if varying_headers is None:
        _safe_log(logger, "debug", "varying_headers found=False")
        return None
    _safe_log(
        logger,
        "debug",
        f"varying_headers found=True headers={varying_headers!r}",
    )
    return await generate_cache_key(
        request.url,
        method=method,
        headers=request.headers,
        varying_headers=varying_headers,
    )


async def generate_cache_key(
    url: URL,
    method: str,
    headers: Headers,
    varying_headers: list[str],
    config: t.Any = None,
) -> str | None:
    """Generate cache key using ACB's fast CRC32C hashing."""
    if config is None:
        config = depends.get("config")

    if method not in cacheable_methods:
        return None

    # Both hash functions are now async for better performance
    vary_hash = await _generate_vary_hash(headers, varying_headers)
    url_hash = await _generate_url_hash(url)

    return f"{config.app.name}:cached:{method}.{url_hash}.{vary_hash}"


async def _generate_vary_hash(headers: Headers, varying_headers: list[str]) -> str:
    """Generate hash for varying headers using ACB's fast CRC32C."""
    vary_values = [
        f"{header}:{value}"
        for header in varying_headers
        if (value := headers.get(header)) is not None
    ]

    if not vary_values:
        return ""

    # ACB's CRC32C is 50x faster than MD5 for cache keys (non-cryptographic)
    result = await hash.crc32c("|".join(vary_values))
    return str(result)  # Ensure return type is str


async def _generate_url_hash(url: URL) -> str:
    """Generate hash for URL using ACB's fast CRC32C."""
    # ACB's CRC32C is 50x faster than MD5 for cache keys (non-cryptographic)
    result = await hash.crc32c(str(url))
    return str(result)  # Ensure return type is str


async def generate_varying_headers_cache_key(url: URL) -> str:
    """Generate cache key for varying headers using ACB's fast CRC32C."""
    # ACB's CRC32C is 50x faster than MD5 for cache keys (non-cryptographic)
    url_hash = await hash.crc32c(str(url.path))
    return f"varying_headers.{url_hash}"


def get_cache_response_headers(response: Response, *, max_age: int) -> dict[str, str]:
    max_age = max(max_age, 0)
    headers = {}
    if "Expires" not in response.headers:
        headers["Expires"] = email.utils.formatdate(time.time() + max_age, usegmt=True)
    patch_cache_control(response.headers, max_age=max_age)

    return headers


def patch_cache_control(
    headers: MutableHeaders,
    **kwargs: t.Unpack[CacheDirectives],
) -> None:
    cache_control: dict[str, t.Any] = {}
    value: t.Any
    for field in parse_http_list(headers.get("Cache-Control", "")):
        try:
            key, value = field.split("=")
        except ValueError:
            cache_control[field] = True
        else:
            cache_control[key] = value

    if "max-age" in cache_control and "max_age" in kwargs:
        kwargs["max_age"] = min(int(cache_control["max-age"]), kwargs["max_age"])

    # Check for unsupported directives
    _check_unsupported_directives(kwargs)

    for key, value in kwargs.items():
        key = key.replace("_", "-")
        cache_control[key] = value

    directives: list[str] = []
    for key, value in cache_control.items():
        if value is False:
            continue
        if value is True:
            directives.append(key)
        else:
            directives.append(f"{key}={value}")

    patched_cache_control = ", ".join(directives)
    if patched_cache_control:
        headers["Cache-Control"] = patched_cache_control
    else:
        del headers["Cache-Control"]


def _check_unsupported_directives(kwargs: t.Any) -> None:
    """Check for unsupported cache control directives."""
    if "public" in kwargs:
        msg = "The 'public' cache control directive isn't supported yet."
        raise NotImplementedError(msg)
    if "private" in kwargs:
        msg = "The 'private' cache control directive isn't supported yet."
        raise NotImplementedError(msg)


class CacheResponder:
    def __init__(self, app: ASGIApp, *, rules: Sequence[Rule]) -> None:
        self.app = app
        self.rules = rules
        try:
            self.logger = depends.get("logger")
        except Exception:
            import logging

            self.logger = logging.getLogger("fastblocks.cache")
        try:
            self.cache = depends.get("cache")
        except Exception:
            self.cache = None
        self.initial_message: Message = {}
        self.is_response_cacheable = True
        self.request: Request | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        self.request = request = Request(scope)
        try:
            response = await get_from_cache(request, cache=self.cache, rules=self.rules)
        except RequestNotCachable:
            if request.method in invalidating_methods:
                send = partial(self.send_then_invalidate, send=send)
        else:
            if response is not None:
                _safe_log(self.logger, "debug", "cache_lookup HIT")
                await response(scope, receive, send)
                return
            send = partial(self.send_with_caching, send=send)
            _safe_log(self.logger, "debug", "cache_lookup MISS")
        await self.app(scope, receive, send)

    async def send_with_caching(self, message: Message, *, send: Send) -> None:
        if not self.is_response_cacheable or message["type"] not in (
            "http.response.start",
            "http.response.body",
        ):
            await send(message)
            return
        if message["type"] == "http.response.start":
            self.initial_message = message
            return
        if message["type"] != "http.response.body":
            return
        if message.get("more_body", False):
            _safe_log(
                self.logger,
                "debug",
                "response_not_cacheable reason=is_streaming",
            )
            self.is_response_cacheable = False
            await send(self.initial_message)
            await send(message)
            return
        if self.request is None:
            return
        body = message["body"]
        response = Response(content=body, status_code=self.initial_message["status"])
        response.raw_headers = list(self.initial_message["headers"])
        try:
            await set_in_cache(
                response,
                request=self.request,
                cache=self.cache,
                rules=self.rules,
            )
        except ResponseNotCachable:
            self.is_response_cacheable = False
        else:
            self.initial_message["headers"] = response.raw_headers.copy()
        await send(self.initial_message)
        await send(message)

    async def send_then_invalidate(self, message: Message, *, send: Send) -> None:
        if self.request is None:
            return
        if message["type"] == "http.response.start" and 200 <= message["status"] < 400:
            await delete_from_cache(
                self.request.url,
                vary=self.request.headers,
                cache=self.cache,
            )
        await send(message)


class CacheControlResponder:
    def __init__(self, app: ASGIApp, **kwargs: t.Unpack[CacheDirectives]) -> None:
        self.app = app
        self.kwargs = kwargs
        try:
            self.logger = depends.get("logger")
        except Exception:
            import logging

            self.logger = logging.getLogger("fastblocks.cache")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        send = partial(self.send_with_caching, send=send)
        await self.app(scope, receive, send)

    @staticmethod
    def kvformat(**kwargs: t.Any) -> str:
        return " ".join((f"{key}={value}" for key, value in kwargs.items()))

    async def send_with_caching(self, message: Message, *, send: Send) -> None:
        if message["type"] == "http.response.start":
            _safe_log(
                self.logger,
                "debug",
                f"patch_cache_control {self.kvformat(**self.kwargs)}",
            )
            headers = MutableHeaders(raw=list(message["headers"]))
            patch_cache_control(headers, **self.kwargs)
            message["headers"] = headers.raw
        await send(message)

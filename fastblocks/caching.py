import base64
import email.utils
import re
import time
import typing as t
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import partial
from urllib.request import parse_http_list

from acb.actions.hash import hash
from acb.adapters import import_adapter
from acb.config import Config
from acb.depends import depends
from acb.logger import Logger
from starlette.datastructures import URL, Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .exceptions import RequestNotCachable, ResponseNotCachable

Cache = import_adapter()  # type: ignore

cachable_methods = frozenset(("GET", "HEAD"))
cachable_status_codes = frozenset(
    (200, 203, 204, 206, 300, 301, 404, 405, 410, 414, 501)
)
one_year = 60 * 60 * 24 * 365
invalidating_methods = frozenset(("POST", "PUT", "PATCH", "DELETE"))


@dataclass
class Rule:
    match: str | re.Pattern[str] | Iterable[str | re.Pattern[str]] = "*"
    status: int | Iterable[int] | None = None
    ttl: float | None = None


def request_matches_rule(
    rule: Rule,
    *,
    request: Request,
) -> bool:
    match = (
        [rule.match] if isinstance(rule.match, (str, re.Pattern)) else list(rule.match)
    )
    for item in match:
        if isinstance(item, re.Pattern):
            if item.match(request.url.path):
                return True
        elif item in ("*", request.url.path):
            return True
    return False


def response_matches_rule(rule: Rule, *, request: Request, response: Response) -> bool:
    if not request_matches_rule(rule, request=request):
        return False
    if rule.status is not None:
        statuses = [rule.status] if isinstance(rule.status, int) else rule.status
        if response.status_code not in statuses:
            return False
    return True


def get_rule_matching_request(
    rules: Sequence[Rule], *, request: Request
) -> Rule | None:
    return next(
        (rule for rule in rules if request_matches_rule(rule, request=request)), None
    )


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
            if response_matches_rule(rule, request=request, response=response)
        ),
        None,
    )


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


@depends.inject
async def set_in_cache(
    response: Response,
    *,
    request: Request,
    rules: Sequence[Rule],
    cache: Cache = depends(),
    logger: Logger = depends(),
) -> None:
    if response.status_code not in cachable_status_codes:
        logger.debug("response_not_cachable reason=status_code")
        raise ResponseNotCachable(response)
    if not request.cookies and "Set-Cookie" in response.headers:
        logger.debug("response_not_cachable reason=cookies_for_cookieless_request")
        raise ResponseNotCachable(response)
    rule = get_rule_matching_response(rules, request=request, response=response)
    if not rule:
        logger.debug("response_not_cachable reason=rule")
        raise ResponseNotCachable(response)
    ttl = rule.ttl if rule.ttl is not None else cache.ttl
    if ttl == 0:
        logger.debug("response_not_cachable reason=zero_ttl")
        raise ResponseNotCachable(response)
    if ttl is None:
        max_age = one_year
        logger.debug(f"max_out_ttl value={max_age!r}")
    else:
        max_age = int(ttl)
    logger.debug(f"set_in_cache max_age={max_age!r}")
    response.headers["X-Cache"] = "hit"
    cache_headers = get_cache_response_headers(response, max_age=max_age)
    logger.debug(f"patch_response_headers headers={cache_headers!r}")
    response.headers.update(cache_headers)
    cache_key = await learn_cache_key(request, response, cache=cache)
    logger.debug(f"learnt_cache_key cache_key={cache_key!r}")
    serialized_response = serialize_response(response)
    logger.debug(
        f"set_response_in_cache key={cache_key!r} value={serialized_response!r}"
    )
    kwargs = {}
    if ttl is not None:
        kwargs["ttl"] = ttl
    await cache.set(key=cache_key, value=serialized_response, **kwargs)
    response.headers["X-Cache"] = "miss"


@depends.inject
async def get_from_cache(
    request: Request,
    *,
    rules: Sequence[Rule],
    cache: Cache = depends(),
    logger: Logger = depends(),
) -> Response | None:
    logger.debug(
        f"get_from_cache "
        f"request.url={str(request.url)!r} "
        f"request.method={request.method!r}"
    )
    if request.method not in cachable_methods:
        logger.debug("request_not_cachable reason=method")
        raise RequestNotCachable(request)
    rule = get_rule_matching_request(rules, request=request)
    if rule is None:
        logger.debug("request_not_cachable reason=rule")
        raise RequestNotCachable(request)
    logger.debug("lookup_cached_response method='GET'")
    cache_key = await get_cache_key(request, method="GET", cache=cache)
    if cache_key is None:
        logger.debug("cache_key found=False")
        return None
    logger.debug(f"cache_key found=True cache_key={cache_key!r}")
    serialized_response = await cache.get(cache_key)
    if serialized_response is None:
        logger.debug("lookup_cached_response method='HEAD'")
        cache_key = await get_cache_key(request, method="HEAD", cache=cache)
        if cache_key is None:
            return None
        logger.debug(f"cache_key found=True cache_key={cache_key!r}")
        serialized_response = await cache.get(cache_key)
    if serialized_response is None:
        logger.debug("cached_response found=False")
        return None
    logger.debug(
        f"cached_response found=True key={cache_key!r} value={serialized_response!r}"
    )
    return deserialize_response(serialized_response)


@depends.inject
async def delete_from_cache(
    url: URL, *, vary: Headers, cache: Cache = depends(), logger: Logger = depends()
) -> None:
    varying_headers_cache_key = generate_varying_headers_cache_key(url)
    varying_headers = await cache.get(varying_headers_cache_key)
    if varying_headers is None:
        return
    for method in "GET", "HEAD":
        cache_key = generate_cache_key(
            url,
            method=method,
            headers=vary,
            varying_headers=varying_headers,
        )
        logger.debug(f"clear_cache key={cache_key!r}")
        await cache.delete(cache_key)

    await cache.delete(varying_headers_cache_key)


def serialize_response(response: Response) -> dict[str, t.Any]:
    return {
        "content": base64.encodebytes(response.body).decode("ascii"),
        "status_code": response.status_code,
        "headers": dict(response.headers),
    }


def deserialize_response(
    serialized_response: t.Any,
) -> Response:
    if not isinstance(serialized_response, dict):
        raise TypeError(f"Expected dict, got {type(serialized_response)}")

    content = serialized_response.get("content")
    if not isinstance(content, str):
        raise TypeError(f"Expected content to be str, got {type(content)}")

    status_code = serialized_response.get("status_code")
    if not isinstance(status_code, int):
        raise TypeError(f"Expected status_code to be int, got {type(status_code)}")

    headers = serialized_response.get("headers")
    if not isinstance(headers, dict):
        raise TypeError(f"Expected headers to be dict, got {type(headers)}")

    return Response(
        content=base64.decodebytes(content.encode("ascii")),
        status_code=status_code,
        headers=headers,
    )


@depends.inject
async def learn_cache_key(
    request: Request,
    response: Response,
    *,
    cache: Cache = depends(),
    logger: Logger = depends(),
) -> str:
    logger.debug(
        "learn_cache_key "
        f"request.method={request.method!r} "
        f"response.headers.Vary={response.headers.get('Vary')!r}"
    )
    url = request.url
    varying_headers_cache_key = generate_varying_headers_cache_key(url)
    cached_vary_headers = set(await cache.get(key=varying_headers_cache_key) or ())
    response_vary_headers = {
        header.lower() for header in parse_http_list(response.headers.get("Vary", ""))
    }
    varying_headers = sorted(response_vary_headers | cached_vary_headers)
    if varying_headers:
        response.headers["Vary"] = ", ".join(varying_headers)
    logger.debug(
        "store_varying_headers "
        f"cache_key={varying_headers_cache_key!r} headers={varying_headers!r}"
    )
    await cache.set(key=varying_headers_cache_key, value=varying_headers)
    return generate_cache_key(
        url,
        method=request.method,
        headers=request.headers,
        varying_headers=varying_headers,
    )


async def get_cache_key(
    request: Request, method: str, cache: Cache = depends(), logger: Logger = depends()
) -> str | None:
    url = request.url
    logger.debug(f"get_cache_key request.url={str(url)!r} method={method!r}")
    varying_headers_cache_key = generate_varying_headers_cache_key(url)
    varying_headers = await cache.get(varying_headers_cache_key)
    if varying_headers is None:
        logger.debug("varying_headers found=False")
        return None
    logger.debug(f"varying_headers found=True headers={varying_headers!r}")
    return generate_cache_key(
        request.url,
        method=method,
        headers=request.headers,
        varying_headers=varying_headers,
    )


@depends.inject
def generate_cache_key(
    url: URL,
    method: str,
    headers: Headers,
    varying_headers: list[str],
    config: Config = depends(),
) -> str | None:
    if method not in cachable_methods:
        return None

    vary_hash = ""
    for header in varying_headers:
        value = headers.get(header)
        if value is not None:
            vary_hash = hash.md5(value, usedforsecurity=False)
    url_hash = hash.md5(str(url), ascii=True, usedforsecurity=False)
    return f"{config.app.name}:cached:{method}.{url_hash}.{vary_hash}"


def generate_varying_headers_cache_key(url: URL) -> str:
    url_hash = hash.md5(str(url.path), ascii=True, usedforsecurity=False)
    return f"varying_headers.{url_hash}"


def get_cache_response_headers(response: Response, *, max_age: int) -> dict[str, str]:
    if max_age < 0:
        max_age = 0
    headers = {}
    if "Expires" not in response.headers:
        headers["Expires"] = email.utils.formatdate(time.time() + max_age, usegmt=True)
    patch_cache_control(response.headers, max_age=max_age)
    return headers


def patch_cache_control(
    headers: MutableHeaders, **kwargs: t.Unpack[CacheDirectives]
) -> None:
    cache_control: dict[str, t.Any] = {}
    value: t.Any
    for field in parse_http_list(headers.get("Cache-Control", "")):
        try:
            key, value = field.split("=")
        except ValueError:  # noqa: PERF203
            cache_control[field] = True
        else:
            cache_control[key] = value
    if "max-age" in cache_control and "max_age" in kwargs:
        kwargs["max_age"] = min(int(cache_control["max-age"]), kwargs["max_age"])
    if "public" in kwargs:
        raise NotImplementedError(
            "The 'public' cache control directive isn't supported yet."
        )
    if "private" in kwargs:
        raise NotImplementedError(
            "The 'private' cache control directive isn't supported yet."
        )
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


class CacheResponder:
    logger: Logger = depends()
    cache: Cache = depends()

    def __init__(
        self,
        app: ASGIApp,
        *,
        rules: Sequence[Rule],
    ) -> None:
        self.app = app
        self.rules = rules
        self.initial_message: Message = {}
        self.is_response_cachable = True
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
                self.logger.debug("cache_lookup HIT")
                await response(scope, receive, send)
                return
            send = partial(self.send_with_caching, send=send)
            self.logger.debug("cache_lookup MISS")

        await self.app(scope, receive, send)

    async def send_with_caching(self, message: Message, *, send: Send) -> None:
        if not self.is_response_cachable or message["type"] not in (
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
            self.logger.debug("response_not_cachable reason=is_streaming")
            self.is_response_cachable = False
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
                response, request=self.request, cache=self.cache, rules=self.rules
            )
        except ResponseNotCachable:
            self.is_response_cachable = False
        else:
            self.initial_message["headers"] = list(response.raw_headers)
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
    logger: Logger = depends()

    def __init__(self, app: ASGIApp, **kwargs: t.Unpack[CacheDirectives]) -> None:
        self.app = app
        self.kwargs = kwargs

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        send = partial(self.send_with_caching, send=send)
        await self.app(scope, receive, send)

    @staticmethod
    def kvformat(**kwargs: t.Any) -> str:
        return " ".join(f"{key}={value}" for key, value in kwargs.items())

    async def send_with_caching(self, message: Message, *, send: Send) -> None:
        if message["type"] == "http.response.start":
            self.logger.debug(f"patch_cache_control {self.kvformat(**self.kwargs)}")
            headers = MutableHeaders(raw=list(message["headers"]))
            patch_cache_control(headers, **self.kwargs)
            message["headers"] = headers.raw

        await send(message)

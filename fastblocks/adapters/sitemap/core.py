"""FastBlocks Sitemap Core Implementation.

Core sitemap functionality moved from standalone module to adapter pattern.
Based on asgi-sitemaps by Florian Dahlitz with FastBlocks enhancements.

Original asgi-sitemaps library:
- Author: Florian Dahlitz
- Repository: https://github.com/DahlitzFlorian/asgi-sitemaps
- License: MIT
"""

import contextvars
import datetime as dt
import inspect
import typing as t
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Sequence,
)
from typing import TypeVar, cast
from urllib.parse import urljoin, urlsplit

from acb.debug import debug
from acb.depends import depends

if t.TYPE_CHECKING:
    from starlette.types import Scope

T = TypeVar("T")
ItemsTypes = Iterable[T] | Awaitable[Iterable[T]] | AsyncIterable[T]

SCOPE_CTX_VAR = contextvars.ContextVar["Scope"]("fastblocks.sitemaps.scope")


class BaseSitemap[T]:
    protocol: str = "auto"

    def __init__(self) -> None:
        if self.protocol not in ("http", "https", "auto"):
            raise ValueError(f"Invalid protocol: {self.protocol}")
        debug(f"BaseSitemap: Initialized with protocol={self.protocol}")

    def items(self) -> ItemsTypes[T]:
        raise NotImplementedError("Subclasses must implement items() method")

    def location(self, item: T) -> str:
        raise NotImplementedError("Subclasses must implement location() method")

    def lastmod(self, item: T) -> dt.datetime | None:
        return None

    def changefreq(self, item: T) -> str | None:
        return None

    def priority(self, item: T) -> float:
        return 0.5

    @property
    def scope(self) -> "Scope":
        try:
            return SCOPE_CTX_VAR.get()
        except LookupError as e:
            raise RuntimeError(
                "Scope accessed outside of an ASGI request. "
                "Ensure sitemap generation happens within request context."
            ) from e


class SitemapApp:
    def __init__(
        self,
        sitemaps: BaseSitemap[t.Any] | list[BaseSitemap[t.Any]],
        *,
        domain: str,
        cache_ttl: int = 3600,
    ) -> None:
        self._sitemaps = (
            [sitemaps] if isinstance(sitemaps, BaseSitemap) else list(sitemaps)
        )
        self._domain = domain
        self._cache_ttl = cache_ttl
        debug(
            f"SitemapApp: Initialized with {len(self._sitemaps)} sitemaps, domain={domain}"
        )

    async def __call__(
        self,
        scope: "Scope",
        receive: Callable[[], Awaitable[dict[str, t.Any]]],
        send: Callable[[dict[str, t.Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self._send_error(send, 404)
            return

        debug(
            f"SitemapApp: Processing sitemap request for {scope.get('path', 'unknown')}"
        )

        try:
            content = await generate_sitemap(
                self._sitemaps, scope=scope, domain=self._domain
            )

            headers = [
                [b"content-type", b"application/xml; charset=utf-8"],
                [b"content-length", str(len(content)).encode()],
                [b"cache-control", f"public, max-age={self._cache_ttl}".encode()],
            ]

            message = await receive()
            if message["type"] != "http.request":
                await self._send_error(send, 400)
                return

            await send(
                {"type": "http.response.start", "status": 200, "headers": headers}
            )
            await send({"type": "http.response.body", "body": content})

            debug(f"SitemapApp: Sent sitemap response ({len(content)} bytes)")

        except Exception as e:
            debug(f"SitemapApp: Error generating sitemap: {e}")
            await self._send_error(send, 500)

    async def _send_error(
        self, send: Callable[[dict[str, t.Any]], Awaitable[None]], status: int
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": f"Error {status}".encode(),
            }
        )


async def generate_sitemap(
    sitemaps: Sequence[BaseSitemap[t.Any]], *, scope: "Scope", domain: str
) -> bytes:
    debug(f"generate_sitemap: Starting generation for {len(sitemaps)} sitemaps")

    SCOPE_CTX_VAR.set(scope)

    cache_key = f"fastblocks:sitemap:{domain}"
    cached_content = await _get_cached_sitemap(cache_key)
    if cached_content:
        debug("generate_sitemap: Returning cached sitemap")
        return cached_content

    try:
        content = await _generate_sitemap_content(sitemaps, scope=scope, domain=domain)

        await _cache_sitemap(cache_key, content)

        debug(f"generate_sitemap: Generated {len(content)} bytes")
        return content

    except Exception as e:
        debug(f"generate_sitemap: Error during generation: {e}")
        raise


async def _generate_sitemap_content(
    sitemaps: Sequence[BaseSitemap[t.Any]], *, scope: "Scope", domain: str
) -> bytes:
    async def _lines() -> AsyncIterator[bytes]:
        yield b'<?xml version="1.0" encoding="utf-8"?>'
        yield b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        total_urls = 0
        for sitemap_idx, sitemap in enumerate(sitemaps):
            debug(
                f"generate_sitemap: Processing sitemap {sitemap_idx + 1}/{len(sitemaps)}"
            )
            try:
                async for item in _ensure_async_iterator(sitemap.items()):
                    yield 4 * b" " + b"<url>"
                    fields = get_fields(sitemap, item, scope=scope, domain=domain)
                    for name, value in fields.items():
                        escaped_value = _escape_xml(value)
                        yield 8 * b" " + f"<{name}>{escaped_value}</{name}>".encode()
                    yield 4 * b" " + b"</url>"
                    total_urls += 1
            except Exception as e:
                debug(f"generate_sitemap: Error processing sitemap {sitemap_idx}: {e}")
        yield b"</urlset>"
        debug(f"generate_sitemap: Generated {total_urls} URLs")

    return b"\n".join([line async for line in _lines()])


async def _ensure_async_iterator[T](items: ItemsTypes[T]) -> AsyncIterator[T]:
    try:
        if hasattr(items, "__aiter__"):
            items_async = cast(AsyncIterable[T], items)
            async for item in items_async:
                yield item
        elif inspect.isawaitable(items):
            items_awaitable = items
            resolved_items = await items_awaitable
            for item in resolved_items:
                yield item
        else:
            items_sync = items
            for item in items_sync:
                yield item
    except Exception as e:
        debug(f"_ensure_async_iterator: Error processing items: {e}")


def get_fields(
    sitemap: BaseSitemap[T], item: T, *, scope: "Scope", domain: str
) -> dict[str, str]:
    if sitemap.protocol == "auto":
        protocol = scope.get("scheme", "https")
    else:
        protocol = sitemap.protocol

    try:
        location = sitemap.location(item)
        lastmod = sitemap.lastmod(item)
        changefreq = sitemap.changefreq(item)
        priority = sitemap.priority(item)

        parsed_location = urlsplit(location)
        if parsed_location.scheme or parsed_location.netloc:
            raise ValueError(f"Location contains scheme or domain: {location}")

        fields: dict[str, str] = {}

        fields["loc"] = urljoin(f"{protocol}://{domain}", location)

        if lastmod is not None:
            fields["lastmod"] = lastmod.strftime("%Y-%m-%d")
        if changefreq is not None:
            fields["changefreq"] = changefreq

        priority_value = max(0.0, min(1.0, priority))
        fields["priority"] = f"{priority_value:.1f}"

        return fields

    except Exception as e:
        debug(f"get_fields: Error processing item {item}: {e}")
        return {"loc": urljoin(f"{protocol}://{domain}", "/"), "priority": "0.5"}


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


async def _get_cached_sitemap(cache_key: str) -> bytes | None:
    try:
        cache = await depends.get("cache")
        if cache and hasattr(cache, "get"):
            cached_data = await cache.get(cache_key)
            if cached_data:
                debug(f"_get_cached_sitemap: Cache hit for {cache_key}")
                return (
                    cached_data
                    if isinstance(cached_data, bytes)
                    else cached_data.encode()
                )
    except Exception as e:
        debug(f"_get_cached_sitemap: Cache error: {e}")

    return None


async def _cache_sitemap(cache_key: str, content: bytes) -> None:
    try:
        cache = await depends.get("cache")
        if cache and hasattr(cache, "set"):
            await cache.set(cache_key, content, ttl=3600)
            debug(f"_cache_sitemap: Cached sitemap ({len(content)} bytes)")
    except Exception as e:
        debug(f"_cache_sitemap: Cache error: {e}")

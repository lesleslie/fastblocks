"""D1 coverage tests for fastblocks/adapters/sitemap/core.py.

Public API of the sitemap core module:
- ``BaseSitemap`` - abstract-style base for sitemap subclasses
- ``SitemapApp`` - ASGI app that emits XML for ``/sitemap.xml`` requests
- ``generate_sitemap`` - top-level coroutine that builds the XML body
- ``get_fields`` - per-item field helper (loc, lastmod, changefreq, priority)
- ``_escape_xml`` - internal XML text escaper

Uncovered lines (per baseline 23% coverage): the SitemapApp ASGI dispatch,
``generate_sitemap`` end-to-end (with cached + non-cached paths),
``get_fields`` happy + error paths, and ``_escape_xml``.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

import contextvars
import datetime as dt
import typing as t

import pytest

from fastblocks.adapters.sitemap.core import (
    SCOPE_CTX_VAR,
    BaseSitemap,
    SitemapApp,
    _escape_xml,
    generate_sitemap,
    get_fields,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_scope() -> dict[str, t.Any]:
    """Minimal Starlette HTTP scope the sitemap machinery expects."""
    return {
        "type": "http",
        "scheme": "https",
        "server": ("example.com", 443),
        "path": "/sitemap.xml",
        "headers": [],
    }


class _StaticSitemap(BaseSitemap[int]):
    """Concrete subclass covering every hook (items, location, lastmod, ...)."""

    protocol = "https"

    def items(self):
        return [1, 2, 3]

    def location(self, item: int) -> str:
        return f"/page-{item}"

    def lastmod(self, item: int) -> dt.datetime:
        return dt.datetime(2026, 1, 1, tzinfo=dt.UTC) + dt.timedelta(days=item)

    def changefreq(self, item: int) -> str:
        return "weekly" if item % 2 == 0 else "daily"

    def priority(self, item: int) -> float:
        return 0.5 + (item * 0.1)


class _BareSitemap(BaseSitemap[int]):
    """Only implements items() + location(); relies on base defaults."""

    def items(self):
        return [42]

    def location(self, item: int) -> str:
        return f"/bare/{item}"


class _AsyncSitemap(BaseSitemap[int]):
    """Returns an async-iterable items() to exercise the async iterator path."""

    def items(self):
        return self._agen()

    async def _agen(self):
        for i in range(2):
            yield i

    def location(self, item: int) -> str:
        return f"/async/{item}"


class _BadLocationSitemap(BaseSitemap[int]):
    """location() returns absolute URL — exercises the safety check."""

    def items(self):
        return [1]

    def location(self, item: int) -> str:  # type: ignore[override]
        return "http://attacker.example/evil"


# ---------------------------------------------------------------------------
# _escape_xml
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEscapeXml:
    def test_escapes_ampersand(self) -> None:
        assert _escape_xml("a & b") == "a &amp; b"

    def test_escapes_angle_brackets(self) -> None:
        assert _escape_xml("<tag>") == "&lt;tag&gt;"

    def test_escapes_quotes(self) -> None:
        assert _escape_xml('"x"') == "&quot;x&quot;"
        assert _escape_xml("'x'") == "&#x27;x&#x27;"

    def test_idempotent_on_plain_text(self) -> None:
        assert _escape_xml("plain text") == "plain text"


# ---------------------------------------------------------------------------
# BaseSitemap
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBaseSitemap:
    def test_protocol_default_is_auto(self) -> None:
        assert BaseSitemap.protocol == "auto"

    def test_invalid_protocol_raises(self) -> None:
        class _Broken(BaseSitemap[int]):
            protocol = "ftp"  # type: ignore[assignment]

        with pytest.raises(ValueError, match="Invalid protocol"):
            _Broken()

    def test_scope_outside_request_raises(self) -> None:
        """Accessing .scope outside of an ASGI request raises RuntimeError.

        Run the access inside a fresh ``Context`` so the SCOPE_CTX_VAR is
        genuinely unset — the default is for it to leak across tests.
        """
        import contextvars as cv

        in_fresh_ctx = cv.copy_context()
        with pytest.raises(RuntimeError, match="outside of an ASGI request"):
            in_fresh_ctx.run(lambda: BaseSitemap().scope)

    def test_default_lastmod_is_none(self) -> None:
        assert BaseSitemap().lastmod(1) is None

    def test_default_changefreq_is_none(self) -> None:
        assert BaseSitemap().changefreq(1) is None

    def test_default_priority_is_half(self) -> None:
        assert BaseSitemap().priority(1) == 0.5


# ---------------------------------------------------------------------------
# get_fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFields:
    def test_builds_full_field_dict(self) -> None:
        sitemap = _StaticSitemap()
        fields = get_fields(sitemap, 1, scope={"scheme": "https"}, domain="example.com")
        assert fields["loc"] == "https://example.com/page-1"
        assert fields["lastmod"] == "2026-01-02"
        assert fields["changefreq"] == "daily"
        assert fields["priority"] == "0.6"

    def test_uses_protocol_from_sitemap_when_set(self) -> None:
        class _Https(BaseSitemap[int]):
            protocol = "https"

            def items(self):
                return [1]

            def location(self, item):
                return "/x"

        fields = get_fields(_Https(), 1, scope={"scheme": "http"}, domain="d.test")
        assert fields["loc"].startswith("https://")

    def test_priority_clamped_to_unit_interval(self) -> None:
        class _HiPri(BaseSitemap[int]):
            def items(self):
                return [1]

            def location(self, item):
                return "/x"

            def priority(self, item):
                return 5.0

        fields = get_fields(_HiPri(), 1, scope={"scheme": "https"}, domain="d.test")
        assert fields["priority"] == "1.0"

    def test_priority_clamped_to_zero(self) -> None:
        class _LoPri(BaseSitemap[int]):
            def items(self):
                return [1]

            def location(self, item):
                return "/x"

            def priority(self, item):
                return -1.0

        fields = get_fields(_LoPri(), 1, scope={"scheme": "https"}, domain="d.test")
        assert fields["priority"] == "0.0"

    def test_falls_back_on_unsafe_absolute_location(self) -> None:
        """Absolute URLs in location() must not leak into the sitemap."""
        fields = get_fields(
            _BadLocationSitemap(),
            1,
            scope={"scheme": "https"},
            domain="example.com",
        )
        # Fallback URL is the domain root with priority 0.5
        assert fields["loc"] == "https://example.com/"
        assert fields["priority"] == "0.5"

    def test_auto_protocol_falls_back_to_https(self) -> None:
        class _Auto(BaseSitemap[int]):
            def items(self):
                return [1]

            def location(self, item):
                return "/x"

        # No 'scheme' in scope => protocol defaults to "https"
        fields = get_fields(_Auto(), 1, scope={}, domain="d.test")
        assert fields["loc"].startswith("https://")


# ---------------------------------------------------------------------------
# generate_sitemap
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateSitemap:
    @pytest.mark.asyncio
    async def test_emits_xml_with_static_items(self) -> None:
        content = await generate_sitemap(
            [_StaticSitemap()],
            scope={"scheme": "https"},
            domain="example.com",
        )
        text = content.decode()
        assert text.startswith("<?xml")
        assert "<urlset" in text
        for i in (1, 2, 3):
            assert f"https://example.com/page-{i}" in text

    @pytest.mark.asyncio
    async def test_handles_async_items(self) -> None:
        content = await generate_sitemap(
            [_AsyncSitemap()],
            scope={"scheme": "https"},
            domain="example.com",
        )
        text = content.decode()
        assert "https://example.com/async/0" in text
        assert "https://example.com/async/1" in text

    @pytest.mark.asyncio
    async def test_multiple_sitemaps_concatenate(self) -> None:
        content = await generate_sitemap(
            [_StaticSitemap(), _BareSitemap()],
            scope={"scheme": "https"},
            domain="example.com",
        )
        text = content.decode()
        assert "/page-1" in text
        assert "/bare/42" in text

    @pytest.mark.asyncio
    async def test_skip_per_sitemap_on_exception(self) -> None:
        class _Boom(BaseSitemap[int]):
            def items(self):
                raise RuntimeError("items failed")

            def location(self, item):
                return "/x"

        content = await generate_sitemap(
            [_Boom(), _StaticSitemap()],
            scope={"scheme": "https"},
            domain="example.com",
        )
        text = content.decode()
        # The broken sitemap is silently skipped; the good one survives.
        assert "/page-1" in text
        assert "</urlset>" in text


# ---------------------------------------------------------------------------
# SitemapApp (ASGI dispatch)
# ---------------------------------------------------------------------------


def _receive_factory():
    async def receive() -> dict[str, t.Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return receive


@pytest.mark.unit
class TestSitemapApp:
    @pytest.mark.asyncio
    async def test_http_request_returns_xml(self, sample_scope: dict) -> None:
        sent: list[dict[str, t.Any]] = []

        async def send(msg: dict[str, t.Any]) -> None:
            sent.append(msg)

        app = SitemapApp(_StaticSitemap(), domain="example.com")
        await app(sample_scope, _receive_factory(), send)

        # First frame: status + headers
        start = sent[0]
        assert start["type"] == "http.response.start"
        assert start["status"] == 200
        headers = dict(start["headers"])
        assert headers[b"content-type"] == b"application/xml; charset=utf-8"
        # Last frame: body
        body = b"".join(
            m.get("body", b"") for m in sent if m["type"] == "http.response.body"
        )
        assert b"<urlset" in body
        assert b"/page-1" in body

    @pytest.mark.asyncio
    async def test_non_http_scope_returns_404(self) -> None:
        sent: list[dict[str, t.Any]] = []

        async def send(msg: dict[str, t.Any]) -> None:
            sent.append(msg)

        app = SitemapApp(_StaticSitemap(), domain="example.com")
        await app(
            {"type": "lifespan"},
            _receive_factory(),
            send,
        )
        assert sent[0]["status"] == 404

    @pytest.mark.asyncio
    async def test_invalid_first_message_returns_400(self, sample_scope: dict) -> None:
        sent: list[dict[str, t.Any]] = []

        async def send(msg: dict[str, t.Any]) -> None:
            sent.append(msg)

        async def receive() -> dict[str, t.Any]:
            return {"type": "http.disconnect"}  # not http.request

        app = SitemapApp(_StaticSitemap(), domain="example.com")
        await app(sample_scope, receive, send)
        assert sent[0]["status"] == 400

    @pytest.mark.asyncio
    async def test_single_sitemap_arg_wrapped_in_list(self, sample_scope: dict) -> None:
        sent: list[dict[str, t.Any]] = []

        async def send(msg: dict[str, t.Any]) -> None:
            sent.append(msg)

        app = SitemapApp(_BareSitemap(), domain="d.test")
        await app(sample_scope, _receive_factory(), send)
        body = b"".join(
            m.get("body", b"") for m in sent if m["type"] == "http.response.body"
        )
        assert b"/bare/42" in body

    @pytest.mark.asyncio
    async def test_cache_ttl_in_response_headers(self, sample_scope: dict) -> None:
        sent: list[dict[str, t.Any]] = []

        async def send(msg: dict[str, t.Any]) -> None:
            sent.append(msg)

        app = SitemapApp(_StaticSitemap(), domain="example.com", cache_ttl=120)
        await app(sample_scope, _receive_factory(), send)
        headers = dict(sent[0]["headers"])
        assert headers[b"cache-control"] == b"public, max-age=120"

    @pytest.mark.asyncio
    async def test_internal_error_returns_500(self, monkeypatch, sample_scope: dict) -> None:
        # Force generate_sitemap to raise.
        from fastblocks.adapters.sitemap import core as core_mod

        async def boom(*args, **kwargs):
            raise RuntimeError("synthetic")

        monkeypatch.setattr(core_mod, "generate_sitemap", boom)

        sent: list[dict[str, t.Any]] = []

        async def send(msg: dict[str, t.Any]) -> None:
            sent.append(msg)

        app = SitemapApp(_StaticSitemap(), domain="example.com")
        await app(sample_scope, _receive_factory(), send)
        assert sent[0]["status"] == 500
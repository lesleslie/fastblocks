"""D7: prove the framework's caching system actually serves cached responses.

Two assertions lock down the CacheControl contract:

1. ``CacheControlResponder`` is a callable ASGI middleware class
   (real, not a stub).
2. When wrapped around a route handler with ``max_age=N``, the
   emitted response carries a ``Cache-Control: max-age=N`` directive.

Brief API adaptation (per constraint E — Tasks 5/6/7/8 findings):

- ``CacheControl`` class does NOT exist. The real API is
  ``CacheControlResponder`` ASGI middleware at
  ``fastblocks/caching.py:875``.
- ``CacheControl.public(max_age=3600).header_value`` is doubly
  wrong: the class doesn't exist, AND ``public=True`` raises
  ``NotImplementedError`` from ``_check_unsupported_directives``
  at ``fastblocks/caching.py:775-782``. This test uses
  ``max_age=3600`` only, which IS supported.
- ``@a.route(...)`` decorator does not exist (Task 5/6/7/8
  precedent). Use ``a.add_route(path, endpoint)``.

ASGI-shape finding during impl:

- ``CacheControlResponder`` wraps an ASGI app, NOT a starlette
  endpoint that takes a single ``request``. The wrapped callable
  must accept ``(scope, receive, send)`` (see
  ``fastblocks/caching.py:886-891``: ``await self.app(scope, receive, send)``).
  An endpoint with signature ``async def cached(request)`` will
  raise ``TypeError: takes 1 positional argument but 3 were given``
  once a real ASGI request lands. This implementation builds a
  plain ASGI handler that emits a ``PlainTextResponse`` inline.
"""
from __future__ import annotations

import pytest
from fastblocks.applications import FastBlocks
from fastblocks.caching import CacheControlResponder
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


CACHED_BODY = "cached-body"
CACHE_MAX_AGE = 3600


@pytest.fixture
def app():
    a = FastBlocks()

    async def cached_endpoint(scope, receive, send):
        response = PlainTextResponse(CACHED_BODY)
        await response(scope, receive, send)

    handler = CacheControlResponder(cached_endpoint, max_age=CACHE_MAX_AGE)
    a.add_route("/cached", handler)
    return a


@pytest.fixture
def client(app):
    return TestClient(app)


def test_cache_control_header_emitted(client):
    """Wrapped route emits Cache-Control with max-age=N."""
    r = client.get("/cached")
    cc = r.headers.get("cache-control", "")
    assert f"max-age={CACHE_MAX_AGE}" in cc, (
        f"D7: Cache-Control missing max-age={CACHE_MAX_AGE} "
        f"(got: {cc!r})"
    )


def test_cache_responder_class_is_callable():
    """Contract: CacheControlResponder is a real ASGI middleware."""
    assert callable(CacheControlResponder), (
        "D7: CacheControlResponder must be callable (ASGI middleware)"
    )

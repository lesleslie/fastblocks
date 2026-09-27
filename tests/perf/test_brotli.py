"""D7: prove Brotli compression is applied by default middleware.

Three assertions lock down the framework's Brotli contract:

1. The compressed body, when decompressed via ``brotli.decompress``,
   matches the original byte-for-byte AND the ratio is well below
   30% (repetitive text compresses 50-80x under Brotli; 30% is a
   loose floor that catches gzip fallback / identity pass-through
   regressions).
2. ``Content-Encoding: br`` is announced so caches / clients know
   how to decompress the body.
3. ``Vary: Accept-Encoding`` is set so caches serve the right
   variant per client (Brotli-encoded body must NOT be served to
   a client that did not advertise ``br``).
4. ``Accept-Encoding: identity`` MUST skip Brotli entirely AND
   the response body must equal the uncompressed original
   (catches the "compression applied unconditionally" anti-pattern).

Brief API adaptation (per constraint A — Tasks 5/6/7/8 findings):

- ``@a.route(...)`` decorator does not exist. Starlette exposes
  ``a.add_route(path, endpoint)``; this test uses that pattern.
- The Brotli middleware is registered as SYSTEM middleware at
  ``MiddlewarePosition.COMPRESSION`` (see ``fastblocks/middleware.py:489``),
  so a bare ``FastBlocks()`` already wires it.

httpx2 TestClient notes (finding during impl):

- TestClient cannot pass ``decoders=[]`` through its constructor (it
  overrides httpx.Client.__init__), so TestClient will auto-decode
  Brotli-encoded bodies and hide them. For the ratio / round-trip
  assertion we therefore drive the ASGI app directly via
  ``_drive_asgi``, capturing raw bytes the server actually emitted.
"""
from __future__ import annotations

import pytest
from fastblocks.applications import FastBlocks
from starlette.responses import Response
from starlette.testclient import TestClient


REPEATABLE_BODY = ("the quick brown fox jumps over the lazy dog " * 200).encode()


@pytest.fixture
def app():
    a = FastBlocks()

    async def compress(request):  # noqa: ARG001
        return Response(REPEATABLE_BODY, media_type="text/plain")

    a.add_route("/compress", compress)
    return a


@pytest.fixture
def client(app):
    return TestClient(app)


def _drive_asgi(app, raw_headers: list[tuple[bytes, bytes]]):
    """Drive the ASGI stack once and capture the raw emitted bytes.

    Returns ``(status_code, headers_list, body_bytes)``. Bypasses
    httpx's auto-decoder pipeline (which would transparently Br-decode
    the response body). Mirrors the raw-ASGI pattern established in
    Task 8's ``test_async_rendering.py`` for direct-engine measurement.
    """
    import anyio

    body_parts: list[bytes] = []
    captured: dict[str, object] = {"status": 0, "headers": []}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            captured["status"] = message["status"]
            captured["headers"] = list(message.get("headers", []))
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))

    async def main():
        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/compress",
                "raw_path": b"/compress",
                "query_string": b"",
                "headers": raw_headers,
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "extensions": {},
            },
            receive,
            send,
        )

    anyio.run(main)
    return captured["status"], captured["headers"], b"".join(body_parts)


def test_brotli_response_meets_ratio_and_decompresses(app):
    """Concrete compression ratio + round-trip decompress.

    Drives the ASGI stack directly so httpx's Brotli auto-decoder
    does not hide the compressed body.
    """
    import brotli

    _, headers, compressed = _drive_asgi(
        app,
        [
            (b"host", b"testserver"),
            (b"accept-encoding", b"br"),
        ],
    )
    original = REPEATABLE_BODY

    ratio = len(compressed) / len(original)
    assert ratio < 0.30, (
        f"D7: Brotli compression ratio {ratio:.2%} exceeds 30% "
        f"({len(compressed)}b / {len(original)}b) — likely fallback or misconfigured. "
        f"Headers: {headers!r}"
    )

    try:
        decompressed = brotli.decompress(compressed)
    except Exception as e:  # noqa: BLE001
        raise AssertionError(
            f"D7: brotli.decompress failed on compressed response — "
            f"Brotli not actually serving (got: {e!r})"
        ) from e
    assert decompressed == original, (
        f"D7: brotli.decompress output does not match original "
        f"(decompressed len={len(decompressed)}, original len={len(original)})"
    )


def test_brotli_content_encoding_header_present(client):
    """Server announces br encoding when client accepts it."""
    r = client.get("/compress", headers={"Accept-Encoding": "br"})
    assert r.headers.get("content-encoding") == "br", (
        f"D7: Content-Encoding missing or wrong "
        f"(got: {r.headers.get('content-encoding')!r})"
    )


def test_brotli_vary_header_present(client):
    """Cache correctness: Vary: Accept-Encoding lets caches serve the right variant."""
    r = client.get("/compress", headers={"Accept-Encoding": "br"})
    assert "accept-encoding" in r.headers.get("vary", "").lower(), (
        f"D7: Vary header missing Accept-Encoding "
        f"(got: {r.headers.get('vary')!r})"
    )


def test_identity_encoding_skips_compression(client):
    """Negative test: Accept-Encoding: identity must NOT trigger Brotli."""
    r = client.get("/compress", headers={"Accept-Encoding": "identity"})
    assert r.headers.get("content-encoding") != "br", (
        f"D7: Brotli applied despite Accept-Encoding: identity "
        f"(content-encoding={r.headers.get('content-encoding')!r})"
    )
    assert r.content == REPEATABLE_BODY, (
        f"D7: identity response body differs from uncompressed original "
        f"(body len={len(r.content)}, expected {len(REPEATABLE_BODY)})"
    )

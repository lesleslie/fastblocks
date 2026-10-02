"""D3: boot test for the ``middleware/security_headers`` adapter.

Spec §D3 row ``middleware/security_headers`` -> middleware-resident
(NOT a Oneiric resolver adapter; verified at
``examples/landing/landing_routes/adapter_matrix.py:96``).

This file is the brief-specified minimal boot test for middleware:
verify the middleware class is importable and instantiable, per the
brief's middleware-boot contract.

NOTE on path: the brief specifies
``tests/adapters/middleware/test_security_headers_boot.py``; the
existing comprehensive test at
``tests/middleware/test_security_headers.py`` already exercises the
real middleware stack composition + per-header value assertions via
``MiddlewareStackManager`` + TestClient. This file is the
brief-specified minimal boot test (one-off, doesn't duplicate the
existing comprehensive coverage).

Security headers middleware is first-party
(``fastblocks.middleware.SecureHeadersMiddleware``) defined at
``fastblocks/middleware.py:227``. The constructor takes a single
ASGI app arg.
"""
from __future__ import annotations


def test_security_headers_middleware_is_importable() -> None:
    """The security-headers middleware class must be importable via
    the fastblocks.middleware surface."""
    from fastblocks.middleware import SecureHeadersMiddleware

    assert SecureHeadersMiddleware is not None, (
        "D3: SecureHeadersMiddleware import returned None"
    )


def test_security_headers_middleware_is_instantiable() -> None:
    """Smoke: ``SecureHeadersMiddleware(app)`` returns a middleware
    instance wrapping the supplied ASGI app. The constructor takes a
    single ASGI app arg per the signature at
    ``fastblocks/middleware.py:245``."""
    from starlette.applications import Starlette

    from fastblocks.middleware import SecureHeadersMiddleware

    app = Starlette()
    middleware = SecureHeadersMiddleware(app)
    assert middleware is not None, (
        "D3: SecureHeadersMiddleware(app) returned None"
    )

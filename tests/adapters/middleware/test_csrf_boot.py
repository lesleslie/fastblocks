"""D3: boot test for the ``middleware/csrf`` adapter.

Spec §D3 row ``middleware/csrf`` -> middleware-resident (NOT a
Oneiric resolver adapter; verified at
``examples/landing/routes/adapter_matrix.py:95``).

This file is the brief-specified minimal boot test for middleware:
verify the middleware class is importable and instantiable, per the
brief's middleware-boot contract.

NOTE on path: the brief specifies
``tests/adapters/middleware/test_csrf_boot.py``; the existing
integration test at ``tests/middleware/test_csrf.py`` already covers
the full CSRF positive + negative paths via Starlette TestClient.
This file is the brief-specified minimal boot test (one-off, doesn't
duplicate the existing comprehensive coverage).

CSRF middleware is third-party (``starlette_csrf.middleware.CSRFMiddleware``)
re-exported through ``fastblocks.middleware`` (see
``fastblocks/middleware.py:47``).
"""
from __future__ import annotations


def test_csrf_middleware_is_importable() -> None:
    """The CSRF middleware class must be importable via the
    fastblocks.middleware surface."""
    from fastblocks.middleware import CSRFMiddleware

    assert CSRFMiddleware is not None, (
        "D3: CSRFMiddleware import returned None"
    )


def test_csrf_middleware_is_instantiable() -> None:
    """Smoke: ``CSRFMiddleware(app, ...)`` returns a middleware
    instance wrapping the supplied ASGI app. The constructor
    requires ``secret`` (used for cookie signing) per
    starlette_csrf's documented signature."""
    from starlette.applications import Starlette

    from fastblocks.middleware import CSRFMiddleware

    app = Starlette()
    middleware = CSRFMiddleware(app, secret="x" * 32)
    assert middleware is not None, (
        "D3: CSRFMiddleware(app, secret=...) returned None"
    )
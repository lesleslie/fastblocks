"""D3: boot test for the ``middleware/brotli`` adapter.

Spec §D3 row ``middleware/brotli`` -> middleware-resident (NOT a
Oneiric resolver adapter; verified at
``examples/landing/routes/adapter_matrix.py:94``). The matrix source
of truth documents: "Brotli has no dedicated test yet — surfaces as
``?`` honestly."

This file is the brief-specified minimal boot test for middleware:
verify the middleware class is importable and instantiable, per the
brief's middleware-boot contract.

Brotli middleware is third-party (``brotli_asgi.BrotliMiddleware``)
re-exported through ``fastblocks.middleware`` (see
``fastblocks/middleware.py:40``). The boot test only requires that
the import + instantiation succeeds.
"""
from __future__ import annotations


def test_brotli_middleware_is_importable() -> None:
    """The brotli middleware class must be importable via the
    fastblocks.middleware surface."""
    from fastblocks.middleware import BrotliMiddleware

    assert BrotliMiddleware is not None, (
        "D3: BrotliMiddleware import returned None"
    )


def test_brotli_middleware_is_instantiable() -> None:
    """Smoke: ``BrotliMiddleware(app)`` returns a middleware instance
    wrapping the supplied ASGI app. The constructor takes a single
    ASGI app arg per brotli_asgi's documented signature."""
    from starlette.applications import Starlette

    from fastblocks.middleware import BrotliMiddleware

    app = Starlette()
    middleware = BrotliMiddleware(app)
    assert middleware is not None, (
        "D3: BrotliMiddleware(app) returned None"
    )

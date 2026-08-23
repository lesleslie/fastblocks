"""Regression test for master-plan line 478-479 lifecycle integration.

Per ADR 0013 Decision 14 + ADR 0012 Decision 2 path-forward option (b):
extend the existing lifespan; do NOT ship a new LifespanManager class.

The test drives Starlette's startup event via
``app.router.lifespan_context(app)`` -- the exact code path Starlette
takes at ASGI startup -- rather than bypassing it by wrapping a
``lifespan(app)`` callable directly. The wrapped context-manager route
is the production startup path that binds the bound class method on
``FastBlocksApp``.
"""

from __future__ import annotations

import asyncio

import jinja2

from fastblocks.adapters.app.default import FastBlocksApp


async def test_lifespan_binds_main_loop_and_jinja_env() -> None:
    """Drive FastBlocksApp's lifespan via Starlette's lifespan_context.

    Starlette stores the ``lifespan`` callable passed to
    ``super().__init__(lifespan=self.lifespan, ...)`` on
    ``app.router.lifespan_context``. Entering that async context is the
    production startup path; it invokes the bound class method
    ``FastBlocksApp.lifespan`` with the app as its argument. The test
    must go through that exact code path so we are not silently
    bypassing the production binding.

    Asserts ``app.state.main_loop`` is an ``asyncio.AbstractEventLoop``
    and ``app.state.jinja_env`` is a ``jinja2.Environment`` after
    startup -- the master-plan line 478-479 lifecycle assertion.
    """
    app = FastBlocksApp()
    # Starlette's exact startup path: enter the ``lifespan_context``
    # async context manager that wraps the bound ``lifespan`` callable.
    # When entered, Starlette invokes the lifespan callable with the
    # app, which in our case is the bound class method on
    # ``FastBlocksApp``.
    async with app.router.lifespan_context(app):
        assert isinstance(
            app.state.main_loop,
            asyncio.AbstractEventLoop,
        ), (
            f"app.state.main_loop must be asyncio.AbstractEventLoop; "
            f"got {type(app.state.main_loop)!r}"
        )
        assert isinstance(
            app.state.jinja_env,
            jinja2.Environment,
        ), (
            f"app.state.jinja_env must be jinja2.Environment; "
            f"got {type(app.state.jinja_env)!r}"
        )

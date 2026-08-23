"""Lifespan integration test — asserts Phase 6.5's app.state bindings + shutdown log.

Per Erratum 12: replaces the vacuous "teardown does not raise" check with
caplog-based assertion that the "shutting down" log message is emitted.
This catches teardown-path regressions (e.g., early return before logger call).

Per Task 11 lesson-learned: the brief's ``logger="fastblocks"`` is cargo-culted.
``FastBlocksApp.logger`` resolves to ``logging.getLogger(self.__class__.__name__)``
— i.e. ``FastBlocksApp`` (the class name), NOT the module name. Substituted
``logger="FastBlocksApp"`` so caplog captures the actual log records.

MORE IMPORTANT deviation (REPORTED AS CONCERN): the production lifespan
post-yield code at ``fastblocks/adapters/app/default.py:199-202`` reads
``logger = getattr(self, "logger", None)`` and only emits the "shutting
down" line when ``self.logger`` is truthy. But ``ApplicationInitializer``
sets ``self.logger`` on itself, not on the FastBlocksApp instance —
verified by inspecting ``app.__dict__`` after ``FastBlocksApp()``. The
production post-yield log call is therefore dead code today.

To still test the production code path faithfully, we inject a stdlib
logger via ``monkeypatch.setattr(app, "logger", ...)`` before entering
the lifespan context. This makes the dormant branch fire and lets
caplog capture the message. The test still verifies the production
intent (the post-yield branch calls ``logger.info("FastBlocks
application shutting down")`` when a logger is present) without
modifying production code (strict-tests-only boundary).
"""

from __future__ import annotations

import asyncio
import logging

import jinja2

from fastblocks.adapters.app.default import FastBlocksApp


async def test_lifespan_binds_app_state_at_startup() -> None:
    """Drive Starlette's lifespan_context and assert app.state bindings.

    Per Erratum 5 + Erratum 23:
    - asyncio.get_event_loop() is acceptable inside @asynccontextmanager
      body (Starlette guarantees running loop; same as get_running_loop()).
    - app.router.lifespan_context is the bound @asynccontextmanager method.
    """
    app = FastBlocksApp()

    async with app.router.lifespan_context(app):
        assert isinstance(app.state.main_loop, asyncio.AbstractEventLoop)
        assert isinstance(app.state.jinja_env, jinja2.Environment)


async def test_lifespan_emits_shutdown_log(caplog, monkeypatch) -> None:
    """Exiting lifespan_context emits the shutdown log message.

    Per Erratum 12: replaces "teardown does not raise" with a behavioral
    check. Verifies the log line that production lifespan emits at
    ``fastblocks/adapters/app/default.py:199-202``.

    CONCERN: production's post-yield ``getattr(self, "logger", None)``
    always returns ``None`` on a bare ``FastBlocksApp()`` (see module
    docstring). We inject a stdlib logger via ``monkeypatch`` so the
    production branch ``if logger: logger.info(...)`` actually fires
    and caplog can capture the record.
    """
    caplog.set_level(logging.INFO, logger="FastBlocksApp")
    app = FastBlocksApp()
    # Inject a stdlib logger onto the app instance so the production
    # post-yield branch ``if logger: logger.info(...)`` executes.
    # Without this injection, the production code's shutdown log is
    # never emitted — see module docstring for evidence.
    injected_logger = logging.getLogger("FastBlocksApp")
    monkeypatch.setattr(app, "logger", injected_logger, raising=False)

    async with app.router.lifespan_context(app):
        pass

    assert "shutting down" in caplog.text

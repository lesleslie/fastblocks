"""C3 smoke test: fastblocks-ui functions are registered on the Jinja env.

Per Phase 1.5 spec Task 8 Integration Contract:
- Triggered from: Templates.init() (called during app lifespan)
- Returns to / updates: templates.env.globals with ui_button, ui_card,
  ui_field, ui_alert, ui_container
- Demonstrable by: this test asserting the keys are present after init
- Rollback signal: page-render failure in examples/landing/ (deferred to Phase 2)
- Observability present: structured log line at style_registry.py:64-81

Exercises the full production wiring path through ``Templates().init()``
(rather than calling ``register_style_functions`` directly) so that
the production ``suppress(Exception)`` wrapper at
``jinja2.py:974-978`` plus the ``config.app.style`` resolution are
both exercised end-to-end. Asserts all 5 fastblocks-ui globals land
in ``env.globals`` per the corrected code-architect S1 review (which
widened the assertion set from the original 2-key version).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fastblocks.adapters.templates.jinja2 import Templates


REQUIRED_UI_GLOBALS = ("ui_button", "ui_card", "ui_field", "ui_alert", "ui_container")


def _build_templates() -> Templates:
    """Construct a Templates() ready for the production init() path.

    Sets the minimum attributes init_envs reads (config.templates.*,
    config.app.style) and stubs app_searchpaths so get_searchpaths is
    not invoked. AsyncJinja2Templates and register_style_functions are
    the real production objects — only the discovery/mocking surface
    is faked.
    """
    templates = Templates()
    config = MagicMock()
    config.app = MagicMock()
    config.app.style = "fastblocks_ui"
    config.templates = MagicMock()
    config.templates.extensions = []
    config.templates.context_processors = []
    config.templates.loader = None
    config.templates.delimiters = {}
    templates.config = config
    templates.logger = MagicMock()
    templates.app_searchpaths = []
    return templates


@pytest.mark.integration
async def test_all_ui_helpers_registered_on_env() -> None:
    """All 5 fastblocks-ui globals are present after Templates().init()."""
    templates = _build_templates()
    await templates.init()

    env = templates.app.env
    missing = [k for k in REQUIRED_UI_GLOBALS if k not in env.globals]
    assert not missing, (
        f"Missing UI globals from env.globals: {missing} "
        f"(have: {sorted(k for k in env.globals if k.startswith('ui_'))})"
    )


@pytest.mark.integration
async def test_ui_helpers_are_callable() -> None:
    """The registered ui_* globals are callable (lambda wrappers around fastblocks_ui)."""
    templates = _build_templates()
    await templates.init()

    env = templates.app.env
    for name in REQUIRED_UI_GLOBALS:
        fn = env.globals.get(name)
        assert callable(fn), f"{name} is not callable: {fn!r}"
"""C3 smoke test: fastblocks-ui functions are registered on the Jinja env.

Per Phase 1.5 spec Task 8 Integration Contract:
- Triggered from: Templates.init() (called during app lifespan)
- Returns to / updates: templates.env.globals with ui_button, ui_card,
  ui_field, ui_alert, ui_container
- Demonstrable by: this test asserting the keys are present after init
- Rollback signal: page-render failure in examples/landing/ (deferred to Phase 2)
- Observability added: structured log line at the wiring call site

Exercise the exact production wiring path at
``fastblocks/adapters/templates/jinja2.py:974-978``: import
``register_style_functions`` (the dispatcher) and invoke it with
``style_name="fastblocks_ui"`` (the value ``config.app.style`` would
resolve to in a default fastblocks deployment). Asserts all 5
fastblocks-ui globals land in ``env.globals`` per the corrected
code-architect S1 review (which widened the assertion set from the
original 2-key version).
"""
from __future__ import annotations

import jinja2
import pytest

from fastblocks.core.style_registry import register_style_functions


REQUIRED_UI_GLOBALS = ("ui_button", "ui_card", "ui_field", "ui_alert", "ui_container")


@pytest.mark.integration
def test_all_ui_helpers_registered_on_env() -> None:
    """All 5 fastblocks-ui globals are present after register_style_functions."""
    env = jinja2.Environment()
    register_style_functions(env, "fastblocks_ui")

    missing = [k for k in REQUIRED_UI_GLOBALS if k not in env.globals]
    assert not missing, (
        f"Missing UI globals from env.globals: {missing} "
        f"(have: {sorted(k for k in env.globals if k.startswith('ui_'))})"
    )


@pytest.mark.integration
def test_ui_helpers_are_callable() -> None:
    """The registered ui_* globals are callable (lambda wrappers around fastblocks_ui)."""
    env = jinja2.Environment()
    register_style_functions(env, "fastblocks_ui")

    for name in REQUIRED_UI_GLOBALS:
        fn = env.globals.get(name)
        assert callable(fn), f"{name} is not callable: {fn!r}"
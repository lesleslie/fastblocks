"""Conftest for templates test configuration.

Per Phase 1.5+ Wave B: installs the jinja2_async_environment stub at
SESSION START (not fixture time), because 7 test files in this
directory do module-level imports of
fastblocks.adapters.templates.jinja2 which transitively imports
jinja2_async_environment.AsyncRedisBytecodeCache at module-load.
A scope="module" autouse fixture runs AFTER collection, too late
to satisfy the import.

Mirrors the existing _install_mcp_common_websocket_stub() pattern
at tests/conftest.py:154-157 (called from pytest_collection_modifyitems
in tests/conftest.py:131-153).

WHY pytest_sessionstart not pytest_collection_start: sessionstart
fires once at the very start of the pytest run, before any
collection. It is the safest hook to guarantee the stub is in place
before any test file is even imported.

WHY pytest_sessionfinish for teardown: standard pytest contract; fires
once at session end after all tests complete.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock


def pytest_ignore_collect(collection_path: Path, config):
    """Ignore collection of test_components directory (preserved from prior conftest)."""
    return "test_components" in str(collection_path)


_SAVED_SYS_MODULES: dict[str, object | None] = {}


def pytest_sessionstart(session):
    """Install jinja2_async_environment stub before any test file is collected.

    Without this, the 7 test files in tests/adapters/templates/ that
    import fastblocks.adapters.templates.jinja2 at module level would
    fail with "cannot import name 'AsyncRedisBytecodeCache' from
    'jinja2_async_environment'" — see test_rendering_jinja2.py:39-44
    for the production-side rationale and test_rendering_jinja2.py:220-234
    for the regression test that enforces this stub shape.
    """
    keys = [
        "jinja2_async_environment",
        "jinja2_async_environment.loaders",
        "jinja2_async_environment.bccache",
        "starlette_async_jinja",
    ]
    for key in keys:
        _SAVED_SYS_MODULES[key] = sys.modules.get(key)

    # starlette_async_jinja stub
    mock_async_jinja2_templates_module = types.ModuleType("starlette_async_jinja")

    class _MockAsyncJinja2Templates:
        def __init__(self, *args, **kwargs) -> None:
            # Mirror MockAsyncJinja2Templates in test_rendering_jinja2.py:
            # lock autoescape=True on the env so contract assertions
            # (e.g. tests/security/test_autoescape_regression.py and
            # tests/adapters/templates/test_boot.py) see a real boolean
            # rather than ``MagicMock(name='mock.autoescape')``.
            self.env = MagicMock()
            self.env.autoescape = True
            self.TemplateResponse = MagicMock()
            self.render_block = MagicMock()

    mock_async_jinja2_templates_module.AsyncJinja2Templates = _MockAsyncJinja2Templates
    sys.modules["starlette_async_jinja"] = mock_async_jinja2_templates_module

    # jinja2_async_environment stub (top-level)
    mock_jinja2_async_env = types.ModuleType("jinja2_async_environment")
    sys.modules["jinja2_async_environment"] = mock_jinja2_async_env

    # AsyncRedisBytecodeCache MUST be on the top-level module
    # (production code at fastblocks/adapters/templates/jinja2.py:96
    # imports from the top-level package, not from .bccache).
    # The regression test at test_rendering_jinja2.py:220-234 enforces this.
    mock_jinja2_async_env.AsyncRedisBytecodeCache = MagicMock

    # jinja2_async_environment.loaders submodule
    mock_loaders = types.ModuleType("jinja2_async_environment.loaders")
    mock_jinja2_async_env.loaders = mock_loaders
    sys.modules["jinja2_async_environment.loaders"] = mock_loaders

    class _MockAsyncBaseLoader:
        def __init__(self, *args, **kwargs):
            if args:
                sp = args[0]
                # Some callers pass a single Path, others pass a list;
                # production BaseTemplateLoader.searchpath is always an iterable.
                self.searchpath = list(sp) if isinstance(sp, (list, tuple)) else [sp]
            else:
                self.searchpath = []

        async def get_source(self, environment, template):
            return None, None, None

    mock_loaders.AsyncBaseLoader = _MockAsyncBaseLoader
    mock_loaders.SourceType = tuple

    # jinja2_async_environment.bccache submodule (also reachable via
    # the bccache.AsyncRedisBytecodeCache alias; see
    # test_rendering_jinja2.py:228-232).
    mock_bccache = types.ModuleType("jinja2_async_environment.bccache")
    mock_bccache.AsyncRedisBytecodeCache = MagicMock
    mock_jinja2_async_env.bccache = mock_bccache
    sys.modules["jinja2_async_environment.bccache"] = mock_bccache


def pytest_sessionfinish(session, exitstatus):
    """Restore sys.modules state installed by pytest_sessionstart."""
    for key, saved_value in _SAVED_SYS_MODULES.items():
        if saved_value is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = saved_value
    _SAVED_SYS_MODULES.clear()

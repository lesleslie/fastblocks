"""Test configuration for FastBlocks."""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportArgumentType=false, reportMissingTypeArgument=false

from __future__ import annotations

# Temporarily exclude files with pytest collection issues (ACB import timing)
collect_ignore = [
    "test_events_integration.py",
    "test_health_integration.py",
    # ``_fixtures/`` holds import-time side-effect modules that
    # register Candidate factories (Phase 1.5.4 cross-module
    # resolution test). They are NOT pytest tests themselves — the
    # test that consumes them lives at
    # ``tests/core/test_resolver_cross_module.py``. Ignoring the
    # whole subtree keeps pytest from importing them twice (once
    # via collection, once via the test's import).
    "_fixtures",
]

import sys
import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import HTMLResponse

if t.TYPE_CHECKING:
    from starlette.types import Message, Scope

from tests._mocks import (
    MockActions,
    MockAdapter,
    MockAdapters,
    MockAsyncBaseLoader,
    MockAsyncPath,
    MockCache,
    MockChoiceLoader,
    MockConfig,
    MockConfigModule,
    MockDebug,
    MockDepends,
    MockDependsInjector,
    MockDictLoader,
    MockFileSystemLoader,
    MockFunctionLoader,
    MockLogger,
    MockModels,
    MockPackageLoader,
    MockPrefixLoader,
    MockRedisLoader,
    MockSitemap,
    MockStorage,
    MockStorageLoader,
    MockTemplateFilters,
    MockTemplateNotFound,
    MockTemplateRenderer,
    MockTemplates,
    MockTemplatesBaseSettings,
    MockUptodate,
    SitemapURL,
)
from tests._websocket_stub import (
    _install_mcp_common_websocket_stub,
    _StubEventTypes,
    _StubMessageType,
    _StubWebSocketAuthenticator,
    _StubWebSocketClient,
    _StubWebSocketMessage,
    _StubWebSocketProtocol,
    _StubWebSocketServer,
)

__all__ = [
    "MockActions",
    "MockAdapter",
    "MockAdapters",
    "MockAsyncBaseLoader",
    "MockAsyncPath",
    "MockCache",
    "MockChoiceLoader",
    "MockConfig",
    "MockConfigModule",
    "MockDebug",
    "MockDepends",
    "MockDependsInjector",
    "MockDictLoader",
    "MockFileSystemLoader",
    "MockFunctionLoader",
    "MockLogger",
    "MockModels",
    "MockPackageLoader",
    "MockPrefixLoader",
    "MockRedisLoader",
    "MockSitemap",
    "MockStorage",
    "MockStorageLoader",
    "MockTemplateFilters",
    "MockTemplateNotFound",
    "MockTemplateRenderer",
    "MockTemplates",
    "MockTemplatesBaseSettings",
    "MockUptodate",
    "SitemapURL",
    "_StubEventTypes",
    "_StubMessageType",
    "_StubWebSocketAuthenticator",
    "_StubWebSocketClient",
    "_StubWebSocketMessage",
    "_StubWebSocketProtocol",
    "_StubWebSocketServer",
]


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers and install test-only stubs."""
    config.addinivalue_line(
        "markers",
        "cli_coverage: mark test as measuring CLI coverage",
    )
    config.addinivalue_line(
        "markers",
        "websocket: mark test as needing the mcp_common.websocket stub",
    )

    # Install the mcp_common.websocket stub at session scope — must be
    # session-scope because websocket test files import at collection time.
    # See conftest-sysmodules-pollution-pattern memory for why per-test is wrong.
    _install_mcp_common_websocket_stub()

    # Patch anyio.Path to use MockAsyncPath for code that still uses it directly.
    from contextlib import suppress

    with suppress(ImportError):
        import anyio

        sys.modules["anyio.Path"] = MockAsyncPath  # type: ignore[assignment]
        if hasattr(anyio, "Path"):
            anyio.Path = MockAsyncPath  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_cache() -> AsyncMock:
    mock = AsyncMock()

    mock.exists = AsyncMock(return_value=False)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.clear = AsyncMock(return_value=True)
    mock.scan = AsyncMock(return_value=[])

    return mock


@pytest.fixture
def cache(mock_cache: AsyncMock) -> AsyncMock:
    # Alias: legacy tests request ``cache`` by name; new name is ``mock_cache``.
    return mock_cache


@pytest.fixture
def mock_storage() -> AsyncMock:
    mock = AsyncMock()

    mock.exists = AsyncMock(return_value=False)
    mock.open = AsyncMock(return_value=None)
    mock.write = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.file_exists = AsyncMock(return_value=False)
    mock.directory_exists = AsyncMock(return_value=False)
    mock.create_directory = AsyncMock(return_value=True)

    mock.templates = AsyncMock()
    mock.templates.exists = AsyncMock(return_value=False)
    mock.templates.open = AsyncMock(return_value=None)
    mock.templates.stat = AsyncMock(return_value={"mtime": 123456789, "size": 1024})

    return mock


@pytest.fixture
def mock_models() -> MockModels:
    return MockModels()


@pytest.fixture
def mock_uptodate() -> MockUptodate:
    return MockUptodate()


@pytest.fixture
def config() -> MockConfig:
    return MockConfig()


@pytest.fixture
def mock_path() -> MockAsyncPath:
    return MockAsyncPath()


@pytest.fixture
def mock_import_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_import(*args: t.Any, **kwargs: t.Any) -> t.Any:
        adapter_name = args[0] if args else kwargs.get("adapter_name", "")
        return _get_mock_adapter(adapter_name)

    monkeypatch.setattr("acb.adapters.import_adapter", mock_import)
    _patch_fastblocks_modules(monkeypatch, mock_import)


def _get_mock_adapter(adapter_name: str) -> tuple[t.Any, t.Any, t.Any]:
    return {
        "cache": (MockCache(), None, None),
        "storage": (MockStorage(), None, None),
        "models": (MockModels(), None, None),
        "templates": (
            MockTemplates(MockConfig(), MockStorage(), MockCache()),
            None,
            None,
        ),
        "routes": (MagicMock(), None, None),
    }.get(adapter_name, (MagicMock(), MagicMock(), MagicMock()))


def _patch_fastblocks_modules(
    monkeypatch: pytest.MonkeyPatch, mock_import: t.Callable
) -> None:
    import sys

    for module_name in list(sys.modules.keys()):
        if module_name.startswith("fastblocks.adapters"):
            module = sys.modules[module_name]
            if hasattr(module, "import_adapter"):
                monkeypatch.setattr(f"{module_name}.import_adapter", mock_import)


@pytest.fixture
def http_request() -> Request:
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        pass

    return Request(scope=scope, receive=receive, send=send)


@pytest.fixture
def mock_jinja2_templates() -> t.Any:
    class MockJinja2Templates:
        def __init__(self) -> None:
            self.templates: dict[str, str] = {}

        def get_template(self, template_name: str) -> t.Any:
            if template_name not in self.templates:
                msg = f"Template not found: {template_name}"
                raise KeyError(msg)

            return template_name

    return MockJinja2Templates


@pytest.fixture
def templates(mock_cache: MockCache, mock_storage: MockStorage) -> MockTemplates:
    config = MockConfig()
    return MockTemplates(config, mock_storage, mock_cache)


@pytest.fixture
def jinja2_templates(templates: MockTemplates) -> t.Any:
    return templates


@pytest.fixture
def mock_adapter() -> type:
    return MockAdapter


@pytest.fixture(autouse=False)
def patch_template_loaders():
    from importlib.util import find_spec

    if not find_spec("fastblocks.adapters.templates.jinja2"):
        yield
        return

    with (
        patch(
            "fastblocks.adapters.templates.jinja2.FileSystemLoader",
            MockFileSystemLoader,
        ),
        patch("fastblocks.adapters.templates.jinja2.RedisLoader", MockRedisLoader),
        patch("fastblocks.adapters.templates.jinja2.ChoiceLoader", MockChoiceLoader),
        patch("fastblocks.adapters.templates.jinja2.StorageLoader", MockStorageLoader),
        patch("fastblocks.adapters.templates.jinja2.PackageLoader", MockPackageLoader),
    ):
        yield


@pytest.fixture(autouse=True)
def patch_depends():
    try:
        with (
            patch(
                "fastblocks.adapters.templates._base.depends.inject",
                MockDependsInjector.inject,
            ),
            patch(
                "fastblocks.adapters.templates._base.TemplatesBaseSettings",
                MockTemplatesBaseSettings,
            ),
        ):
            yield
    except (ImportError, AttributeError):
        yield


# ---------------------------------------------------------------------------
# Module state autouse fixtures
# ---------------------------------------------------------------------------

_RESTORED_NAMESPACES = ("fastblocks", "jinja2_async_environment")


@pytest.fixture(autouse=True)
def clean_resolver() -> t.Generator[None]:
    """Reset the fastblocks Resolver singleton around every test.

    Phase 1.5.4 — the Oneiric ``Resolver`` API does not expose a
    public ``clear()`` (see the note in ``fastblocks/core/resolver.py``),
    so we reset by REINITIALIZING the singleton in place:
    ``get_resolver().__init__()``. This replaces ``self.registry``
    with a fresh ``CandidateRegistry`` while preserving the instance
    identity, so callers that captured a reference at import time
    (e.g. ``fastblocks.mcp.tools.depends = FastblocksRegistry(get_resolver())``)
    still point at the now-empty registry.

    The earlier Phase 1.5.4 implementation cleared the cache with
    ``_resolver = None`` and let the next ``get_resolver()`` build a
    fresh Resolver — that worked for the cross-module test (which
    cached Candidate identity at module-import time) but caused
    ``depends`` (captured at tools.py import) to point at a stale
    Resolver while ``register_candidate`` ran against a new one.
    Phase 1.5.5 surfaced this divergence via the MCP integration
    test, which exercises live ``depends.resolve(...)`` after
    re-registration.

    This fixture runs at BOTH setup AND teardown — the teardown
    reset is what prevents the singleton leaking state into the
    next test in collection order.

    ``autouse=True`` so every test gets a clean resolver without
    having to remember to depend on this fixture.
    """
    from fastblocks.core.resolver import get_resolver

    # Setup: clear any registrations from prior tests in the same process.
    get_resolver().__init__()
    yield
    # Teardown: clear this test's registrations so the NEXT test
    # starts with an empty registry.
    get_resolver().__init__()


@pytest.fixture(autouse=True)
def reset_acb_modules():
    """Clean up ACB modules after tests to prevent state pollution."""
    acb_module_names = [
        "acb",
        "acb.adapters",
        "acb.config",
        "acb.depends",
        "acb.actions",
        "acb.actions.encode",
        "acb.actions.hash",
        "acb.logger",
        "acb.debug",
        "acb.console",
        "acb.adapters.app",
        "acb.adapters.auth",
        "acb.adapters.admin",
    ]

    yield

    for module_name in acb_module_names:
        if module_name in sys.modules:
            del sys.modules[module_name]


@pytest.fixture(autouse=True)
def restore_module_state():
    """Save and restore sys.modules state for packages polluted by test mocks."""

    def _matches(key: str) -> bool:
        return any(key == ns or key.startswith(f"{ns}.") for ns in _RESTORED_NAMESPACES)

    saved = {k: v for k, v in sys.modules.items() if _matches(k)}
    yield
    for key in list(sys.modules.keys()):
        if _matches(key):
            if key not in saved:
                del sys.modules[key]
            elif sys.modules[key] is not saved[key]:
                sys.modules[key] = saved[key]
    for key, value in saved.items():
        if key not in sys.modules:
            sys.modules[key] = value


@pytest.fixture
def mock_config():
    return MockConfig()


@pytest.fixture
def mock_templates(mock_config):
    return MockTemplates(config=mock_config)


@pytest.fixture
def mock_request():
    return Request(scope={"type": "http", "method": "GET", "path": "/test"})


@pytest.fixture
def mock_response():
    return HTMLResponse(content="test")


@pytest.fixture
def mock_fastblocks_app(mock_config):
    from unittest.mock import Mock

    app = Mock()
    app.config = mock_config
    app.middleware = []
    app.routes = []
    return app


@pytest.fixture
def fresh_registry():
    """A private FastblocksRegistry for tests that need isolated state.

    Lifted from tests/core/test_resolve_instance.py:_fresh_registry
    during Phase 2 Commit4. Card5's helper was private (leading
    underscore); Phase 2 promotes it to a public conftest fixture
    consumed by both Card5's tests and Phase 2's
    test_resolver_mismatch.py.

    The fixture builds a private Resolver (not the canonical
    singleton from get_resolver()) — Phase 1.5x Card 8's "non-
    canonical warning" will fire on construction. That warning is
    acceptable here; it's the same posture Card5 used and the
    existing test_facade_identity_check.py suppresses it via caplog.
    """
    from oneiric.core.resolution import Resolver
    from fastblocks.core.resolver import FastblocksRegistry

    return FastblocksRegistry(Resolver())


# ---------------------------------------------------------------------------
# Hypothesis profile mechanics (Phase 5 v4 retry — Task 3)
# ---------------------------------------------------------------------------

import logging
import os

from hypothesis import settings, Verbosity

HYPOTHESIS_PROFILE = os.environ.get("HYPOTHESIS_PROFILE", "ci")

# Per Erratum 24: try/except because settings.register_profile is process-global
# and xdist worker re-import would raise InvalidArgument on second registration.
try:
    settings.register_profile(
        "dev", max_examples=10, deadline=None, derandomize=False,
        verbosity=Verbosity.normal,
    )
    settings.register_profile(
        "ci", max_examples=100, deadline=None, derandomize=False,
        verbosity=Verbosity.normal,
    )
    settings.register_profile(
        "debug", max_examples=1, deadline=None, derandomize=True,
        verbosity=Verbosity.verbose,
    )
except Exception:
    pass  # Already registered (xdist worker re-import)

settings.load_profile(HYPOTHESIS_PROFILE)


# ---------------------------------------------------------------------------
# Playwright + FastBlocksApp fixtures (Phase 5 v4 retry — Task 3)
# ---------------------------------------------------------------------------

import pytest_asyncio
from playwright.async_api import async_playwright

from fastblocks.adapters.app.default import FastBlocksApp  # per F-L1-001


@pytest_asyncio.fixture
async def clean_axe_core_page():
    """Fresh Playwright page per test; closes browser context on teardown.

    Function scope is MANDATORY — Playwright pages aren't safe to share across tests.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()
            await browser.close()


@pytest.fixture
def fastblocks_test_app():
    """Per-test FastBlocks app — fresh app instance per test.

    Function scope (per Erratum 25: conservative, not strictly mandatory
    given clean_resolver doesn't touch app.state. The binding constraint
    is the ~20s cost across ~4 tests, which fits within 5-min CI budget).
    """
    return FastBlocksApp()

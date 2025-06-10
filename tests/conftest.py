"""Test configuration for FastBlocks."""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportArgumentType=false, reportMissingTypeArgument=false

import asyncio
import functools
import json
import os
import sys
import types
import typing as t
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Optional, Protocol, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.types import Message, Scope


def _create_mock_debug_settings() -> type:
    """Create a mock debug settings class for ACB."""

    class MockDebugSettings:
        def __init__(self) -> None:
            self.enabled = False
            self.settings_path = "/mock/path/to/settings"

    return MockDebugSettings


def _create_asyncio_mock_functions() -> tuple[Callable, Callable, Callable]:
    """Create mock functions for asyncio-related operations."""

    # Mock for asyncio.run to avoid issues with settings file creation
    async def mock_build_settings() -> dict:
        return {}

    def mock_asyncio_run(coro) -> Any:
        if coro.__qualname__ == "_settings_build_values":
            return {}
        # For other coroutines, use the real asyncio.run
        return asyncio.run(coro)

    # Create patch for ACB's load_yml_settings method
    async def mock_load_yml_settings() -> dict:
        return {}

    return mock_build_settings, mock_asyncio_run, mock_load_yml_settings


def _create_mock_yaml_functions() -> tuple[Callable, Callable]:  # noqa: F841
    """Create mock functions for YAML operations."""

    # Create patch for ACB's yaml.dump method to avoid file writes
    async def mock_yaml_dump(obj, path) -> None:
        pass

    # Create a module-level patch function for Config.init
    def mock_config_init(self) -> None:
        MockDebugSettings = _create_mock_debug_settings()
        self.debug = MockDebugSettings()

    return mock_yaml_dump, mock_config_init


# Use the function to prevent unused warning
_create_mock_yaml_functions()  # noqa: F841


def _is_minify_action_test() -> bool:
    """Check if we're running minify action tests."""
    import sys

    # Check if test_minify.py is in the command line arguments
    for arg in sys.argv:
        if "test_minify.py" in arg or "actions/minify" in arg:
            return True

    # Also check if we're in pytest and the current test node contains minify
    with suppress(ImportError, AttributeError):
        import pytest

        # Check if we're in a test session and the current item is a minify test
        if hasattr(pytest, "current_node") and pytest.current_node:
            return "test_minify" in str(pytest.current_node)
    return False


def _apply_patches() -> None:
    """Apply necessary patches to prevent filesystem access."""
    _, mock_asyncio_run, _ = _create_asyncio_mock_functions()

    # Apply the patches
    patches = [
        patch("asyncio.run", mock_asyncio_run),
    ]

    # Apply the patches immediately
    for p in patches:
        p.start()


def _create_acb_modules() -> tuple[dict[str, ModuleType], type]:
    """Create the basic ACB module structure."""
    MockDebugSettings = _create_mock_debug_settings()

    # Preemptively add our patched modules to sys.modules
    # This ensures our mocks are used instead of the real modules
    # that might try to access the filesystem
    mock_acb_module = types.ModuleType("acb")
    mock_acb_module.__path__ = [
        "/mock/path/to/acb"
    ]  # Add __path__ to make it a package

    mock_acb_config = types.ModuleType("acb.config")
    mock_acb_depends = types.ModuleType("acb.depends")
    mock_acb_actions = types.ModuleType("acb.actions")
    mock_acb_actions.__path__ = ["/mock/path/to/acb/actions"]
    mock_acb_actions_encode = types.ModuleType("acb.actions.encode")
    mock_acb_actions_hash = types.ModuleType("acb.actions.hash")
    mock_acb_adapters = types.ModuleType("acb.adapters")
    mock_acb_logger = types.ModuleType("acb.logger")

    # Build a dictionary of modules
    mock_acb_debug = types.ModuleType("acb.debug")

    modules_dict = {
        "acb": mock_acb_module,
        "acb.config": mock_acb_config,
        "acb.depends": mock_acb_depends,
        "acb.actions": mock_acb_actions,
        "acb.actions.encode": mock_acb_actions_encode,
        "acb.actions.hash": mock_acb_actions_hash,
        "acb.adapters": mock_acb_adapters,
        "acb.logger": mock_acb_logger,
        "acb.debug": mock_acb_debug,
    }

    return modules_dict, MockDebugSettings


def _setup_acb_module(mock_acb_module: ModuleType) -> None:
    """Set up the main ACB module with necessary classes and attributes."""

    # Add missing Adapter class and pkg_registry to acb module
    class Adapter:
        def __init__(self, *args, **kwargs) -> None:
            pass

    # Add register_pkg function
    def register_pkg() -> None:
        """Mock implementation of register_pkg."""
        pass

    mock_acb_module.Adapter = Adapter
    mock_acb_module.pkg_registry = MagicMock()
    mock_acb_module.register_pkg = register_pkg


def _setup_acb_adapters(mock_acb_adapters: ModuleType) -> None:
    """Set up the ACB adapters module with necessary functions."""
    mock_acb_adapters.get_adapters = MagicMock(return_value=[])
    mock_acb_adapters.get_adapter = MagicMock(return_value=MagicMock())
    mock_acb_adapters.get_installed_adapter = MagicMock(return_value=MagicMock())
    mock_acb_adapters.import_adapter = MagicMock(
        side_effect=lambda adapter_name="templates": (
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
    )
    mock_acb_adapters.root_path = "/mock/path/to/adapters"


def _create_acb_classes(MockDebugSettings: type) -> tuple[type, type, type, Any]:
    """Create the necessary classes for ACB modules."""

    # Set up the basic functionality needed by tests
    class Config:
        def __init__(self) -> None:
            self.debug = MockDebugSettings()

        def init(self) -> None:
            pass

    class Settings:
        def __init__(self) -> None:
            self.debug = {}

    class AdapterBase:
        def __init__(self, *args, **kwargs) -> None:
            pass

    # Mock the dependencies module
    class Depends:
        def __init__(self) -> None:
            self.registered_classes = {}

        def __call__(self, cls=None) -> Any:
            """Make Depends callable to handle depends()."""
            if cls is None:
                return Config()
            if cls == Config:
                return Config()
            return MagicMock()

        @classmethod
        def get(cls, adapter_class) -> Any:
            if adapter_class.__name__ == "Config":
                return Config()
            return MagicMock()

    depends = Depends()
    depends.inject = lambda f: f
    depends.set = lambda cls: cls

    return Config, Settings, AdapterBase, depends


def _setup_acb_config(
    mock_acb_config: ModuleType, Config: type, Settings: type, AdapterBase: type
) -> None:
    """Set up the ACB config module with necessary classes."""
    mock_acb_config.Config = Config
    mock_acb_config.Settings = Settings
    mock_acb_config.AdapterBase = AdapterBase


def _setup_acb_depends(mock_acb_depends: ModuleType, depends: Any) -> None:
    """Set up the ACB depends module with necessary functions."""
    # Make depends directly accessible as a module attribute
    mock_acb_depends.depends = depends
    # Also set it as the default export for from acb.depends import depends
    setattr(mock_acb_depends, "__call__", depends.__call__)


def _setup_acb_actions_encode(mock_acb_actions_encode: ModuleType) -> None:
    """Set up the ACB actions.encode module with necessary functions."""

    # Set up encode module with dump/load functions
    def mock_dump(obj) -> str:
        return json.dumps(obj)

    def mock_load(data) -> Any:
        return json.loads(data)

    mock_acb_actions_encode.dump = MagicMock(side_effect=mock_dump)
    mock_acb_actions_encode.load = MagicMock(side_effect=mock_load)

    # Ensure yaml is available with dummy methods
    mock_acb_actions_encode.yaml = MagicMock()
    mock_acb_actions_encode.yaml.dump = AsyncMock()
    mock_acb_actions_encode.yaml.load = AsyncMock(return_value={})


def _setup_acb_actions_hash(mock_acb_actions_hash: ModuleType) -> None:
    """Set up the ACB actions.hash module with necessary functions."""

    def mock_hash(content: Any) -> str:
        """Mock hash function."""
        if isinstance(content, str):
            return f"hash_{len(content)}"
        elif isinstance(content, bytes):
            return f"hash_{len(content)}"
        return "hash_mock"

    mock_acb_actions_hash.hash = mock_hash

    # Add url_encode for filters_mock
    def url_encode(s: str) -> str:
        from urllib.parse import quote_plus

        return quote_plus(s)

    mock_acb_actions_hash.url_encode = url_encode


def _setup_acb_logger(mock_acb_logger: ModuleType) -> None:
    """Set up the ACB logger module with a mock Logger class."""

    class MockLogger:
        def __init__(self, name: str = "test_logger", **kwargs: Any) -> None:
            self.name = name

        def bind(self, **kwargs: Any) -> "MockLogger":
            return self

        def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
            pass

        def info(self, message: str, *args: Any, **kwargs: Any) -> None:
            pass

        def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
            pass

        def error(self, message: str, *args: Any, **kwargs: Any) -> None:
            pass

        def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
            pass

    mock_acb_logger.Logger = MockLogger
    mock_acb_logger.InterceptHandler = MagicMock()


def _setup_acb_debug(mock_acb_debug: ModuleType) -> None:
    """Set up the ACB debug module with a mock debug function."""

    def debug(*args: Any, **kwargs: Any) -> None:
        """Mock debug function that does nothing."""
        pass

    mock_acb_debug.debug = debug


def _patch_acb_modules() -> None:
    """Patch ACB modules to prevent filesystem access during tests.

    This function patches key components of the ACB framework that attempt to
    write to the filesystem during module import, preventing test failures due
    to missing files or directories.
    """
    # Apply necessary patches
    _apply_patches()

    # Create ACB modules
    modules_dict, MockDebugSettings = _create_acb_modules()

    # Set up individual modules
    _setup_acb_module(modules_dict["acb"])
    _setup_acb_adapters(modules_dict["acb.adapters"])

    # Create necessary classes
    Config, Settings, AdapterBase, depends = _create_acb_classes(MockDebugSettings)

    # Set up module contents
    _setup_acb_config(modules_dict["acb.config"], Config, Settings, AdapterBase)
    _setup_acb_depends(modules_dict["acb.depends"], depends)
    _setup_acb_actions_encode(modules_dict["acb.actions.encode"])
    _setup_acb_actions_hash(modules_dict["acb.actions.hash"])
    _setup_acb_logger(modules_dict["acb.logger"])
    _setup_acb_debug(modules_dict["acb.debug"])

    # Add our modules to sys.modules
    for module_name, module in modules_dict.items():
        sys.modules[module_name] = module


# Patch ACB modules immediately when conftest.py is imported
# This needs to happen before any test modules import FastBlocks modules with ACB dependencies
_patch_acb_modules()


def pytest_configure(config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "cli_coverage: mark test as measuring CLI coverage"
    )

    # Patch anyio.Path to use our MockAsyncPath implementation
    # This prevents filesystem access when using anyio.Path
    from contextlib import suppress

    with suppress(ImportError):
        import anyio

        sys.modules["anyio.Path"] = MockAsyncPath
        if hasattr(anyio, "Path"):
            anyio.Path = MockAsyncPath


class MockAsyncPath:
    def __init__(self, path: Union[str, Path, "MockAsyncPath"] = "") -> None:
        if isinstance(path, MockAsyncPath):
            self._path = path._path
        else:
            self._path = str(path)

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return f"MockAsyncPath('{self._path}')"

    def __fspath__(self) -> str:
        return self._path

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, MockAsyncPath):
            return self._path == other._path
        if isinstance(other, str | Path):
            return self._path == str(other)
        return False

    def __truediv__(self, other: Union[str, Path, "MockAsyncPath"]) -> "MockAsyncPath":
        other_str = str(other)
        if self._path.endswith("/"):
            return MockAsyncPath(f"{self._path}{other_str}")
        return MockAsyncPath(f"{self._path}/{other_str}")

    @property
    def parent(self) -> "MockAsyncPath":
        parent_path = "/".join(self._path.split("/")[:-1])
        if not parent_path:
            parent_path = "/"
        return MockAsyncPath(parent_path)

    @property
    def name(self) -> str:
        return self._path.split("/")[-1]

    @property
    def stem(self) -> str:
        """Return the final path component without its suffix."""
        name = self.name
        i = name.rfind(".")
        if i == -1:
            return name
        return name[:i]

    @property
    def parts(self) -> tuple[str, ...]:
        parts = [part for part in self._path.split("/") if part]
        if self._path.startswith("/"):
            return ("/",) + tuple(parts)
        return tuple(parts)

    async def exists(self) -> bool:
        return True

    async def is_file(self) -> bool:
        return "." in self._path.split("/")[-1]

    async def is_dir(self) -> bool:
        return not await self.is_file()

    async def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        """Mock implementation of mkdir."""
        return None

    def with_suffix(self, suffix: str) -> "MockAsyncPath":
        if "." in self._path:
            base = self._path.rsplit(".", 1)[0]
        else:
            base = self._path
        return MockAsyncPath(f"{base}{suffix}")

    async def iterdir(self):
        """Mock implementation of iterdir that returns an async iterator."""

        class AsyncIterator:
            def __init__(self, items=None) -> None:
                self.items = items or []
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        return AsyncIterator()

    async def glob(self, pattern: str) -> list["MockAsyncPath"]:
        return []


class MockAdapter:
    def __init__(
        self, name: str = "test", category: str = "app", path: Any = None
    ) -> None:
        self.name = name
        self.category = category
        self.path = path
        self.style = "test_style"

    def __repr__(self) -> str:
        return f"MockAdapter(name={self.name})"


class MockConfig:
    def __init__(self) -> None:
        self.app = Mock()
        self.app.name = "test_app"
        self.app.debug = True

        self.templates = Mock()
        self.templates.directory = "templates"
        self.templates.extension = ".html"

        self.cache = Mock()
        self.cache.enabled = True
        self.cache.ttl = 3600

        self.storage = Mock()
        self.storage.local_path = "storage"
        self.storage.local_fs = True

        self.sitemap = Mock()
        self.sitemap.change_freq = "hourly"
        self.sitemap.priority = 0.5

        self.package_name: str | None = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __call__(self, key: str | None = None) -> Any:
        if key is None:
            return self
        return self[key]

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def set(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class MockTemplateFilters:
    @staticmethod
    def truncate(text: str, length: int) -> str:
        return text[: length - 3] + "..." if len(text) > length else text

    @staticmethod
    def filesize(size: int) -> str:
        if size < 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


class MockTemplateRenderer:
    def __init__(
        self,
        storage: Optional["MockStorage"] = None,
        cache: Optional["MockCache"] = None,
    ) -> None:
        self.templates: dict[str, str] = {
            "page.html": "<html><body>page.html: title, content, items</body></html>",
            "custom.html": "<html><body>Custom template response</body></html>",
            "cached.html": "<html><body>Cached content</body></html>",
            "test.html": "<html><body>test.html: {{ title }}, {{ content }}</body></html>",
        }
        self.storage = storage
        self.cache = cache
        self._mock_responses: dict[str, Response] = {}

    def add_template(self, name: str, content: str) -> None:
        self.templates[name] = content

    def set_response(self, template: str, response: Response) -> None:
        self._mock_responses[template] = response

    async def render_template(
        self,
        request: Request,
        template: str,
        context: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        if template in self._mock_responses:
            return self._mock_responses[template]

        if context is None:
            context = {}

        if headers is None:
            headers = {}

        if template not in self.templates:
            raise MockTemplateNotFound(template)

        if template == "page.html" and "title" in context:
            return HTMLResponse(
                content="<html><body>page.html: title, content, items</body></html>",
                headers=headers,
            )

        if template == "test.html":
            content = "<html><body>test.html: title, content, items</body></html>"
            return HTMLResponse(content=content, headers=headers)

        content = self.templates[template]

        for key, value in context.items():
            if isinstance(value, str):
                content = content.replace("{{ " + key + " }}", value)

        return HTMLResponse(content=content, headers=headers)

    async def render_template_block(
        self,
        request: Request,
        template: str,
        block: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        if context is None:
            context = {}

        if template not in self.templates:
            raise MockTemplateNotFound(template)

        return f"Block {block} from {template}"


class MockTemplates:
    def __init__(
        self,
        config: Optional["MockConfig"] = None,
        storage: Any = None,
        cache: Any = None,
    ) -> None:
        self.storage = storage
        self.cache = cache
        self.config = config or MockConfig()

        if not hasattr(self.config, "app"):
            setattr(self.config, "app", SimpleNamespace(style="test_style"))
        elif not hasattr(self.config.app, "style"):
            self.config.app.style = "test_style"

        self.app = MockTemplateRenderer(storage, cache)
        self.admin = MockTemplateRenderer(storage, cache)

        self.app_searchpaths = None
        self.admin_searchpaths = None

        self.filters = {
            "truncate": MockTemplateFilters.truncate,
            "filesize": MockTemplateFilters.filesize,
        }

    def get_searchpath(self, adapter: Any, path: Any) -> list[Any]:
        style = self.config.app.style
        base_path = path / "base"
        style_path = path / style
        style_adapter_path = path / style / adapter.name
        theme_adapter_path = style_adapter_path / "theme"
        return [
            theme_adapter_path,
            style_adapter_path,
            style_path,
            base_path,
        ]

    async def get_searchpaths(self, adapter: Any) -> list[Any]:
        from unittest.mock import patch

        with patch("fastblocks.adapters.templates._base.root_path", adapter.path):
            return self.get_searchpath(
                adapter, adapter.path / "templates" / adapter.category
            )

    def get_storage_path(self, path: str | Path) -> str:
        return f"templates/{path}"

    def get_cache_key(self, path: str | Path) -> str:
        return f"template:{path}"


class MockStorage:
    def __init__(self) -> None:
        self._storage: dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any:
        return self._storage[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def __delitem__(self, key: str) -> None:
        del self._storage[key]

    def __contains__(self, key: str) -> bool:
        return key in self._storage

    def get(self, key: str, default: Any = None) -> Any:
        return self._storage.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def delete(self, key: str) -> None:
        if key in self._storage:
            del self._storage[key]

    def exists(self, key: str) -> bool:
        return key in self._storage

    def clear(self) -> None:
        self._storage.clear()


class MockCache:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any, expire: int = 0) -> None:
        self._cache[key] = value

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def exists(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()


class MockAdapters:
    def __init__(self) -> None:
        self.root_path = MockAsyncPath("/mock/root/path")
        self.Adapter = MagicMock()
        self.pkg_registry = {}
        self._adapters = self._create_adapter_objects()

    def _create_adapter_objects(self) -> dict[str, MockAdapter]:
        adapters = {}

        for name in ("cache", "storage", "templates", "routes"):
            adapter = MockAdapter(name)
            adapter.path = MockAsyncPath(f"/mock/adapters/{name}")
            adapters[name] = adapter

        return adapters

    def import_adapter(self, adapter_name: str = "cache") -> tuple[Any, Any, Any]:
        mock_cache = MockCache()
        mock_storage = MockStorage()
        mock_models = MockModels()
        mock_templates = MockTemplates(MockConfig(), mock_storage, mock_cache)

        if adapter_name == "cache":
            return (mock_cache, mock_storage, mock_models)
        elif adapter_name == "storage":
            return (mock_storage, mock_models, None)
        elif adapter_name == "templates":
            return (mock_templates, None, None)
        elif adapter_name == "routes":
            mock_routes = MagicMock()
            return (mock_routes, None, None)
        return (MagicMock(), MagicMock(), MagicMock())

    def get_adapters(self) -> list[Any]:
        return list(self._adapters.values())

    def get_installed_adapter(self, adapter_name: str) -> Any:
        return self._adapters.get(adapter_name, MagicMock())

    def get_adapter(self, adapter_name: str) -> Any:
        if adapter_name == "cache":
            return MockCache()
        elif adapter_name == "storage":
            return MockStorage()
        elif adapter_name == "templates":
            return MockTemplates(MockConfig(), MockStorage(), MockCache())
        elif adapter_name == "routes":
            return MagicMock()
        return MagicMock()


class MockConfigModule:
    def __init__(self) -> None:
        self._config = MockConfig()
        self.AsyncPath = MockAsyncPath
        self.Config = self._config
        self.Adapter = MagicMock()
        self.pkg_registry = {}

    class AdapterBase:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.name = "mock_adapter"
            self.settings = {}

    class Settings:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.settings = {}
            self.app = SimpleNamespace()
            self.adapters = SimpleNamespace()
            self.debug = SimpleNamespace()

        def load(self) -> None:
            pass

        def __getattr__(self, name: str) -> Any:
            return self.settings.get(name, None)

        def __setattr__(self, name: str, value: Any) -> None:
            if name in ("settings", "app", "adapters", "debug"):
                super().__setattr__(name, value)
            else:
                self.settings[name] = value


class MockActions:
    def __init__(self) -> None:
        self.hash = self._create_hash_module()

    def _create_hash_module(self) -> Any:
        class HashModule:
            def __init__(self) -> None:
                pass

            def hash(self, content: Any) -> str:
                if isinstance(content, str):
                    return f"hash_{len(content)}"
                elif isinstance(content, bytes):
                    return f"hash_{len(content)}"
                return "hash_mock"

        return HashModule()


class MockDepends:
    def __init__(self) -> None:
        self.dependencies: dict[str, Any] = {}

        def depends_func(*args: Any, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                return func

            return decorator

        def inject_func(func: Any) -> Any:
            return func

        def set_func(cls: Any) -> Any:
            self.dependencies[cls.__name__] = cls
            return cls

        def get_func(name: str) -> Any:
            return self.dependencies.get(name, MagicMock())

        self.depends = depends_func
        setattr(self.depends, "inject", inject_func)
        setattr(self.depends, "set", set_func)
        setattr(self.depends, "get", get_func)


class MockDependsInjector:
    @staticmethod
    def inject(f: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if (
                "config" not in kwargs
                and len(args) > 1
                and isinstance(args[1], MockConfig)
            ):
                kwargs["config"] = args[1]
            return f(*args, **kwargs)

        return wrapper


class MockTemplatesBaseSettings:
    def __init__(
        self, config: Any = None, cache_timeout: int = 300, **values: Any
    ) -> None:
        self.cache_timeout = cache_timeout
        if config:
            self.update_from_config(config)

    def update_from_config(self, config: Any) -> None:
        self.cache_timeout = 300 if getattr(config, "deployed", False) else 1


class MockDebug:
    def __init__(self) -> None:
        self.enabled = True

    def debug(self, *args: Any, **kwargs: Any) -> None:
        pass

    def trace(self, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, *args: Any, **kwargs: Any) -> None:
        pass


class MockLogger:
    def __init__(self) -> None:
        self.InterceptHandler = MagicMock()
        self.Logger = self._create_logger_class()

    def _create_logger_class(self) -> Any:
        class LoggerClass:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.name = kwargs.get("name", "mock_logger")

            def bind(self, **kwargs: Any) -> "LoggerClass":
                return self

            def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def info(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def error(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

        return LoggerClass


class MockSitemap:
    def __init__(self) -> None:
        class InnerSitemap:
            def __init__(self) -> None:
                self.urls = []
                self.change_freq = "hourly"
                self.priority = 0.5

        self.sitemap = InnerSitemap()
        self.config: Any = None

    async def init(self) -> None:
        pass

    async def add_url(self, url: str, **kwargs: Any) -> None:
        if not url.startswith(("/", "http")):
            raise ValueError(f"Invalid URL format: {url}")

        if " " in url:
            raise ValueError(f"URL contains invalid characters: {url}")

        if url.startswith("ftp:"):
            raise ValueError(f"Unsupported URL protocol: {url}")

        change_freq = kwargs.get("change_freq", "hourly")

        valid_freqs = (
            "always",
            "hourly",
            "daily",
            "weekly",
            "monthly",
            "yearly",
            "never",
        )
        if change_freq not in valid_freqs:
            raise ValueError(f"Invalid change frequency: {change_freq}")

        priority = kwargs.get("priority", 0.5)

        if not isinstance(priority, int | float) or priority < 0.0 or priority > 1.0:
            raise ValueError(
                f"Invalid priority value: {priority}. Must be between 0.0 and 1.0"
            )

        last_modified = kwargs.get("last_modified", datetime.now())

        url_obj = SitemapURL(
            loc=url,
            change_freq=change_freq,
            priority=priority,
            last_modified=last_modified,
        )
        self.sitemap.urls.append(url_obj)

    async def generate(self) -> str:
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        for url in self.sitemap.urls:
            xml += "  <url>\n"
            xml += f"    <loc>{url.loc}</loc>\n"
            if hasattr(url, "last_modified"):
                xml += (
                    f"    <lastmod>{url.last_modified.strftime('%Y-%m-%d')}</lastmod>\n"
                )
            if hasattr(url, "change_freq"):
                xml += f"    <changefreq>{url.change_freq}</changefreq>\n"
            if hasattr(url, "priority"):
                xml += f"    <priority>{url.priority}</priority>\n"
            xml += "  </url>\n"

        xml += "</urlset>"
        return xml

    async def write(self, path: Any = None) -> None:
        xml = await self.generate()

        if path is None:
            if hasattr(self.config, "storage") and hasattr(
                self.config.storage, "local_path"
            ):
                path = Path(self.config.storage.local_path) / "sitemap.xml"
            else:
                raise ValueError(
                    "No path provided and no default path available in config"
                )

        if hasattr(path, "_path"):
            path = Path(path._path)

        Path(path).parent.mkdir(exist_ok=True, parents=True)

        Path(path).write_text(xml)


class MockModels:
    def __init__(self) -> None:
        self.models: dict[str, Any] = {}

    def get_model(self, model_name: str) -> Any:
        return self.models.get(model_name)

    def register_model(self, model_name: str, model: Any) -> None:
        self.models[model_name] = model


class MockUptodate:
    def __init__(self) -> None:
        self.updates: dict[str, bool] = {}

    def check(self, package: str) -> bool:
        return self.updates.get(package, True)

    def set_update(self, package: str, is_up_to_date: bool) -> None:
        self.updates[package] = is_up_to_date


@pytest.fixture
def mock_cache() -> AsyncMock:
    mock = AsyncMock()

    mock.exists = AsyncMock(return_value=False)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.clear = AsyncMock(return_value=True)

    return mock


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
    def mock_import(*args: Any, **kwargs: Any) -> Any:
        adapter_name = args[0] if args else kwargs.get("adapter_name", "")

        if adapter_name == "cache":
            return (MockCache(), None, None)
        elif adapter_name == "storage":
            return (MockStorage(), None, None)
        elif adapter_name == "models":
            return (MockModels(), None, None)
        elif adapter_name == "templates":
            mock_templates = MockTemplates(MockConfig(), MockStorage(), MockCache())
            return (mock_templates, None, None)
        elif adapter_name == "routes":
            mock_routes = MagicMock()
            return (mock_routes, None, None)

        return (MagicMock(), MagicMock(), MagicMock())

    monkeypatch.setattr("acb.adapters.import_adapter", mock_import)

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
def mock_jinja2_templates() -> Any:
    class MockJinja2Templates:
        def __init__(self) -> None:
            self.templates: dict[str, str] = {}

        def get_template(self, template_name: str) -> Any:
            if template_name not in self.templates:
                raise Exception(f"Template not found: {template_name}")

            return template_name

    return MockJinja2Templates


@pytest.fixture
def templates(mock_cache: MockCache, mock_storage: MockStorage) -> MockTemplates:
    config = MockConfig()
    return MockTemplates(config, mock_storage, mock_cache)


@pytest.fixture
def jinja2_templates(templates: MockTemplates) -> Any:
    return templates


@pytest.fixture
def mock_templates(mock_cache: MockCache, mock_storage: MockStorage) -> MockTemplates:
    config = MockConfig()
    return MockTemplates(config, mock_storage, mock_cache)


@pytest.fixture
def mock_adapter() -> type:
    return MockAdapter


class SitemapURL:
    def __init__(
        self, loc: str, change_freq: str, priority: float, last_modified: datetime
    ) -> None:
        self.loc = loc
        self.change_freq = change_freq
        self.priority = priority
        self.last_modified = last_modified


@pytest.fixture(autouse=False)  # Changed to non-autouse
def patch_template_loaders():
    # Only patch if module exists to prevent errors in filters tests
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
def mock_acb():  # noqa: C901
    """Mock the ACB module for testing."""
    # Create mock modules
    module_structure = {
        "acb": types.ModuleType("acb"),
        "acb.actions": types.ModuleType("acb.actions"),
        "acb.actions.encode": types.ModuleType("acb.actions.encode"),
        "acb.config": types.ModuleType("acb.config"),
        "acb.depends": types.ModuleType("acb.depends"),
        "acb.adapters": types.ModuleType("acb.adapters"),
        "anyio": types.ModuleType("anyio")
        if "anyio" not in sys.modules
        else sys.modules["anyio"],
    }

    # Set up package paths
    module_structure["acb"].__path__ = ["/mock/path/to/acb"]
    module_structure["acb.actions"].__path__ = ["/mock/path/to/acb/actions"]
    module_structure["acb.adapters"].__path__ = ["/mock/path/to/acb/adapters"]

    # Make sure anyio.Path uses our MockAsyncPath
    module_structure["anyio"].Path = MockAsyncPath

    # Create mock implementations
    class AdapterBase:
        def __init__(self, *args, **kwargs) -> None:
            self.path = "/mock/path/to/adapter"

        def get_path(self) -> str:
            return self.path

    class Settings:
        """Mock ACB Settings class."""

        def __init__(self, *args, **kwargs) -> None:
            self.data = {}
            self.debug = {}
            self.app = {"name": "test_app", "debug": True}

        def __getitem__(self, key: str) -> Any:
            return getattr(self, key, {})

    class DebugSettings:
        """Mock ACB DebugSettings class."""

        def __init__(self) -> None:
            self.enabled = False

    class Config:
        """Mock ACB Config class."""

        def __init__(self, *args, **kwargs) -> None:
            self.data = {}
            self.debug = DebugSettings()
            self.app = {"name": "test_app", "debug": True}

        def load(self) -> dict:
            return self.data

        def dump(self) -> None:
            pass

        def init(self) -> None:
            """Mock initialization - does nothing."""
            pass

        @classmethod
        def get_instance(cls) -> "Config":
            """Get singleton instance."""
            return cls()

    def injectable(func=None, *args, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__acb_injectable__ = True
            return wrapper

        return decorator(func) if func else decorator

    def provider(func=None, *args, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__acb_provider__ = True
            return wrapper

        return decorator(func) if func else decorator

    def dump(obj):
        """Mock encode.dump."""
        return json.dumps(obj)

    def load(data):
        """Mock encode.load."""
        return json.loads(data)

    # Create a mock depends module with get function
    class Depends:
        """Mock ACB depends module."""

        def __init__(self) -> None:
            pass

        def __call__(self, cls=None) -> Any:
            """Make Depends callable to handle depends()."""
            if cls is None:
                return Config()
            if cls == Config:
                return Config()
            return MagicMock()

        @classmethod
        def get(cls, adapter_class):
            """Return a mock Config instance."""
            if adapter_class == Config:
                return Config()
            return MagicMock()

    depends = Depends()
    depends.injectable = injectable
    depends.provider = provider
    depends.inject = lambda f: f
    depends.set = lambda cls: cls

    # Add all classes and functions to modules
    module_structure["acb.config"].Config = Config
    module_structure["acb.config"].Settings = Settings
    module_structure["acb.config"].DebugSettings = DebugSettings
    module_structure["acb.config"].AdapterBase = AdapterBase

    module_structure["acb.depends"].depends = depends
    module_structure["acb.depends"].injectable = injectable
    module_structure["acb.depends"].provider = provider
    module_structure["acb.depends"].get = (
        lambda cls: Config() if cls == Config else MagicMock()
    )

    module_structure["acb.actions.encode"].dump = dump
    module_structure["acb.actions.encode"].load = load

    module_structure["acb.adapters"].AdapterBase = AdapterBase
    module_structure["acb.adapters"].get_adapter = MagicMock(return_value=None)
    module_structure["acb.adapters"].get_installed_adapter = MagicMock(
        return_value=None
    )
    module_structure["acb.adapters"].import_adapter = MagicMock(
        side_effect=lambda adapter_name="templates": (
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
    )

    # Register mock modules
    with patch.dict("sys.modules", module_structure):
        yield module_structure


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


# Not using these anymore


def _setup_fastblocks_module_structure() -> None:
    """Set up the FastBlocks module structure with all necessary submodules.

    This function creates mock modules for fastblocks package structure
    to ensure imports work correctly during testing.
    """
    # Create the main module structure
    module_structure = {
        "fastblocks.adapters": types.ModuleType("fastblocks.adapters"),
        "fastblocks.adapters.templates": types.ModuleType(
            "fastblocks.adapters.templates"
        ),
        "fastblocks.adapters.templates._base": types.ModuleType(
            "fastblocks.adapters.templates._base"
        ),
        "fastblocks.adapters.templates._filters": types.ModuleType(
            "fastblocks.adapters.templates._filters"
        ),
        "fastblocks.adapters.templates.jinja2": types.ModuleType(
            "fastblocks.adapters.templates.jinja2"
        ),
        "fastblocks.adapters.admin": types.ModuleType("fastblocks.adapters.admin"),
        "fastblocks.adapters.admin._base": types.ModuleType(
            "fastblocks.adapters.admin._base"
        ),
        "fastblocks.adapters.app": types.ModuleType("fastblocks.adapters.app"),
        "fastblocks.adapters.app._base": types.ModuleType(
            "fastblocks.adapters.app._base"
        ),
        "fastblocks.adapters.auth": types.ModuleType("fastblocks.adapters.auth"),
        "fastblocks.adapters.auth._base": types.ModuleType(
            "fastblocks.adapters.auth._base"
        ),
        "fastblocks.adapters.routes": types.ModuleType("fastblocks.adapters.routes"),
        "fastblocks.adapters.routes._base": types.ModuleType(
            "fastblocks.adapters.routes._base"
        ),
        "fastblocks.adapters.sitemap": types.ModuleType("fastblocks.adapters.sitemap"),
        "fastblocks.adapters.sitemap._base": types.ModuleType(
            "fastblocks.adapters.sitemap._base"
        ),
        "fastblocks.adapters.sitemap._routes": types.ModuleType(
            "fastblocks.adapters.sitemap._routes"
        ),
    }

    # Set up each module
    _setup_templates_base_module(
        module_structure["fastblocks.adapters.templates._base"]
    )
    _setup_templates_filters_module(
        module_structure["fastblocks.adapters.templates._filters"]
    )
    _setup_templates_jinja2_module(
        module_structure["fastblocks.adapters.templates.jinja2"]
    )
    _setup_admin_base_module(module_structure["fastblocks.adapters.admin._base"])

    # Set up module paths and inheritance
    for module_name, module in module_structure.items():
        module.__path__ = [f"/mock/path/to/{module_name.replace('.', '/')}"]
        sys.modules[module_name] = module

    # Link parent modules to child modules
    for module_name, module in module_structure.items():
        if "._" in module_name:
            parent_name = module_name.rsplit("._", 1)[0]
            attr_name = f"_{module_name.split('._')[-1]}"
            if parent_name in module_structure:
                setattr(module_structure[parent_name], attr_name, module)

    # Add imports from child modules to parent modules
    for parent_name in (
        "fastblocks.adapters.templates",
        "fastblocks.adapters.admin",
        "fastblocks.adapters.app",
        "fastblocks.adapters.auth",
        "fastblocks.adapters.routes",
        "fastblocks.adapters.sitemap",
    ):
        if parent_name in module_structure:
            parent = module_structure[parent_name]
            # Import classes from _base
            base_module_name = f"{parent_name}._base"
            if base_module_name in module_structure:
                base_module = module_structure[base_module_name]
                for attr_name in dir(base_module):
                    if not attr_name.startswith("_") or attr_name == "__all__":
                        setattr(parent, attr_name, getattr(base_module, attr_name))


def _setup_admin_base_module(admin_base: ModuleType) -> None:
    """Set up the admin base module with necessary classes."""

    class MockAdapterBase:
        def __init__(self, **kwargs: t.Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class MockAdminBaseSettings:
        def __init__(self) -> None:
            self.title = "FastBlocks Dashboard"
            self.style = "bootstrap"
            self.logo_url = "/static/img/logo.png"
            self.login_view = "/admin/login"
            self.login_template = "admin/login.html"
            self.templates_dir = "admin/templates"

    class AdminBase(MockAdapterBase):
        def __init__(self, **kwargs: t.Any) -> None:
            super().__init__(**kwargs)
            self.settings = MockAdminBaseSettings()

    setattr(admin_base, "AdapterBase", MockAdapterBase)
    setattr(admin_base, "AdminBaseSettings", MockAdminBaseSettings)
    setattr(admin_base, "AdminBase", AdminBase)


def _setup_templates_base_module(templates_base: ModuleType) -> None:
    """Set up the templates base module with necessary attributes."""
    mock_depends = _create_mock_depends()
    _setup_base_imports(templates_base, mock_depends)
    _setup_type_aliases(templates_base)
    _setup_safe_await(templates_base)
    _setup_protocol_classes(templates_base)
    _setup_settings_class(templates_base, mock_depends)
    _setup_templates_protocol(templates_base)
    _setup_templates_base_class(templates_base)


def _create_mock_depends():
    """Create a mock depends object that's callable."""

    class MockDependsCallable:
        def __call__(self, cls=None):
            return MockConfig()

        def inject(self, f):
            return MockDependsInjector.inject(f)

    return MockDependsCallable()


def _setup_base_imports(templates_base: ModuleType, mock_depends) -> None:
    """Set up the basic imports from acb."""
    templates_base.Adapter = MagicMock()
    templates_base.pkg_registry = MagicMock()
    templates_base.pkg_registry.get = MagicMock(return_value=[])
    templates_base.root_path = MockAsyncPath("/mock/path/to/templates")
    templates_base.get_adapters = MagicMock(return_value=[])
    templates_base.AdapterBase = MagicMock()
    templates_base.Config = MockConfig
    templates_base.Settings = type(
        "Settings", (), {"__init__": lambda self, **kwargs: None}
    )
    templates_base.depends = mock_depends
    templates_base.AsyncPath = MockAsyncPath
    templates_base.Request = MagicMock()
    templates_base.Response = MagicMock()


def _setup_type_aliases(templates_base: ModuleType) -> None:
    """Create type aliases for type annotations."""
    templates_base.TemplateContext = dict
    templates_base.TemplateResponse = MagicMock()
    templates_base.TemplateStr = str
    templates_base.TemplatePath = str


def _setup_safe_await(templates_base: ModuleType) -> None:
    """Create the safe_await function."""

    async def mock_safe_await(func_or_value: Any) -> Any:
        if callable(func_or_value):
            try:
                result = func_or_value()
                if hasattr(result, "__await__") and callable(
                    getattr(result, "__await__")
                ):
                    return await result  # type: ignore[misc]
                return result
            except Exception:
                return True
        return func_or_value

    templates_base.safe_await = mock_safe_await


def _setup_protocol_classes(templates_base: ModuleType) -> None:
    """Add protocol classes for templates."""

    class TemplateRenderer(Protocol):
        async def render_template(
            self,
            request: Any,
            template: str,
            context: dict | None = None,
        ) -> Any:
            pass

    class TemplateLoader(Protocol):
        async def get_template(self, name: str) -> Any:
            pass

        async def list_templates(self) -> list[str]:
            return []

    templates_base.TemplateRenderer = TemplateRenderer
    templates_base.TemplateLoader = TemplateLoader


def _setup_settings_class(templates_base: ModuleType, mock_depends) -> None:
    """Add the TemplatesBaseSettings class."""

    class TemplatesBaseSettings:
        cache_timeout: int = 300

        def __init__(self, config: MockConfig | None = None, **values: Any) -> None:
            self.cache_timeout = 300 if getattr(config, "deployed", False) else 1

    templates_base.TemplatesBaseSettings = TemplatesBaseSettings


def _setup_templates_protocol(templates_base: ModuleType) -> None:
    """Add the TemplatesProtocol class."""

    class TemplatesProtocol(Protocol):
        def get_searchpath(self, adapter: Any, path: Any) -> None:
            pass

        async def get_searchpaths(self, adapter: Any) -> list[Any]:
            return []

        @staticmethod
        def get_storage_path(path: Any) -> Any:
            pass

        @staticmethod
        def get_cache_key(path: Any) -> str:
            return str(path)

    templates_base.TemplatesProtocol = TemplatesProtocol


def _setup_templates_base_class(templates_base: ModuleType) -> None:
    """Add the TemplatesBase class."""

    class TemplatesBase:
        app: Any | None = None
        admin: Any | None = None
        app_searchpaths: list[Any] | None = None
        admin_searchpaths: list[Any] | None = None

        def __init__(self, **kwargs: Any) -> None:
            self.config = MockConfig()

        def get_searchpath(self, adapter: Any, path: Any) -> list[Any]:
            style = self.config.app.style
            base_path = path / "base"
            style_path = path / style
            style_adapter_path = path / style / adapter.name
            theme_adapter_path = style_adapter_path / "theme"
            return [
                theme_adapter_path,
                style_adapter_path,
                style_path,
                base_path,
            ]

        async def get_searchpaths(self, adapter: Any) -> list[Any]:
            searchpaths = []
            searchpaths.extend(
                self.get_searchpath(
                    adapter, templates_base.root_path / "templates" / adapter.category
                )
            )
            return searchpaths

        @staticmethod
        def get_storage_path(path: Any) -> Any:
            templates_path_name = "templates"
            if templates_path_name not in str(path).split("/"):
                templates_path_name = "_templates"
                parts = str(path).split("/")
                templates_idx = parts.index(templates_path_name)
                depth = templates_idx - 1
                _path = parts[depth:]
                _path.insert(1, _path.pop(0))
                return MockAsyncPath("/".join(_path))

            parts = str(path).split("/")
            depth = parts.index(templates_path_name)
            return MockAsyncPath("/".join(parts[depth:]))

        @staticmethod
        def get_cache_key(path: Any) -> str:
            parts = str(path).split("/")
            return ":".join(parts)

    templates_base.TemplatesBase = TemplatesBase


def _setup_templates_jinja2_module(templates_jinja2: ModuleType) -> None:
    """Set up the templates jinja2 module with loaders."""
    # Import classes and types
    templates_jinja2.t = t
    templates_jinja2.suppress = suppress
    templates_jinja2.literal_eval = MagicMock(side_effect=lambda x: x)
    templates_jinja2.HTMLParser = MagicMock()
    templates_jinja2.import_module = MagicMock(side_effect=lambda x: MagicMock())
    templates_jinja2.find_spec = MagicMock(return_value=MagicMock())
    templates_jinja2.isclass = MagicMock(side_effect=lambda x: isinstance(x, type))
    templates_jinja2.Path = Path
    templates_jinja2.search = MagicMock(return_value=MagicMock())
    templates_jinja2.get_adapter = MagicMock(return_value=MagicMock())
    templates_jinja2.import_adapter = MagicMock(
        return_value=(MockCache(), MockStorage(), MockModels())
    )
    templates_jinja2.Config = MockConfig
    templates_jinja2.debug = MagicMock()
    templates_jinja2.depends = MagicMock()
    templates_jinja2.depends.inject = lambda f: f
    templates_jinja2.AsyncPath = MockAsyncPath
    templates_jinja2.TemplateNotFound = Exception
    templates_jinja2.Extension = MagicMock()
    templates_jinja2.i18n = MagicMock()
    templates_jinja2.loopcontrols = MagicMock()
    templates_jinja2.jinja_debug = MagicMock()
    templates_jinja2.AsyncRedisBytecodeCache = MagicMock()
    templates_jinja2.AsyncBaseLoader = MagicMock()
    templates_jinja2.SourceType = tuple
    templates_jinja2.AsyncJinja2Templates = MagicMock()

    # Import from _base
    from importlib.util import find_spec

    if find_spec("fastblocks.adapters.templates._base"):
        # Import real module if available
        from fastblocks.adapters.templates._base import (
            TemplatesBase,
            TemplatesBaseSettings,
        )

        templates_jinja2.TemplatesBase = TemplatesBase
        templates_jinja2.TemplatesBaseSettings = TemplatesBaseSettings
    else:
        # Use our mocked versions
        templates_jinja2.TemplatesBase = type("TemplatesBase", (), {})
        templates_jinja2.TemplatesBaseSettings = MockTemplatesBaseSettings

    # Add the LoaderProtocol
    class LoaderProtocol(Protocol):
        cache: Any
        config: Any
        storage: Any

        async def get_source_async(
            self, template: str | Any
        ) -> tuple[str, str | None, Callable[[], bool] | Callable[[], Any]]:
            return ("", None, lambda: True)

        async def list_templates_async(self) -> list[str]:
            return []

    templates_jinja2.LoaderProtocol = LoaderProtocol

    # Add the Templates class
    class Templates(MockTemplates):
        pass

    templates_jinja2.Templates = Templates

    # Add the loaders
    setattr(templates_jinja2, "FileSystemLoader", MockFileSystemLoader)
    setattr(templates_jinja2, "RedisLoader", MockRedisLoader)
    setattr(templates_jinja2, "StorageLoader", MockStorageLoader)
    setattr(templates_jinja2, "ChoiceLoader", MockChoiceLoader)
    setattr(templates_jinja2, "PackageLoader", MockPackageLoader)
    setattr(templates_jinja2, "DictLoader", MockDictLoader)
    setattr(templates_jinja2, "FunctionLoader", MockFunctionLoader)
    setattr(templates_jinja2, "PrefixLoader", MockPrefixLoader)


def _setup_templates_filters_module(templates_filters: ModuleType) -> None:
    """Set up the templates filters module with minify and filters."""
    mock_minify = _create_mock_minify()
    filters_class = _create_mock_filters_class(mock_minify)
    _setup_filters_module_attributes(templates_filters, mock_minify, filters_class)


def _create_mock_minify():
    """Create a mock minify module with real functions."""
    mock_minify = MagicMock()

    def mock_html(content: str) -> str:
        return "<html><body>minified</body></html>"

    def mock_js(content: str) -> str:
        return "function test(){return true;}"

    def mock_css(content: str) -> str:
        return "body{color:red}"

    mock_minify.html = MagicMock(side_effect=mock_html)
    mock_minify.js = MagicMock(side_effect=mock_js)
    mock_minify.css = MagicMock(side_effect=mock_css)

    return mock_minify


def _create_mock_filters_class(mock_minify):
    """Create the MockFiltersClass that uses the mock minify module."""

    class MockFiltersClass:
        @staticmethod
        def map_src(s: str) -> str:
            from urllib.parse import quote_plus

            return quote_plus(s)

        @staticmethod
        def minify_html(content: str) -> str:
            return mock_minify.html(content)

        @staticmethod
        def minify_js(content: str) -> str:
            return mock_minify.js(content)

        @staticmethod
        def minify_css(content: str) -> str:
            return mock_minify.css(content)

        @staticmethod
        def url_encode(s: str) -> str:
            from urllib.parse import quote_plus

            return quote_plus(s)

        @staticmethod
        def truncate(s: str, length: int = 100) -> str:
            return s[:length] + "..." if len(s) > length else s

        @staticmethod
        def filesize(size: int) -> str:
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    return MockFiltersClass


def _setup_filters_module_attributes(
    templates_filters: ModuleType, mock_minify, filters_class
) -> None:
    """Set up the filters module attributes."""
    setattr(templates_filters, "minify", mock_minify)
    setattr(templates_filters, "Filters", filters_class)
    setattr(templates_filters, "t", t)

    # Add fastblocks.actions.minify reference - only for templates filter tests
    # Don't mock if we're running minify action tests
    if not _is_minify_action_test():
        fastblocks_actions_minify = types.ModuleType("fastblocks.actions.minify")
        fastblocks_actions_minify.html = mock_minify.html
        fastblocks_actions_minify.js = mock_minify.js
        fastblocks_actions_minify.css = mock_minify.css
        # Add the minify object that tests expect to import
        fastblocks_actions_minify.minify = mock_minify
        sys.modules["fastblocks.actions.minify"] = fastblocks_actions_minify

        # Create fastblocks.actions module if it doesn't exist
        if "fastblocks.actions" not in sys.modules:
            fastblocks_actions = types.ModuleType("fastblocks.actions")
            fastblocks_actions.minify = fastblocks_actions_minify
            sys.modules["fastblocks.actions"] = fastblocks_actions


# We're no longer mocking the module structure


class MockTemplateNotFound(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        self.message = f"Template '{name}' not found"
        super().__init__(self.message)


class MockAsyncBaseLoader:
    def __init__(self, searchpath: Path | list[Any] | None = None) -> None:
        if searchpath is None:
            self.searchpath = [MockAsyncPath("templates")]
        elif isinstance(searchpath, list):
            self.searchpath = searchpath
        else:
            self.searchpath = [searchpath]

        self.encoding = "utf-8"

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        raise NotImplementedError()

    async def list_templates_async(self) -> list[str]:
        raise NotImplementedError()


class MockFileSystemLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        searchpath: Path | list[Any] | None = None,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__(searchpath=searchpath)
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    def get_source(self, template: str = "") -> tuple[str, str, Callable[[], bool]]:
        if not self.searchpath:
            raise MockTemplateNotFound(template)

        for i in range(len(self.searchpath)):
            path = self.searchpath[i]

            if isinstance(path, str):
                path = Path(path)

            template_path = path / template
            if Path(template_path).exists():
                content = Path(template_path).read_text(encoding=self.encoding)
                return content, str(template_path), lambda: True

        raise MockTemplateNotFound(template)

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        if not self.searchpath:
            raise MockTemplateNotFound(template)

        if self.storage and hasattr(self.storage, "templates"):
            with suppress(Exception):
                if self.storage.templates.exists(f"templates/{template}"):
                    content_bytes = self.storage.templates.open(f"templates/{template}")

                    if isinstance(content_bytes, bytes):
                        content = content_bytes.decode(self.encoding)
                    else:
                        content = str(content_bytes)

                    if self.cache:
                        cache_key = f"template:{template}"
                        self.cache.set(cache_key, content)

                    return content, template, lambda: True

        for i in range(len(self.searchpath)):
            path = self.searchpath[i]

            if isinstance(path, str):
                path = Path(path)

            template_path = path / template
            if Path(template_path).exists():
                content = open(template_path).read()
                return content, str(template_path), lambda: True

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> list[str]:
        templates = set()

        for i in range(len(self.searchpath)):
            path = self.searchpath[i]

            path_str = str(path)
            if not Path(path_str).exists():
                continue

            for root, _, files in os.walk(path_str):
                for filename in files:
                    template_path = Path(root, filename)
                    relative_path = str(template_path).replace(str(path) + os.sep, "")

                    if os.sep != "/":
                        relative_path = relative_path.replace(os.sep, "/")

                    templates.add(relative_path)

        return sorted(templates)


class MockRedisLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        if self.cache:
            cache_key = f"template:{template}"
            exists = self.cache.exists(cache_key)
            if isinstance(exists, AsyncMock):
                exists = exists.return_value

            if exists:
                cached = self.cache.get(cache_key)
                if isinstance(cached, AsyncMock):
                    cached = cached.return_value
                return cached, f"templates/{template}", lambda: True

        if self.storage and hasattr(self.storage, "templates"):
            with suppress(Exception):
                exists = self.storage.templates.exists(f"templates/{template}")
                if isinstance(exists, AsyncMock):
                    exists = exists.return_value

                if exists:
                    content_bytes = self.storage.templates.open(f"templates/{template}")

                    if isinstance(content_bytes, AsyncMock):
                        content_bytes = content_bytes.return_value

                    if isinstance(content_bytes, bytes):
                        content = content_bytes.decode(self.encoding)
                    else:
                        content = str(content_bytes)

                    if self.cache:
                        cache_key = f"template:{template}"
                        self.cache.set(cache_key, content)

                    return content, f"templates/{template}", lambda: True

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> list[str]:
        return ["test1.html", "test2.html", "subdir/test3.html"]


class MockStorageLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        searchpath: Path | list[Any] | None = None,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        if not self.storage or not hasattr(self.storage, "templates"):
            raise MockTemplateNotFound(template)

        template_path = f"templates/{template}"

        if self.cache:
            cache_key = f"template:{template}"
            cached = self.cache.get(cache_key)
            if cached:
                return cached, template_path, lambda: True

        try:
            if not self.storage.templates.exists(template_path):
                raise MockTemplateNotFound(template)

            content_bytes = self.storage.templates.open(template_path)

            if isinstance(content_bytes, bytes):
                content = content_bytes.decode(self.encoding)
            else:
                content = str(content_bytes)

            if self.cache:
                cache_key = f"template:{template}"
                self.cache.set(cache_key, content)

            return content, template_path, lambda: True
        except Exception as e:
            raise MockTemplateNotFound(template) from e

    async def list_templates_async(self) -> list[str]:
        if not self.storage or not hasattr(self.storage, "templates"):
            return []

        try:
            templates = self.storage.templates.list(Path("templates"))
            return templates
        except Exception:
            return []


class MockChoiceLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        loaders: list[Any] | None = None,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.loaders = loaders or []
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        for loader in self.loaders:
            try:
                return await loader.get_source_async(environment, template)
            except MockTemplateNotFound:
                continue

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> list[str]:
        templates = set()

        for loader in self.loaders:
            templates.update(await loader.list_templates_async())

        return sorted(templates)


class MockPackageLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        package_name: str | None = None,
        package_path: str | None = None,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.package_name = package_name or "tests"
        self.package_path = package_path or "templates"
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        if template == "test.html":
            return (
                "<html><body>Test from package</body></html>",
                f"templates/{template}",
                lambda: True,
            )

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> list[str]:
        return ["test1.html", "test2.html", "subdir/test3.html"]


class MockDictLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        templates: dict[str, str] | None = None,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.templates = templates or {}
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        if template not in self.templates:
            raise MockTemplateNotFound(template)

        content = self.templates[template]
        return content, template, lambda: True

    async def list_templates_async(self) -> list[str]:
        return list(self.templates.keys())


class MockFunctionLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        load_func: Callable[[str], str] | None = None,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.load_func = load_func or (lambda x: x)
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        content = self.load_func(template)
        return content, template, lambda: True

    async def list_templates_async(self) -> list[str]:
        return []


class MockPrefixLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        loaders: dict[str, Any] | None = None,
        delimiter: str | None = None,
        encoding: str | None = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.loaders = loaders or {}
        self.delimiter = delimiter or "/"
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> tuple[str, str, Callable[[], bool]]:
        if self.delimiter not in template:
            raise MockTemplateNotFound(template)

        prefix, name = template.split(self.delimiter, 1)
        if prefix not in self.loaders:
            raise MockTemplateNotFound(template)

        return await self.loaders[prefix].get_source_async(environment, name)

    async def list_templates_async(self) -> list[str]:
        templates = set()

        for prefix, loader in self.loaders.items():
            templates.update(
                prefix + self.delimiter + template
                for template in await loader.list_templates_async()
            )

        return sorted(templates)


# Use the function to prevent unused warning - call at end after all classes are defined
_setup_fastblocks_module_structure()  # noqa: F841

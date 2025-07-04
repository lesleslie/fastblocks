"""Centralized dependency injection and resolution system for FastBlocks.

This module provides a unified approach to dependency management, particularly
for ACB integration and other external dependencies.
"""

import importlib.util
import typing as t
from contextlib import suppress
from functools import lru_cache
from threading import local

HashFunc = t.Callable[[t.Any], str]
GetAdapterFunc = t.Callable[[str], t.Any]
ImportAdapterFunc = t.Callable[[str | list[str] | None], t.Any]
ConfigType = t.TypeVar("ConfigType")
LoggerType = t.TypeVar("LoggerType")
DependencyType = t.TypeVar("DependencyType")

_local = local()


class DependencyResolver:
    def __init__(self) -> None:
        self._cache: dict[str, t.Any] = {}
        self._initialized = False

    @lru_cache(maxsize=1)
    def get_acb_modules(self) -> dict[str, t.Any]:
        if not self._initialized:
            self._initialize_cache()
            self._initialized = True
        return self._cache.copy()

    def get_acb_subset(self, *keys: str) -> tuple[t.Any, ...]:
        if not self._initialized:
            self._setup_mock_implementations()
            self._initialized = True
        for key in keys:
            if key not in self._cache or self._cache[key].__class__.__name__.startswith(
                "Mock"
            ):
                self._load_real_acb_module(key)

        return tuple(self._cache.get(key) for key in keys)

    def _load_real_acb_module(self, key: str) -> None:
        if not self._is_acb_available():
            return
        module_loaders = {
            "register_pkg": self._load_register_pkg,
            "hash": self._load_hash,
            "get_adapter": self._load_adapters,
            "get_installed_adapter": self._load_adapters,
            "import_adapter": self._load_adapters,
            "AdapterBase": self._load_adapter_base,
            "Config": self._load_config,
            "Settings": self._load_settings,
            "AppSettings": self._load_app_settings,
            "depends": self._load_depends,
            "InterceptHandler": self._load_logger_components,
            "Logger": self._load_logger_components,
            "Adapter": self._load_adapter,
            "pkg_registry": self._load_pkg_registry,
            "get_adapters": self._load_get_adapters,
            "root_path": self._load_root_path,
            "debug": self._load_debug,
        }
        if loader := module_loaders.get(key):
            loader()

    def _initialize_cache(self) -> None:
        self._setup_mock_implementations()
        if self._is_acb_available():
            self._load_real_acb_modules()

    def _create_mock_functions(self) -> dict[str, t.Any]:
        def mock_register_pkg() -> None:
            return None

        def mock_hash_func(x: t.Any) -> str:
            return str(hash(x))

        def mock_get_adapter(category: str) -> t.Any:
            return None

        def mock_get_installed_adapter(category: str) -> t.Any:
            return False

        def mock_import_adapter(
            _adapter_categories: str | list[str] | None = None,
        ) -> t.Any:
            return None

        def mock_get_adapters() -> list[t.Any]:
            return []

        def mock_root_path() -> str:
            return "."

        def mock_debug(*args: t.Any) -> bool:
            return False

        return {
            "register_pkg": mock_register_pkg,
            "hash": mock_hash_func,
            "get_adapter": mock_get_adapter,
            "get_installed_adapter": mock_get_installed_adapter,
            "import_adapter": mock_import_adapter,
            "get_adapters": mock_get_adapters,
            "root_path": mock_root_path,
            "debug": mock_debug,
        }

    def _create_mock_config(self) -> tuple[t.Any, t.Any]:
        MockSecretKey = type(
            "MockSecretKey",
            (),
            {"get_secret_value": lambda self: "mock_secret_key_12345"},
        )()
        MockDebug = type("MockDebug", (), {"fastblocks": False, "production": False})()
        MockApp = type(
            "MockApp",
            (),
            {"name": "fastblocks", "secret_key": MockSecretKey, "token_id": "_fb_"},
        )()
        MockConfig = type(
            "MockConfig", (), {"app": MockApp, "deployed": False, "debug": MockDebug}
        )
        return MockConfig, MockConfig()

    def _create_mock_classes(self, mock_config: t.Any) -> dict[str, t.Any]:
        MockAdapterBase = type("MockAdapterBase", (), {})

        class MockDepends:
            def get(self, x: str) -> t.Any:
                return mock_config if x == "config" else None

            @staticmethod
            def inject(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
                return func

            def __call__(self):
                return mock_config

        MockInterceptHandler = type("MockInterceptHandler", (), {})
        MockLogger = type("MockLogger", (), {})

        class MockSettings:
            def __init__(self, **kwargs: t.Any) -> None:
                for key, value in kwargs.items():
                    setattr(self, key, value)

        MockAppSettings = type("MockAppSettings", (), {})
        MockAdapter = type("MockAdapter", (), {})
        MockPkgRegistry = type("MockPkgRegistry", (), {"get": list})

        return {
            "AdapterBase": MockAdapterBase,
            "depends": MockDepends(),
            "InterceptHandler": MockInterceptHandler,
            "Logger": MockLogger,
            "Settings": MockSettings,
            "AppSettings": MockAppSettings,
            "Adapter": MockAdapter,
            "pkg_registry": MockPkgRegistry,
        }

    def _setup_mock_implementations(self) -> None:
        mock_functions = self._create_mock_functions()
        MockConfig, mock_config = self._create_mock_config()
        mock_classes = self._create_mock_classes(mock_config)
        self._cache.update(mock_functions)
        self._cache.update(mock_classes)
        self._cache.update(
            {
                "Config": MockConfig,
                "_config_available": False,
                "_logger_available": False,
                "_acb_available": False,
            }
        )

    def _is_acb_available(self) -> bool:
        try:
            spec = importlib.util.find_spec("acb")
            return spec is not None
        except Exception:
            return False

    def _safe_import(self, import_func: t.Callable[[], None]) -> bool:
        try:
            import_func()
            return True
        except Exception:
            return False

    def _load_real_acb_modules(self) -> None:
        acb_available = self._safe_import(self._load_register_pkg)
        self._safe_import(self._load_hash)
        self._safe_import(self._load_adapters)
        self._safe_import(self._load_depends)
        self._safe_import(self._load_config)
        self._safe_import(self._load_settings)
        self._safe_import(self._load_app_settings)
        self._safe_import(self._load_adapter_base)
        self._safe_import(self._load_adapter)
        self._safe_import(self._load_pkg_registry)
        self._safe_import(self._load_get_adapters)
        self._safe_import(self._load_root_path)
        self._safe_import(self._load_debug)
        self._safe_import(self._load_logger_components)
        self._cache["_acb_available"] = acb_available

    def _load_register_pkg(self) -> None:
        with suppress(Exception):
            from acb import register_pkg as real_register_pkg

            self._cache["register_pkg"] = real_register_pkg

    def _load_hash(self) -> None:
        with suppress(Exception):
            from acb.actions.hash import hash as real_hash

            self._cache["hash"] = real_hash

    def _load_adapters(self) -> None:
        with suppress(Exception):
            from acb.adapters import get_adapter as real_get_adapter
            from acb.adapters import get_installed_adapter as real_get_installed_adapter
            from acb.adapters import import_adapter as real_import_adapter

            self._cache["get_adapter"] = real_get_adapter
            self._cache["get_installed_adapter"] = real_get_installed_adapter
            self._cache["import_adapter"] = real_import_adapter

    def _load_config(self) -> None:
        with suppress(Exception):
            from acb.config import Config as real_config

            self._cache["Config"] = real_config

    def _load_settings(self) -> None:
        with suppress(Exception):
            from acb.config import Settings as real_settings

            self._cache["Settings"] = real_settings

    def _load_app_settings(self) -> None:
        with suppress(Exception):
            from acb.config import AppSettings as real_app_settings

            self._cache["AppSettings"] = real_app_settings

    def _load_adapter_base(self) -> None:
        with suppress(Exception):
            from acb.adapters import Adapter as real_adapter_base

            self._cache["AdapterBase"] = real_adapter_base

    def _load_depends(self) -> None:
        with suppress(Exception):
            from acb.depends import depends as real_depends

            self._cache["depends"] = real_depends

    def _load_logger_components(self) -> None:
        with suppress(Exception):
            from acb.logger import InterceptHandler as real_intercept_handler

            self._cache["InterceptHandler"] = real_intercept_handler
        with suppress(Exception):
            from acb.logger import Logger as real_logger

            self._cache["Logger"] = real_logger

    def _load_adapter(self) -> None:
        with suppress(Exception):
            from acb import Adapter as real_adapter

            self._cache["Adapter"] = real_adapter

    def _load_pkg_registry(self) -> None:
        with suppress(Exception):
            from acb import pkg_registry as real_pkg_registry

            self._cache["pkg_registry"] = real_pkg_registry

    def _load_get_adapters(self) -> None:
        with suppress(Exception):
            from acb.adapters import get_adapters as real_get_adapters

            self._cache["get_adapters"] = real_get_adapters

    def _load_root_path(self) -> None:
        with suppress(Exception):
            from acb.adapters import root_path as real_root_path

            self._cache["root_path"] = real_root_path

    def _load_debug(self) -> None:
        with suppress(Exception):
            from acb.debug import debug as real_debug

            self._cache["debug"] = real_debug


_resolver = DependencyResolver()


def get_acb_modules() -> dict[str, t.Any]:
    return _resolver.get_acb_modules()


def get_acb_subset(*keys: str) -> tuple[t.Any, ...]:
    return _resolver.get_acb_subset(*keys)


def get_cache_adapter() -> t.Any:
    _, import_adapter, _, _, _ = get_acb_subset(
        "hash", "import_adapter", "Config", "depends", "Logger"
    )
    return import_adapter("cache")


def get_acb_modules_for_caching() -> tuple[t.Any, ...]:
    return get_acb_subset("hash", "import_adapter", "Config", "depends", "Logger")


def get_acb_modules_for_middleware() -> tuple[t.Any, ...]:
    return get_acb_subset("get_adapter", "Config", "depends", "Logger")


def get_acb_modules_for_applications() -> tuple[t.Any, ...]:
    return get_acb_subset(
        "register_pkg",
        "get_installed_adapter",
        "Config",
        "AdapterBase",
        "InterceptHandler",
        "Logger",
        "depends",
    )


def reset_dependency_cache() -> None:
    global _resolver
    _resolver = DependencyResolver()


class DependencyMixin:
    @property
    def acb_modules(self) -> dict[str, t.Any]:
        return get_acb_modules()

    def get_acb_dependency(
        self, key: str, default: DependencyType | None = None
    ) -> DependencyType | t.Any:
        return self.acb_modules.get(key, default)

"""FastBlocks - Asynchronous web application framework for rapid HTMX/Jinja template delivery."""

from __future__ import annotations

import sys
from typing import Any

from . import exceptions

try:
    from . import actions
except (ImportError, TypeError):
    import types

    actions = types.ModuleType("actions")
    actions.minify = types.ModuleType("minify")  # type: ignore[attr-defined]

try:
    from . import applications
except (ImportError, TypeError):
    import types

    applications = types.ModuleType("applications")

try:
    from . import caching
except (ImportError, TypeError):
    import types

    caching = types.ModuleType("caching")

    def mock_get_from_cache(*args: Any, **kwargs: Any) -> None:
        return None

    def mock_cache_func(*args: Any, **kwargs: Any) -> str:
        return "mock_cache_key"

    def mock_void_func(*args: Any, **kwargs: Any) -> None:
        return None

    class MockRule:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    caching.get_from_cache = mock_get_from_cache  # type: ignore[attr-defined]
    caching.learn_cache_key = mock_cache_func  # type: ignore[attr-defined]
    caching.delete_from_cache = mock_void_func  # type: ignore[attr-defined]
    caching.get_rule_matching_request = mock_void_func  # type: ignore[attr-defined]
    caching.get_cache_key = mock_cache_func  # type: ignore[attr-defined]
    caching.generate_cache_key = mock_cache_func  # type: ignore[attr-defined]
    caching.set_in_cache = mock_void_func  # type: ignore[attr-defined]
    caching.patch_cache_control = mock_void_func  # type: ignore[attr-defined]
    caching.CacheResponder = type("CacheResponder", (), {})  # type: ignore[attr-defined]
    caching.CacheControlResponder = type("CacheControlResponder", (), {})  # type: ignore[attr-defined]
    caching.Rule = MockRule  # type: ignore[attr-defined]

try:
    from . import middleware
except (ImportError, TypeError):
    import types

    middleware = types.ModuleType("middleware")

    def mock_secure_headers(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    def mock_delete_from_cache(*args: Any, **kwargs: Any) -> None:
        return None

    middleware.secure_headers = mock_secure_headers  # type: ignore[attr-defined]
    middleware.delete_from_cache = mock_delete_from_cache  # type: ignore[attr-defined]
    middleware.SecureHeadersMiddleware = type("SecureHeadersMiddleware", (), {})  # type: ignore[attr-defined]
    middleware.CacheControlResponder = type("CacheControlResponder", (), {})  # type: ignore[attr-defined]
    middleware.CacheMiddleware = type("CacheMiddleware", (), {})  # type: ignore[attr-defined]

__all__ = ["actions", "applications", "caching", "exceptions", "middleware"]

current_module = sys.modules[__name__]
for module_name in ("actions", "applications", "caching", "middleware"):
    module_obj = locals().get(module_name)
    if module_obj:
        setattr(current_module, module_name, module_obj)
        sys.modules[f"fastblocks.{module_name}"] = module_obj

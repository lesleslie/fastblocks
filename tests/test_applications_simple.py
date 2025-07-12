"""Simple application tests."""

import sys
import types
from unittest.mock import MagicMock

# Mock ACB modules before importing
acb_module = types.ModuleType("acb")
acb_config_module = types.ModuleType("acb.config")
acb_depends_module = types.ModuleType("acb.depends")

# Mock classes
acb_config_module.AdapterBase = type("AdapterBase", (object,), {})  # type: ignore[attr-defined]

# Mock depends
mock_depends = MagicMock()
mock_depends.get = MagicMock(return_value=MagicMock())
acb_depends_module.depends = mock_depends  # type: ignore[attr-defined]

# Register modules
sys.modules["acb"] = acb_module
sys.modules["acb.config"] = acb_config_module
sys.modules["acb.depends"] = acb_depends_module

from fastblocks.applications import FastBlocksSettings, MiddlewareManager
from fastblocks.middleware import MiddlewarePosition


def test_fastblocks_settings_init_subclass() -> None:
    """Test FastBlocksSettings.__init_subclass__."""

    class TestSettings(FastBlocksSettings):
        pass

    # Should have AdapterBase in bases
    assert any(base.__name__ == "AdapterBase" for base in TestSettings.__bases__)


def test_middleware_manager_init() -> None:
    """Test MiddlewareManager initialization."""
    manager = MiddlewareManager()

    assert isinstance(manager._system_middleware, dict)
    assert manager._middleware_stack_cache is None
    assert isinstance(manager.user_middleware, list)
    assert not manager.user_middleware


def test_middleware_manager_add_user_middleware() -> None:
    """Test MiddlewareManager.add_user_middleware."""
    manager = MiddlewareManager()
    mock_middleware_class = MagicMock()

    manager.add_user_middleware(mock_middleware_class, arg1="value1")

    assert len(manager.user_middleware) == 1
    assert manager._middleware_stack_cache is None


def test_middleware_manager_add_system_middleware() -> None:
    """Test MiddlewareManager.add_system_middleware."""
    manager = MiddlewareManager()
    mock_middleware_class = MagicMock()

    manager.add_system_middleware(
        mock_middleware_class,
        MiddlewarePosition.COMPRESSION,
        option1="value1",
    )

    assert MiddlewarePosition.COMPRESSION in manager._system_middleware
    assert manager._middleware_stack_cache is None


def test_middleware_manager_get_middleware_stack() -> None:
    """Test MiddlewareManager.get_middleware_stack."""
    stack = MiddlewareManager().get_middleware_stack()

    assert isinstance(stack, dict)
    assert "user_middleware" in stack
    assert "system_middleware" in stack
    assert isinstance(stack["user_middleware"], list)
    assert isinstance(stack["system_middleware"], dict)


def test_middleware_manager_extract_middleware_info() -> None:
    """Test MiddlewareManager._extract_middleware_info."""
    manager = MiddlewareManager()

    # Test with a mock object
    mock_middleware = MagicMock()
    mock_middleware.__class__.__name__ = "TestMiddleware"

    info = manager._extract_middleware_info(mock_middleware)

    assert isinstance(info, dict)
    assert "class" in info


def test_middleware_position_enum_values() -> None:
    """Test MiddlewarePosition enum values."""
    assert MiddlewarePosition.CSRF.value == 0
    assert MiddlewarePosition.SESSION.value == 1
    assert MiddlewarePosition.HTMX.value == 2
    assert MiddlewarePosition.CURRENT_REQUEST.value == 3
    assert MiddlewarePosition.COMPRESSION.value == 4
    assert MiddlewarePosition.SECURITY_HEADERS.value == 5


def test_middleware_position_names() -> None:
    """Test MiddlewarePosition enum names."""
    assert MiddlewarePosition.CSRF.name == "CSRF"
    assert MiddlewarePosition.SESSION.name == "SESSION"
    assert MiddlewarePosition.HTMX.name == "HTMX"
    assert MiddlewarePosition.CURRENT_REQUEST.name == "CURRENT_REQUEST"
    assert MiddlewarePosition.COMPRESSION.name == "COMPRESSION"
    assert MiddlewarePosition.SECURITY_HEADERS.name == "SECURITY_HEADERS"

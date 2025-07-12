"""Test caching constants and basic functionality."""

import sys
import types
from unittest.mock import MagicMock

import pytest

# Mock ACB modules before importing
acb_module = types.ModuleType("acb")
acb_depends_module = types.ModuleType("acb.depends")

# Mock depends
mock_depends = MagicMock()
mock_depends.get = MagicMock(return_value=MagicMock())
acb_depends_module.depends = mock_depends  # type: ignore[attr-defined]

# Register modules
sys.modules["acb"] = acb_module
sys.modules["acb.depends"] = acb_depends_module

from fastblocks.caching import (
    CacheDirectives,
    CacheUtils,
    cacheable_methods,
    cacheable_status_codes,
    invalidating_methods,
)


def test_cacheable_methods() -> None:
    """Test cacheable methods constant."""
    assert isinstance(cacheable_methods, frozenset)
    assert "GET" in cacheable_methods
    assert "HEAD" in cacheable_methods
    # OPTIONS may not be in cacheable methods in all implementations


def test_cacheable_status_codes() -> None:
    """Test cacheable status codes constant."""
    assert isinstance(cacheable_status_codes, frozenset)
    assert 200 in cacheable_status_codes
    assert 301 in cacheable_status_codes
    assert 404 in cacheable_status_codes


def test_invalidating_methods() -> None:
    """Test invalidating methods constant."""
    assert isinstance(invalidating_methods, frozenset)
    assert "POST" in invalidating_methods
    assert "PUT" in invalidating_methods
    assert "DELETE" in invalidating_methods
    assert "PATCH" in invalidating_methods


def test_cache_directives_creation() -> None:
    """Test CacheDirectives creation."""
    directives = CacheDirectives()

    # Check that it's a dict-like object
    assert isinstance(directives, dict)


def test_cache_utils_creation() -> None:
    """Test CacheUtils creation."""
    cache_utils = CacheUtils()

    # Check that it has expected attributes
    assert hasattr(cache_utils, "__dict__")
    assert isinstance(cache_utils.__dict__, dict)


def test_cache_directives_with_values() -> None:
    """Test CacheDirectives with values."""
    directives = CacheDirectives(max_age=3600, private=True, no_cache=False)

    # Should have the keys set
    assert directives.get("max_age") == 3600
    assert directives.get("private") is True
    assert directives.get("no_cache") is False


def test_cache_utils_safe_log() -> None:
    """Test CacheUtils safe_log method."""
    mock_logger = MagicMock()

    # Test that safe_log exists and is callable
    assert hasattr(CacheUtils, "safe_log")
    assert callable(CacheUtils.safe_log)

    # Test calling safe_log
    CacheUtils.safe_log(mock_logger, "info", "test message")


def test_cache_constants_types() -> None:
    """Test that cache constants are correct types."""
    # Test types
    assert isinstance(cacheable_methods, frozenset)
    assert isinstance(cacheable_status_codes, frozenset)
    assert isinstance(invalidating_methods, frozenset)

    # Test they're not empty
    assert cacheable_methods
    assert cacheable_status_codes
    assert invalidating_methods


def test_cache_directives_immutability() -> None:
    """Test that cache constants are immutable."""
    # frozenset should be immutable
    with pytest.raises(AttributeError):
        cacheable_methods.add("NEW_METHOD")  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        cacheable_status_codes.add(999)  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        invalidating_methods.add("NEW_METHOD")  # type: ignore[attr-defined]
